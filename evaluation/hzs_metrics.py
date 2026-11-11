# -*- coding: utf-8 -*-
"""HZS 任务导向评测核心（框架无关）

设计要点
========
1. 输入只有两样：COCO 格式的 GT，和本模块定义的 prediction dump 包装格式。
   RF-DETR / RT-DETR 各自只负责「把模型输出导出成 dump」，**所有指标都由本模块计算**。
   两个框架走的是同一份匹配代码，跨框架可比性由代码结构保证，不靠人工纪律维持。

2. 预测在**低阈值**下导出一次（dump_score_threshold，默认 0.01）；
   confidence_threshold 在**指标计算时**才施加。
   好处：调阈值不需要重跑模型；在 val 上调出来的阈值可以原样套到 test，
   且 test 上不存在「扫阈值取最大 F1」的操作空间 —— 从流程上杜绝了 test 泄漏。

3. task_iou_threshold / confidence_threshold 一律来自配置文件，不硬编码。

4. 三组指标（对应 E:/HZS/自定义指标.txt）：
     任务导向   : P/R/F1 @ task_iou_threshold 与 @0.50，整体 + per-class
     标准 COCO  : AP50 / AP75 / AP50:95（pycocotools，定义不改）
     场景级     : image_AP / image_P / image_R / image_F1（runway/railway/solar_farm）
   **不合成任何加权总分。**

5. 匹配口径（严格按需求文档）：
     仅 score >= confidence_threshold 的预测参与；
     同类才可匹配；一对一；按置信度降序贪心；
     IoU >= task_iou_threshold 记 TP；未匹配预测记 FP；未匹配 GT 记 FN。
     不使用 IoU>0。

用法
====
    python hzs_metrics.py --config hzs_metrics_config.yaml \
        --gt  <instances_test.json> \
        --dump <predictions.json> \
        --out  <report.json> [--md <report.md>] [--model-name RF-DETR]
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
import datetime

import numpy as np

# ----------------------------------------------------------------------------
# 基础工具
# ----------------------------------------------------------------------------


def log(*a):
    print(*a)
    sys.stdout.flush()


def xywh_to_xyxy(b):
    x, y, w, h = b
    return [x, y, x + w, y + h]


def _iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a:(N,4) b:(M,4) xyxy -> (N,M) IoU"""
    if a.size == 0 or b.size == 0:
        return np.zeros((a.shape[0], b.shape[0]), dtype=np.float64)
    lt = np.maximum(a[:, None, :2], b[None, :, :2])
    rb = np.minimum(a[:, None, 2:], b[None, :, 2:])
    wh = np.clip(rb - lt, 0, None)
    inter = wh[..., 0] * wh[..., 1]
    area_a = np.clip(a[:, 2] - a[:, 0], 0, None) * np.clip(a[:, 3] - a[:, 1], 0, None)
    area_b = np.clip(b[:, 2] - b[:, 0], 0, None) * np.clip(b[:, 3] - b[:, 1], 0, None)
    union = area_a[:, None] + area_b[None, :] - inter
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(union > 0, inter / union, 0.0)
    return out


def _safe_div(a, b):
    return float(a) / float(b) if b else float("nan")


def _f1(p, r):
    if p is None or r is None or math.isnan(p) or math.isnan(r):
        return float("nan")
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


# ----------------------------------------------------------------------------
# 载入
# ----------------------------------------------------------------------------


def load_gt(path):
    d = json.load(io.open(path, encoding="utf-8"))
    return d


def load_dump(path):
    d = json.load(io.open(path, encoding="utf-8"))
    if "predictions" not in d:
        # 容错：也接受纯 COCO results 列表
        d = {"predictions": d, "image_ids": sorted(set(p["image_id"] for p in d)),
             "meta": {}}
    return d


def assert_test_set_identity(gt, dump, gt_path, dump_path, strict=True):
    """核心护栏：prediction 的 image_id 必须与 GT 的 image_id 完全一致。

    需求原文：「如果检测到 prediction image IDs 与 test GT image IDs 不匹配，
              应直接报错而不是继续计算。」

    这里用**严格相等**而非子集，是因为 dumper 被要求为**每一张** test 图都写下
    一条记录（哪怕该图没有任何预测）。因此集合不等就直接说明：
      - dumper 漏跑了图，或
      - 预测来自另一个 split / 另一版 GT。
    两种情况都必须停下来。
    """
    gt_ids = set(i["id"] for i in gt["images"])
    pred_ids = set(int(x) for x in dump.get("image_ids", []))
    only_pred = pred_ids - gt_ids
    only_gt = gt_ids - pred_ids

    if only_pred or only_gt:
        msg = [
            "",
            "!! 评测中止：prediction 与 GT 的 image_id 不一致 !!",
            "   GT   : %s  (%d 张)" % (gt_path, len(gt_ids)),
            "   dump : %s  (%d 张)" % (dump_path, len(pred_ids)),
            "   只在 dump 里出现的 image_id : %d 个 %s"
            % (len(only_pred), sorted(only_pred)[:10]),
            "   只在 GT   里出现的 image_id : %d 个 %s"
            % (len(only_gt), sorted(only_gt)[:10]),
            "   常见原因：dumper 指向了别的 split、GT 与 dump 不是同一版数据集、"
            "或 dumper 静默跳过了若干图片。",
        ]
        if strict:
            raise SystemExit("\n".join(msg))
        log("\n".join(msg))
    return len(only_pred) == 0 and len(only_gt) == 0


