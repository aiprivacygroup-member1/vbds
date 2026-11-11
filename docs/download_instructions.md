# Download and extraction instructions

## 1. Packages

The image data is distributed as 21 ZIP files outside this repository:

| Package group | Files | Contents |
|---|---:|---|
| `vbds-v1.0-public-S02-*.zip` | 4 | DIOR, 9,565 images |
| `vbds-v1.0-public-S03-*.zip` | 3 | fMoW, 484 images |
| `vbds-v1.0-public-S04-*.zip` | 3 | NWPU-RESISC45, 1,275 images |
| `vbds-v1.0-public-S05-*.zip` | 3 | VisDrone, 200 images |
| `vbds-v1.0-public-S08-*.zip` | 3 | TTPLA batch 1, 129 images |
| `vbds-v1.0-public-S09-train-part{1,2}of2.zip` | 2 | TTPLA batch 2, 130 images |
| `vbds-v1.0-public-annotations-{g3,final}.zip` | 2 | COCO annotations |
| `vbds-v1.0-public-metadata.zip` | 1 | splits, manifests, statistics, taxonomy |

Download the list and hashes from `release/release_manifest.json`; the short form is
`release/checksums.sha256`.

## 2. Verify before extracting

```bash
sha256sum -c release/checksums.sha256     # run from the directory that contains packages/
```

Every file reports `OK`. A mismatch indicates an incomplete download; re-download that file
before extracting.

## 3. Extract

```bash
./extract_packages.sh ./packages /data/vbds
```

or, by hand:

```bash
for z in packages/vbds-v1.0-public-*.zip; do unzip -n "$z" -d /data/vbds; done
```

Each package extracts to `VBDS/images/<split>/` and carries its own `LICENSES/<source>_NOTICE.txt`
plus `packages/<package-id>/PACKAGE_INFO.json` and `MANIFEST.csv`. Parts of the same split merge
without conflict; extraction order does not matter.

## 4. Check the result

```bash
python scripts/validate_dataset.py \
    --annotations /data/vbds/VBDS/annotations \
    --splits /data/vbds/VBDS/splits \
    --images /data/vbds/VBDS/images
```

Expected: 11,783 annotated images, 0 missing, 0 failures. On-disk file count is 11,784 because one
fMoW image is stored under two names (`...jpg` and `...__dup2.jpg`), so that the G3 and final
annotations each resolve.
