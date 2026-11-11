# -*- coding: utf-8 -*-
"""Assemble the VBDS/ GitHub tree from the release pieces produced earlier."""
from __future__ import annotations
import argparse, csv, json, os, shutil
from collections import defaultdict

KEEP = ["LICENSE", "README.md", "NOTICE"]


def copy_public_into_tree(rel, tree):
    for sub in ("annotations/g3", "annotations/final", "splits"):
        dst = os.path.join(tree, sub)
        os.makedirs(dst, exist_ok=True)
        src = os.path.join(rel, "public", sub)
        for f in sorted(os.listdir(src)):
            shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
    dst = os.path.join(tree, "metadata")
    os.makedirs(dst, exist_ok=True)
    for src_dir in (os.path.join(rel, "metadata"),):
        for f in sorted(os.listdir(src_dir)):
            shutil.copy2(os.path.join(src_dir, f), os.path.join(dst, f))
    os.makedirs(os.path.join(tree, "release"), exist_ok=True)
    shutil.copy2(os.path.join(rel, "metadata/release_manifest.json"),
                 os.path.join(tree, "release/release_manifest.json"))
    shutil.copy2(os.path.join(rel, "packages/checksums.sha256"),
                 os.path.join(tree, "release/checksums.sha256"))


def copy_evaluation(art, tree):
    src = os.path.join(art, "evaluation")
    dst = os.path.join(tree, "evaluation")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def copy_scripts(vbds_root, tree):
    dst = os.path.join(tree, "scripts")
    for f in ("prepare_public_release.py", "build_vbds.py", "make_metadata.py",
              "make_reconstruction.py", "audit_sources.py", "assemble_tree.py"):
        p = os.path.join(vbds_root, f)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(dst, f))


def build_examples(art, rel, tree, max_bytes=1_200_000):
    rows = list(csv.DictReader(open(os.path.join(rel, "public/metadata/public_image_manifest.csv"),
                                    encoding="utf-8-sig")))
    by_src = defaultdict(list)
    for r in rows:
        by_src[r["source_unit"]].append(r)

    img_dir = os.path.join(tree, "examples/images")
    os.makedirs(img_dir, exist_ok=True)

    # annotations, keyed by (split, basename)
    anns = {}
    for split in ("train", "val", "test"):
        d = json.load(open(os.path.join(tree, "annotations/g3/instances_%s.json" % split),
                           encoding="utf-8"))
        names = {im["id"]: (os.path.basename(im["file_name"]), im["width"], im["height"])
                 for im in d["images"]}
        by_id = defaultdict(list)
        for a in d["annotations"]:
            by_id[a["image_id"]].append(a)
        for iid, (nm, w, h) in names.items():
            anns[(split, nm)] = (w, h, by_id.get(iid, []))

    catalog = {"dataset": "VBDS v1.0", "note": "Illustrative samples only; see README.md.",
               "images": []}
    src_name = {"S04": "NWPU-RESISC45"}
    for sid in sorted(by_src):
        cand = sorted(by_src[sid], key=lambda r: int(r["size_bytes"]))
        for r in cand:
            if int(r["size_bytes"]) > max_bytes:
                continue
            key = (r["split_g3"], r["file_name"])
            if key not in anns:
                continue
            w, h, as_ = anns[key]
            if not as_:
                continue
            src = os.path.join(art, "datasets/public/images", r["split_final"], r["file_name"])
            if not os.path.exists(src):
                continue
            dst_name = "%s_%s" % (sid, r["file_name"])
            shutil.copy2(src, os.path.join(img_dir, dst_name))
            catalog["images"].append({
                "file": "images/" + dst_name,
                "source_unit": sid,
                "source_name": src_name.get(sid, r["source_name"]),
                "split_g3": r["split_g3"],
                "original_file_name": r["file_name"],
                "width": w, "height": h,
                "md5": r["image_md5"],
                "annotations": [{"category_id": a["category_id"], "bbox": a["bbox"]} for a in as_],
            })
            break

    with open(os.path.join(tree, "examples/examples.json"), "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    lines = ["# Example images", "",
             "Sample images from the redistributable sources, showing the imagery and the COCO",
             "entry layout.", "",
             "| file | source | licence | G3 split | boxes |", "|---|---|---|---|---:|"]
    lic = {"S02": "CC BY-NC 4.0", "S03": "fMoW Challenge Public License", "S04": "CC BY-NC 4.0",
           "S05": "CC BY-NC-SA 3.0", "S08": "Apache 2.0", "S09": "Apache 2.0"}
    for e in catalog["images"]:
        lines.append("| `%s` | %s (%s) | %s | %s | %d |"
                     % (e["file"], e["source_name"], e["source_unit"], lic[e["source_unit"]],
                        e["split_g3"], len(e["annotations"])))
    lines += ["", "Annotations are reproduced in `examples.json` in COCO fields, keyed by",
              "`category_id` 0–25. Attribution and full terms are in `SOURCE_LICENSES.md`.",
              "Each image keeps its original MD5 so it can be traced to",
              "`metadata/public_image_manifest.csv`.", ""]
    with open(os.path.join(tree, "examples/README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("examples:", len(catalog["images"]),
          "bytes:", sum(os.path.getsize(os.path.join(img_dir, e["file"].split("/")[-1]))
                        for e in catalog["images"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--release", required=True)
    ap.add_argument("--tree", required=True)
    ap.add_argument("--vbds-root", required=True)
    a = ap.parse_args()
    copy_public_into_tree(a.release, a.tree)
    copy_evaluation(a.artifact, a.tree)
    copy_scripts(a.vbds_root, a.tree)
    build_examples(a.artifact, a.release, a.tree)
    print("tree assembled at", a.tree)


if __name__ == "__main__":
    main()