def assert_class_mapping(gt, class_names, strict=True):
    """模型的类别顺序必须与 GT categories 的名称顺序一致，否则 category_id 会错位。"""
    cats = sorted(gt["categories"], key=lambda c: c["id"])
    gt_names = [c["name"] for c in cats]
    gt_ids = [c["id"] for c in cats]
    if class_names is None:
        return gt_ids
    if list(class_names) != gt_names:
        msg = [
            "",
            "!! 评测中止：模型类别顺序与 GT categories 不一致 !!",
            "   GT   : %s" % gt_names,
            "   模型 : %s" % list(class_names),
            "   若名称相同但次序不同，category_id 会整体错位。",
        ]
        if strict:
            raise SystemExit("\n".join(msg))
        log("\n".join(msg))
    # 返回 模型索引 -> category_id 的映射
    name2id = dict(zip(gt_names, gt_ids))
    return [name2id[n] for n in class_names]


# ----------------------------------------------------------------------------
# 任务导向匹配
# ----------------------------------------------------------------------------


def match_one_to_one(gt_boxes, pred_boxes, iou_thr):
    """单张图、单个类别内的一对一匹配。

    gt_boxes  : (G,4) xyxy
    pred_boxes: (P,4) xyxy，调用方须已按置信度**降序**排好
    返回 (tp_idx, fp_idx, fn_idx, iou_of_tp)
    """
    G, P = len(gt_boxes), len(pred_boxes)
    if G == 0 and P == 0:
        return [], [], [], np.zeros(0)
    iou = _iou_matrix(np.asarray(pred_boxes, dtype=np.float64).reshape(-1, 4),
                      np.asarray(gt_boxes, dtype=np.float64).reshape(-1, 4)) \
        if P and G else np.zeros((P, G))

    gt_taken = np.zeros(G, dtype=bool)
    tp, fp, ious = [], [], []
    for pi in range(P):
        if G == 0:
            fp.append(pi)
            continue
        row = iou[pi].copy()
        row[gt_taken] = -1.0
        gi = int(np.argmax(row))
        if row[gi] >= iou_thr:
            gt_taken[gi] = True
            tp.append(pi)
            ious.append(float(row[gi]))
        else:
            fp.append(pi)
    fn = [gi for gi in range(G) if not gt_taken[gi]]
    return tp, fp, fn, np.asarray(ious, dtype=np.float64)


def evaluate_task(gt, preds, conf_thr, iou_thr, cat_ids, cat_names):
    """在给定 (confidence_threshold, iou_threshold) 下算 TP/FP/FN 与 P/R/F1。"""
    id2img = {i["id"]: i for i in gt["images"]}
    gt_by = {}          # (img, cls) -> [xyxy]
    gt_area = {}        # (img, cls) -> [area]
    for a in gt["annotations"]:
        k = (a["image_id"], a["category_id"])
        gt_by.setdefault(k, []).append(xywh_to_xyxy(a["bbox"]))
        gt_area.setdefault(k, []).append(float(a.get("area", 0.0)))

    # 过滤置信度、按 (img, cls) 分组、组内按分数降序
    pred_by = {}
    for p in preds:
        if p["score"] < conf_thr:
            continue
        pred_by.setdefault((p["image_id"], p["category_id"]), []).append(p)
    for k in pred_by:
        pred_by[k].sort(key=lambda x: -x["score"])

    per = {c: {"TP": 0, "FP": 0, "FN": 0, "iou_sum": 0.0, "n_gt": 0}
           for c in cat_ids}
    for c in cat_ids:
        for iid in id2img:
            g = gt_by.get((iid, c), [])
            p = pred_by.get((iid, c), [])
            per[c]["n_gt"] += len(g)
            # 预测的 bbox 存的是 COCO 的 xywh，必须转成 xyxy 才能和 g 比。
            # 漏掉这一步会把 xywh 当 xyxy 用：大框偶尔还能过阈值，
            # 小框退化成无效框永远匹配不上（railway 正常、airplane 为 0）。
            tp, fp, fn, ious = match_one_to_one(
                g, [xywh_to_xyxy(q["bbox"]) for q in p], iou_thr)
            per[c]["TP"] += len(tp)
            per[c]["FP"] += len(fp)
            per[c]["FN"] += len(fn)
            if ious.size:
                per[c]["iou_sum"] += float(ious.sum())

    rows = {}
    for c in cat_ids:
        d = per[c]
        P = _safe_div(d["TP"], d["TP"] + d["FP"])
        R = _safe_div(d["TP"], d["TP"] + d["FN"])
        rows[cat_names[c]] = {
            "TP": d["TP"], "FP": d["FP"], "FN": d["FN"],
            "n_gt": d["n_gt"],
            "precision": P, "recall": R, "F1": _f1(P, R),
            "mean_iou_of_TP": _safe_div(d["iou_sum"], d["TP"]),
        }

    TP = sum(per[c]["TP"] for c in cat_ids)
    FP = sum(per[c]["FP"] for c in cat_ids)
    FN = sum(per[c]["FN"] for c in cat_ids)
    micro_p, micro_r = _safe_div(TP, TP + FP), _safe_div(TP, TP + FN)

    valid = [v for v in rows.values() if not math.isnan(v["F1"])]
    overall = {
        "TP": TP, "FP": FP, "FN": FN,
        "precision": micro_p, "recall": micro_r, "F1": _f1(micro_p, micro_r),
        "macro_precision": float(np.mean([v["precision"] for v in valid])) if valid else float("nan"),
        "macro_recall": float(np.mean([v["recall"] for v in valid])) if valid else float("nan"),
        "macro_F1": float(np.mean([v["F1"] for v in valid])) if valid else float("nan"),
    }
    return overall, rows


