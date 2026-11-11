# Data access

VBDS aggregates imagery from 16 source units. Sources whose terms permit redistribution are
distributed with this release; the rest must be obtained from their original providers. This file
states, per source unit, what is shipped, what is not, and where the original can be obtained.

Access keys used below:

| Status | Meaning | Shipped in public packages |
|---|---|---|
| `PUBLIC_APPROVED` | the source licence permits redistribution, with attribution and non-commercial terms | images + annotations |
| `EXTERNAL_SOURCE` | research use permitted by the provider; redistribution not granted | nothing; obtain from provider |
| `PERMISSION_REQUIRED` | rights holders exist; redistribution permission has not been granted | nothing |
| `WEB_COLLECTED` | images collected from public web pages, without a file-level licence record | nothing |
| `WITHHELD` | no licence, or commercial-only terms | nothing |

## 1. Per-source access table

| Unit | Source | Images | Status | Public release | How to obtain the original |
|---|---|---:|---|---|---|
| S01 | DOTA v1.5 | 1,115 | `EXTERNAL_SOURCE` | not shipped | <https://captain-whu.github.io/DOTA/dataset.html> (academic use; redistribution requires written permission) |
| S02 | DIOR (incl. DIOR `chimney` subset) | 9,565 | `PUBLIC_APPROVED` | images + annotations | <https://gcheng-nwpu.github.io/> · <https://ieee-dataport.org/documents/dior> |
| S03 | fMoW | 484 | `PUBLIC_APPROVED` | images + annotations | <https://github.com/fMoW/dataset> |
| S04 | NWPU-RESISC45 | 1,275 | `PUBLIC_APPROVED` | images + annotations | <https://gcheng-nwpu.github.io/> |
| S05 | VisDrone | 200 | `PUBLIC_APPROVED` | images + annotations | <https://github.com/VisDrone/VisDrone-Dataset> |
| S06 | BirdsEye-RU | 2,934 | `PERMISSION_REQUIRED` | not shipped | <https://www.kaggle.com/datasets/mdahanafarifkhan/birdseye-ru> |
| S07 | ERA | 128 | `PERMISSION_REQUIRED` | not shipped | <https://lcmou.github.io/ERA_Dataset/> |
| S08 | TTPLA (tower subset, batch 1) | 129 | `PUBLIC_APPROVED` | images + annotations | <https://github.com/R3ab/ttpla_dataset> |
| S09 | TTPLA (tower subset, batch 2) | 130 | `PUBLIC_APPROVED` | images + annotations | <https://github.com/R3ab/ttpla_dataset> |
| S10 | TADBench (plate frames) | 170 | `WITHHELD` | not shipped | <https://github.com/UnicomAI/UnicomBenchmark/tree/main/TADBench> (no licence file) |
| S11 | Web: surveillance | 135 | `WEB_COLLECTED` | not shipped | no source list published |
| S12 | Web: container area / crane | 103 | `WEB_COLLECTED` | not shipped | mixed hosts; no file-level licence record |
| S13 | Web: surface mine | 100 | `WEB_COLLECTED` | not shipped | mixed hosts; no file-level licence record |
| S14 | Web: gas-station canopy | 99 | `WITHHELD` | not shipped | commercial stock and search thumbnails |
| S15 | Web: no-UAV sign | 53 | `WITHHELD` | not shipped | stock library material |
| S16 | Web: solar farm | 40 | `WITHHELD` | not shipped | commercial stock material |
| | **total** | **16,660** | | **11,783 images shipped** | |

Per-source counts are in `metadata/source_manifest.csv`; per-image provenance is in the
`source_unit` column of each split CSV.

## 2. What the public release contains

| Component | Contents |
|---|---|
| image packages (18 ZIPs) | 11,783 images from S02, S03, S04, S05, S08, S09 |
| `annotations-g3` | COCO train/val/test for the 11,783 public images, G3 version (77,302 boxes) |
| `annotations-final` | the same images, refined version (76,708 boxes) |
| `metadata` | split lists, per-image manifest, statistics, taxonomy, per-source NOTICEs |

The public release is a subset of the benchmark. Full-benchmark tables are computed on the full G3
test split (1,685 images, 8,568 boxes); public-subset results are reported separately.

## 3. Sources not included

- **DOTA (S01).** The DOTA terms grant academic use and prohibit commercial use; they do not grant
  redistribution. The annotations derived from DOTA images are therefore not published either.
  Obtain DOTA from the official site and use `reconstruction/` to match the images.
- **BirdsEye-RU (S06).** The Kaggle metadata declares CC BY-SA 4.0; redistribution permission has
  not been granted. Not released.
- **ERA (S07).** No licence is declared for the ERA dataset. Not released.
- **TADBench (S10).** The repository and data directory contain no LICENSE file. Not released.
- **Web-collected batches (S11–S16).** Images were gathered from mixed hosts, including commercial
  stock libraries and search thumbnails. No file-level licence record exists, and the batch is not
  released in any form.

## 4. Reconstructing the full benchmark

`reconstruction/` contains:

- `reconstruction_manifest.csv` — one row per non-public image with file name, split (G3 and
  final), source unit, width/height, size and MD5 of the file used in the experiments;
- `source_access_guide.md` — how to obtain each original and which subset was used;
- `reconstruct.py` — a helper that verifies a locally obtained original against the manifest and
  reports which benchmark images it covers.

The manifest lets a holder of the originals check that they hold the same files. It contains no
image data; it identifies files only.

Annotations for non-public images are not published; a reconstructed image set provides the images
used by the benchmark but not their labels. This is described in `docs/data_availability.md`.

## 5. Requests

Requests for access to restricted portions, or for clarification of a source's status, should be
addressed to the corresponding author of the paper (`liyinglong@zjut.edu.cn`). Rights in
third-party imagery remain with the respective providers.
