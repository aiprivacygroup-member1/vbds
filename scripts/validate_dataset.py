# -*- coding: utf-8 -*-
"""Validate a VBDS release tree.

Checks structure, taxonomy consistency, referential integrity, geometry, exact duplicates and the
agreement between split lists and annotation files. Optionally verifies that every annotated
image is present on disk.

The script is read-only.

Usage:
  python validate_dataset.py --annotations annotations --splits splits
  python validate_dataset.py --annotations annotations --splits splits \
      --images /data/VBDS/images --out reports/validation_public.json

Exit code: 0 if no check failed, 1 if any check failed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict

VERSIONS = ("g3", "final")
SPLITS = ("train", "val", "test")
EXPECTED_CATEGORIES = 26
EXPECTED_IDS = list(range(EXPECTED_CATEGORIES))


class Report:
    def __init__(self):
        self.checks = []
        self.stats = {"versions": {}, "images_on_disk": {}}

    def add(self, cid, name, status, detail, **extra):
        self.checks.append({"id": cid, "name": name, "status": status, "detail": detail, **extra})

    def ok(self, cid, name, detail=""):
        self.add(cid, name, "pass", detail)

    def warn(self, cid, name, detail):
        self.add(cid, name, "warn", detail)

    def fail(self, cid, name, detail):
        self.add(cid, name, "fail", detail)

    @property
    def n_fail(self):
        return sum(1 for c in self.checks if c["status"] == "fail")

    @property
    def n_warn(self):
        return sum(1 for c in self.checks if c["status"] == "warn")

    @property
    def n_pass(self):
        return sum(1 for c in self.checks if c["status"] == "pass")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def index_images(root):
    """basename -> list of paths, and (split_dir, basename) -> path."""
    by_name = defaultdict(list)
    for dp, _, files in os.walk(root):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")):
                by_name[f].append(os.path.join(dp, f))
    return by_name


def check_structure(rep, ann_dir):
    for version in VERSIONS:
        for split in SPLITS:
            p = os.path.join(ann_dir, version, "instances_%s.json" % split)
            if os.path.exists(p):
                rep.ok("structure.%s.%s" % (version, split), "annotation file present",
                       os.path.relpath(p, os.path.dirname(ann_dir.rstrip("/\\")) or "."))
            else:
                rep.fail("structure.%s.%s" % (version, split), "annotation file missing", p)


def check_taxonomy(rep, files):
    signatures = {}
    for key, data in files.items():
        cats = data.get("categories", [])
        sig = [(c.get("id"), c.get("name")) for c in cats]
        signatures[key] = sig
        ids = [c.get("id") for c in cats]
        if len(cats) != EXPECTED_CATEGORIES:
            rep.fail("taxonomy.count.%s" % key, "category count", "found %d, expected %d" % (len(cats), EXPECTED_CATEGORIES))
        elif ids != EXPECTED_IDS:
            rep.fail("taxonomy.ids.%s" % key, "category ids", "found %s" % ids)
        else:
            rep.ok("taxonomy.ids.%s" % key, "26 categories, ids 0-25", "ok")
    distinct = {tuple(v) for v in signatures.values()}
    if len(distinct) == 1:
        rep.ok("taxonomy.consistency", "identical category table in every file", "%d files" % len(files))
    else:
        rep.fail("taxonomy.consistency", "category tables differ across files",
                 "%d distinct tables" % len(distinct))


def check_referential(rep, files):
    for key, data in files.items():
        imgs = data.get("images", [])
        anns = data.get("annotations", [])
        img_ids = [im.get("id") for im in imgs]
        dup_img = [k for k, v in Counter(img_ids).items() if v > 1]
        if dup_img:
            rep.fail("ref.image_ids.%s" % key, "image ids unique", "%d duplicated" % len(dup_img))
        else:
            rep.ok("ref.image_ids.%s" % key, "image ids unique", "%d images" % len(imgs))

        ann_ids = [a.get("id") for a in anns]
        dup_ann = [k for k, v in Counter(ann_ids).items() if v > 1]
        if dup_ann:
            rep.fail("ref.annotation_ids.%s" % key, "annotation ids unique", "%d duplicated" % len(dup_ann))
        else:
            rep.ok("ref.annotation_ids.%s" % key, "annotation ids unique", "%d annotations" % len(anns))

        idset = set(img_ids)
        missing = [a for a in anns if a.get("image_id") not in idset]
        if missing:
            rep.fail("ref.missing_image.%s" % key, "every annotation resolves to an image",
                     "%d annotations reference a missing image" % len(missing))
        else:
            rep.ok("ref.missing_image.%s" % key, "every annotation resolves to an image", "ok")

        bad_cat = [a for a in anns if a.get("category_id") not in set(EXPECTED_IDS)]
        if bad_cat:
            rep.fail("ref.category_range.%s" % key, "category_id within 0-25",
                     "%d out of range" % len(bad_cat))
        else:
            rep.ok("ref.category_range.%s" % key, "category_id within 0-25", "ok")

        no_box = [im for im in imgs if im.get("width", 0) <= 0 or im.get("height", 0) <= 0]
        if no_box:
            rep.fail("ref.image_size.%s" % key, "positive image dimensions",
                     "%d images with non-positive size" % len(no_box))
        else:
            rep.ok("ref.image_size.%s" % key, "positive image dimensions", "ok")


def check_geometry(rep, files):
    for key, data in files.items():
        dims = {im["id"]: (im["width"], im["height"]) for im in data["images"]}
        bad_shape, out_of_bounds, nonpositive = [], [], []
        for a in data["annotations"]:
            b = a.get("bbox")
            if not isinstance(b, list) or len(b) != 4:
                bad_shape.append(a["id"])
                continue
            x, y, w, h = b
            if w <= 0 or h <= 0:
                nonpositive.append(a["id"])
                continue
            iw, ih = dims[a["image_id"]]
            if x < 0 or y < 0 or x + w > iw + 0.5 or y + h > ih + 0.5:
                out_of_bounds.append(a["id"])
        if bad_shape:
            rep.fail("geom.shape.%s" % key, "bbox is [x, y, w, h]", "%d malformed" % len(bad_shape))
        else:
            rep.ok("geom.shape.%s" % key, "bbox is [x, y, w, h]", "ok")
        if nonpositive:
            rep.fail("geom.positive.%s" % key, "w and h positive", "%d non-positive" % len(nonpositive))
        else:
            rep.ok("geom.positive.%s" % key, "w and h positive", "ok")
        if out_of_bounds:
            rep.warn("geom.bounds.%s" % key, "bbox inside image bounds",
                     "%d boxes exceed the image rectangle (first ids: %s)"
                     % (len(out_of_bounds), out_of_bounds[:5]))
        else:
            rep.ok("geom.bounds.%s" % key, "bbox inside image bounds", "ok")


def check_duplicates(rep, files):
    for key, data in files.items():
        seen = Counter()
        for a in data["annotations"]:
            b = a["bbox"]
            seen[(a["image_id"], a["category_id"], round(b[0], 6), round(b[1], 6),
                  round(b[2], 6), round(b[3], 6))] += 1
        dups = sum(v - 1 for v in seen.values() if v > 1)
        n_groups = sum(1 for v in seen.values() if v > 1)
        if dups == 0:
            rep.ok("dup.%s" % key, "no exact duplicate boxes", "0")
        elif key in ("final.train",):
            rep.warn("dup.%s" % key, "exact duplicate boxes present",
                     "%d extra rows in %d groups (documented in docs/annotation_protocol.md §5)"
                     % (dups, n_groups))
        else:
            rep.fail("dup.%s" % key, "exact duplicate boxes present",
                     "%d extra rows in %d groups" % (dups, n_groups))


def check_splits(rep, split_dir, files):
    for version in VERSIONS:
        for split in SPLITS:
            p = os.path.join(split_dir, "%s_%s.csv" % (version, split))
            key = "%s.%s" % (version, split)
            if key not in files:
                continue
            if not os.path.exists(p):
                rep.fail("split.file.%s" % key, "split list present", p)
                continue
            with open(p, encoding="utf-8-sig") as f:
                names = {r["file_name"] for r in csv.DictReader(f)}
            ann_names = {os.path.basename(im["file_name"]) for im in files[key]["images"]}
            if names == ann_names:
                rep.ok("split.match.%s" % key, "split list matches annotation file",
                       "%d images" % len(names))
            else:
                rep.fail("split.match.%s" % key, "split list matches annotation file",
                         "only in csv: %d, only in annotations: %d"
                         % (len(names - ann_names), len(ann_names - names)))


def check_images(rep, img_root, files):
    by_name = index_images(img_root)
    rep.stats["images_on_disk"]["files"] = sum(len(v) for v in by_name.values())
    for key, data in files.items():
        needed = {os.path.basename(im["file_name"]) for im in data["images"]}
        absent = [n for n in needed if n not in by_name]
        if absent:
            rep.fail("img.present.%s" % key, "every annotated image is on disk",
                     "%d missing (first: %s)" % (len(absent), absent[:5]))
        else:
            rep.ok("img.present.%s" % key, "every annotated image is on disk",
                   "%d images, %d files on disk" % (len(needed), len(by_name)))
        ambiguous = [n for n in needed if len(by_name.get(n, [])) > 1]
        if ambiguous:
            rep.warn("img.ambiguous.%s" % key, "image basenames unique on disk",
                     "%d basenames resolve to more than one file (first: %s)"
                     % (len(ambiguous), ambiguous[:5]))
        else:
            rep.ok("img.ambiguous.%s" % key, "image basenames unique on disk", "ok")


def describe(files):
    for key, data in files.items():
        version, split = key.split(".")
        counts = Counter(a["category_id"] for a in data["annotations"])
        names = {c["id"]: c["name"] for c in data["categories"]}
        rep_stats = {
            "images": len(data["images"]),
            "boxes": len(data["annotations"]),
            "per_class": {names[k]: counts.get(k, 0) for k in sorted(names)},
        }
        if "info" in data:
            rep_stats["info"] = data["info"]
        yield version, split, rep_stats


def to_markdown(rep, meta):
    lines = []
    lines.append("# Validation report\n")
    lines.append("Generated by `scripts/validate_dataset.py` (read-only).\n")
    lines.append("| | |\n|---|---|")
    for k, v in meta.items():
        lines.append("| %s | %s |" % (k, v))
    lines.append("")
    lines.append("## Summary\n")
    lines.append("| checks passed | warnings | failures |\n|---:|---:|---:|")
    lines.append("| %d | %d | %d |" % (rep.n_pass, rep.n_warn, rep.n_fail))
    lines.append("")
    fails = [c for c in rep.checks if c["status"] == "fail"]
    warns = [c for c in rep.checks if c["status"] == "warn"]
    if fails:
        lines.append("## Failures\n")
        lines.append("| check | detail |\n|---|---|")
        for c in fails:
            lines.append("| `%s` | %s |" % (c["id"], c["detail"]))
        lines.append("")
    if warns:
        lines.append("## Warnings\n")
        lines.append("| check | detail |\n|---|---|")
        for c in warns:
            lines.append("| `%s` | %s |" % (c["id"], c["detail"]))
        lines.append("")
    lines.append("## Counts\n")
    lines.append("| version | split | images | boxes |")
    lines.append("|---|---|---:|---:|")
    for version in VERSIONS:
        for split in SPLITS:
            s = rep.stats["versions"].get("%s.%s" % (version, split))
            if s:
                lines.append("| %s | %s | %d | %d |" % (version, split, s["images"], s["boxes"]))
    lines.append("")
    lines.append("## Per-class boxes\n")
    first = rep.stats["versions"].get("g3.test")
    if first:
        lines.append("| class | g3 test |")
        lines.append("|---|---:|")
        for k, v in first["per_class"].items():
            lines.append("| `%s` | %d |" % (k, v))
        lines.append("")
    lines.append("## All checks\n")
    lines.append("| id | status | detail |\n|---|---|---|")
    for c in rep.checks:
        lines.append("| `%s` | %s | %s |" % (c["id"], c["status"], c["detail"]))
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotations", required=True, help="directory containing g3/ and final/")
    ap.add_argument("--splits", required=True, help="directory containing {version}_{split}.csv")
    ap.add_argument("--images", default=None, help="optional root of extracted images")
    ap.add_argument("--out", default="reports/validation.json")
    ap.add_argument("--md", default=None, help="Markdown output path (default: alongside --out)")
    args = ap.parse_args()

    rep = Report()
    check_structure(rep, args.annotations)

    files = {}
    for version in VERSIONS:
        for split in SPLITS:
            key = "%s.%s" % (version, split)
            p = os.path.join(args.annotations, version, "instances_%s.json" % split)
            if not os.path.exists(p):
                continue
            try:
                files[key] = load_json(p)
            except Exception as e:                                    # noqa: BLE001
                rep.fail("parse.%s" % key, "annotation file parses", "%s: %s" % (type(e).__name__, e))

    if files:
        check_taxonomy(rep, files)
        check_referential(rep, files)
        check_geometry(rep, files)
        check_duplicates(rep, files)
        check_splits(rep, args.splits, files)
        for version, split, s in describe(files):
            rep.stats["versions"]["%s.%s" % (version, split)] = s
        if args.images:
            check_images(rep, args.images, files)

    meta = {
        "dataset": "VBDS v1.0",
        "annotations": args.annotations,
        "splits": args.splits,
        "images": args.images if args.images else "(not checked)",
        "files_checked": len(files),
    }
    result = {"meta": meta, "summary": {"pass": rep.n_pass, "warn": rep.n_warn, "fail": rep.n_fail},
              "stats": rep.stats, "checks": rep.checks}

    out = args.out
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    md = args.md or os.path.splitext(out)[0] + ".md"
    os.makedirs(os.path.dirname(os.path.abspath(md)), exist_ok=True)
    with open(md, "w", encoding="utf-8") as f:
        f.write(to_markdown(rep, meta))

    print("%d checks: %d pass, %d warn, %d fail" % (len(rep.checks), rep.n_pass, rep.n_warn, rep.n_fail))
    for c in rep.checks:
        if c["status"] != "pass":
            print("  [%s] %s: %s" % (c["status"], c["id"], c["detail"]))
    print("wrote", out, "and", md)
    return 1 if rep.n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
