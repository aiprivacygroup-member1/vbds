# -*- coding: utf-8 -*-
"""Verify a sha256sum-format checksum file.

Lines are `<sha256>  <relative path>` (two spaces), the format produced by sha256sum. Paths are
resolved relative to the checksum file's directory unless --base is given.

Usage:
  python verify_checksums.py --checksums release/checksums.sha256
  python verify_checksums.py --checksums release/checksums.sha256 --base /data/packages --json out.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse(path):
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            digest, name = parts
            entries.append((digest.lower(), name.lstrip("*").strip()))
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checksums", required=True)
    ap.add_argument("--base", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    base = a.base or os.path.dirname(os.path.abspath(a.checksums))
    entries = parse(a.checksums)
    rows, bad = [], 0
    for digest, name in entries:
        p = name if os.path.isabs(name) else os.path.join(base, name)
        if not os.path.exists(p):
            rows.append({"file": name, "status": "missing"})
            bad += 1
            continue
        actual = sha256_file(p)
        status = "ok" if actual == digest else "mismatch"
        if status != "ok":
            bad += 1
        rows.append({"file": name, "status": status, "expected": digest, "actual": actual,
                     "bytes": os.path.getsize(p)})

    for r in rows:
        if r["status"] != "ok":
            print("[%s] %s" % (r["status"], r["file"]))
    print("%d files: %d ok, %d failed" % (len(rows), len(rows) - bad, bad))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"checksums": a.checksums, "base": base, "files": rows,
                       "ok": len(rows) - bad, "failed": bad}, f, indent=2)
        print("wrote", a.json)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
