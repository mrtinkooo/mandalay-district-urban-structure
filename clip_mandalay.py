"""Extract GlobalBuildingAtlas footprints within Mandalay District, Myanmar.

Pipeline:
  1. Unzip Myanmar admin boundaries and pull the Mandalay District (admin2,
     pcode MMR010D001) polygon.
  2. Fetch the GBA.ODbLPolygon tile that covers Mandalay (asiawest,
     e095_n25_e100_n20) from HuggingFace if not already cached.
  3. Read the tile with a bbox prefilter (EPSG:3857), keep features that
     intersect the district, reproject to EPSG:4326, and write GeoJSON.
"""

import json
import os
import time
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data_raw"
WORK = ROOT / "data_processed"  # scratch for the unzipped admin2 layer

ADMIN_ZIP = DATA / "mmr_admin_boundaries.geojson.zip"
ADMIN2 = WORK / "mmr_admin2.geojson"
DISTRICT = DATA / "mandalay_district.geojson"

TILE_URL = (
    "https://huggingface.co/datasets/zhu-xlab/GBA.ODbLPolygon/"
    "resolve/main/asiawest/e095_n25_e100_n20.geojson"
)
TILE_CACHE = Path(
    os.environ.get("GBA_TILE", "/tmp/gba_asiawest_e095_n25_e100_n20.geojson")
)

OUT = DATA / "mandalay_district_buildings.geojson"
MANDALAY_PCODE = "MMR010D001"


def extract_admin2() -> None:
    if ADMIN2.exists():
        return
    print(f"Unzipping admin2 layer from {ADMIN_ZIP.name}")
    WORK.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ADMIN_ZIP) as z:
        z.extract("mmr_admin2.geojson", path=WORK)


def extract_mandalay_district() -> None:
    if DISTRICT.exists():
        return
    extract_admin2()
    print(f"Selecting Mandalay District ({MANDALAY_PCODE}) polygon")
    admin2 = json.load(ADMIN2.open())
    for f in admin2["features"]:
        if f["properties"].get("adm2_pcode") == MANDALAY_PCODE:
            json.dump(
                {"type": "FeatureCollection", "features": [f]},
                DISTRICT.open("w"),
            )
            return
    raise RuntimeError(f"adm2_pcode {MANDALAY_PCODE} not found in {ADMIN2}")


def download_tile() -> None:
    if TILE_CACHE.exists():
        size_mb = TILE_CACHE.stat().st_size / 1e6
        print(f"Using cached tile: {TILE_CACHE} ({size_mb:.0f} MB)")
        return
    print(f"Downloading ~630 MB tile from {TILE_URL}")
    TILE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(TILE_URL, TILE_CACHE)


def clip() -> None:
    t0 = time.time()
    district = gpd.read_file(DISTRICT).to_crs("EPSG:3857")
    bbox = tuple(district.total_bounds)
    print(f"District bbox (EPSG:3857): {bbox}")

    print("Reading tile with bbox prefilter…")
    bldgs = gpd.read_file(TILE_CACHE, bbox=bbox, engine="pyogrio")
    bldgs = bldgs.set_crs("EPSG:3857", allow_override=True)
    print(f"  bbox prefilter: {len(bldgs):,} features ({time.time() - t0:.1f}s)")

    geom = district.geometry.iloc[0]
    inside = bldgs.loc[bldgs.geometry.intersects(geom)].copy()
    print(f"  inside district: {len(inside):,}")

    inside.to_crs("EPSG:4326").to_file(OUT, driver="GeoJSON", engine="pyogrio")
    size_mb = OUT.stat().st_size / 1e6
    print(f"Wrote {OUT} ({size_mb:.1f} MB) in {time.time() - t0:.1f}s")


def main() -> None:
    DATA.mkdir(exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    extract_mandalay_district()
    download_tile()
    clip()


if __name__ == "__main__":
    main()
