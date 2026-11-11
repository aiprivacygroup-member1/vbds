# -*- coding: utf-8 -*-
"""Build the VBDS public release packages.

Every package is an independent ZIP (ZIP64, stored, no recompression) holding the images of one
source unit and one final split. Groups larger than PART_MAX are split into balanced parts.
Each package carries its own per-source NOTICE, PACKAGE_INFO.json and MANIFEST.csv.

Nothing is written outside VBDS_release/ and no source file is modified.

Usage:
  python prepare_public_release.py --artifact <public artifact> --release <VBDS_release>
"""
from __future__ import annotations

import argparse, csv, hashlib, json, os, sys, zipfile
from collections import defaultdict

PART_MAX = 1_800_000_000      # split a group into parts above ~1.8 GB
ZIP_DATE = (2026, 11, 11, 0, 0, 0)

NOTICES = {
    "S02": {
        "name": "DIOR",
        "license": "CC BY-NC 4.0",
        "url": "https://creativecommons.org/licenses/by-nc/4.0/",
        "cite": "Li, K. et al. Object detection in optical remote sensing images: A survey and a new benchmark. ISPRS J. Photogramm. Remote Sens. 159 (2020).",
        "modification": "Images renamed only. Annotations in VBDS are drawn by the VBDS authors and are not the original DIOR annotations.",
        "terms": "Non-commercial use only. Attribution to the DIOR authors required. No additional restrictions may be imposed.",
    },
    "S03": {
        "name": "fMoW (Functional Map of the World)",
        "license": "fMoW Challenge Public License",
        "url": "https://github.com/fMoW/dataset",
        "cite": "Christie, G. et al. Functional Map of the World. CVPR 2018.",
        "modification": "Images renamed; one image carries a __dup2 suffix in the refined annotation. Annotations drawn by the VBDS authors.",
        "terms": "Non-commercial research use. Attribution required. See the bundled fMoW licence text.",
    },
    "S04": {
        "name": "NWPU-RESISC45",
        "license": "CC BY-NC 4.0",
        "url": "https://creativecommons.org/licenses/by-nc/4.0/",
        "cite": "Cheng, G., Han, J., Lu, X. Remote Sensing Image Scene Classification: Benchmark and State of the Art. Proc. IEEE 105(10), 2017.",
        "modification": "Images renamed. Annotations drawn by the VBDS authors.",
        "terms": "Non-commercial use only. Attribution required.",
    },
    "S05": {
        "name": "VisDrone",
        "license": "CC BY-NC-SA 3.0",
        "url": "https://creativecommons.org/licenses/by-nc-sa/3.0/",
        "cite": "Zhu, P. et al. Detection and Tracking Meet Drones Challenge. IEEE TPAMI 44(11), 2021.",
        "modification": "Images renamed. Annotations drawn by the VBDS authors.",
        "terms": "Non-commercial use, attribution, share-alike: adaptations must be distributed under the same licence.",
    },
    "S08": {
        "name": "TTPLA (transmission tower subset, batch 1)",
        "license": "Apache License 2.0",
        "url": "https://github.com/R3ab/ttpla_dataset/blob/master/LICENSE",
        "cite": "Abdelfattah, R., Wang, X., Wang, S. TTPLA: An Aerial-Image Dataset for Detection and Segmentation of Transmission Towers and Power Lines. ACCV 2020.",
        "modification": "Images cropped/screenshotted from TTPLA imagery and renamed; labels converted to the VBDS taxonomy and to COCO format.",
        "terms": "Apache License 2.0. Retain this NOTICE and the licence text; state that files were modified.",
    },
    "S09": {
        "name": "TTPLA (transmission tower subset, batch 2)",
        "license": "Apache License 2.0",
        "url": "https://github.com/R3ab/ttpla_dataset/blob/master/LICENSE",
        "cite": "Abdelfattah, R., Wang, X., Wang, S. TTPLA: An Aerial-Image Dataset for Detection and Segmentation of Transmission Towers and Power Lines. ACCV 2020.",
        "modification": "Images cropped/screenshotted from TTPLA imagery and renamed; labels converted to the VBDS taxonomy and to COCO format.",
        "terms": "Apache License 2.0. Retain this NOTICE and the licence text; state that files were modified.",
    },
}