# ----------------------------------------------------------------------------
# 标准 COCO AP（定义不改，直接交给 pycocotools）
# ----------------------------------------------------------------------------


def evaluate_coco_ap(gt_path, preds, cat_ids, cat_names):
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    coco_gt = COCO(gt_path)
    results = [{"image_id": int(p["image_id"]), "category_id": int(p["category_id"]),
                "bbox": [float(v) for v in p["bbox"]], "score": float(p["score"])}
               for p in preds]

    if not results:
        nan = float("nan")
        empty = {c: {"AP50": nan, "AP75": nan, "AP50_95": nan} for c in cat_ids}
        return {"AP50": nan, "AP75": nan, "AP50_95": nan, "AP_all_classes": nan}, empty, {}

    with open(os.devnull, "w") as devnull:
        import contextlib
        with contextlib.redirect_stdout(devnull):
            coco_dt = coco_gt.loadRes(results)
            ev = COCOeval(coco_gt, coco_dt, "bbox")
            ev.evaluate()
            ev.accumulate()
            # ev.stats 是 summarize() 填的，不调它 stats 就是空的。
            # 标准 COCO 12 项定义（summarize 内部顺序）：
            #   [0] AP@[.50:.95]  [1] AP50  [2] AP75
            #   [3..5] AP small/medium/large
            #   [6..8] AR@1/10/100   [9..11] AR small/medium/large
            ev.summarize()

    iou_thrs = np.asarray(ev.params.iouThrs)
    t50 = int(np.argmin(np.abs(iou_thrs - 0.50)))
    t75 = int(np.argmin(np.abs(iou_thrs - 0.75)))
    s = np.asarray(ev.stats, dtype=np.float64)
    if s.size < 12:
        raise SystemExit(
            "!! COCOeval 的 stats 只有 %d 项（应 12 项），summarize() 未生效。" % s.size)

    overall = {"AP50": float(s[1]), "AP75": float(s[2]), "AP50_95": float(s[0]),
               "AR100": float(s[8])}

    prec = ev.eval["precision"]        # (T, R, K, A, M)
    cats_eval = list(ev.params.catIds)
    per = {}
    for c in cat_ids:
        if c not in cats_eval:
            per[cat_names[c]] = {"AP50": float("nan"), "AP75": float("nan"),
                                 "AP50_95": float("nan"), "n_gt": 0}
            continue
        k = cats_eval.index(c)
        def _ap(t_idx=None):
            blk = prec[t_idx, :, k, 0, 2] if t_idx is not None else prec[:, :, k, 0, 2]
            v = np.asarray(blk, dtype=np.float64)
            v = v[v > -1]
            return float(v.mean()) if v.size else float("nan")
        per[cat_names[c]] = {"AP50": _ap(t50), "AP75": _ap(t75), "AP50_95": _ap(),
                             "n_gt": len(coco_gt.getAnnIds(catIds=[c]))}

    # 附加：各类别 AP50 的算术平均，用于核对 stats[1]
    vals = [v["AP50"] for v in per.values() if not math.isnan(v["AP50"])]
    overall["AP50_mean_over_classes"] = float(np.mean(vals)) if vals else float("nan")
    return overall, per, {"iouThrs": iou_thrs.tolist(), "maxDets": list(ev.params.maxDets)}


# ----------------------------------------------------------------------------
# 场景级（image-level）指标
# ----------------------------------------------------------------------------


def _binary_image_ap(rows):
    """rows: [(score, label)] -> 101 点插值的 AP（COCO 风格）"""
    rows = [r for r in rows]
    npos = sum(1 for _, y in rows if y == 1)
    if npos == 0:
        return float("nan"), []
    rows.sort(key=lambda r: -r[0])
    tp = np.cumsum([y for _, y in rows]).astype(np.float64)
    fp = np.cumsum([1 - y for _, y in rows]).astype(np.float64)
    rec = tp / npos
    prec = tp / np.maximum(tp + fp, 1e-12)
    # 单调化
    for i in range(len(prec) - 2, -1, -1):
        prec[i] = max(prec[i], prec[i + 1])
    rec_thrs = np.linspace(0, 1, 101)
    curve = []
    for t in rec_thrs:
        m = rec >= t
        curve.append(float(prec[m].max()) if m.any() else 0.0)
    return (float(np.mean(curve)) if curve else float("nan")), curve


