# Reconstruction materials

4,877 images of the benchmark are not redistributed. This directory records what they are, so
that a researcher who obtains the originals from their providers can check that they hold the same
files the experiments were run on.

| File | Contents |
|---|---|
| `reconstruction_manifest.csv` | one row per non-public image: file name, G3 split, final split, source unit, width, height, size in bytes, MD5 |
| `source_mapping.json` | per source unit: provider, declared licence, counts, reason for exclusion |
| `source_access_guide.md` | how to obtain each original, and what to expect when matching |
| `reconstruct.py` | hashes a local copy and reports which manifest rows it covers |

## What this directory contains

- Image identifiers: file name, dimensions, size and MD5. No images.
- No annotations. Labels for non-public images are available from the authors under the
  conditions in `DATA_ACCESS.md` §5.
- No URLs harvested from third-party pages for the web-collected units (S11–S16); those batches
  have no published source list.

## Using the manifest

```bash
# after downloading, e.g., DOTA v1.5 to /data/dota
python reconstruct.py --manifest reconstruction_manifest.csv \
    --source-root /data/dota --out report_dota.json
```

The report counts `matched`, `absent`, `name_match_md5_differs` and `not_checked` per source
unit. Rows reported as `matched` are the exact files used in the experiments.

## Checksums

The manifest records per-image MD5, as produced by the experiment pipeline. Package-level
integrity uses SHA-256 (`release/checksums.sha256`).
