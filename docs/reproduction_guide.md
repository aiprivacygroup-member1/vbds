# Reproduction guide

Three levels of reproduction are possible with this release.

| Level | What it does | Needs |
|---|---|---|
| **L1** | recompute reported metrics from prediction dumps | GT files (public subset included) |
| **L2** | run inference with the published checkpoints | weights + images |
| **L3** | retrain the six baselines | tiled training set + GPU budget |

The public release supports **L1 on the public subset**.

## 1. Set up

```bash
git clone https://github.com/aiprivacygroup-member1/vbds
cd vbds
python -m pip install -r requirements.txt
```

## 2. Validate the release

```bash
# annotations and splits only
python scripts/validate_dataset.py --annotations annotations --splits splits

# with extracted images: verifies every image resolves, checks size and md5
python scripts/validate_dataset.py --annotations annotations --splits splits \
    --images /path/to/extracted/VBDS/images

# package integrity
python scripts/verify_checksums.py --checksums release/checksums.sha256
```

`validate_dataset.py` writes `reports/validation.json` and `.md`.

## 3. Expected counts for the public subset

| Check | Expected |
|---|---:|
| public images | 11,783 |
| G3 boxes (train/val/test) | 46,000 / 25,715 / 5,587 |
| final boxes (train/val/test) | 53,749 / 15,222 / 7,737 |
| categories per file | 26 |
| annotations with missing image | 0 |

## 4. L1 — recompute a table from prediction dumps

If you have a dump in the project format:

```bash
python evaluation/reproduce_main_table.py \
    --gt annotations/g3/instances_test.json \
    --pred <prediction dump>.json \
    --config <model config>.yaml \
    --out results/recomputed.csv
```

The evaluator applies the confidence threshold from the config. AP is computed from the full
ranked dump.

Thresholds used for the six baselines (selected on validation by micro-F1):

| model | threshold |
|---|---:|
| D-FINE-X | 0.60 |
| RT-DETR-v2-R18 | 0.60 |
| RF-DETR-Small | 0.40 |
| DINO-4scale-R50 | 0.35 |
| YOLO26l | 0.30 |
| Faster R-CNN-R50-FPN | 0.65 |
| GroundingDINO (zero-shot) | 0.35 |

Thresholds are selected per model and per validation subset.

## 5. L2 / L3 — full benchmark

Evaluating on the full test split requires:

1. the 4,877 non-public images, obtained from their providers (`DATA_ACCESS.md`);
2. the annotations for those images, available from the authors (`DATA_ACCESS.md` §5).

Retraining additionally requires the tiled training set (18,950 images / 173,464 boxes; see
`docs/data_availability.md` §3).

## 6. Reporting a number

State the annotation version, the split, and whether the run is on the public subset or the full
benchmark, e.g.

> G3, public test (994 images, 5,587 boxes), YOLO26l, AP50:95 = …