def evaluate_image_level(gt, preds, conf_thr, scene_classes, cat_names, cat_ids):
    """对 runway / railway / solar_farm 计算 image 级 AP / P / R / F1。

    image_score(i,c) = 图 i 中类 c 所有预测的最大置信度，无预测则 0
    image_GT(i,c)    = 图 i 中是否存在类 c 的 GT
    """
    id2name = {v: k for k, v in cat_names.items()}
    has = set((a["image_id"], a["category_id"]) for a in gt["annotations"])
    all_ids = [i["id"] for i in gt["images"]]

    max_score = {}
    for p in preds:
        k = (p["image_id"], p["category_id"])
        if p["score"] > max_score.get(k, -1.0):
            max_score[k] = float(p["score"])

    out = {}
    for cname in scene_classes:
        c = id2name.get(cname)
        if c is None:
            out[cname] = {"error": "GT 中不存在该类"}
            continue
        rows = [(max_score.get((iid, c), 0.0), 1 if (iid, c) in has else 0)
                for iid in all_ids]
        ap, _ = _binary_image_ap(rows)
        tp = sum(1 for s, y in rows if s >= conf_thr and y == 1)
        fp = sum(1 for s, y in rows if s >= conf_thr and y == 0)
        fn = sum(1 for s, y in rows if s < conf_thr and y == 1)
        P, R = _safe_div(tp, tp + fp), _safe_div(tp, tp + fn)
        out[cname] = {
            "n_image_pos": sum(1 for _, y in rows if y == 1),
            "n_image_total": len(rows),
            "image_AP": ap,
            "image_TP": tp, "image_FP": fp, "image_FN": fn,
            "image_precision": P, "image_recall": R, "image_F1": _f1(P, R),
        }
    return out


# ----------------------------------------------------------------------------
# 汇总
# ----------------------------------------------------------------------------


def assert_bbox_convention(preds, sample=20000, min_pos_ratio=0.99):
    """守卫：预测框按 COCO 的 [x,y,w,h] 存储。

    这是一个真实踩过的坑 —— 匹配时若把 xywh 当 xyxy 用，IoU 全错，
    而且症状很迷惑：大框偶尔还能过阈值、小框永远匹配不上，
    整体 P/R/F1 接近 0，但同一份预测算出的 COCO AP 却完全正常。
    所以在这里显式检查：xywh 的 w/h 必须为正。
    """
    import random
    n = len(preds)
    if n == 0:
        return 1.0
    idx = range(n) if n <= sample else random.Random(0).sample(range(n), sample)
    pos = tot = 0
    for i in idx:
        w, h = float(preds[i]["bbox"][2]), float(preds[i]["bbox"][3])
        tot += 1
        if w > 0 and h > 0:
            pos += 1
    ratio = pos / tot if tot else 1.0
    if ratio < min_pos_ratio:
        raise SystemExit(
            "\n!! 预测框的 w/h 只有 %.1f%% 为正，不符合 COCO 的 [x,y,w,h] 约定。\n"
            "   若 dump 里存的是 xyxy，匹配会全错而 COCO AP 却正常。" % (100 * ratio))
    return ratio


