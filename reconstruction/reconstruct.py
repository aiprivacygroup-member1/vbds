# -*- coding: utf-8 -*-
"""Check a locally obtained copy of the originals against the reconstruction manifest.

This script does not download anything and does not bypass any access control. It hashes files
you already have, compares them with the manifest, and reports which benchmark images are
covered.

Usage:
  python reconstruct.py --manifest reconstruction_manifest.csv \
      --source-root /data/originals --out reconstruction_report.json

--source-root may be given more than once; directories are searched recursively.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def index_files(roots):
    """basename -> [paths]. Originals are matched by content, so names may differ."""
    by_name = defaultdict(list)
    for root in roots:
        for dp, _, files in os.walk(root):
            for f in files:
                by_name[f].append(os.path.join(dp, f))
    return by_name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--source-root", action="append", required=True)
    ap.add_argument("--out", default="reconstruction_report.json")
    ap.add_argument("--max-bytes", type=int, default=0,
                    help="stop hashing after this many bytes of candidates (0 = no limit)")
    a = ap.parse_args()

    with open(a.manifest, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    by_name = index_files(a.source_root)
    print("files indexed under source roots:", sum(len(v) for v in by_name.values()), flush=True)

    hashed = 0
    result = {"manifest": a.manifest, "source_roots": a.source_root,
              "totals": Counter(), "per_source": defaultdict(Counter), "missing": [], "mismatch": []}
    md5_cache = {}

    for r in rows:
        sid = r["source_unit"]
        cands = by_name.get(r["file_name"], [])
        status = "absent"
        for p in cands:
            if p not in md5_cache:
                if a.max_bytes and hashed >= a.max_bytes:
                    status = "not_checked"
                    break
                md5_cache[p] = md5_file(p)
                hashed += os.path.getsize(p)
            if md5_cache[p] == r["image_md5"]:
                status = "matched"
                break
            status = "name_match_md5_differs"
        result["totals"][status] += 1
        result["per_source"][sid][status] += 1
        if status == "absent":
            result["missing"].append(r["file_name"])
        elif status not in ("matched",):
            result["mismatch"].append({"file_name": r["file_name"],
                                       "expected_md5": r["image_md5"], "status": status})

    result["totals"] = dict(result["totals"])
    result["per_source"] = {k: dict(v) for k, v in result["per_source"].items()}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(json.dumps(result["totals"], indent=2))
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
