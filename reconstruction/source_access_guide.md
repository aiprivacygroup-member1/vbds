# Source access guide (non-public units)

Ten source units are not redistributed. This guide states where each original can be obtained and
what to expect when matching it against `reconstruction_manifest.csv`.

The manifest identifies images, not labels. Annotations for these images are available from the
authors (`DATA_ACCESS.md` §5).

## S01 · DOTA v1.5 (1,115 images)

- Provider: <https://captain-whu.github.io/DOTA/dataset.html>
- Terms: academic use; redistribution not granted.
- Contents: 1,115 images carrying `airplane`, `bridge`, `harbor`, `ship`, `storage_tank`,
  `vehicle`, `crane` and `helicopter` boxes (P-prefixed `P####.png` files).
- Matching: DOTA distributes large images; the files here are whole images, not crops. Match on
  MD5 first; if the provider repackages, compare dimensions and visual content.
- Labels: DOTA's own labels, remapped to the VBDS taxonomy.

## S06 · BirdsEye-RU (2,934 images)

- Provider: <https://www.kaggle.com/datasets/mdahanafarifkhan/birdseye-ru>
- Terms: Kaggle metadata declares CC BY-SA 4.0.
- Contents: 2,934 images carrying 8,462 `face` boxes — the entire `face` class.
- Matching: the Kaggle archive structure (`train`/`valid`/`test`) matches the manifest layout.

## S07 · ERA (128 images)

- Provider: <https://lcmou.github.io/ERA_Dataset/>
- Terms: no licence declared.
- Contents: 128 frames carrying `crowd`, `person` and `vehicle` boxes.

## S10 · TADBench (170 images)

- Provider: <https://github.com/UnicomAI/UnicomBenchmark/tree/main/TADBench>
- Terms: no LICENSE file in the repository or the data directory.
- Contents: 170 traffic-surveillance frames carrying 266 `plate` boxes.
- Matching: frames were extracted from video; frame indices are not preserved in the file names,
  so MD5 matching is the reliable test.

## S11 · Web: surveillance (135 images)

- No source list is published. 189 `surveillance` boxes.

## S12 · Web: container area / crane (103 images)

- Mixed hosts (Pexels, Unsplash, Pixabay, Shutterstock, Alamy, Dreamstime). 176 `container_area`
  and 159 `crane` boxes.
- Not reconstructible without the original URL list.

## S13 · Web: surface mine (100 images)

- Mixed free and commercial hosts. 100 `surface_mine` boxes; no source list is published.

## S14 · Web: gas-station canopy (99 images)

- Commercial stock and search thumbnails. 113 `gas_station_canopy` boxes.

## S15 · Web: no-UAV sign (53 images)

- Stock library material with perspective augmentation. 53 `no_uav_sign` boxes.

## S16 · Web: solar farm (40 images)

- Commercial stock material. 46 `solar_farm` boxes.

## Summary

| Reconstructible | Not reconstructible |
|---|---|
| S01 DOTA, S06 BirdsEye-RU, S07 ERA, S10 TADBench | S11–S16 (web-collected, no published source list) |

Four units (S01, S06, S07, S10 — 4,347 images, 45,913 G3 boxes) can be restored by downloading
from the provider and matching the manifest. The remaining six (S11–S16 — 530 images) have no
public source list. Per-unit counts are in `source_mapping.json` and
`reconstruction_manifest.csv`.
