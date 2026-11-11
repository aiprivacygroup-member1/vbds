# VBDS — Visual-Cue Benchmark and Dataset for Sensitive-Content Identification in Aerial Imagery

VBDS is a 26-class object-detection benchmark for sensitive visual cues in aerial and low-altitude
imagery. It covers airspace-control objects, critical infrastructure, ground activity relevant to
public safety, and identity-related cues. Images are drawn from 16 source units and annotated in
COCO format with a single taxonomy shared by every experiment.

This repository contains code, metadata, split definitions and the redistributable annotations,
together with the documentation needed to obtain the remaining data from its original sources. Image archives are distributed as separate packages (§6); no image data is
stored in git.

**Version:** v1.0 · **Release date:** 2026-11-11 · **Annotation versions:** pre-refinement (G3),
refined (final)

---

## 1. Task

Given an aerial or low-altitude image, detect every instance of the 26 classes and return an
axis-aligned bounding box plus a class label. Evaluation follows COCO AP (IoU 0.50:0.95) and
additionally reports task-oriented precision, recall and F1 at fixed IoU and confidence operating
points selected on the validation split.

## 2. Taxonomy

The 26 classes are grouped into four domains used for reporting:

| Domain | Classes |
|---|---|
| Airspace control (5) | `no_uav_sign`, `airplane`, `helipad`, `helicopter`, `runway` |
| Critical infrastructure (15) | `bridge`, `dam`, `wind_turbine`, `harbor`, `ship`, `storage_tank`, `container_area`, `crane`, `surface_mine`, `solar_farm`, `tower`, `cooling_tower`, `gas_station_canopy`, `electric_substation`, `railway` |
| Ground activity / public safety (4) | `vehicle`, `person`, `surveillance`, `crowd` |
| Identity privacy (2) | `face`, `plate` |

`taxonomy/categories.json` gives the authoritative `category_id → name → domain` mapping
(`category_id` 0–25, as used in training). `docs/taxonomy.md` lists per-class counts.

## 3. Dataset

Two annotation versions are distributed:

| Version | Content | Images | Boxes |
|---|---|---:|---:|
| **Pre-refinement (G3)** | deduplicated integrated annotation; used for all benchmark tables | 16,660 | **124,106** |
| **Refined (final)** | G3 plus the manually audited four classes (airplane, bridge, storage_tank, helicopter) | 16,660 | **123,648** |

Benchmark splits (G3): **train 11,587 / val 3,388 / test 1,685** images
(73,986 / 41,552 / 8,568 boxes).

The distributed images form the public release, a subset of the benchmark:

| Subset | Source units | Images | G3 boxes | Size |
|---|---|---:|---:|---:|
| Public release (redistributable) | 6 | **11,783** | **77,302** | 6.94 GB |
| Not redistributed | 10 | 4,877 | 46,804 | 14.04 GB |
| **Full benchmark** | 16 | **16,660** | **124,106** | 20.97 GB |

Statistics for the public subset are in §5 and `metadata/dataset_statistics.json`. Results
computed on the public subset are reported as public-subset results and are kept separate from
full-benchmark results.

## 4. Versions and splits

| Snapshot | Role |
|---|---|
| G1 | early partial test annotation, retained for GT-version studies |
| G2 | pre-deduplication integrated annotation (164,743 boxes) |
| **G3** | deduplicated authoritative annotation (124,106 boxes), Tables 7–13 |
| **final** | G3 + merged four-class manual refinement (123,648 boxes), released version |
| T16 | five-class training-label optimisation experiment, 11,473 common train images |
| E02 v2 | scene-group-isolated split of `final`, 1,543 test images |

`docs/dataset_versions.md` describes how the versions relate and which split each table uses.

## 5. Public release and full benchmark

11,783 images come from sources whose licences permit redistribution: DIOR, fMoW,
NWPU-RESISC45, VisDrone and two TTPLA subsets (source units S02–S05, S08, S09). They are released
in the public packages with the annotations for those images only.

The remaining 4,877 images (DOTA, BirdsEye-RU, ERA, TADBench, and web-collected batches) are not
redistributed, because their upstream terms do not grant redistribution. Their annotations are
likewise not published. `DATA_ACCESS.md` lists what can be obtained from where;
`reconstruction/` provides the manifest and scripts for rebuilding the benchmark locally from
legitimately obtained originals.

Public-subset coverage:

- 19 of 26 classes have at least one box in the public release.
- Public G3 counts: train 8,327 / val 2,462 / test 994 images; 46,000 / 25,715 / 5,587 boxes.
- Full-benchmark results in the paper use the full G3 test split (1,685 images, 8,568 boxes);
  public-subset results use 994 test images and are reported separately.

