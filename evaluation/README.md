# Evaluation

This directory contains the evaluator used for all reported numbers and the scripts that produce
the paper's tables from prediction dumps.

## Metrics

`hzs_metrics.py` takes a COCO GT file, a prediction dump and a YAML config, and computes:

- **COCO AP** via pycocotools: AP50:95, AP50, AP75, AP_small/medium/large (32²/96² thresholds).
- **Task-oriented P/R/F1** at IoU 0.30 and 0.50 with a confidence threshold fixed on the
  validation split.
- **Image-level metrics** (image AP / precision / recall / F1) for scene-like classes.

## Input checks

The evaluator verifies that the dump and the GT describe the same evaluation:

- the dump's `image_ids` equal the GT image-id set;
- `meta.image_count` equals the GT image count;
- class names and their order equal the GT categories;
- `meta.split` equals the config's split.

These checks catch a mismatched split or annotation version before metrics are computed.

```bash
python hzs_metrics.py --config <model config>.yaml \
                      --gt <annotations>/instances_test.json \
                      --dump <prediction dump>.json \
                      --out results/dfine.json --md results/dfine.md
```

## Prediction dump format

```json
{ "meta": {"model": ..., "framework": ..., "checkpoint": ..., "split": "test",
           "gt_annotation": ..., "gt_annotation_md5": "...", "class_names": [...],
           "image_count": 1685, "dump_score_threshold": 0.01, "nms": false},
  "image_ids": [...],
  "predictions": [{"image_id": 12, "category_id": 1, "bbox": [x,y,w,h], "score": 0.83}, ...] }
```

`bbox` is COCO `[x, y, w, h]` in original image pixels. Dumps are exported at a low score
threshold (e.g. 0.01) so that AP does not depend on the reported operating point.

## Table scripts

The `reproduce_*.py` scripts recompute the paper's tables from prediction dumps. Paths in the
commands refer to your own experiment outputs.

| script | Table | note |
|---|---|---|
| `reproduce_main_table.py` | 7 | also writes the Table 8 per-class matrix with `--per-class-out`; `--include-gdino` adds the GroundingDINO row |
| `reproduce_gt_versions.py` | 11 | G1/G2/G3 rescoring of frozen dumps |
| `reproduce_4cls.py` | 13 | thresholds read from the frozen `*_threshold.json` |
| `reproduce_t16.py` | 12 | each arm uses its own val-selected threshold |
| `reproduce_e02.py` | 15 | builds the 1,543 / 1,541 test subsets in memory and runs COCOeval |

## Files

| file | role |
|---|---|
| `hzs_metrics.py` | core evaluator (COCO + task-oriented + image-level) |
| `reproduce_*.py` | table-specific drivers |
| `compare_models.py` | side-by-side comparison of several evaluation reports |

Prediction dumps are produced by the inference code of each baseline model, which is not part of
this repository. The dump format below is the only input the evaluator requires.