EVIDENCE = {
    "S02": ["dior_ieeedataport.html", "dior_opendatalab.html"],
    "S03": ["fmow_LICENSE.txt"],
    "S04": [],
    "S05": ["visdrone_github_readme.md", "visdrone_dataprotection.html"],
    "S08": ["ttpla_LICENSE.txt", "ttpla_README.md"],
    "S09": ["ttpla_LICENSE.txt", "ttpla_README.md"],
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def balanced_parts(files, n_parts):
    """Largest-processing-time greedy: keeps part sizes within ~one large file of each other."""
    bins = [[] for _ in range(n_parts)]
    load = [0] * n_parts
    for f in sorted(files, key=lambda x: -x[2]):
        i = load.index(min(load))
        bins[i].append(f)
        load[i] += f[2]
    return [b for b in bins if b]


def write_zip(path, entries, compress=zipfile.ZIP_STORED):
    """entries: list of (arcname, src_path_or_None, bytes_or_None)."""
    with zipfile.ZipFile(path, "w", compression=compress, allowZip64=True) as z:
        for arcname, src, data in entries:
            if src is not None:
                zi = zipfile.ZipInfo(arcname, date_time=ZIP_DATE)
                zi.compress_type = compress
                zi.external_attr = 0o644 << 16
                with open(src, "rb") as f:
                    z.writestr(zi, f.read())
            else:
                zi = zipfile.ZipInfo(arcname, date_time=ZIP_DATE)
                zi.compress_type = compress
                zi.external_attr = 0o644 << 16
                z.writestr(zi, data)


def notice_text(sid):
    n = NOTICES[sid]
    return (
        "VBDS public release — source notice\n"
        "===================================\n\n"
        "Source unit: %s\nDataset:     %s\nLicence:     %s\nLicence URL: %s\n\n"
        "Attribution / citation\n----------------------\n%s\n\n"
        "Modification statement\n----------------------\n%s\n\n"
        "Terms\n-----\n%s\n\n"
        "This package redistributes a subset of the original imagery. The original dataset is the\n"
        "authoritative distribution; see DATA_ACCESS.md in the VBDS repository.\n"
        % (sid, n["name"], n["license"], n["url"], n["cite"], n["modification"], n["terms"])
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--release", required=True)
    ap.add_argument("--limit", type=int, default=0, help="debug: only build the first N packages")
    ap.add_argument("--plain-only", action="store_true",
                    help="rebuild only the annotation and metadata packages, keeping image entries")
    a = ap.parse_args()
    art, rel = a.artifact, a.release
    img_root = os.path.join(art, "datasets/public/images")
    pkg_dir = os.path.join(rel, "packages")
    os.makedirs(pkg_dir, exist_ok=True)

    rows = list(csv.DictReader(open(os.path.join(rel, "public/metadata/public_image_manifest.csv"),
                                    encoding="utf-8-sig")))

    # Group by (source, final split); resolve on-disk path and verify checksums.
    groups = defaultdict(list)
    problems = []
    for r in ([] if a.plain_only else rows):
        src = os.path.join(img_root, r["split_final"], r["file_name"])
        if not os.path.exists(src):
            alt = os.path.join(img_root, r["split_final"], r["file_name"].replace("__dup2", ""))
            problems.append((r["file_name"], "missing", os.path.exists(alt)))
            continue
        size = os.path.getsize(src)
        if size != int(r["size_bytes"]):
            problems.append((r["file_name"], "size_mismatch", size))
        if md5_file(src) != r["image_md5"]:
            problems.append((r["file_name"], "md5_mismatch", 0))
        groups[(r["source_unit"], r["split_final"])].append((r["file_name"], src, size))
        # G3 annotations keep the pre-rename name for one fMoW image; ship a byte-identical alias
        if "__dup2" in r["file_name"]:
            groups[(r["source_unit"], r["split_final"])].append(
                (r["file_name"].replace("__dup2", ""), src, size))

    if problems:
        print("PROBLEMS:", problems[:20], "total", len(problems))
        sys.exit(2)

    packages = []
    if a.plain_only:
        prev = json.load(open(os.path.join(rel, "metadata/release_manifest.json"), encoding="utf-8"))
        packages = [p for p in prev["packages"] if p.get("kind") == "images"]
        print("kept image entries:", len(packages))
        order = []
    else:
        order = sorted(groups)
    for (sid, split) in order:
        files = groups[(sid, split)]
        total = sum(f[2] for f in files)
        n_parts = max(1, -(-total // PART_MAX))
        parts = balanced_parts(files, n_parts) if n_parts > 1 else [files]
        for k, part in enumerate(parts, 1):
            suffix = "" if len(parts) == 1 else "-part%dof%d" % (k, len(parts))
            pkg = "vbds-v1.0-public-%s-%s%s" % (sid, split, suffix)
            zpath = os.path.join(pkg_dir, pkg + ".zip")
            print("building", pkg, "files", len(part), "bytes", sum(f[2] for f in part), flush=True)

            man = ["file_name,split,size_bytes,md5,sha256"]
            entries = []
            hashes = {}
            for name, src, size in sorted(part):
                d = sha256_file(src)
                hashes[name] = d
                man.append("%s,%s,%d,%s,%s" % (name, split, size, md5_file(src), d))
                entries.append(("VBDS/images/%s/%s" % (split, name), src, None))

            info = {
                "package_id": pkg,
                "format_version": "1.0",
                "source_id": sid,
                "source_name": NOTICES[sid]["name"],
                "split": split,
                "part": k,
                "n_parts": len(parts),
                "images": len(part),
                "bytes_uncompressed": sum(f[2] for f in part),
                "license": NOTICES[sid]["license"],
                "license_url": NOTICES[sid]["url"],
                "extract_to": "any directory; all packages share the layout VBDS/images/<split>/",
                "notes": ("One fMoW image is shipped under both its refined name (...__dup2.jpg) and "
                          "its pre-refinement name so that both annotation versions resolve."
                          if any("__dup2" in f[0] for f in part) else ""),
            }
            entries.append(("VBDS/LICENSES/%s_NOTICE.txt" % sid, None, notice_text(sid).encode("utf-8")))
            for ev in EVIDENCE[sid]:
                p = os.path.join(art, "licenses/evidence", ev)
                if os.path.exists(p):
                    entries.append(("VBDS/LICENSES/evidence/%s/%s" % (sid, ev), p, None))
            entries.append(("VBDS/packages/%s/PACKAGE_INFO.json" % pkg, None,
                            json.dumps(info, indent=2, ensure_ascii=False).encode("utf-8")))
            entries.append(("VBDS/packages/%s/MANIFEST.csv" % pkg, None,
                            ("\n".join(man) + "\n").encode("utf-8")))
            entries.append(("VBDS/packages/%s/README.txt" % pkg, None,
                            ("Extract this archive anywhere; images land in VBDS/images/%s/.\n"
                             "Use the split CSVs and the COCO files in the annotations package to\n"
                             "assign images to splits: the image directory records the final split,\n"
                             "which differs from the G3 split for some images.\n" % split).encode("utf-8")))
            write_zip(zpath, entries)
            packages.append({
                "package_id": pkg,
                "file": pkg + ".zip",
                "kind": "images",
                "source_id": sid,
                "split": split,
                "part": k,
                "n_parts": len(parts),
                "images": len(part),
                "bytes_uncompressed": info["bytes_uncompressed"],
                "bytes": os.path.getsize(zpath),
                "sha256": sha256_file(zpath),
                "license": NOTICES[sid]["license"],
            })
            print("  ->", packages[-1]["bytes"], packages[-1]["sha256"][:16], flush=True)
            if a.limit and len(packages) >= a.limit:
                break
        if a.limit and len(packages) >= a.limit:
            break

    # annotation and metadata packages
    def add_plain(kind, name, srcs):
        pkg = "vbds-v1.0-public-%s" % name
        zpath = os.path.join(pkg_dir, pkg + ".zip")
        entries = [(arc, src, None) for arc, src in srcs]
        write_zip(zpath, entries)
        packages.append({"package_id": pkg, "file": pkg + ".zip", "kind": kind,
                         "images": 0, "bytes": os.path.getsize(zpath),
                         "sha256": sha256_file(zpath)})
        print("built", pkg, os.path.getsize(zpath), flush=True)

    for version in ("g3", "final"):
        srcs = []
        for split in ("train", "val", "test"):
            p = os.path.join(rel, "public/annotations", version, "instances_%s.json" % split)
            srcs.append(("VBDS/annotations/%s/instances_%s.json" % (version, split), p))
        add_plain("annotations", "annotations-" + version, srcs)

    meta_srcs = []
    for f in sorted(os.listdir(os.path.join(rel, "public/splits"))):
        meta_srcs.append(("VBDS/splits/" + f, os.path.join(rel, "public/splits", f)))
    for f in sorted(os.listdir(os.path.join(rel, "public/metadata"))):
        meta_srcs.append(("VBDS/metadata/public/" + f, os.path.join(rel, "public/metadata", f)))
    for f in sorted(os.listdir(os.path.join(rel, "metadata"))):
        meta_srcs.append(("VBDS/metadata/" + f, os.path.join(rel, "metadata", f)))
    add_plain("metadata", "metadata", meta_srcs)

    json.dump({"dataset": "VBDS v1.0", "created": "2026-11-11",
               "packages": packages,
               "total_bytes": sum(p["bytes"] for p in packages)},
              open(os.path.join(rel, "metadata/release_manifest.json"), "w"), indent=2)
    with open(os.path.join(pkg_dir, "checksums.sha256"), "w", newline="\n") as f:
        for p in packages:
            f.write("%s  packages/%s\n" % (p["sha256"], p["file"]))
    print("packages:", len(packages), "total bytes:", sum(p["bytes"] for p in packages))


if __name__ == "__main__":
    main()
