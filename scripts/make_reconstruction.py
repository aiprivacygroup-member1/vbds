# -*- coding: utf-8 -*-
"""Emit the reconstruction manifest for the non-redistributable images.

The manifest records file name, split (G3 and final), source unit, dimensions, byte size and
MD5 for every image that is not in the public release. It contains no image data and no
annotation coordinates.

Usage:
  python make_reconstruction.py --artifact <public artifact> --release <VBDS_release>
"""
from __future__ import annotations
import argparse, csv, json, os
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--release", required=True)
    a = ap.parse_args()

    rows = list(csv.DictReader(open(os.path.join(a.artifact, "manifests/image_index.csv"),
                                    encoding="utf-8-sig")))
    rest = [r for r in rows if r["redistributable"] != "yes"]
    print("restricted images:", len(rest))

    out_dir = os.path.join(a.release, "reconstruction")
    os.makedirs(out_dir, exist_ok=True)

    cols = ["file_name", "split_g3", "split_final", "source_unit", "source_name",
            "width", "height", "size_bytes", "image_md5"]
    rest.sort(key=lambda r: (r["source_unit"], r["split_final"], r["file_name"]))
    with open(os.path.join(out_dir, "reconstruction_manifest.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rest:
            w.writerow([r[c] for c in cols])

    per = defaultdict(lambda: {"images": 0, "bytes": 0, "splits": defaultdict(int),
                               "name": None})
    for r in rest:
        d = per[r["source_unit"]]
        d["images"] += 1
        d["bytes"] += int(r["size_bytes"])
        d["splits"][r["split_final"]] += 1
        d["name"] = r["source_name"]

    inv = {r["id"]: r for r in csv.DictReader(open(os.path.join(a.artifact,
                                                               "docs/source_inventory.csv"),
                                                   encoding="utf-8-sig"))}
    mapping = {}
    for sid in sorted(per):
        d = per[sid]
        mapping[sid] = {
            "source_name": d["name"],
            "inventory_name": inv[sid]["name"],
            "site": inv[sid]["site"],
            "paper": inv[sid]["paper"],
            "declared_license": inv[sid]["license_name"],
            "license_url": inv[sid]["license_url"],
            "images": d["images"],
            "bytes": d["bytes"],
            "splits": dict(d["splits"]),
            "public_release": False,
            "reason": "Redistribution not granted; see SOURCE_LICENSES.md.",
            "verification": "MD5 and byte size of each file as used in the experiments",
        }
    json.dump({"version": "1.0", "sources": mapping,
               "total_images": len(rest),
               "total_bytes": sum(int(r["size_bytes"]) for r in rest)},
              open(os.path.join(out_dir, "source_mapping.json"), "w"), indent=2,
              ensure_ascii=False)
    print("wrote", out_dir)
    print("total bytes:", sum(int(r["size_bytes"]) for r in rest))


if __name__ == "__main__":
    main()
