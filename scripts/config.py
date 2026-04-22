"""Central configuration for the Mandalay urban structure analysis.

All paths are resolved relative to the repo root so the pipeline works from
any working directory. No user-specific paths are baked in.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --- inputs -----------------------------------------------------------------
DATA_RAW = ROOT / "data_raw"
ADMIN_ZIP = DATA_RAW / "mmr_admin_boundaries.geojson.zip"
DISTRICT_GEOJSON = DATA_RAW / "mandalay_district.geojson"
BUILDINGS_GZ = DATA_RAW / "mandalay_district_buildings.geojson.gz"

# --- processed --------------------------------------------------------------
DATA_PROCESSED = ROOT / "data_processed"
TOWNSHIPS_GEOJSON = DATA_PROCESSED / "mandalay_townships.geojson"
BUILDINGS_WITH_TOWNSHIP = DATA_PROCESSED / "buildings_with_township.parquet"

# --- outputs ----------------------------------------------------------------
OUTPUTS = ROOT / "outputs"
TABLES_DIR = OUTPUTS / "tables"
CHARTS_DIR = OUTPUTS / "charts"
MAPS_DIR = OUTPUTS / "maps"

DOCS = ROOT / "docs"
DOCS_ASSETS = DOCS / "assets"
DOCS_IMG = DOCS_ASSETS / "img"
DOCS_CSS = DOCS_ASSETS / "css"
DOCS_INTERACTIVE = DOCS / "interactive"

# --- spatial ----------------------------------------------------------------
# Mandalay District is centred near 22°N, 96°E.
# EPSG:32646 = UTM zone 46N (WGS84), metres — suitable for the whole district.
# Used for all area, length, and shape metrics in the pipeline.
WORKING_CRS = "EPSG:32646"
DISPLAY_CRS = "EPSG:4326"  # geographic, for interactive web maps
WEB_MERCATOR = "EPSG:3857"  # required for contextily basemaps

# --- Mandalay District admin codes -----------------------------------------
MANDALAY_DISTRICT_PCODE = "MMR010D001"

# --- building-size classes (m²) ---------------------------------------------
# Breaks chosen on the empirical distribution of this dataset (see
# scripts/compute_indicators.py — the histogram is heavily right-skewed,
# with a long tail of institutional / industrial footprints). The breaks
# follow widely used urban-morphology conventions:
#   very small  : < 30 m²   — huts, sheds, accessory structures
#   small       : 30–80     — typical single-unit rural/peri-urban dwellings
#   medium      : 80–200    — urban residential, small shops
#   large       : 200–1000  — apartment blocks, schools, medium commercial
#   very large  : >= 1000   — factories, warehouses, malls, pagoda compounds
SIZE_CLASS_BREAKS_M2 = [0, 30, 80, 200, 1000, float("inf")]
SIZE_CLASS_LABELS = ["very small", "small", "medium", "large", "very large"]

# --- matplotlib styling -----------------------------------------------------
FIG_DPI = 150
TOWNSHIP_CMAP = "YlOrRd"


def ensure_dirs() -> None:
    """Create all output directories if they do not already exist."""
    for d in (
        DATA_PROCESSED,
        OUTPUTS,
        TABLES_DIR,
        CHARTS_DIR,
        MAPS_DIR,
        DOCS,
        DOCS_ASSETS,
        DOCS_IMG,
        DOCS_CSS,
        DOCS_INTERACTIVE,
    ):
        d.mkdir(parents=True, exist_ok=True)
