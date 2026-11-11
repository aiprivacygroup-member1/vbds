# Example images

Sample images from the redistributable sources, showing the imagery and the COCO entry layout.

| file | source | licence | G3 split | boxes |
|---|---|---|---|---:|
| `images/S02_wind_turbine_dior_06704.jpg` | DIOR (S02) | CC BY-NC 4.0 | train | 6 |
| `images/S03_helipad_helipad_20_2_rgb_2.jpg` | fMoW (S03) | fMoW Challenge Public License | val | 1 |
| `images/S04_runway_runway_248.jpg` | NWPU-RESISC45 (S04) | CC BY-NC 4.0 | train | 1 |
| `images/S05_person_9999981_00000_d_0000052.jpg` | VisDrone (S05) | CC BY-NC-SA 3.0 | train | 3 |
| `images/S08_tower_66_00136.jpg` | TTPLA-yolo (S08) | Apache 2.0 | train | 4 |

Annotations are reproduced in `examples.json` in COCO fields, keyed by
`category_id` 0–25. Attribution and full terms are in `SOURCE_LICENSES.md`. Each image keeps its
original MD5 so it can be traced to `metadata/public_image_manifest.csv`.
