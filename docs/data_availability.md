# Data availability

This page states which parts of the benchmark are distributed, which parts are obtained from
their providers, and how the two relate.

## 1. The public release is a subset of the benchmark

The public release holds 11,783 of 16,660 images and 77,302 of 124,106 G3 boxes (62.3% of boxes).
Nineteen of the 26 classes have at least one box in the public release. The classes without
public boxes (`face`, `plate`, `no_uav_sign`, `surface_mine`, `surveillance`, `crowd`,
`gas_station_canopy`) come from source units that are not redistributable; their counts in the
full benchmark are listed in `taxonomy.md` §3.

The public subset is a complete, self-consistent dataset: annotations, splits, images and checksums
cover the same 11,783 images, and all reported public-subset numbers are computed on it.

Full-benchmark results use the full G3 test split (1,685 images, 8,568 boxes). Public-subset
results use the 994 public test images (5,587 G3 boxes). The two sets of numbers are reported
separately throughout the paper and this repository.

## 2. Annotations for non-public images are not published

The 4,877 non-public images come from 10 source units. Their annotations are held back with the
images: a label that describes a non-redistributable image is derived from that image, and the
source terms do not grant its redistribution.

`reconstruction/reconstruction_manifest.csv` identifies each non-public image by file name, split,
size and MD5, so that a holder of the originals can confirm they hold the same files. The
manifest does not contain labels. Reconstructing the image set yields the benchmark images, not
the ground truth for those images; full-benchmark evaluation requires the annotation files, which
are available from the authors under the conditions in `DATA_ACCESS.md` §5.

## 3. Training data used by the six baselines

The six Table-7 detection models were trained on a tiled set: 11,587 whole images plus 7,363
1024×1024 tiles (6,714 positive, 649 background), totalling 18,950 images and 173,464 boxes.
The tiled set contains crops of non-redistributable images and is not part of the public release.
`docs/dataset_versions.md` §4 gives its composition.

## 4. Which release to use

The dataset is distributed in two annotation versions and several splits:

- `annotations/g3/` — the annotation version used for all benchmark tables in the paper;
- `annotations/final/` — the released dataset version, including the four-class refinement;
- `splits/{g3,final}_{train,val,test}.csv` — the corresponding split membership.

A result is identified by both the annotation version and the split, for example
"G3, test". `docs/dataset_versions.md` lists the versions and the split used by each table.
