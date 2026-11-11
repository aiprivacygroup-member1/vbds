# Taxonomy

26 classes, `category_id` 0–25, identical in every COCO file and every experiment. The ids were
fixed before training and are never renumbered. Machine-readable form: `taxonomy/categories.json`.

## 1. Class table

`full G3` is the count over all 16,660 images; `public G3` is the count over the 11,783 images in
the public release. A zero in the public column means the class is present in the benchmark but
absent from the redistributable subset.

| id | class | domain | paper term | full G3 | public G3 |
|---:|---|---|---|---:|---:|
| 0 | no_uav_sign | airspace control | no_uav_sign | 53 | 0 |
| 1 | airplane | airspace control | airplane | 17,418 | 10,076 |
| 2 | bridge | critical infrastructure | bridge | 5,204 | 3,132 |
| 3 | dam | critical infrastructure | dam | 1,050 | 1,050 |
| 4 | wind_turbine | critical infrastructure | wind_turbine | 5,375 | 5,363 |
| 5 | harbor | critical infrastructure | harbor | 10,334 | 5,406 |
| 6 | ship | critical infrastructure | ship | 31,153 | 23,276 |
| 7 | storage_tank | critical infrastructure | storage_tank | 15,778 | 12,089 |
| 8 | vehicle | ground activity / public safety | vehicle | 19,745 | 9,376 |
| 9 | container_area | critical infrastructure | container_area | 178 | 2 |
| 10 | crane | critical infrastructure | crane | 303 | 2 |
| 11 | surface_mine | critical infrastructure | surface_mine | 100 | 0 |
| 12 | solar_farm | critical infrastructure | solar_farm | 311 | 265 |
| 13 | tower | critical infrastructure | tower | 397 | 397 |
| 14 | face | identity privacy | face | 8,462 | 0 |
| 15 | person | ground activity / public safety | person | 3,722 | 3,701 |
| 16 | plate | identity privacy | plate | 266 | 0 |
| 17 | cooling_tower | critical infrastructure | chimney | 1,599 | 1,599 |
| 18 | helipad | airspace control | helipad | 104 | 104 |
| 19 | helicopter | airspace control | helicopter | 652 | 17 |
| 20 | runway | airspace control | runway | 584 | 583 |
| 21 | gas_station_canopy | critical infrastructure | gas_station_canopy | 113 | 0 |
| 22 | electric_substation | critical infrastructure | electric_substation | 164 | 164 |
| 23 | railway | critical infrastructure | railway | 700 | 700 |
| 24 | surveillance | ground activity / public safety | surveillance | 189 | 0 |
| 25 | crowd | ground activity / public safety | crowd | 152 | 0 |
| | **total** | | | **124,106** | **77,302** |

Domain sizes: airspace control 5 classes; critical infrastructure 15; ground activity / public
safety 4; identity privacy 2.

## 2. Naming notes

- **`cooling_tower`** is the DIOR `chimney` class. The paper's table header uses "chimney";
  the COCO files use `cooling_tower` on `category_id` 17. Both refer to the same boxes.
- **`tower`** is a transmission tower (TTPLA), not a generic building.
- **`runway`** and **`railway`** come from a scene-classification source (NWPU-RESISC45), where
  the label is image-level; boxes for these classes mark the scene's principal linear structure.
  The annotation procedure is described in `annotation_protocol.md` §2.
- **`face`** marks presence only. No identity information exists anywhere in the dataset.
- **`plate`** marks vehicle registration plates; the images are frames from traffic surveillance,
  and only the plate region is annotated.

## 3. Classes absent from the public release

Seven classes have zero public boxes because their images come from source units that are not
redistributable:

| class | boxes in full benchmark | source unit |
|---|---:|---|
| no_uav_sign | 53 | web-collected (S15) |
| surface_mine | 100 | web-collected (S13) |
| face | 8,462 | BirdsEye-RU (S06) |
| plate | 266 | TADBench (S10) |
| gas_station_canopy | 113 | web-collected (S14) |
| surveillance | 189 | web-collected (S11) |
| crowd | 152 | ERA (S07) |

These classes cannot be evaluated on the public subset; their full-benchmark counts are listed
above. Access to the source images is described in `DATA_ACCESS.md`.

## 4. Mapping from source labels

`taxonomy/source_category_mapping.json` records, per source unit, how many boxes of each VBDS
class came from that source. Some notable mappings:

| source label | VBDS class |
|---|---|
| DIOR `windmill` | `wind_turbine` |
| DIOR `chimney` | `cooling_tower` |
| DOTA `container-crane` | `crane` |
| VisDrone `pedestrian` | `person` |
| fMoW `solar_farm` / `helipad` / `electric_substation` | same names |

Boxes drawn for VBDS (web-collected classes, plate, part of tower/solar_farm) have no upstream
label mapping; they are described in `annotation_protocol.md`.
