# -*- coding: utf-8 -*-
"""把多个模型的评测报告合并成对照表

需求原文：
    「不要自行计算类似 0.5*F1_30 + 0.3*AP50 + 0.2*AP50:95 这样的自定义总分。
      不同指标分别报告。不要通过人为选择权重来决定 RF-DETR 和 RT-DETR 谁更好。」

所以本脚本**只做并排展示，不做任何排序或加权**。谁更好由人看表判断。

用法
----
    python compare_models.py --reports rfdetr_test.json rtdetr_test.json \
        --md compare.md --csv compare.csv
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hzs_metrics import fmt, log, tag_iou, tag_pct   # noqa: E402


def tags_of(r):
    return ["iou%02d" % round(x * 100) for x in r["meta"]["eval_iou_thresholds"]]


def check_same_test_set(reports):
    """所有报告必须评在同一份 GT 上，否则并排比较没有意义。"""
    keys = set()
    for r in reports:
        m = r["meta"]
        keys.add((m["gt_annotation"], m["gt_image_count"], m["gt_annotation_count"]))
    if len(keys) > 1:
        raise SystemExit(
            "\n!! 各报告用的 GT 不一致，不能并排比较：\n" +
            "\n".join("   %s  图片%d 标注%d" % k for k in sorted(keys)))
    # 分组也要一致，否则表0 里同名组装的不是同一批类
    gkeys = set()
    for r in reports:
        gs = r.get("groups") or {}
        gkeys.add(tuple((g, tuple(gs[g]["members"])) for g in sorted(gs)))
    if len(gkeys) > 1:
        raise SystemExit(
            "\n!! 各报告的分组定义（成员类别）不一致，表0 不可并排：\n" +
            "\n".join("   %s" % (k,) for k in sorted(gkeys)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", nargs="+", required=True)
    ap.add_argument("--md", default=None)
    ap.add_argument("--csv", default=None)
    a = ap.parse_args()

    reports = [json.load(io.open(p, encoding="utf-8")) for p in a.reports]
    check_same_test_set(reports)

    m0 = reports[0]["meta"]
    tags = tags_of(reports[0])

    log("")
    log("=" * 110)
    log("模型对照表")
    log("=" * 110)
    log("  GT annotation : %s" % m0["gt_annotation"])
    log("  split         : %s" % m0["split"])
    log("  GT 图片数     : %d" % m0["gt_image_count"])
    log("  task_iou      : %s" % ", ".join("%.2f" % x
                                           for x in reports[0]["meta"]["eval_iou_thresholds"]))
    for r in reports:
        m = r["meta"]
        log("  ---")
        log("  %-16s checkpoint=%s" % (m["model"], m["checkpoint"]))
        log("  %-16s confidence_threshold=%.3f  dump阈值=%s  framework=%s"
            % ("", m["confidence_threshold"], fmt(m["dump_score_threshold"]),
               m["framework"]))
    log("=" * 110)
    log("  注意：以上阈值各不相同则不可直接比较 —— 请确认两边 confidence_threshold 一致。")

    # checkpoint 选型协议：两边不对称时必须显式提示，否则读者会默认
    # "都是 val-selected"，从而高估可比性。
    sels = {r["meta"]["model"]: (r["meta"].get("checkpoint_selection") or "未记录")
            for r in reports}
    log("")
    log("  checkpoint 选型协议：")
    for k, v in sels.items():
        log("    %-18s %s" % (k, v))
    if len(set(sels.values())) > 1:
        log("")
        log("  ⚠ 两边选型协议**不一致**。这意味着两个模型不是在同一个选择压力下")
        log("    挑出来的 checkpoint，引用这组对比数字时必须一并写明这一条。")
    elif any(v == "未记录" for v in sels.values()):
        log("")
        log("  ⚠ 有模型的选型协议未记录，无法判断是否对称 —— 引用前请补全。")

    # ---- 表0：分组口径（主表）----
    groups_of = [r.get("groups") or {} for r in reports]
    if any(groups_of):
        log("")
        log("【表0】分组口径对照（All / object-like / scene-like）—— 正式引用请用本表")
        log("  分组定义与成员（每个模型报告中均已写死，这里以第一个模型为准）：")
        g0 = groups_of[0]
        for gname in ("all", "object-like", "scene-like"):
            g = g0.get(gname)
            if not g:
                continue
            log("    %-12s n=%2d  定义=%s" % (gname, g["n_classes"], g["definition"]))
            log("    %-12s 成员: %s" % ("", ", ".join(g["members"])))
        h0 = "%-18s %-12s %6s" % ("Model", "Group", "n_cls")
        for t in tags:
            s = tag_iou(t)
            h0 += " %9s %9s %9s" % ("P@" + s, "R@" + s, "F1@" + s)
        h0 += " %8s %8s %10s" % ("mAP50", "mAP75", "mAP50:95")
        log("")
        log(h0)
        log("-" * len(h0))
        for r in reports:
            gs = r.get("groups") or {}
            for gname in ("all", "object-like", "scene-like"):
                g = gs.get(gname)
                if not g:
                    continue
                row = "%-18s %-12s %6d" % (r["meta"]["model"], gname, g["n_classes"])
                for t in tags:
                    d = g["task"][t]
                    row += " %9s %9s %9s" % (fmt(d["precision"]), fmt(d["recall"]),
                                             fmt(d["F1"]))
                row += " %8s %8s %10s" % (fmt(g["AP50"]), fmt(g["AP75"]), fmt(g["AP50_95"]))
                log(row)
            log("")
        log("  分组 mAP = 该组各类 AP 的算术平均；分组 P/R/F1 为 micro。")

    # ---- 表1 ----
    head = "%-18s" % "Model"
    for t in tags:
        s = tag_iou(t)
        head += " %9s %9s %9s" % ("P@" + s, "R@" + s, "F1@" + s)
    head += " %8s %8s %10s" % ("mAP50", "mAP75", "mAP50:95")
    log("")
    log("【表1】整体指标（micro）")
    log(head)
    log("-" * len(head))
    for r in reports:
        row = "%-18s" % r["meta"]["model"]
        for t in tags:
            o = r["task_oriented"][t]["overall"]
            row += " %9s %9s %9s" % (fmt(o["precision"]), fmt(o["recall"]), fmt(o["F1"]))
        ap_ = r["coco_ap"]["overall"]
        row += " %8s %8s %10s" % (fmt(ap_["AP50"]), fmt(ap_["AP75"]), fmt(ap_["AP50_95"]))
        log(row)
    log("")
    log("  (未做任何加权综合；各指标独立解释)")

    # ---- 表2 ----
    names = sorted(reports[0]["coco_ap"]["per_class"].keys())
    h2 = "%-20s %-18s %6s" % ("Class", "Model", "n_gt")
    for t in tags:
        s = tag_pct(t)
        h2 += " %7s %7s %8s" % ("P" + s, "R" + s, "F1_" + s)
    h2 += " %7s %7s %9s %8s" % ("AP50", "AP75", "AP50:95", "ImgF1")
    log("")
    log("【表2】per-class 指标")
    log(h2)
    log("-" * len(h2))
    for cname in names:
        for r in reports:
            ap_ = r["coco_ap"]["per_class"].get(cname, {})
            row = "%-20s %-18s %6s" % (cname, r["meta"]["model"], ap_.get("n_gt", "-"))
            for t in tags:
                pc = r["task_oriented"][t]["per_class"].get(cname, {})
                row += " %7s %7s %8s" % (fmt(pc.get("precision")), fmt(pc.get("recall")),
                                         fmt(pc.get("F1")))
            row += " %7s %7s %9s" % (fmt(ap_.get("AP50")), fmt(ap_.get("AP75")),
                                     fmt(ap_.get("AP50_95")))
            il = r["image_level"].get(cname)
            row += " %8s" % (fmt(il["image_F1"]) if il and "image_F1" in il else "-")
            log(row)
        log("")

    # ---- 表3 ----
    scene = reports[0]["meta"]["scene_like_classes"]
    if scene:
        h3 = "%-20s %-18s %8s %8s %9s %8s %8s %8s" % (
            "Class", "Model", "图正例", "图总数", "image_AP", "img_P", "img_R", "img_F1")
        log("【表3】场景级 image-level 指标")
        log(h3)
        log("-" * len(h3))
        for cname in scene:
            for r in reports:
                d = r["image_level"].get(cname, {})
                if "error" in d:
                    log("%-20s %-18s  %s" % (cname, r["meta"]["model"], d["error"]))
                    continue
                log("%-20s %-18s %8d %8d %9s %8s %8s %8s" % (
                    cname, r["meta"]["model"], d["n_image_pos"], d["n_image_total"],
                    fmt(d["image_AP"]), fmt(d["image_precision"]),
                    fmt(d["image_recall"]), fmt(d["image_F1"])))
            log("")

    # ---- 落盘 ----
    if a.md:
        L = ["# 模型对照表\n",
             "| 项 | 值 |", "|---|---|",
             "| GT annotation | `%s` |" % m0["gt_annotation"],
             "| split | %s |" % m0["split"],
             "| GT 图片数 | %d |" % m0["gt_image_count"],
             "| task IoU | %s |" % ", ".join("%.2f" % x for x in
                                             reports[0]["meta"]["eval_iou_thresholds"]),
             ""]
        for r in reports:
            m = r["meta"]
            L.append("- **%s** — confidence=%.3f, dump=%.3f, framework=%s\n"
                     % (m["model"], m["confidence_threshold"],
                        m["dump_score_threshold"] or 0, m["framework"]))
            L.append("  - checkpoint：`%s`\n" % m.get("checkpoint"))
            L.append("  - checkpoint epoch：%s；选型协议：%s\n"
                     % (m.get("checkpoint_epoch"),
                        m.get("checkpoint_selection") or "**未记录**"))
            if m.get("weights"):
                L.append("  - 权重来源：`%s`\n" % m["weights"])
        if len(set(sels.values())) > 1:
            L.append("\n> ⚠ **两边 checkpoint 选型协议不一致**。这组对比是在不同的"
                     "选择压力下挑出的 checkpoint 上做的，引用时须一并写明。\n")
        if any(groups_of):
            g0 = groups_of[0]
            L.append("\n## 表0 分组口径对照（All / object-like / scene-like）—— 正式引用请用本表\n")
            for gname in ("all", "object-like", "scene-like"):
                g = g0.get(gname)
                if not g:
                    continue
                L.append("- **%s**（n=%d）：%s" % (gname, g["n_classes"], g["definition"]))
                L.append("  - 成员：%s" % ", ".join("`%s`" % c for c in g["members"]))
            L.append("")
            h = ("| Model | Group | n_cls |"
                 + "".join(" P@%s | R@%s | F1@%s |" % (tag_iou(t), tag_iou(t), tag_iou(t))
                           for t in tags)
                 + " mAP50 | mAP75 | mAP50:95 |")
            L.append(h)
            L.append("|" + "---|" * (h.count("|") - 1))
            for r in reports:
                gs = r.get("groups") or {}
                for gname in ("all", "object-like", "scene-like"):
                    g = gs.get(gname)
                    if not g:
                        continue
                    row = "| %s | %s | %d |" % (r["meta"]["model"], gname, g["n_classes"])
                    for t in tags:
                        d = g["task"][t]
                        row += " %s | %s | %s |" % (fmt(d["precision"]), fmt(d["recall"]),
                                                    fmt(d["F1"]))
                    row += " %s | %s | %s |" % (fmt(g["AP50"]), fmt(g["AP75"]),
                                                fmt(g["AP50_95"]))
                    L.append(row)
            L.append("")
            L.append("> 分组 mAP = 该组各类 AP 的算术平均（COCO 的 AP 定义即按类别求平均）；"
                     "分组 P/R/F1 为 micro。\n")

        L.append("\n## 表1 整体指标\n")
        h = "| Model |" + "".join(
            " P@%s | R@%s | F1@%s |" % ((tag_iou(t),) * 3) for t in tags) \
            + " mAP50 | mAP75 | mAP50:95 |"
        L.append(h)
        L.append("|" + "---|" * (h.count("|") - 1))
        for r in reports:
            row = "| %s |" % r["meta"]["model"]
            for t in tags:
                o = r["task_oriented"][t]["overall"]
                row += " %s | %s | %s |" % (fmt(o["precision"]), fmt(o["recall"]),
                                            fmt(o["F1"]))
            ap_ = r["coco_ap"]["overall"]
            row += " %s | %s | %s |" % (fmt(ap_["AP50"]), fmt(ap_["AP75"]),
                                        fmt(ap_["AP50_95"]))
            L.append(row)
        L.append("\n> 不含任何加权综合分数，不给出模型优劣排序。\n")
        io.open(a.md, "w", encoding="utf-8", newline="\n").write("\n".join(L))
        log("\nMarkdown -> %s" % a.md)

    if a.csv:
        with io.open(a.csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            cols = ["model", "framework", "gt_annotation", "split",
                    "confidence_threshold", "task_iou_threshold"]
            for t in tags:
                s = tag_pct(t)
                cols += ["P" + s, "R" + s, "F1_" + s]
            cols += ["mAP50", "mAP75", "mAP50:95"]
            w.writerow(cols)
            for r in reports:
                row = [r["meta"]["model"], r["meta"]["framework"],
                       r["meta"]["gt_annotation"], r["meta"]["split"],
                       r["meta"]["confidence_threshold"],
                       r["meta"]["task_iou_threshold"]]
                for t in tags:
                    o = r["task_oriented"][t]["overall"]
                    row += [o["precision"], o["recall"], o["F1"]]
                ap_ = r["coco_ap"]["overall"]
                row += [ap_["AP50"], ap_["AP75"], ap_["AP50_95"]]
                w.writerow(row)
            # 分组长表
            for gname in ("all", "object-like", "scene-like"):
                for r in reports:
                    g = (r.get("groups") or {}).get(gname)
                    if not g:
                        continue
                    row = [r["meta"]["model"], "group:" + gname,
                           r["meta"]["gt_annotation"], r["meta"]["split"],
                           r["meta"]["confidence_threshold"],
                           r["meta"]["task_iou_threshold"]]
                    for t in tags:
                        d = g["task"][t]
                        row += [d["precision"], d["recall"], d["F1"]]
                    row += [g["AP50"], g["AP75"], g["AP50_95"]]
                    w.writerow(row)

            # per-class 长表
            for cname in names:
                for r in reports:
                    ap_ = r["coco_ap"]["per_class"].get(cname, {})
                    row = [r["meta"]["model"], "class:" + cname,
                           r["meta"]["gt_annotation"], r["meta"]["split"],
                           r["meta"]["confidence_threshold"],
                           r["meta"]["task_iou_threshold"]]
                    for t in tags:
                        pc = r["task_oriented"][t]["per_class"].get(cname, {})
                        row += [pc.get("precision"), pc.get("recall"), pc.get("F1")]
                    row += [ap_.get("AP50"), ap_.get("AP75"), ap_.get("AP50_95")]
                    w.writerow(row)
        log("CSV -> %s" % a.csv)


if __name__ == "__main__":
    main()
