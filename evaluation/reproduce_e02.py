# -*- coding: utf-8 -*-
"""Rebuild the E02 scene-isolated test table (paper Table 15) from the frozen dump.

Two test sets:
  full_1543    all test images of the v2 scene-group split (primary result)
  strict_1541  minus the 2 images in groups flagged as near-duplicate leakage (sensitivity)

AP is threshold-independent, so no confidence threshold is involved here.

Usage:
    python reproduce_e02.py \
        --gt ../annotations/final/instances_test.json \
        --preds ../dumps/e02/preds_e02_v2_test.json \
        --subset ../dumps/e02/e02_v2_clean_test_subset.csv \
        --out ../results/recomputed_E02.csv
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def coco_stats(gt: dict, preds: list) -> dict:
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    coco_gt = COCO()
    coco_gt.dataset = gt
    coco_gt.createIndex()
    results = [{"image_id": int(p["image_id"]), "category_id": int(p["category_id"]),
                "bbox": [float(v) for v in p["bbox"]], "score": float(p["score"])}
               for p in preds]
    with open(os.devnull, "w") as devnull, contextlib.redirect_stdout(devnull):
        coco_dt = coco_gt.loadRes(results)
        ev = COCOeval(coco_gt, coco_dt, "bbox")
        ev.evaluate()
        ev.accumulate()
        ev.summarize()
    s = np.asarray(ev.stats, dtype=np.float64)  # 12 standard COCO entries
    return {"AP50_95": s[0], "AP50": s[1], "AP75": s[2],
            "AP_small": s[3], "AP_medium": s[4], "AP_large": s[5],
            "AR_at_1": s[6], "AR_at_10": s[7], "AR_at_100": s[8]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", required=True)
    ap.add_argument("--preds", required=True)
    ap.add_argument("--subset", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    gt = json.load(open(a.gt, encoding="utf-8"))
    dump = json.load(open(a.preds, encoding="utf-8"))
    preds = dump["predictions"]
    gt_ids = {im["id"] for im in gt["images"]}
    if set(int(x) for x in dump["image_ids"]) != gt_ids:
        raise SystemExit("dump image_ids != GT image_ids")

    kept = {r["image_name"] for r in csv.DictReader(open(a.subset, encoding="utf-8-sig"))
            if r["inclusion"] == "included"}
    name_of = {im["file_name"]: im["id"] for im in gt["images"]}
    keep_ids = {name_of[n] for n in kept if n in name_of}
    sub_gt = {"images": [im for im in gt["images"] if im["id"] in keep_ids],
              "annotations": [x for x in gt["annotations"] if x["image_id"] in keep_ids],
              "categories": gt["categories"]}
    sub_preds = [p for p in preds if int(p["image_id"]) in keep_ids]

    rows = []
    for tag, g, p in (("full_1543", gt, preds), ("strict_1541", sub_gt, sub_preds)):
        if tag == "full_1543":
            assert len(g["images"]) == 1543, len(g["images"])
        else:
            assert len(g["images"]) == 1541, len(g["images"])
        s = coco_stats(g, p)
        rows.append({"test_set": tag, **{k: "%.6f" % v for k, v in s.items()},
                     "n_images": len(g["images"]), "n_boxes": len(g["annotations"])})
        print("%-12s images=%d boxes=%d AP50:95=%.6f"
              % (tag, len(g["images"]), len(g["annotations"]), s["AP50_95"]))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
