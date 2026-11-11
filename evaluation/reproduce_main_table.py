# -*- coding: utf-8 -*-
"""Rebuild the six-model main table (paper Table 7) from prediction dumps.

The metric code itself is `hzs_metrics.py`, imported unmodified; this script only
iterates models and writes the CSV.

Usage:
    python reproduce_main_table.py \
        --gt ../annotations/g3/instances_test.json \
        --preds-dir ../dumps/six_models \
        --configs-dir ../configs/six_models \
        --out ../results/recomputed_main_table.csv
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
    ("dfine", "D-FINE-X (HGNetv2-B5)", "supervised"),
    ("rtdetr", "RT-DETR-v2-R18", "supervised"),
    ("rfdetr", "RF-DETR-Small", "supervised"),
    ("dino", "DINO-4scale-R50", "supervised"),
    ("yolo26", "YOLO26l", "supervised"),
    ("frcnn", "Faster R-CNN-R50-FPN", "supervised"),
    ("gdino", "GroundingDINO-T", "ovd"),
]

COLS = ["model", "supervision", "conf_threshold", "AP50", "AP75", "AP50_95",
        "P@IoU0.30", "R@IoU0.30", "F1@IoU0.30", "P@IoU0.50", "R@IoU0.50", "F1@IoU0.50",
        "n_gt_images", "n_gt_boxes", "preds_file", "preds_md5", "gt_md5"]


def md5f(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", required=True)
    ap.add_argument("--preds-dir", required=True)
    ap.add_argument("--configs-dir", required=True)
    ap.add_argument("--thresholds-dir", required=True,
                    help="directory holding val_threshold_<key>_M4.json — the frozen "
                         "val-selected operating points (authoritative; the config YAML "
                         "carries a pre-retune value)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--include-gdino", action="store_true",
                    help="GroundingDINO is a zero-shot reference; include it explicitly")
    ap.add_argument("--per-class-out", default=None,
                    help="also write the per-class AP table (paper Table 8)")
    ap.add_argument("--gdino-preds", default=None,
                    help="directory containing the GroundingDINO dump"
                         "predictions/test_predictions.json, not under A")
    a = ap.parse_args()

    gt_md5 = md5f(a.gt)
    rows = []
    pc_rows = []
    for key, name, sup in MODELS:
        if key == "gdino" and not a.include_gdino:
            continue
        cfg_p = os.path.join(a.configs_dir, "config_%s_M4.yaml" % key)
        pred_p = os.path.join(a.preds_dir, "preds_%s_test_M4.json" % key)
        if key == "gdino" and a.gdino_preds:
            pred_p = a.gdino_preds
        if not (os.path.exists(cfg_p) and os.path.exists(pred_p)):
            print("skip %-8s (missing %s)" % (key, "config" if not os.path.exists(cfg_p) else "preds"))
            continue
        thr_p = os.path.join(a.thresholds_dir, "val_threshold_%s_M4.json" % key)
        if not os.path.exists(thr_p):
            raise SystemExit("missing frozen threshold: %s" % thr_p)
        cfg = H.load_config(cfg_p)
        cfg["confidence_threshold"] = float(
            json.load(open(thr_p, encoding="utf-8"))["chosen_confidence_threshold"])
        d = H.evaluate_all(a.gt, pred_p, cfg, model_name=name)
        rows.append({
            "model": name, "supervision": sup,
            "conf_threshold": d["meta"]["confidence_threshold"],
            "AP50": d["coco_ap"]["overall"]["AP50"],
            "AP75": d["coco_ap"]["overall"]["AP75"],
            "AP50_95": d["coco_ap"]["overall"]["AP50_95"],
            "P@IoU0.30": d["task_oriented"]["iou30"]["overall"]["precision"],
            "R@IoU0.30": d["task_oriented"]["iou30"]["overall"]["recall"],
            "F1@IoU0.30": d["task_oriented"]["iou30"]["overall"]["F1"],
            "P@IoU0.50": d["task_oriented"]["iou50"]["overall"]["precision"],
            "R@IoU0.50": d["task_oriented"]["iou50"]["overall"]["recall"],
            "F1@IoU0.50": d["task_oriented"]["iou50"]["overall"]["F1"],
            "n_gt_images": d["meta"]["gt_image_count"],
            "n_gt_boxes": d["meta"]["gt_annotation_count"],
            "preds_file": os.path.basename(pred_p),
            "preds_md5": md5f(pred_p),
            "gt_md5": gt_md5,
        })
        for cls, v in d["coco_ap"]["per_class"].items():
            pc_rows.append({"model": name, "class": cls,
                            "AP50": v["AP50"], "AP75": v["AP75"],
                            "AP50_95": v["AP50_95"]})
        print("%-24s AP50:95=%.6f" % (name, rows[-1]["AP50_95"]))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print("wrote", a.out)

    if a.per_class_out:
        os.makedirs(os.path.dirname(os.path.abspath(a.per_class_out)), exist_ok=True)
        with open(a.per_class_out, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["model", "class", "AP50", "AP75", "AP50_95"])
            w.writeheader()
            w.writerows(pc_rows)
        print("wrote %s (%d rows)" % (a.per_class_out, len(pc_rows)))


if __name__ == "__main__":
    main()
