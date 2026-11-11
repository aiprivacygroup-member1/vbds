# Scripts

## For users

| Script | Purpose |
|---|---|
| `validate_dataset.py` | read-only validation of annotations, splits and (optionally) images; writes JSON + Markdown |
| `verify_checksums.py` | verifies a `sha256sum`-format file against the files on disk |

Both use only the Python standard library.

## Release build

These scripts rebuild the release from the full dataset, which is not public. They are included
for reference.

| Script | Purpose |
|---|---|
| `audit_sources.py` | per-source image/byte/box counts and public–non-public overlap from the image ledger |
| `build_vbds.py` | filters G3 and final COCO files to redistributable images, keeping ids unchanged; writes public splits and manifest |
| `make_metadata.py` | writes `metadata/source_manifest.csv`, `metadata/dataset_statistics.json` and the taxonomy files |
| `make_reconstruction.py` | writes `reconstruction/reconstruction_manifest.csv` for the 4,877 non-public images |
| `prepare_public_release.py` | builds the per-source/split ZIPs, per-package manifests, SHA-256 list and `release_manifest.json` |
| `assemble_tree.py` | assembles this repository tree from the release pieces, including `examples/` |

Build order: `audit_sources` → `build_vbds` → `make_metadata` → `make_reconstruction` →
`prepare_public_release` → `assemble_tree`.

Properties preserved by the build:

- `category_id`, `image_id` and annotation ids are never renumbered.
- Images are not resized, recompressed or otherwise altered; image packages use `ZIP_STORED`.
- Annotations are copied, never edited.
- Package contents are copies of the source files.
