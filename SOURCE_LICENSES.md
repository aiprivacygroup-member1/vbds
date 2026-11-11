# Source licences and redistribution evidence

Each source unit was checked against its own published terms. The table records what is relied
on. Machine-readable version: `metadata/source_manifest.csv`. Captured evidence (pages, licence
files, repository snapshots) is filed per source in the image packages under
`VBDS/LICENSES/evidence/<unit>/`.

Summary: 6 units are redistributable (11,783 images), 10 are not (4,877 images).

## 1. Redistributable units

### S02 · DIOR — CC BY-NC 4.0

- Source: <https://gcheng-nwpu.github.io/> · <https://ieee-dataport.org/documents/dior>
- Terms: Creative Commons Attribution-NonCommercial 4.0 International,
  <https://creativecommons.org/licenses/by-nc/4.0/>.
- Relied on: the licence permits reproduction and adaptation for non-commercial purposes with
  attribution. VBDS redistributes renamed images and its own annotations, non-commercially.
- Attribution: cite Li et al., *Object detection in optical remote sensing images: A survey and a
  new benchmark*, ISPRS J. Photogramm. Remote Sens. 159 (2020).
- Note: the DIOR `chimney` class is mapped to the VBDS `cooling_tower` class. This is a label
  mapping, not a claim that DIOR and VBDS share a taxonomy.

### S03 · fMoW — fMoW Challenge Public License

- Source: <https://github.com/fMoW/dataset>, licence text at `/blob/master/LICENSE`.
- Terms: non-commercial research use, attribution required; the full text ships as
  `LICENSES/evidence/S03/fmow_LICENSE.txt`.
- Relied on: redistribution of derived data for non-commercial research is within the grant.
- Attribution: cite Christie et al., *Functional Map of the World*, CVPR 2018.

### S04 · NWPU-RESISC45 — CC BY-NC 4.0

- Source: <https://gcheng-nwpu.github.io/>.
- Terms: CC BY-NC 4.0.
- Attribution: cite Cheng, Han & Lu, *Remote Sensing Image Scene Classification: Benchmark and
  State of the Art*, Proc. IEEE 105(10), 2017.

### S05 · VisDrone — CC BY-NC-SA 3.0

- Source: <https://github.com/VisDrone/VisDrone-Dataset> · data-protection page
  <https://aiskyeye.com/data-protection/>.
- Terms: CC BY-NC-SA 3.0 — non-commercial, attribution, share-alike.
- Relied on: redistribution is permitted; share-alike means VBDS annotations for these images
  are offered under the same licence (stated in `LICENSE` §2).
- Attribution: cite Zhu et al., *Detection and Tracking Meet Drones Challenge*, IEEE TPAMI 44(11),
  2021.

### S08 / S09 · TTPLA — Apache License 2.0

- Source: <https://github.com/R3ab/ttpla_dataset>, repository root `LICENSE`
  (Apache License Version 2.0).
- Terms: Apache 2.0 — reproduction, modification and redistribution permitted, including
  commercially, subject to attribution, retention of the licence and NOTICE, and a statement of
  changes.
- Relied on: the repository publishes both code and imagery; the imagery is therefore offered
  under the repository licence. VBDS redistributes cropped/screenshotted images with a
  modification statement in each package's NOTICE.
- Attribution: cite Abdelfattah, Wang & Wang, *TTPLA: An Aerial-Image Dataset for Detection and
  Segmentation of Transmission Towers and Power Lines*, ACCV 2020.

## 2. Non-redistributable units

| Unit | Source | Licence position | Consequence |
|---|---|---|---|
| S01 | DOTA v1.5 | academic use only; redistribution not granted | images and annotations withheld |
| S06 | BirdsEye-RU | Kaggle metadata declares CC BY-SA 4.0; redistribution permission not granted | withheld |
| S07 | ERA | no licence declared upstream | withheld |
| S10 | TADBench | repository and data directory contain no LICENSE | withheld |
| S11 | Web: surveillance | no file-level licence record | withheld |
| S12 | Web: container/crane | mixed Pexels/Unsplash/Pixabay and Shutterstock/Alamy/Dreamstime; no file-level record | withheld in full |
| S13 | Web: surface mine | mixed free and commercial hosts | withheld in full |
| S14 | Web: gas-station canopy | commercial stock and search thumbnails | withheld |
| S15 | Web: no-UAV sign | stock library material | withheld |
| S16 | Web: solar farm | commercial stock material | withheld |

For S12 and S13 a subset of files is plausibly redistributable under the free-host licences.
These units are not split, because host-level attribution is not file-level clearance and a
partial release would be an incomplete subset.

## 3. Scope

- No licence is claimed over third-party imagery by the VBDS authors.
- No sub-licensing, no relicensing, and no transfer of rights to users of this repository.
- The `LICENSE` file states the terms that the authors apply to their own code, metadata and
  annotations.
