# -*- coding: utf-8 -*-
"""Build the VBDS public subset (images already live in the public artifact tree).

- Reads manifests/image_index.csv to decide, per (split, file_name), whether the image is
  redistributable.
- Filters the G3 and final COCO annotation files to redistributable images only.
- Keeps image_id / annotation_id / category_id unchanged (no renumbering).
- Emits splits, statistics and a file-level public manifest.

Usage:
  python build_vbds.py --artifact /path/to/public_artifact --out /path/to/VBDS_release/public
"""
from __future__ import annotations
import argparse, csv, json, os, shutil
from collections import Counter, defaultdict


def load_index(artifact):
    rows = list(csv.DictReader(open(os.path.join(artifact, "manifests/image_index.csv"),
                                    encoding="utf-8-sig")))
    return rows


def filter_coco(src, keep_names, dst):
    data = json.load(open(src, encoding="utf-8"))
    imgs = [im for im in data["images"] if os.path.basename(im["file_name"]) in keep_names]
    ids = {im["id"] for im in imgs}
    anns = [a for a in data["annotations"] if a["image_id"] in ids]
    out = {"info": data.get("info", {}), "licenses": data.get("licenses", []),
           "images": imgs, "annotations": anns, "categories": data["categories"]}
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = load_index(a.artifact)
    public = [r for r in rows if r["redistributable"] == "yes"]
    restricted = [r for r in rows if r["redistributable"] != "yes"]
    print("public images:", len(public), "restricted:", len(restricted))

    os.makedirs(os.path.join(a.out, "annotations/g3"), exist_ok=True)
    os.makedirs(os.path.join(a.out, "annotations/final"), exist_ok=True)
    os.makedirs(os.path.join(a.out, "splits"), exist_ok=True)
    os.makedirs(os.path.join(a.out, "metadata"), exist_ok=True)

    keep = defaultdict(set)          # (version, split) -> names
    for r in public:
        # One fMoW image was renamed to ...__dup2.jpg in the final annotations; G3 keeps the
        # original name. Add both spellings so neither version loses the image.
        keep[("g3", r["split_g3"])].add(r["file_name"].replace("__dup2", ""))
        keep[("final", r["split_final"])].add(r["file_name"])

    stats = {"public": {}, "restricted": {}, "full": {}}
    for version, adir in (("g3", "annotations_g3"), ("final", "annotations_final")):
        for split in ("train", "val", "test"):
            src = os.path.join(a.artifact, "datasets", adir, "instances_%s.json" % split)
            dst = os.path.join(a.out, "annotations", version, "instances_%s.json" % split)
            out = filter_coco(src, keep[(version, split)], dst)
            stats["public"].setdefault(version, {})[split] = {
                "images": len(out["images"]), "annotations": len(out["annotations"])}
            print(version, split, len(out["images"]), len(out["annotations"]))

    # restricted stats = full - public
    for version in ("g3", "final"):
        full = {}
        for split in ("train", "val", "test"):
            data = json.load(open(os.path.join(a.artifact, "datasets",
                                               "annotations_g3" if version == "g3" else "annotations_final",
                                               "instances_%s.json" % split), encoding="utf-8"))
            full[split] = {"images": len(data["images"]), "annotations": len(data["annotations"])}
        stats["full"][version] = full
        stats["restricted"][version] = {
            s: {"images": full[s]["images"] - stats["public"][version][s]["images"],
                "annotations": full[s]["annotations"] - stats["public"][version][s]["annotations"]}
            for s in full}

    # public split lists
    for version, skey in (("g3", "split_g3"), ("final", "split_final")):
        per_split = defaultdict(list)
        for r in public:
            per_split[r[skey]].append(r)
        for split, rs in per_split.items():
            rs.sort(key=lambda x: x["file_name"])
            with open(os.path.join(a.out, "splits", "%s_%s.csv" % (version, split)), "w",
                      newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["file_name", "source_unit", "source_name", "image_id", "width", "height"])
                for r in rs:
                    # G3 keeps the pre-rename name for one fMoW image; the split list must match
                    # the annotation file it belongs to.
                    name = r["file_name"].replace("__dup2", "") if version == "g3" else r["file_name"]
                    w.writerow([name, r["source_unit"], r["source_name"],
                                r["image_id_g3"] if version == "g3" else r["image_id_final"],
                                r["width"], r["height"]])

    # file-level public manifest (images live under datasets/public/images/<split>/)
    with open(os.path.join(a.out, "metadata", "public_image_manifest.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file_name", "split_g3", "split_final", "source_unit", "source_name",
                    "width", "height", "size_bytes", "image_md5", "rel_path_g3", "rel_path_final"])
        for r in sorted(public, key=lambda x: (x["source_unit"], x["file_name"])):
            w.writerow([r["file_name"], r["split_g3"], r["split_final"], r["source_unit"],
                        r["source_name"], r["width"], r["height"], r["size_bytes"],
                        r["image_md5"],
                        "images/%s/%s" % (r["split_final"], r["file_name"]),
                        "images/%s/%s" % (r["split_final"], r["file_name"])])

    # class distribution
    def class_stats(coco_paths):
        c = Counter(); per_split = {}
        for p in coco_paths:
            d = json.load(open(p, encoding="utf-8"))
            c.update(x["category_id"] for x in d["annotations"])
            per_split[os.path.basename(p)] = len(d["annotations"])
        return c, per_split

    cats = {c["id"]: c["name"] for c in json.load(open(
        os.path.join(a.out, "annotations/g3/instances_test.json"), encoding="utf-8"))["categories"]}
    paths = [os.path.join(a.out, "annotations/g3/instances_%s.json" % s) for s in ("train", "val", "test")]
    cc, ps = class_stats(paths)
    stats["public"]["per_class_g3"] = {cats[k]: cc.get(k, 0) for k in sorted(cats)}
    stats["public"]["g3_boxes_total"] = sum(cc.values())
    stats["public"]["g3_boxes_per_split"] = ps

    json.dump(stats, open(os.path.join(a.out, "metadata", "statistics.json"), "w"), indent=2)
    print("public G3 boxes:", sum(cc.values()))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
