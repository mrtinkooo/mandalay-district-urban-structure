# Mandalay District — Township-level Urban Structure

Open, reproducible geospatial analysis of 286,818 building footprints across
the 7 townships of **Mandalay District, Myanmar** (adm2 pcode
`MMR010D001`). Outputs include:

- township-level urban-structure indicators (density, built-up ratio,
  footprint-size distribution, shape metrics)
- static PNG maps and charts
- interactive Leaflet/Folium maps
- a self-contained static website in `docs/` that can be served via
  **GitHub Pages**

Live site (once Pages is enabled on `main` / `docs`):
<https://geonet-myanmar.github.io/mandalay-district-buildings/>

---

## Repository layout

```
.
├── clip_mandalay.py                          # one-off GBA → district clip (original)
├── run_all.py                                # full analysis pipeline (step 1–8)
├── requirements.txt
├── README.md
├── LICENSE
│
├── data_raw/
│   ├── mmr_admin_boundaries.geojson.zip      # MIMU/UN OCHA admin 0-5 layers
│   ├── mandalay_district.geojson             # district polygon only (admin-2)
│   └── mandalay_district_buildings.geojson.gz  # 286,818 footprints, EPSG:4326
│
├── data_processed/                           # produced by the pipeline
│   ├── mandalay_townships.geojson            # 7 township polygons (admin-3)
│   ├── mandalay_townships_indicators.geojson # township polygons + every indicator
│   ├── buildings_with_township.parquet       # building + township + shape metrics
│   └── audit_report.json
│
├── scripts/
│   ├── config.py                             # paths, CRS, size-class breaks
│   ├── io_utils.py
│   ├── audit_data.py                         # step 1 — data audit
│   ├── prepare_townships.py                  # step 2 — extract 7 townships
│   ├── spatial_join.py                       # step 3 — assign + shape metrics
│   ├── compute_indicators.py                 # step 4 — township summary tables
│   ├── make_charts.py                        # step 5 — PNG charts
│   ├── make_maps.py                          # step 6 — PNG maps
│   ├── make_interactive_map.py               # step 7 — Folium HTML maps
│   └── build_site.py                         # step 8 — render docs/index.html
│
├── outputs/                                  # publication-ready artifacts
│   ├── tables/   (CSV: township_summary, township_size_classes, …)
│   ├── charts/   (PNG, 8 charts)
│   └── maps/     (PNG, 6 maps)
│
└── docs/                                     # ← GitHub Pages root
    ├── index.html
    ├── assets/css/style.css
    ├── assets/img/                           # copies of charts + maps
    └── interactive/
        ├── townships_choropleth.html
        └── building_heatmap.html
```

## Quick start

Requires Python 3.10+.

```bash
git clone https://github.com/geonet-myanmar/mandalay-district-buildings
cd mandalay-district-buildings
pip install -r requirements.txt

python run_all.py          # runs all 8 pipeline steps (~1 min)
```

Or run individual steps:

```bash
python -m scripts.audit_data
python -m scripts.prepare_townships
python -m scripts.spatial_join
python -m scripts.compute_indicators
python -m scripts.make_charts
python -m scripts.make_maps
python -m scripts.make_interactive_map
python -m scripts.build_site
```

## Pipeline

| Step | Script | Reads | Writes |
|------|--------|-------|--------|
| 1 | `audit_data` | `data_raw/*` | `data_processed/audit_report.json` |
| 2 | `prepare_townships` | admin-3 layer | `data_processed/mandalay_townships.geojson` |
| 3 | `spatial_join` | buildings + townships | `data_processed/buildings_with_township.parquet` |
| 4 | `compute_indicators` | joined parquet | `outputs/tables/*.csv`, enriched townships geojson |
| 5 | `make_charts` | summary tables | `outputs/charts/*.png` |
| 6 | `make_maps` | enriched townships, buildings | `outputs/maps/*.png` |
| 7 | `make_interactive_map` | enriched townships, buildings | `docs/interactive/*.html` |
| 8 | `build_site` | charts, maps, tables | `docs/index.html`, `docs/assets/...` |

