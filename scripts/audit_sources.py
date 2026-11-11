# -*- coding: utf-8 -*-
"""Audit the existing artifact trees and emit machine-readable facts for the VBDS release."""
import csv, json, os, sys
from collections import defaultdict, Counter

# Paths to the two staging trees and the output directory. Override with
# VBDS_PUBLIC_TREE / VBDS_RESTRICTED_TREE / VBDS_AUDIT_OUT.
PUB = os.environ.get("VBDS_PUBLIC_TREE", "LVBD-Sen-ICDE2027")
RES = os.environ.get("VBDS_RESTRICTED_TREE", "LVBD-Sen-Restricted")
OUT = os.environ.get("VBDS_AUDIT_OUT", "audit")
os.makedirs(OUT, exist_ok=True)

rows = list(csv.DictReader(open(os.path.join(PUB, "manifests/image_index.csv"), encoding="utf-8-sig")))
print("image_index rows:", len(rows))

by_src = defaultdict(lambda: {"images": 0, "bytes": 0, "boxes_g3": 0, "boxes_final": 0,
                              "splits_g3": Counter(), "splits_final": Counter(),
                              "redistributable": Counter(), "license_class": Counter(),
                              "source_name": None})
for r in rows:
    s = r["source_unit"]
    d = by_src[s]
    d["images"] += 1
    d["bytes"] += int(r["size_bytes"])
    d["boxes_g3"] += int(r["n_boxes_g3"])
    d["boxes_final"] += int(r["n_boxes_final"])
    d["splits_g3"][r["split_g3"]] += 1
    d["splits_final"][r["split_final"]] += 1
    d["redistributable"][r["redistributable"]] += 1
    d["license_class"][r["license_class"]] += 1
    d["source_name"] = r["source_name"]

print("sources:", len(by_src))
tot = {"images": 0, "bytes": 0, "boxes_g3": 0, "boxes_final": 0}
for s in sorted(by_src):
    d = by_src[s]
    print(s, d["source_name"], d["images"], round(d["bytes"]/1e6, 1), "MB",
          d["boxes_g3"], d["boxes_final"], dict(d["splits_g3"]), dict(d["redistributable"]))
    for k in tot:
        tot[k] += d[k]
print("TOTAL", tot)

# duplicates between public and restricted asset lists
pub_assets = list(csv.DictReader(open(os.path.join(PUB, "manifests/public_assets.csv"), encoding="utf-8-sig")))
res_assets = list(csv.DictReader(open(os.path.join(RES, "manifests/restricted_assets.csv"), encoding="utf-8-sig")))
pub_keys = {(r["split"], r["file_name"]) for r in pub_assets}
res_keys = {(r["split"], r["file_name"]) for r in res_assets}
print("public assets:", len(pub_assets), "restricted assets:", len(res_assets),
      "overlap:", len(pub_keys & res_keys))

# image files on disk
def count_files(root, sub):
    n = 0; b = 0
    p = os.path.join(root, sub)
    for dp, _, fs in os.walk(p):
        for f in fs:
            n += 1; b += os.path.getsize(os.path.join(dp, f))
    return n, b

print("public images on disk:", count_files(PUB, "datasets/public/images"))
print("restricted images on disk:", count_files(RES, "images"))

json.dump({"per_source": {s: {"images": d["images"], "bytes": d["bytes"],
                              "boxes_g3": d["boxes_g3"], "boxes_final": d["boxes_final"],
                              "splits_g3": dict(d["splits_g3"]), "splits_final": dict(d["splits_final"]),
                              "redistributable": dict(d["redistributable"]),
                              "license_class": dict(d["license_class"]),
                              "source_name": d["source_name"]}
                         for s, d in by_src.items()},
           "total": tot, "source_units": len(by_src),
           "public_assets": len(pub_assets), "restricted_assets": len(res_assets)},
          open(os.path.join(OUT, "audit_source_stats.json"), "w"), indent=2, ensure_ascii=False)
print("wrote", os.path.join(OUT, "audit_source_stats.json"))
