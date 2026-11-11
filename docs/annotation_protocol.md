# Annotation protocol and provenance

This document states how each class was labelled: labels inherited from a source dataset, labels
drawn for VBDS, and labels revised after the benchmark was frozen.

## 1. Box format

- COCO JSON, one file per split: `instances_{train,val,test}.json`.
- `bbox` = `[x, y, w, h]` in absolute pixels of the original image; `w`, `h` > 0.
- One box per visible instance. No segmentation masks, no keypoints, no attributes.
- `iscrowd` is 0 throughout; crowded scenes are annotated instance by instance.
- Images are never resized. A box drawn on a tile or crop was mapped back to whole-image
  coordinates with at most 1 px rounding.
- `area` = `w * h`.
- `category_id`, `image_id` and annotation ids keep their frozen values. Nothing is renumbered
  between versions, so rows can be joined across G3 and final by `(image_id, category_id, bbox)`.

## 2. Where the labels come from

Three provenances coexist in G3. They are listed per class below; the counts are G3 boxes.

### 2.1 Source-dataset labels, used unchanged

| class | boxes | source |
|---|---:|---|
| harbor | 10,334 | DIOR 5,406 + DOTA 4,928 |
| ship | 31,153 | DIOR 23,276 + DOTA 7,874 + web 3 |
| vehicle | 19,745 | DIOR + DOTA + VisDrone + ERA + web (small hand-drawn part) |
| face | 8,462 | BirdsEye-RU |
| crowd | 152 | ERA |
| wind_turbine | 5,375 | DIOR 5,363 + web 12 |
| cooling_tower | 1,599 | DIOR `chimney`, label mapping only |
| helipad | 104 | fMoW 102 + DIOR 2 |
| runway | 584 | NWPU-RESISC45 |

### 2.2 Source images with hand-drawn labels

| class | boxes | notes |
|---|---:|---|
| solar_farm | 311 | fMoW 265 + hand-drawn web 46 (the fMoW part carries source labels) |
| electric_substation | 164 | 163 boxes hand-drawn (153 images); 1 box on a DIOR image |
| tower | 397 | TTPLA subset 195 (source YOLO labels) + 202 hand-drawn (labelme) |
| crane | 303 | DOTA 142 + 159 hand-drawn web + DIOR 2 |
| person | 3,722 | VisDrone 3,701 + BirdsEye 6 + ERA 2 + web 13 |

### 2.3 Classes drawn entirely for VBDS

`no_uav_sign` (53), `container_area` (176), `surface_mine` (100), `gas_station_canopy` (113),
`surveillance` (189), `plate` (266). These were annotated with labelme on web-collected or
traffic-surveillance frames.

### 2.4 Classes carried from source labels

For `dam`, `runway`, `railway`, `helipad` and the fMoW part of `solar_farm`, the G3 boxes are the
source dataset's labels. The counts match the source annotations exactly: 987/987 dam images,
575/575 runway images, 700/700 railway images, 283/285 solar_farm images and 77/77 helipad images
by coordinate comparison.

## 3. Deduplication (G2 → G3)

- Key: `(image_id, category_id, bbox)` with **bit-exact** float equality.
- The first occurrence is kept; later identical copies are dropped.
- No IoU clustering and no coordinate tolerance.
- Ids are not renumbered, so `G2 − G3` equals the shipped `dropped_duplicates_{split}.csv`
  exactly. 40,637 boxes were removed (24.67%); image counts are unchanged.

## 4. Four-class re-annotation (final)

`airplane`, `bridge`, `storage_tank` and `helicopter` were re-annotated on 4,585 images with the
old boxes visible, then merged. Net change −458 boxes:

| class | G3 | final | Δ | re-annotated images |
|---|---:|---:|---:|---:|
| airplane | 17,418 | 17,212 | −206 | 1,453 |
| bridge | 5,204 | 5,129 | −75 | 1,977 |
| storage_tank | 15,778 | 15,583 | −195 | 848 |
| helicopter | 652 | 669 | +17 | 28 |

The paper's four-class audit (Table 13) measures the effect of the revision with predictions
frozen, isolating the GT change from the model.

The other 22 classes are byte-identical between G3 and final.

## 5. Verification before release

- Every annotation's `image_id` resolves to an image in the same file.
- `category_id` ∈ 0–25 and every file carries the same 26 categories in the same order.
- Bounding boxes are inside the image bounds (no negative coordinates, no zero area).
- G3 and final share the same `image_id` per split file and the same annotation ids.
- Public annotation files reference only public images.
- Image checksums (MD5 per file) are recorded in `metadata/public_image_manifest.csv`, and the
  SHA-256 of every package is recorded in `release/checksums.sha256`.

Reports: `reports/validation.md` and `reports/validation.json`, produced by
`scripts/validate_dataset.py`.
