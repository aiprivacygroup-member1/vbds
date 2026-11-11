# Annotation and split versions

Six annotation states are used across the project's experiments. They are related by the
operations below, and each table in the paper is computed on the version named in this file.

## 1. Version table

| id | What it is | Images | Boxes | Where it is used |
|---|---|---:|---:|---|
| **G1** | early test GT with only the re-annotated supplement applied | 1,685 (test) | 9,648 | GT-version study |
| **G2** | integrated annotation before deduplication | 16,660 | 164,743 | Table 10 (M1–M4) |
| **G3** | G2 after exact-duplicate removal — authoritative | 16,660 | **124,106** | Tables 7, 8, 11, 12, 13, 15; all GDINO results |
| **final** | G3 + merged four-class re-annotation | 16,660 | 123,648 | released dataset; Table 15 uses its partition |
| **T16 / T1-lab** | five-class training-label optimisation, inside a fixed 11,473-image train set | 11,473 (train) | — | Table 12 |
| **E02 v2** | scene-group-isolated split of `final` | 1,543 test (1,541 strict) | 12,688 test | Table 15 |

Table 10 reports the M1–M4 comparison computed on G2 (9,820 test boxes), before deduplication.
Every other main table uses G3.

## 2. How the versions relate

```
source annotations (DOTA, DIOR, fMoW, ...)
        │
        ├── integrated  ──► G2 (164,743)  ── exact-duplicate removal ──► G3 (124,106)
        │                                                                  │
        │                                                                  ├──► final (123,648)
        │                                                                  │    four classes re-annotated
        │                                                                  │
        │                                                                  └──► E02 v2 split of final
        │
        └── early partial test ──► G1 (9,648)
```

- **G2 → G3** removes exact duplicates only. Rule in `annotation_protocol.md` §3.
- **G3 → final** changes `airplane`, `bridge`, `storage_tank`, `helicopter`; 22 classes untouched.
- **E02 v2** re-partitions `final` by scene group, so that near-duplicate scenes stay within one
  split.

## 3. Splits

| split | train | val | test | used by |
|---|---:|---:|---:|---|
| G3 | 11,587 | 3,388 | 1,685 | Tables 7, 8, 11, 12, 13 |
| final | 11,699 | 3,391 | 1,570 | released dataset |
| E02 v2 (`full_1543`) | — | — | 1,543 | Table 15 |
| E02 v2 (`strict_1541`) | — | — | 1,541 | Table 15 sensitivity analysis |

1,040 public images change split between G3 and final. Split membership is defined by the split
CSVs in `splits/`; the image directory records storage only.

## 4. Training data used by the six baselines

All six Table-7 models were trained on the **tiled** set:

| component | images | boxes |
|---|---:|---:|
| whole-image half (same labels as G3 train) | 11,587 | 90,878 (pre-dedup) |
| 1024×1024 tiles (6,714 positive + 649 background) | 7,363 | 82,586 |
| **total** | **18,950** | **173,464** |

Training-frequency analyses use the 18,950 / 173,464 counts. The tiled set contains crops of
non-redistributable images and is not part of the public release (`docs/data_availability.md` §3).

## 5. Version tags in the published files

Every annotation file carries an `info` block naming its version. A reported number is identified
by both the version and the split, for example "G3, test, 1,685 images".
