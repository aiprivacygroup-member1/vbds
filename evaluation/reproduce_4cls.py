# -*- coding: utf-8 -*-
"""Rebuild the four-class audit table (paper Table 13) from prediction dumps.

Thresholds are NOT re-tuned here: they are read
from the frozen `*_threshold.json` files that selected them on val. Re-tuning on test
would silently change the operating point, so this script refuses to do it.

Usage:
    python reproduce_4cls.py --root ../dumps/four_class --out ../results/recomputed_4cls.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hzs_metrics as H  # noqa: E402

TASK_IOU = 0.30
IOU_THRS = [0.30, 0.50]

# (phase, model key, dump template, gt file, threshold template)
RUNS = [
    ("before", "rfdetr_M1", "before_rfdetr_M1_test.dump.json", "gt_before_origids_test.json", "before_rfdetr_M1_threshold.json"),
    ("before", "rfdetr_M4", "before_rfdetr_M4_test.dump.json", "gt_before_origids_test.json", "before_rfdetr_M4_threshold.json"),
    ("before", "rtdetr_M1", "before_rtdetr_M1_test.dump.json", "gt_before_origids_test.json", "before_rtdetr_M1_threshold.json"),
    ("before", "rtdetr_M4", "before_rtdetr_M4_test.dump.json", "gt_before_origids_test.json", "before_rtdetr_M4_threshold.json"),
    ("swap", "rfdetr_M1", "swap_rfdetr_M1_test.dump.json", "gt_after_origids_test.json", "swap_rfdetr_M1_threshold.json"),
    ("swap", "rfdetr_M4", "swap_rfdetr_M4_test.dump.json", "gt_after_origids_test.json", "swap_rfdetr_M4_threshold.json"),
    ("swap", "rtdetr_M1", "swap_rtdetr_M1_test.dump.json", "gt_after_origids_test.json", "swap_rtdetr_M1_threshold.json"),
    ("swap", "rtdetr_M4", "swap_rtdetr_M4_test.dump.json", "gt_after_origids_test.json", "swap_rtdetr_M4_threshold.json"),
    ("after", "rfdetr", "preds_rfdetr_test_4cls.json", "instances_test.json", "after_rfdetr_threshold.json"),
    ("after", "rtdetr", "preds_rtdetr_test_4cls.json", "instances_test.json", "after_rtdetr_threshold.json"),
]

COLS = ["phase", "model", "conf", "P@30", "R@30", "F1@30", "AP50", "AP50_95", "n_gt"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="directory with the four-class dumps")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = []
    for phase, model, dump_name, gt_name, thr_name in RUNS:
        gt_p = os.path.join(a.root, "gt", gt_name)
        dump_p = os.path.join(a.root, "predictions", dump_name)
        thr_p = os.path.join(a.root, "thresholds", thr_name)
        for p in (gt_p, dump_p, thr_p):
            if not os.path.exists(p):
                raise SystemExit("missing required file: %s" % p)
        conf = float(json.load(open(thr_p, encoding="utf-8"))["chosen"])
        cfg = {"split": "test", "task_iou_threshold": TASK_IOU,
               "eval_iou_thresholds": IOU_THRS, "confidence_threshold": conf,
               "scene_like_classes": []}
        d = H.evaluate_all(gt_p, dump_p, cfg, model_name="%s_%s" % (model, phase))
        ov30 = d["task_oriented"]["iou30"]["overall"]
        ap = d["coco_ap"]["overall"]
        rows.append({
            "phase": phase, "model": model, "conf": conf,
            "P@30": ov30["precision"], "R@30": ov30["recall"], "F1@30": ov30["F1"],
            "AP50": ap["AP50"], "AP50_95": ap["AP50_95"],
            "n_gt": d["meta"]["gt_annotation_count"],
        })
        print("%-7s %-10s conf=%.2f AP50:95=%.4f" % (phase, model, conf, ap["AP50_95"]))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
