# -*- coding: utf-8 -*-
"""Rebuild the paired training-label optimisation table (paper Table 12) from frozen dumps.

Thresholds are NOT re-tuned here: each run's threshold is read from
`val_threshold_rtdetr_T16_T<k>.json`, which records the val selection (`split_tuned_on: val`).
T0 and T1 are evaluated separately with their own val-selected threshold (the paper protocol),
so the delta is paired but each arm sits at its own operating point.

Output is long-form (scope, metric, T0, T1, delta_T1_minus_T0), one block for overall AP,
one for the IoU 0.30 / 0.50 task metrics, one per class, matching
the paired-delta CSV.

Usage:
    python reproduce_t16.py \
        --gt ../annotations/g3/instances_test.json \
        --preds-dir ../dumps/t16 \
        --thresholds-dir ../dumps/t16 \
        --base-config ../configs/t16/coco_detection_T0.yml \
        --out ../results/recomputed_t16.csv
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

TAGS = ("T0", "T1")
AP_KEYS = ("AP50", "AP75", "AP50_95", "AR100")
TASK_KEYS = ("TP", "FP", "FN", "precision", "recall", "F1",
             "macro_precision", "macro_recall", "macro_F1")
CLASS_KEYS = ("AP50", "AP75", "AP50_95")


def md5(p: str) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", required=True)
    ap.add_argument("--preds-dir", required=True)
    ap.add_argument("--thresholds-dir", required=True)
    ap.add_argument("--base-config", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    dump = {t: os.path.join(a.preds_dir, "preds_rtdetr_T16_%s_test.json" % t) for t in TAGS}
    thr_p = {t: os.path.join(a.thresholds_dir, "val_threshold_rtdetr_T16_%s.json" % t)
             for t in TAGS}
    for p in [a.gt, a.base_config] + list(dump.values()) + list(thr_p.values()):
        if not os.path.exists(p):
            raise SystemExit("missing required file: %s" % p)

    # T0 and T1 must have scored the same test images for the paired delta to mean anything.
    ids = {t: set(json.load(open(dump[t], encoding="utf-8"))["image_ids"]) for t in TAGS}
    if ids["T0"] != ids["T1"]:
        raise SystemExit("T0/T1 test image sets differ: |T0\\T1|=%d |T1\\T0|=%d"
                         % (len(ids["T0"] - ids["T1"]), len(ids["T1"] - ids["T0"])))
    print("test images: %d (identical across T0/T1)" % len(ids["T0"]))
    print("test GT md5: %s" % md5(a.gt))

    res = {}
    for t in TAGS:
        j = json.load(open(thr_p[t], encoding="utf-8"))
        if j.get("split_tuned_on") != "val":
            raise SystemExit("%s was not tuned on val" % thr_p[t])
        conf = float(j["chosen_confidence_threshold"])
        cfg = H.load_config(a.base_config)
        cfg["confidence_threshold"] = conf
        d = H.evaluate_all(a.gt, dump[t], cfg, model_name="RT-DETR-v2-R18 / T16-%s" % t)
        res[t] = {"conf": conf,
                  "ap": d["coco_ap"]["overall"],
                  "per_class": d["coco_ap"]["per_class"],
                  "task": d["task_oriented"]}
        print("%s conf=%.4f AP50:95=%.6f" % (t, conf, res[t]["ap"]["AP50_95"]))

    rows = []

    def add(scope, metric, va, vb):
        rows.append({"scope": scope, "metric": metric, "T0": va, "T1": vb,
                     "delta_T1_minus_T0": (None if va is None or vb is None else vb - va)})

    for k in AP_KEYS:
        add("overall", k, res["T0"]["ap"][k], res["T1"]["ap"][k])
    for iou in ("iou30", "iou50"):
        oa = res["T0"]["task"][iou]["overall"]
        ob = res["T1"]["task"][iou]["overall"]
        for k in TASK_KEYS:
            add("overall", "%s.%s" % (iou, k), oa[k], ob[k])
    names = [c["name"] for c in json.load(open(a.gt, encoding="utf-8"))["categories"]]
    for cls in names:
        pa = res["T0"]["per_class"].get(cls, {})
        pb = res["T1"]["per_class"].get(cls, {})
        for k in CLASS_KEYS:
            add("class:%s" % cls, k, pa.get(k), pb.get(k))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scope", "metric", "T0", "T1",
                                          "delta_T1_minus_T0"])
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if v is None else repr(v) if isinstance(v, float) else v)
                        for k, v in r.items()})
    print("wrote %s (%d rows)" % (a.out, len(rows)))


if __name__ == "__main__":
    main()
