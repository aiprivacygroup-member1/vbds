# -*- coding: utf-8 -*-
"""Rebuild the whole/tiled M1-M4 matrix (paper Table 10) from prediction dumps.

CONVENTION: this table reports the **arithmetic mean of per-class AP** (`AP_all_classes`),
not pycocotools' overall AP used in Table 7. The two differ because the mean weights every
class equally. Do not cross-compare the columns.

GT is G2 (post-re-annotation, pre-dedup; 9,820 boxes), which is what the archived matrix used.

Usage:
    python reproduce_b_matrix.py \
        --preds-dir ../dumps/whole_tiled \
        --configs-dir ../configs/whole_tiled \
        --gt ../annotations/g2/instances_test.json \
        --out ../results/recomputed_B_matrix.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hzs_metrics as H  # noqa: E402

RUNS = [(m, k) for m in ("rfdetr", "rtdetr") for k in ("M1", "M2", "M3", "M4")]
COLS = ["model", "variant", "conf", "P@0.30", "R@0.30", "F1@0.30",
        "P@0.50", "R@0.50", "F1@0.50", "mAP50", "mAP75", "mAP50_95"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds-dir", required=True)
    ap.add_argument("--fallback-preds-dir", default=None,
                    help="M4 dumps live with experiment A, not B")
    ap.add_argument("--configs-dir", required=True)
    ap.add_argument("--gt", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = []
    for model, variant in RUNS:
        cfg_p = os.path.join(a.configs_dir, "config_%s_%s.yaml" % (model, variant))
        pred_p = os.path.join(a.preds_dir, "preds_%s_test_%s.json" % (model, variant))
        if not os.path.exists(pred_p) and a.fallback_preds_dir:
            pred_p = os.path.join(a.fallback_preds_dir,
                                  "preds_%s_test_%s.json" % (model, variant))
        if not (os.path.exists(cfg_p) and os.path.exists(pred_p)):
            print("skip %s %s" % (model, variant))
            continue
        cfg = H.load_config(cfg_p)  # B configs carry the thresholds used for this table
        d = H.evaluate_all(a.gt, pred_p, cfg, model_name="%s_%s" % (model, variant))
        ov30 = d["task_oriented"]["iou30"]["overall"]
        ov50 = d["task_oriented"]["iou50"]["overall"]
        per = d["coco_ap"]["per_class"]

        def cmean(metric):
            v = [x[metric] for x in per.values() if not (x[metric] != x[metric])]
            return sum(v) / len(v) if v else float("nan")

        rows.append({
            "model": model, "variant": variant, "conf": d["meta"]["confidence_threshold"],
            "P@0.30": ov30["precision"], "R@0.30": ov30["recall"], "F1@0.30": ov30["F1"],
            "P@0.50": ov50["precision"], "R@0.50": ov50["recall"], "F1@0.50": ov50["F1"],
            "mAP50": cmean("AP50"), "mAP75": cmean("AP75"), "mAP50_95": cmean("AP50_95"),
        })
        print("%-8s %-3s conf=%.2f mAP50:95=%.4f" % (model, variant, rows[-1]["conf"],
                                                     rows[-1]["mAP50_95"]))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