All spatial operations use **EPSG:32646 (UTM 46N)**, metres — a single
metric CRS for every area, length, and shape measurement in the district.

## Data sources

- **Building footprints** — clipped from
  [GlobalBuildingAtlas](https://github.com/zhu-xlab/GlobalBuildingAtlas)
  tile `asiawest/e095_n25_e100_n20`, a merge of OpenStreetMap (© OSM
  contributors, ODbL) and Microsoft Building Footprints (ODbL). Every
  feature carries a `source` attribute of `osm` or `ms`.
- **Township boundaries (admin-3)** — MIMU / UN OCHA Myanmar common
  operational datasets, bundled in `data_raw/mmr_admin_boundaries.geojson.zip`;
  filtered to `adm2_pcode == MMR010D001`.

The original clip is reproduced by `clip_mandalay.py` (downloads the 630 MB
GBA tile to `/tmp` on first run). Every step after that runs off the
already-clipped `data_raw/mandalay_district_buildings.geojson.gz`.

## Indicators

Per township, `outputs/tables/township_summary.csv` contains:

| column | meaning |
|--------|---------|
| `township_area_km2` | area (km²) computed in EPSG:32646 |
| `building_count` | number of footprints whose centroid falls inside |
| `total_builtup_area_m2` / `_km2` | sum of footprint areas |
| `mean_/median_/min_/max_/std_building_area_m2` | footprint-size stats |
| `building_density_per_km2` | buildings / km² |
| `builtup_ratio` | built-up area / township area (0–1) |
| `builtup_area_per_km2` | built-up m² / km² |
| `mean_compactness_pp` | Polsby-Popper (4π·A/P²); 1 = circle |
| `mean_mrr_fill` | footprint area / min-rotated-rectangle area |
| `mean_mrr_elongation` | MRR short-side / long-side |
| `share_footprint_ge_1000m2` | share of footprints ≥ 1000 m² |

Size-class breaks (m²): `30 / 80 / 200 / 1000` → *very small, small,
medium, large, very large* (see `scripts/config.py` for justification).

## GitHub Pages

The `docs/` folder is a fully static, self-contained site — no build
step, no runtime dependencies. To publish:

1. In GitHub: **Settings → Pages → Source = "Deploy from a branch"**
2. Branch = `main`, folder = `/docs`
3. Save. Site is live at
   `https://<user>.github.io/<repo>/` within a minute or so.

The interactive maps are plain `.html` files that use the Leaflet CDN, so
they render directly from Pages with no backend.

## Limitations

- **Footprint completeness varies by source.** GBA merges Microsoft and
  OSM; very small huts may be under-represented in some areas, and large
  compounds may be drawn as a single polygon in others.
- **No semantic attributes.** No building use, height, age, or
  occupancy — we only know the polygon and which dataset drew it. All
  size-class labels here are shape-based proxies, not land-use classes.
- **Centroid-based join.** A building whose footprint straddles a
  township boundary is assigned to whichever township contains its
  centroid (15 slivers with centroids exactly outside every polygon are
  attached to the nearest township). This avoids double-counting but
  may mis-attribute a handful of boundary-straddling buildings.
- **Township area** is recomputed in EPSG:32646; it differs from the
  MIMU-published `area_sqkm` by < 0.5 %.
- **No demographic data.** Anything "per capita" would require an
  additional population layer (e.g. WorldPop) not included here.

## Licenses

- **Code** — MIT (see `LICENSE`).
- **Derived data** — ODbL 1.0, inherited from GBA / OSM / Microsoft.
  Any redistribution must preserve attribution and share-alike.
- **Admin boundaries** — MIMU terms, redistributed unchanged.

## Citation

If you use this dataset or the derived indicators, please cite the
upstream GBA project:

> Sun, X., Zhu, X. X., et al. *GlobalBuildingAtlas: A global building
> dataset with AI-derived polygons, heights, and LoD1 3D models.*
> <https://github.com/zhu-xlab/GlobalBuildingAtlas>