## 6. Download

The data packages are published outside git:

| Asset | Location |
|---|---|
| `vbds-v1.0-public-*.zip` (images, 18 packages) | Zenodo record [10.5281/zenodo.24126537](https://doi.org/10.5281/zenodo.24126537) |
| `vbds-v1.0-public-annotations-g3.zip`, `-final.zip` | same record |
| `vbds-v1.0-public-metadata.zip` | same record |
| `checksums.sha256` | same record |

Every package has an entry in `metadata/release_manifest.json` with its size, file count and
SHA-256; `release/checksums.sha256` collects them. Check with:

```bash
sha256sum -c release/checksums.sha256
```

## 7. Repository layout

```
README.md                  this file
LICENSE                    scope of the licence granted by this repository
DATA_ACCESS.md             what can be downloaded, obtained, or not released
SOURCE_LICENSES.md         per-source licence status and evidence
CITATION.cff               citation metadata
requirements.txt           Python dependencies
.gitignore                 excludes images, archives, prediction dumps
docs/                      overview, taxonomy, annotation protocol, versions,
                           reproduction guide, data availability
taxonomy/                  categories.json, source_category_mapping.json
metadata/                  source manifest, dataset statistics, release manifest
annotations/               COCO annotations for the public images only (g3/, final/)
splits/                    public split lists, {g3,final}_{train,val,test}.csv
scripts/                   validation, checksum and release-build tools
evaluation/                COCO and task-oriented evaluator used for the paper
examples/                  sample images from the redistributable sources
reconstruction/            manifest of the 4,877 non-public images + a checker
reports/                   validation report for the public annotations
release/                   release manifest and package checksums
```

Image archives are not tracked in git; `.gitignore` excludes image directories and large
prediction dumps.

## 8. Annotation format

COCO JSON with `images`, `annotations`, `categories`, `info` and `licenses`:

- `images[]`: `id`, `file_name`, `width`, `height`.
- `annotations[]`: `id`, `image_id`, `category_id`, `bbox` `[x, y, w, h]`, `area`, `iscrowd`.
- `categories[]`: `id` 0–25 and `name`, identical across all files.
- `bbox` coordinates are absolute pixels in the original image; `w` and `h` are positive.
- `category_id` is never renumbered. `image_id` and annotation ids keep their values within each
  split file.

Images are identified by `(split, file_name)` or by the `image_id` in the annotation file. Five
fMoW helipad basenames occur in more than one split; in `final` one of them is named
`..._rgb__dup2.jpg`, and the public packages ship the image under both names so that the G3 and
final annotations each resolve. The public annotation files contain only public images; no
annotation references a missing image.

## 9. Setup and validation

```bash
python -m pip install -r requirements.txt

# validate annotations and splits
python scripts/validate_dataset.py --annotations annotations --splits splits \
    --out reports/validation.json

# optionally include extracted images
python scripts/validate_dataset.py --annotations annotations --splits splits \
    --images <extracted public images root> --out reports/validation.json

python scripts/verify_checksums.py --checksums release/checksums.sha256 --base <dir containing packages/>
```

`validate_dataset.py` writes a machine-readable JSON report and a Markdown summary.

## 10. Benchmark and evaluation

`evaluation/hzs_metrics.py` implements the COCO AP computation and the task-oriented P/R/F1
metrics used in the paper. `evaluation/reproduce_main_table.py` recomputes a results table from a
prediction dump and a GT file. Confidence thresholds are selected on validation data only.

Full-benchmark evaluation uses the G3 test file of the full annotation set, which is not part of
the public release (see `DATA_ACCESS.md`).

## 11. Citation

```bibtex
@dataset{vbds2026,
  title     = {VBDS: A Visual-Cue Benchmark and Dataset for Sensitive-Content Identification in Aerial Imagery},
  author    = {Li, Yinglong},
  year      = {2026},
  publisher = {Zenodo},
  version   = {1.0},
  doi       = {10.5281/zenodo.24126537}
}
```

The paper citation will be added once the paper is published. `CITATION.cff` carries the same
record in machine-readable form.

## 12. Licence

This repository does not grant a single licence over all content. The authors' code, metadata and
annotations are covered by the scope statement in `LICENSE`; third-party images remain under
their original licences. Redistributable subsets carry the terms of their sources (DIOR and
NWPU-RESISC45: CC BY-NC 4.0; VisDrone: CC BY-NC-SA 3.0; fMoW: Challenge Public License; TTPLA:
Apache 2.0). See `SOURCE_LICENSES.md`; each image package carries a per-source `NOTICE.txt` and,
where the licence text is a file, a copy of it.