def evaluate_all(gt_path, dump_path, cfg, model_name=None, strict=True):
    gt = load_gt(gt_path)
    dump = load_dump(dump_path)
    meta = dump.get("meta", {})

    cat_ids = sorted(c["id"] for c in gt["categories"])
    cat_names = {c["id"]: c["name"] for c in gt["categories"]}

    # ---- 护栏 ----
    assert_test_set_identity(gt, dump, gt_path, dump_path, strict=strict)
    mapping = assert_class_mapping(gt, meta.get("class_names"), strict=strict)
    if mapping != cat_ids:
        # 模型类别 k 对应 GT category_id = mapping[k]
        remap = {k: mapping[k] for k in range(len(mapping))}
        for p in dump["predictions"]:
            p["category_id"] = remap[int(p["category_id"])]

    # ---- dump 自身元信息与 GT 的一致性 ----
    n_gt_img = len(gt["images"])
    if meta.get("image_count") not in (None, n_gt_img):
        raise SystemExit("!! dump 声称 image_count=%s，但 GT 有 %d 张 !!"
                         % (meta.get("image_count"), n_gt_img))

    preds = dump["predictions"]
    assert_bbox_convention(preds)

    # split 以 dump 的 meta 为准（dump 是从 --gt 文件名推出来的），
    # 不能用 config 里的值 —— 否则评 val 时 header 会写 test。
    split = meta.get("split") or cfg.get("split")
    if meta.get("split") and cfg.get("split") and meta["split"] != cfg["split"]:
        raise SystemExit(
            "\n!! split 不一致，拒绝继续：\n"
            "   dump meta.split = %s\n   config.split    = %s\n"
            % (meta["split"], cfg["split"]))

    iou_thrs = list(cfg["eval_iou_thresholds"])
    conf_thr = float(cfg["confidence_threshold"])
    task_iou = float(cfg["task_iou_threshold"])
    scene = list(cfg.get("scene_like_classes", []))

    # 任务导向阈值必须包含在评测阈值里
    if task_iou not in iou_thrs:
        iou_thrs = [task_iou] + iou_thrs

    out = {
        "meta": {
            "model": model_name or meta.get("model", "unknown"),
            "framework": meta.get("framework"),
            "checkpoint": meta.get("checkpoint"),
            "split": split,
            "gt_annotation": os.path.abspath(gt_path),
            "gt_image_count": n_gt_img,
            "gt_annotation_count": len(gt["annotations"]),
            "prediction_source": os.path.abspath(dump_path),
            "dump_score_threshold": meta.get("dump_score_threshold"),
            "image_count": len(dump.get("image_ids", [])),
            "prediction_count": len(preds),
            "confidence_threshold": conf_thr,
            "task_iou_threshold": task_iou,
            "eval_iou_thresholds": iou_thrs,
            "scene_like_classes": scene,
            # 选型协议：两边不对称，必须随报告一起落盘，否则半年后没人说得清
            "checkpoint_epoch": meta.get("checkpoint_epoch"),
            "checkpoint_selection": meta.get("checkpoint_selection"),
            "weights": meta.get("weights"),
            "dataloader": meta.get("dataloader"),
            # dump 指纹：让"这份报告出自哪份 prediction"可机械核验
            "dump_md5": _md5_file(dump_path),
            "dump_meta": {k: meta.get(k) for k in
                          ("framework", "split", "gt_annotation", "gt_image_count",
                           "num_predictions", "img_folder", "ann_file", "image_dir")},
            "evaluated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        },
        "task_oriented": {},
        "coco_ap": {},
        "image_level": {},
    }

    for it in iou_thrs:
        ov, per = evaluate_task(gt, preds, conf_thr, it, cat_ids, cat_names)
        tag = "iou%02d" % round(it * 100)
        out["task_oriented"][tag] = {"overall": ov, "per_class": per}

    ap_ov, ap_per, ap_meta = evaluate_coco_ap(gt_path, preds, cat_ids, cat_names)
    out["coco_ap"] = {"overall": ap_ov, "per_class": ap_per, "coordinate_meta": ap_meta}

    out["image_level"] = evaluate_image_level(gt, preds, conf_thr, scene, cat_names, cat_ids)
    out["groups"] = build_groups(out, cat_ids, cat_names, scene, iou_thrs)
    return out


def _md5_file(path, chunk=1 << 20):
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def build_groups(out, cat_ids, cat_names, scene, iou_thrs):
    """把类别拆成三组，各自给一份汇总，并**写出成员名单**。

    为什么不能只报"24 类口径"
    ------------------------
    只写数字不写成员，半年后没人说得清"剔掉的是哪两个、为什么剔"。
    这里每组都显式落盘 members，报告里也逐组打印。

    组划分：
      all          = 全部类别
      object-like  = 全部 - scene_like
      scene-like   = config 的 scene_like_classes（默认 runway/railway/solar_farm）
    """
    scene_set = [c for c in cat_ids if cat_names[c] in set(scene)]
    object_set = [c for c in cat_ids if c not in set(scene_set)]

    def _members(ids):
        return [cat_names[c] for c in ids]

    groups = {}
    for gname, ids in (("all", list(cat_ids)),
                       ("object-like", object_set),
                       ("scene-like", scene_set)):
        if not ids:
            continue
        g = {
            "members": _members(ids),
            "n_classes": len(ids),
            "definition": {
                "all": "全部类别",
                "object-like": "全部类别 减去 scene-like",
                "scene-like": "config 的 scene_like_classes（场景型大目标）",
            }[gname],
            "task": {},
        }
        for it in iou_thrs:
            tag = "iou%02d" % round(it * 100)
            per = out["task_oriented"][tag]["per_class"]
            TP = sum(per[n]["TP"] for n in _members(ids))
            FP = sum(per[n]["FP"] for n in _members(ids))
            FN = sum(per[n]["FN"] for n in _members(ids))
            P = _safe_div(TP, TP + FP)
            R = _safe_div(TP, TP + FN)
            g["task"][tag] = {"TP": TP, "FP": FP, "FN": FN,
                              "precision": P, "recall": R, "F1": _f1(P, R)}
        # COCO 的 AP 本身就是"按类别求平均"，所以子集的 AP = 该子集各类 AP 的均值
        ap_per = out["coco_ap"]["per_class"]
        for metric in ("AP50", "AP75", "AP50_95"):
            vals = [ap_per[n][metric] for n in _members(ids)
                    if not math.isnan(ap_per[n][metric])]
            g[metric] = float(np.mean(vals)) if vals else float("nan")
        g["n_classes_with_defined_AP50_95"] = sum(
            1 for n in _members(ids) if not math.isnan(ap_per[n]["AP50_95"]))
        groups[gname] = g
    return groups


# ----------------------------------------------------------------------------
# 打印
# ----------------------------------------------------------------------------


def tag_iou(t):
    """'iou30' -> '0.30'，整体表列名用 P@0.30（与需求里的写法一致）。"""
    return "%.2f" % (int(t[3:]) / 100.0)


def tag_pct(t):
    """'iou30' -> '30'，per-class 表列名用 P30 / P50（与需求里的写法一致）。"""
    return str(int(t[3:]))


def fmt(v, nd=4):
    if v is None:
        return "-"
    if isinstance(v, float) and math.isnan(v):
        return "N/A"
    if isinstance(v, float):
        return ("%." + str(nd) + "f") % v
    return str(v)


def print_header(r):
    m = r["meta"]
    log("")
    log("=" * 96)
    log("HZS 评测报告   model=%s" % m["model"])
    log("=" * 96)
    log("  split                : %s" % m["split"])
    log("  GT annotation        : %s" % m["gt_annotation"])
    log("  GT 图片数            : %d" % m["gt_image_count"])
    log("  GT 标注数            : %d" % m["gt_annotation_count"])
    log("  prediction 来源      : %s" % m["prediction_source"])
    log("  prediction 图片数    : %d   (须与 GT 图片数相等)" % m["image_count"])
    log("  prediction 框数      : %d" % m["prediction_count"])
    log("  dump 导出阈值        : %s   (模型推理时使用的低阈值)"
        % fmt(m["dump_score_threshold"]))
    log("  confidence_threshold : %.3f" % m["confidence_threshold"])
    log("  task_iou_threshold   : %.3f" % m["task_iou_threshold"])
    log("  checkpoint           : %s" % m["checkpoint"])
    log("  ckpt epoch           : %s" % fmt(m.get("checkpoint_epoch")))
    log("  选型协议             : %s"
        % (m.get("checkpoint_selection") or "未记录（见 HZS_CONTEXT §6）"))
    if m.get("weights"):
        log("  权重来源             : %s" % m["weights"])
    log("  framework            : %s" % m["framework"])
    log("  dump md5             : %s" % (m.get("dump_md5") or "-"))
    log("  评测时间             : %s" % m["evaluated_at"])
    log("=" * 96)
    sel = m.get("checkpoint_selection")
    if sel:
        log("  本模型的 checkpoint 选型协议：%s" % sel)
    else:
        log("  本模型的 checkpoint 选型协议：**未记录** —— 跨模型比较前必须补上。")
    log("  （跨模型的协议差异由 compare_models.py 单独提示，不在单模型报告里下结论）")


def print_tables(r):
    m = r["meta"]
    iou_thrs = m["eval_iou_thresholds"]
    tags = ["iou%02d" % round(x * 100) for x in iou_thrs]
    scene = m["scene_like_classes"]

    log("")
    log("【表1】整体指标")
    head = "Model".ljust(16)
    for t in tags:
        head += "P@%s  R@%s  F1@%s  " % ((tag_iou(t),) * 3)
    head += "mAP50   mAP75   mAP50:95"
    log(head)
    log("-" * len(head))
    row = m["model"].ljust(16)
    for t in tags:
        o = r["task_oriented"][t]["overall"]
        row += "%-6s %-6s %-6s " % (fmt(o["precision"]), fmt(o["recall"]), fmt(o["F1"]))
    ap = r["coco_ap"]["overall"]
    row += "%-7s %-7s %-8s" % (fmt(ap["AP50"]), fmt(ap["AP75"]), fmt(ap["AP50_95"]))
    log(row)
    log("")
    log("  整体 P/R/F1 为 micro（把所有类的 TP/FP/FN 汇总后计算），"
        "与需求文档 task_precision = TP/(TP+FP) 的定义一致。")
    for t in tags:
        o = r["task_oriented"][t]["overall"]
        log("  %s  TP=%d FP=%d FN=%d | macro-F1=%s"
            % (t, o["TP"], o["FP"], o["FN"], fmt(o["macro_F1"])))

    # ---- 表0：分组口径（主表） ----
    groups = r.get("groups") or {}
    if groups:
        log("")
        log("【表0】分组口径（All / object-like / scene-like）—— 正式引用请用本表")
        log("  分组定义与成员（写死在报告里，避免日后忘记剔了谁、为什么剔）：")
        for gname in ("all", "object-like", "scene-like"):
            g = groups.get(gname)
            if not g:
                continue
            log("    %-12s n=%2d  定义=%s" % (gname, g["n_classes"], g["definition"]))
            log("    %-12s 成员: %s" % ("", ", ".join(g["members"])))
        h0 = "%-12s %6s %6s" % ("Group", "n_cls", "TP")
        for t in tags:
            n = tag_pct(t)
            h0 += " %7s %7s %7s" % ("P" + n, "R" + n, "F1_" + n)
        h0 += " %8s %8s %9s" % ("mAP50", "mAP75", "mAP50:95")
        log("")
        log(h0)
        log("-" * len(h0))
        for gname in ("all", "object-like", "scene-like"):
            g = groups.get(gname)
            if not g:
                continue
            row = "%-12s %6d %6d" % (gname, g["n_classes"], g["task"][tags[0]]["TP"])
            for t in tags:
                d = g["task"][t]
                row += " %7s %7s %7s" % (fmt(d["precision"]), fmt(d["recall"]), fmt(d["F1"]))
            row += " %8s %8s %9s" % (fmt(g["AP50"]), fmt(g["AP75"]), fmt(g["AP50_95"]))
            log(row)
        log("")
        log("  * All classes 的 mAP 与标准 COCO mAP 一致；分组 mAP = 该组各类 AP 的算术平均")
        log("    （COCO 的 AP 定义本身就是按类别求平均，故子集平均值是合法聚合）。")
        log("  * 分组 P/R/F1 是 micro：组内各类 TP/FP/FN 先求和再算，不是各类 F1 的平均。")

    log("")
    log("【表2】per-class 指标")
    h2 = "%-20s %6s %6s %6s" % ("Class", "n_gt", "TP", "FN")
    for t in tags:
        n = tag_pct(t)
        h2 += " %6s %6s %6s" % ("P" + n, "R" + n, "F1_" + n)
    h2 += " %7s %7s %8s" % ("AP50", "AP75", "AP50:95")
    h2 += " %8s" % "ImageF1"
    log(h2)
    log("-" * len(h2))

    names = sorted(r["coco_ap"]["per_class"].keys())
    for cname in names:
        a = r["coco_ap"]["per_class"][cname]
        line = "%-20s %6d" % (cname, a.get("n_gt", 0))
        first = True
        for t in tags:
            pc = r["task_oriented"][t]["per_class"][cname]
            if first:
                line += " %6d %6d" % (pc["TP"], pc["FN"])
                first = False
            line += " %6s %6s %6s" % (fmt(pc["precision"]), fmt(pc["recall"]), fmt(pc["F1"]))
        line += " %7s %7s %8s" % (fmt(a["AP50"]), fmt(a["AP75"]), fmt(a["AP50_95"]))
        il = r["image_level"].get(cname)
        line += " %8s" % (fmt(il["image_F1"]) if il and "image_F1" in il else "-")
        log(line)

    if scene:
        log("")
        log("【表3】场景级 image-level 指标（%s）" % ", ".join(scene))
        h3 = "%-20s %8s %8s %8s %8s %8s %8s %8s" % (
            "Class", "图正例", "图总数", "image_AP", "img_P", "img_R", "img_F1",
            "TP/FP/FN")
        log(h3)
        log("-" * len(h3))
        for cname in scene:
            d = r["image_level"].get(cname, {})
            if "error" in d:
                log("%-20s  %s" % (cname, d["error"]))
                continue
            log("%-20s %8d %8d %8s %8s %8s %8s   %d/%d/%d" % (
                cname, d["n_image_pos"], d["n_image_total"], fmt(d["image_AP"]),
                fmt(d["image_precision"]), fmt(d["image_recall"]), fmt(d["image_F1"]),
                d["image_TP"], d["image_FP"], d["image_FN"]))

    log("")
    log("提示：n_gt=0 的类别其 P/R/F1/AP 在本次 split 上未定义，显示为 N/A。")


def report_to_md(r):
    m = r["meta"]
    tags = ["iou%02d" % round(x * 100) for x in m["eval_iou_thresholds"]]
    L = []
    L.append("# HZS 评测报告\n")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    for k, label in (("model", "模型"), ("framework", "框架"), ("checkpoint", "checkpoint"),
                     ("split", "split"), ("gt_annotation", "GT annotation"),
                     ("gt_image_count", "GT 图片数"), ("gt_annotation_count", "GT 标注数"),
                     ("prediction_source", "prediction 来源"),
                     ("image_count", "prediction 图片数"),
                     ("prediction_count", "prediction 框数"),
                     ("dump_score_threshold", "dump 导出阈值"),
                     ("confidence_threshold", "confidence_threshold"),
                     ("task_iou_threshold", "task_iou_threshold"),
                     ("evaluated_at", "评测时间")):
        L.append("| %s | `%s` |" % (label, m.get(k)))
    L.append("")
    L.append("> confidence threshold 与 IoU threshold 严格分离；"
             "confidence threshold 只在 val 上选取，test 上不做任何阈值搜索。\n")

    groups = r.get("groups") or {}
    if groups:
        L.append("## 表0 分组口径（All / object-like / scene-like）—— 正式引用请用本表\n")
        L.append("分组定义与成员（写死在报告里，避免日后忘记剔了谁、为什么剔）：\n")
        for gname in ("all", "object-like", "scene-like"):
            g = groups.get(gname)
            if not g:
                continue
            L.append("- **%s**（n=%d）：%s" % (gname, g["n_classes"], g["definition"]))
            L.append("  - 成员：%s" % ", ".join("`%s`" % c for c in g["members"]))
        L.append("")
        h0 = "| Group | n_cls |" + "".join(
            " P@%s | R@%s | F1@%s |" % ((tag_iou(t),) * 3) for t in tags) \
            + " mAP50 | mAP75 | mAP50:95 |"
        L.append(h0)
        L.append("|" + "---|" * (h0.count("|") - 1))
        for gname in ("all", "object-like", "scene-like"):
            g = groups.get(gname)
            if not g:
                continue
            row = "| %s | %d |" % (gname, g["n_classes"])
            for t in tags:
                d = g["task"][t]
                row += " %s | %s | %s |" % (fmt(d["precision"]), fmt(d["recall"]),
                                            fmt(d["F1"]))
            row += " %s | %s | %s |" % (fmt(g["AP50"]), fmt(g["AP75"]), fmt(g["AP50_95"]))
            L.append(row)
        L.append("")
        L.append("> All classes 的 mAP 与标准 COCO mAP 一致；分组 mAP = 该组各类 AP 的算术平均"
                 "（COCO 的 AP 定义本身就是按类别求平均）。分组 P/R/F1 是 micro。\n")

    L.append("## 表1 整体指标\n")
    h = "| Model |" + "".join(
        " P@%s | R@%s | F1@%s |" % ((tag_iou(t),) * 3) for t in tags
    ) + " mAP50 | mAP75 | mAP50:95 |"
    L.append(h)
    L.append("|" + "---|" * (h.count("|") - 1))
    row = "| %s |" % m["model"]
    for t in tags:
        o = r["task_oriented"][t]["overall"]
        row += " %s | %s | %s |" % (fmt(o["precision"]), fmt(o["recall"]), fmt(o["F1"]))
    ap = r["coco_ap"]["overall"]
    row += " %s | %s | %s |" % (fmt(ap["AP50"]), fmt(ap["AP75"]), fmt(ap["AP50_95"]))
    L.append(row)
    L.append("")

    L.append("## 表2 per-class 指标\n")
    h2 = "| Class | n_gt |"
    for t in tags:
        n = tag_pct(t)
        h2 += " P%s | R%s | F1_%s |" % (n, n, n)
    h2 += " AP50 | AP75 | AP50:95 | Image F1 |"
    L.append(h2)
    L.append("|" + "---|" * (h2.count("|") - 1))
    for cname in sorted(r["coco_ap"]["per_class"].keys()):
        a = r["coco_ap"]["per_class"][cname]
        line = "| %s | %d |" % (cname, a.get("n_gt", 0))
        for t in tags:
            pc = r["task_oriented"][t]["per_class"][cname]
            line += " %s | %s | %s |" % (fmt(pc["precision"]), fmt(pc["recall"]), fmt(pc["F1"]))
        line += " %s | %s | %s |" % (fmt(a["AP50"]), fmt(a["AP75"]), fmt(a["AP50_95"]))
        il = r["image_level"].get(cname)
        line += " %s |" % (fmt(il["image_F1"]) if il and "image_F1" in il else "-")
        L.append(line)
    L.append("")

    if m["scene_like_classes"]:
        L.append("## 表3 场景级 image-level 指标\n")
        L.append("| Class | 图正例 | 图总数 | image_AP | image_P | image_R | image_F1 | TP/FP/FN |")
        L.append("|---|---|---|---|---|---|---|---|")
        for cname in m["scene_like_classes"]:
            d = r["image_level"].get(cname, {})
            if "error" in d:
                L.append("| %s | - | - | - | - | - | - | - |" % cname)
                continue
            L.append("| %s | %d | %d | %s | %s | %s | %s | %d/%d/%d |" % (
                cname, d["n_image_pos"], d["n_image_total"], fmt(d["image_AP"]),
                fmt(d["image_precision"]), fmt(d["image_recall"]), fmt(d["image_F1"]),
                d["image_TP"], d["image_FP"], d["image_FN"]))
        L.append("")
    L.append("> 本报告不给出任何加权综合分数；不同指标分别报告。")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--gt", required=True)
    ap.add_argument("--dump", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--md", default=None)
    ap.add_argument("--model-name", default=None)
    ap.add_argument("--no-strict", action="store_true")
    a = ap.parse_args()

    cfg = load_config(a.config)
    r = evaluate_all(a.gt, a.dump, cfg, model_name=a.model_name,
                     strict=not a.no_strict)
    print_header(r)
    print_tables(r)
    if a.out:
        json.dump(r, io.open(a.out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        log("\nJSON -> %s" % a.out)
    if a.md:
        io.open(a.md, "w", encoding="utf-8", newline="\n").write(report_to_md(r))
        log("Markdown -> %s" % a.md)


def load_config(path):
    """极简 YAML 读取（避免依赖 pyyaml 版本差异；本项目的配置结构很浅）。"""
    try:
        import yaml
        with io.open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        pass
    cfg = {}
    for ln in io.open(path, encoding="utf-8"):
        ln = ln.split("#")[0].strip()
        if not ln or ":" not in ln:
            continue
        k, v = ln.split(":", 1)
        k, v = k.strip(), v.strip()
        if v.startswith("[") and v.endswith("]"):
            items = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
            cfg[k] = [float(x) if _isnum(x) else x for x in items]
        elif _isnum(v):
            cfg[k] = float(v)
        elif v.lower() in ("true", "false"):
            cfg[k] = v.lower() == "true"
        else:
            cfg[k] = v.strip("'\"")
    return cfg


def _isnum(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


if __name__ == "__main__":
    main()
