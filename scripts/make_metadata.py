# -*- coding: utf-8 -*-
"""Emit VBDS release metadata: source manifest, statistics, taxonomy mappings."""
from __future__ import annotations
import argparse, csv, json, os
from collections import Counter, defaultdict

STATUS = {
    "S01": ("EXTERNAL_SOURCE", "Academic use only; redistribution not granted. Obtain from the official DOTA release."),
    "S02": ("PUBLIC_APPROVED", "CC BY-NC 4.0: redistribution permitted for non-commercial use with attribution."),
    "S03": ("PUBLIC_APPROVED", "fMoW Challenge Public License: redistribution permitted for non-commercial use with attribution."),
    "S04": ("PUBLIC_APPROVED", "CC BY-NC 4.0: redistribution permitted for non-commercial use with attribution."),
    "S05": ("PUBLIC_APPROVED", "CC BY-NC-SA 3.0: redistribution permitted for non-commercial use, share-alike, with attribution."),
    "S06": ("PERMISSION_REQUIRED", "Kaggle metadata declares CC BY-SA 4.0; redistribution permission not granted."),
    "S07": ("PERMISSION_REQUIRED", "No licence declared for the ERA videos; permission from the rights holders is required."),
    "S08": ("PUBLIC_APPROVED", "Apache License 2.0: redistribution permitted with attribution/NOTICE."),
    "S09": ("PUBLIC_APPROVED", "Apache License 2.0: redistribution permitted with attribution/NOTICE."),
    "S10": ("WITHHELD", "No LICENSE file upstream; frames from traffic surveillance may contain plates and location data."),
    "S11": ("WEB_COLLECTED", "Web surveillance imagery; no file-level licence record."),
    "S12": ("WEB_COLLECTED", "Mixed web sources (stock libraries and free-image hosts); no file-level licence record."),
    "S13": ("WEB_COLLECTED", "Mixed web sources; no file-level licence record."),
    "S14": ("WITHHELD", "Commercial stock imagery and search thumbnails; no redistribution permission."),
    "S15": ("WITHHELD", "Stock-library imagery and search thumbnails; no redistribution permission."),
    "S16": ("WITHHELD", "Commercial stock imagery; no redistribution permission."),
}

PERMISSION = {
    "PUBLIC_APPROVED": "granted (conditional)",
    "EXTERNAL_SOURCE": "not granted",
    "PERMISSION_REQUIRED": "requires owner permission",
    "WEB_COLLECTED": "not established",
    "WITHHELD": "not granted",
}

