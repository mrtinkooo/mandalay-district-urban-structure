"""Step 2 — extract the 7 Mandalay District township polygons.

Reads `mmr_admin3.geojson` from the admin-boundaries zip, filters to rows
with adm2_pcode == MMR010D001, and writes a minimal GeoJSON used by every
downstream step.
"""

from __future__ import annotations

import geopandas as gpd

from scripts import config as C
from scripts.io_utils import extract_admin_layer


KEEP_COLS = [
    "adm3_pcode",
    "adm3_name",
    "adm3_name1",  # Burmese (Myanmar) name
    "adm2_pcode",
    "adm2_name",
    "area_sqkm",  # area as published by MIMU — kept for sanity-check only
    "center_lat",
    "center_lon",
    "geometry",
]


def build_townships() -> gpd.GeoDataFrame:
    admin3 = extract_admin_layer(
        C.ADMIN_ZIP, "mmr_admin3.geojson", C.DATA_PROCESSED
    )
    gdf = gpd.read_file(admin3)
    mda = gdf[gdf["adm2_pcode"] == C.MANDALAY_DISTRICT_PCODE].copy()
    mda = mda[[c for c in KEEP_COLS if c in mda.columns]]
    mda = mda.sort_values("adm3_pcode").reset_index(drop=True)
    return mda


def main() -> None:
    C.ensure_dirs()
    mda = build_townships()
    mda.to_file(C.TOWNSHIPS_GEOJSON, driver="GeoJSON")
    print(f"[townships] wrote {len(mda)} townships to {C.TOWNSHIPS_GEOJSON}")
    print(mda.drop(columns="geometry").to_string(index=False))


if __name__ == "__main__":
    main()
