# -*- coding: utf-8 -*-
"""Rebuild the multi-GT-version rescoring table (paper Table 11).

Same frozen prediction dumps, three test GT versions (G1 pre-reannotation, G2 complete,
G3 deduplicated). The metric code is the unmodified `hzs_metrics.py`.

The confidence threshold comes from each model's frozen eval config (the "config_yaml"
convention). It is deliberately NOT re-selected per GT: changing GT and threshold at the
same time would confound the comparison.

Usage:
    python reproduce_gt_versions.py \
        --preds-dir ../dumps/six_models \
        --configs-dir ../configs/six_models \
        --g1 ../annotations/g1/instances_test.json \
        --g2 ../annotations/g2/instances_test.json \
        --g3 ../annotations/g3/instances_test.json \
        --out ../results/recomputed_gt_versions.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hzs_metrics as H  # noqa: E402

MODELS = [
    ("dfine", "D-FINE-X (HGNetv2-B5)"),
    ("rtdetr", "RT-DETR-v2-R18"),
    ("rfdetr", "RF-DETR-Small"),
    ("dino", "DINO-4scale-R50"),
    ("yolo26", "YOLO26l"),
    ("frcnn", "Faster R-CNN-R50-FPN"),
]

COLS = ["model", "gt_key", "gt_n_images", "gt_n_boxes", "gt_md5", "conf",
        "AP50", "AP75", "AP50_95", "AR100",
        "P@0.30", "R@0.30", "F1@0.30", "P@0.50", "R@0.50", "F1@0.50"]


def md5f(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds-dir", required=True)
    ap.add_argument("--configs-dir", required=True)
    ap.add_argument("--thresholds-dir", required=True,
                    help="val_threshold_<key>_M4.json files (frozen val-selected conf)")
    ap.add_argument("--g1", required=True)
    ap.add_argument("--g2", required=True)
    ap.add_argument("--g3", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    gts = [("G1_old_partial", a.g1), ("G2_new_complete", a.g2), ("G3_dedupv1", a.g3)]
    for k, p in gts:
        if not os.path.exists(p):
            raise SystemExit("missing GT %s: %s" % (k, p))

    rows = []
    for key, name in MODELS:
        cfg_p = os.path.join(a.configs_dir, "config_%s_M4.yaml" % key)
        pred_p = os.path.join(a.preds_dir, "preds_%s_test_M4.json" % key)
        if not os.path.exists(pred_p):
            print("skip %-8s (missing dump)" % key)
            continue
        thr_p = os.path.join(a.thresholds_dir, "val_threshold_%s_M4.json" % key)
        if not os.path.exists(thr_p):
            raise SystemExit("missing frozen threshold: %s" % thr_p)
        cfg = H.load_config(cfg_p)
        cfg["confidence_threshold"] = float(
            json.load(open(thr_p, encoding="utf-8"))["chosen_confidence_threshold"])
        for gk, gp in gts:
            d = H.evaluate_all(gp, pred_p, cfg, model_name=name)
            ov30 = d["task_oriented"]["iou30"]["overall"]
            ov50 = d["task_oriented"]["iou50"]["overall"]
            ap_ov = d["coco_ap"]["overall"]
            rows.append({
                "model": name, "gt_key": gk,
                "gt_n_images": d["meta"]["gt_image_count"],
                "gt_n_boxes": d["meta"]["gt_annotation_count"],
                "gt_md5": md5f(gp), "conf": d["meta"]["confidence_threshold"],
                "AP50": ap_ov["AP50"], "AP75": ap_ov["AP75"],
                "AP50_95": ap_ov["AP50_95"], "AR100": ap_ov["AR100"],
                "P@0.30": ov30["precision"], "R@0.30": ov30["recall"], "F1@0.30": ov30["F1"],
                "P@0.50": ov50["precision"], "R@0.50": ov50["recall"], "F1@0.50": ov50["F1"],
            })
            print("%-24s %-16s AP50:95=%.6f" % (name, gk, ap_ov["AP50_95"]))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