ANN_PERMISSION = {
    "S01": "not granted",
    "S02": "granted (CC BY-NC 4.0)",
    "S03": "granted (non-commercial, attribution)",
    "S04": "granted (CC BY-NC 4.0)",
    "S05": "granted (CC BY-NC-SA 3.0)",
    "S06": "not granted",
    "S07": "not established",
    "S08": "granted (Apache 2.0)",
    "S09": "granted (Apache 2.0)",
    "S10": "not established",
    "S11": "author-drawn; image rights with the source pages",
    "S12": "author-drawn; image rights with the source pages",
    "S13": "author-drawn; image rights with the source pages",
    "S14": "author-drawn; image rights with the rights holders",
    "S15": "author-drawn; image rights with the rights holders",
    "S16": "author-drawn; image rights with the rights holders",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--release", required=True)
    a = ap.parse_args()
    art, rel = a.artifact, a.release

    index = list(csv.DictReader(open(os.path.join(art, "manifests/image_index.csv"), encoding="utf-8-sig")))
    inv = {r["id"]: r for r in csv.DictReader(open(os.path.join(art, "docs/source_inventory.csv"), encoding="utf-8-sig"))}

    per = defaultdict(lambda: {"images": 0, "bytes": 0, "boxes_g3": 0, "boxes_final": 0,
                               "split_g3": Counter(), "split_final": Counter()})
    for r in index:
        d = per[r["source_unit"]]
        d["images"] += 1
        d["bytes"] += int(r["size_bytes"])
        d["boxes_g3"] += int(r["n_boxes_g3"])
        d["boxes_final"] += int(r["n_boxes_final"])
        d["split_g3"][r["split_g3"]] += 1
        d["split_final"][r["split_final"]] += 1

    os.makedirs(os.path.join(rel, "metadata"), exist_ok=True)
    with open(os.path.join(rel, "metadata/source_manifest.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source_id", "source_name", "source_url", "original_license", "license_evidence",
                    "redistribution_permission", "annotation_redistribution_permission",
                    "image_count", "total_size_bytes", "release_status", "notes"])
        for sid in sorted(per):
            d, i = per[sid], inv[sid]
            st, note = STATUS[sid]
            w.writerow([sid, i["name"], i["site"], i["license_name"], i["license_url"],
                        PERMISSION[st], ANN_PERMISSION[sid], d["images"], d["bytes"], st,
                        note + " | train/val/test (G3) = %d/%d/%d | boxes G3/final = %d/%d"
                        % (d["split_g3"].get("train", 0), d["split_g3"].get("val", 0),
                           d["split_g3"].get("test", 0), d["boxes_g3"], d["boxes_final"])])

    # statistics: full / public / restricted, per class, both GT versions
    cats = None
    full_stats, pub_stats = {}, {}
    per_source_class = defaultdict(Counter)   # source -> class -> G3 boxes
    name_by_split = {}
    for split in ("train", "val", "test"):
        idx = [r for r in index if r["split_g3"] == split]
        name_by_split[split] = {r["file_name"].replace("__dup2", ""): r["source_unit"] for r in idx}
    for version, adir in (("g3", "annotations_g3"), ("final", "annotations_final")):
        full_stats[version] = {}
        for split in ("train", "val", "test"):
            data = json.load(open(os.path.join(art, "datasets", adir, "instances_%s.json" % split), encoding="utf-8"))
            cats = {c["id"]: c["name"] for c in data["categories"]}
            c = Counter(x["category_id"] for x in data["annotations"])
            full_stats[version][split] = {"images": len(data["images"]), "boxes": len(data["annotations"]),
                                          "per_class": {cats[k]: c.get(k, 0) for k in sorted(cats)}}
            if version == "g3":
                id2src = {}
                for im in data["images"]:
                    nm = os.path.basename(im["file_name"]).replace("__dup2", "")
                    id2src[im["id"]] = name_by_split[split].get(nm, "UNKNOWN")
                for x in data["annotations"]:
                    per_source_class[id2src.get(x["image_id"], "UNKNOWN")][cats[x["category_id"]]] += 1

    for version in ("g3", "final"):
        pub_stats[version] = {}
        for split in ("train", "val", "test"):
            data = json.load(open(os.path.join(rel, "public/annotations", version,
                                               "instances_%s.json" % split), encoding="utf-8"))
            c = Counter(x["category_id"] for x in data["annotations"])
            pub_stats[version][split] = {"images": len(data["images"]), "boxes": len(data["annotations"]),
                                         "per_class": {cats[k]: c.get(k, 0) for k in sorted(cats)}}

    def agg(d):
        return {"images": sum(d[s]["images"] for s in d), "boxes": sum(d[s]["boxes"] for s in d),
                "per_class": {k: sum(d[s]["per_class"][k] for s in d) for k in cats.values()}}
    stats = {
        "dataset": "VBDS v1.0",
        "restricted_stats": {},
        "full_benchmark": {v: agg(full_stats[v]) for v in full_stats},
        "public_release": {v: agg(pub_stats[v]) for v in pub_stats},
        "per_split": {"full": full_stats, "public": pub_stats},
    }
    for v in ("g3", "final"):
        stats["restricted_stats"][v] = {
            "images": stats["full_benchmark"][v]["images"] - stats["public_release"][v]["images"],
            "boxes": stats["full_benchmark"][v]["boxes"] - stats["public_release"][v]["boxes"],
            "per_class": {k: stats["full_benchmark"][v]["per_class"][k] - stats["public_release"][v]["per_class"][k]
                          for k in cats.values()}}
    json.dump(stats, open(os.path.join(rel, "metadata/dataset_statistics.json"), "w"), indent=2, ensure_ascii=False)

    # taxonomy
    os.makedirs(os.path.join(rel, "..", "VBDS", "taxonomy"), exist_ok=True)
    base = os.path.join(rel, "..", "VBDS")
    # domains from the verified 5/15/4/2 grouping (DATASET_CARD.md)
    card = {
        "no_uav_sign": "airspace_control", "airplane": "airspace_control", "helipad": "airspace_control",
        "helicopter": "airspace_control", "runway": "airspace_control",
        "bridge": "critical_infrastructure", "dam": "critical_infrastructure", "wind_turbine": "critical_infrastructure",
        "harbor": "critical_infrastructure", "ship": "critical_infrastructure", "storage_tank": "critical_infrastructure",
        "container_area": "critical_infrastructure", "crane": "critical_infrastructure",
        "surface_mine": "critical_infrastructure", "solar_farm": "critical_infrastructure",
        "tower": "critical_infrastructure", "cooling_tower": "critical_infrastructure",
        "gas_station_canopy": "critical_infrastructure", "electric_substation": "critical_infrastructure",
        "railway": "critical_infrastructure",
        "vehicle": "ground_activity_public_safety", "person": "ground_activity_public_safety",
        "surveillance": "ground_activity_public_safety", "crowd": "ground_activity_public_safety",
        "face": "identity_privacy", "plate": "identity_privacy",
    }
    categories = []
    for cid in sorted(cats):
        nm = cats[cid]
        categories.append({"id": cid, "name": nm, "domain": card.get(nm, "unassigned"),
                           "full_g3_boxes": stats["full_benchmark"]["g3"]["per_class"][nm],
                           "public_g3_boxes": stats["public_release"]["g3"]["per_class"][nm]})
    json.dump({"version": "1.0", "n_categories": len(categories), "categories": categories},
              open(os.path.join(base, "taxonomy/categories.json"), "w"), indent=2, ensure_ascii=False)
    json.dump({s: {k: v for k, v in sorted(per_source_class[s].items())} for s in sorted(per_source_class)},
              open(os.path.join(base, "taxonomy/source_category_mapping.json"), "w"), indent=2, ensure_ascii=False)
    print("sources:", len(per), "categories:", len(categories))
    print("full boxes:", stats["full_benchmark"]["g3"]["boxes"], "public:", stats["public_release"]["g3"]["boxes"])
    print("wrote metadata + taxonomy")


if __name__ == "__main__":
    main()
