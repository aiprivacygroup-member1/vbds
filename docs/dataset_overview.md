# Dataset overview

## 1. What VBDS is

VBDS is a 26-class object-detection benchmark for **sensitive visual cues** in aerial and
low-altitude imagery: airspace-control objects, critical infrastructure, activity relevant to
public safety, and identity-related cues. Every image carries a single COCO annotation set drawn
in one taxonomy, so results across models, sources and experiments are directly comparable.

- **Full benchmark:** 16,660 images, 124,106 boxes (G3 annotation), from 16 source units.
- **Public release:** 11,783 images and their annotations — the part whose licensing permits
  redistribution.
- **Non-public portion:** 4,877 images from 10 source units, not redistributed.

## 2. Composition

| Unit | Source | Images | G3 boxes | Public |
|---|---|---:|---:|---|
| S01 | DOTA v1.5 | 1,115 | 37,024 | no |
| S02 | DIOR (incl. chimney subset) | 9,565 | 71,344 | yes |
| S03 | fMoW | 484 | 530 | yes |
| S04 | NWPU-RESISC45 | 1,275 | 1,279 | yes |
| S05 | VisDrone | 200 | 3,752 | yes |
| S06 | BirdsEye-RU | 2,934 | 8,468 | no |
| S07 | ERA | 128 | 155 | no |
| S08 | TTPLA (tower subset, batch 1) | 129 | 195 | yes |
| S09 | TTPLA (tower subset, batch 2) | 130 | 202 | yes |
| S10 | TADBench (plate frames) | 170 | 266 | no |
| S11 | Web: surveillance | 135 | 189 | no |
| S12 | Web: container area / crane | 103 | 355 | no |
| S13 | Web: surface mine | 100 | 100 | no |
| S14 | Web: gas-station canopy | 99 | 113 | no |
| S15 | Web: no-UAV sign | 53 | 88 | no |
| S16 | Web: solar farm | 40 | 46 | no |
| | **total** | **16,660** | **124,106** | **11,783** |

## 3. Annotation versions

| Version | Images | Boxes | Purpose |
|---|---:|---:|---|
| G2 (pre-dedup) | 16,660 | 164,743 | earlier integrated annotation |
| **G3** | 16,660 | **124,106** | benchmark results (Tables 7–13) |
| **final** | 16,660 | **123,648** | released version; G3 + four-class re-annotation |

The difference between G3 and final is confined to `airplane`, `bridge`, `storage_tank` and
`helicopter`, plus a handful of boxes that changed class as a result. All other classes are
byte-identical.

## 4. Splits

| Split | G3 images | G3 boxes | final images | final boxes |
|---|---:|---:|---:|---:|
| train | 11,587 | 73,986 | 11,699 | 87,243 |
| val | 3,388 | 41,552 | 3,391 | 24,261 |
| test | 1,685 | 8,568 | 1,570 | 12,144 |

Benchmark tables use the G3 partition; the released dataset also provides the `final` partition
used by the scene-isolation study. Each split CSV names its version.

## 5. Benchmark characteristics

- **Long tail.** `ship` has 31,153 boxes; `no_uav_sign` has 53; `container_area` 178 and
  `crane` 303. Six classes have fewer than 300 boxes.
- **Mixed viewpoints and sensors.** Satellite (DOTA, DIOR, NWPU-RESISC45, fMoW) and low-altitude
  drone imagery (VisDrone, TTPLA, ERA) under one taxonomy.
- **Class distribution varies by partition.** In the E02 v2 test split `face` has no boxes, so 25
  classes are evaluable there.
- **Label provenance by class.** Some classes carry the source dataset's own labels, others were
  hand-drawn for this benchmark (`annotation_protocol.md`).
- **Deduplication record.** Exact-duplicate boxes removed between G2 and G3 are shipped as
  `dropped_duplicates_*.csv`.

## 6. Intended use

Benchmarking detectors under aerial viewpoint and long-tailed sensitive-cue classes; label-noise
and annotation-quality studies; evaluating zero-shot/open-vocabulary detectors against a fixed
GT.

## 7. Out of scope

- **No face recognition or identification.** The `face` class marks the *presence* of a face-like
  region; there are no identity labels, embeddings or matches.
- **No surveillance deployment.** The benchmark is for measurement, not for building or
  operating monitoring systems.
- No timestamps, GPS coordinates, camera identifiers or platform metadata are included.
- Redistribution of non-public images is outside the terms of this release; see `DATA_ACCESS.md`.
