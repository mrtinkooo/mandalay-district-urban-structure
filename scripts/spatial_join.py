"""Step 3 — assign each building to a township and compute geometric metrics.

For each building we compute:
  * footprint area (m²) in the projected CRS
  * perimeter (m)
  * Polsby-Popper compactness  = 4π·A / P²   (1 = perfect circle)
  * shape index                 = P / (2·√(π·A))   (1 = perfect circle, >1 elongated)
  * minimum-rotated-rectangle fill ratio = A / area(mrr)  (1 = rectangular)
  * mrr elongation              = short_side / long_side   (1 = square, → 0 elongated)

Buildings are joined to townships using a `within` predicate on the building
centroid (cheaper than polygon-to-polygon overlay and appropriate here since
building footprints are small compared with townships; centroid-in-township
is unambiguous for 99.99%+ of features).

The joined table is written as Parquet for fast downstream loading.
"""

from __future__ import annotations

import time

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry.base import BaseGeometry

from scripts import config as C
from scripts.io_utils import read_gzipped_geojson


def _shape_metrics(geoms: gpd.GeoSeries) -> pd.DataFrame:
    area = geoms.area
    perim = geoms.length
    # Polsby-Popper; safe for perim==0 → fill NaN
    with np.errstate(divide="ignore", invalid="ignore"):
        pp = 4 * np.pi * area / np.square(perim)
        shape_idx = perim / (2 * np.sqrt(np.pi * area))

    # Minimum rotated rectangle — vectorised via apply; cheap enough at 286k rows.
    def _mrr_metrics(g: BaseGeometry) -> tuple[float, float]:
        if g.is_empty:
            return (np.nan, np.nan)
        mrr = g.minimum_rotated_rectangle
        coords = list(mrr.exterior.coords)
        # mrr has 5 points (closed ring), 4 unique; compute side lengths of
        # the first two consecutive edges (perpendicular to each other).
        from math import hypot

        def _edge(p, q):
            return hypot(q[0] - p[0], q[1] - p[1])

        s1 = _edge(coords[0], coords[1])
        s2 = _edge(coords[1], coords[2])
        long_side = max(s1, s2)
        short_side = min(s1, s2)
        mrr_area = mrr.area
        fill = g.area / mrr_area if mrr_area > 0 else np.nan
        elong = short_side / long_side if long_side > 0 else np.nan
        return (fill, elong)

    mrr_vals = np.array([_mrr_metrics(g) for g in geoms.values])
    return pd.DataFrame(
        {
            "area_m2": area.values,
            "perim_m": perim.values,
            "compactness_pp": pp.values,
            "shape_index": shape_idx.values,
            "mrr_fill": mrr_vals[:, 0],
            "mrr_elongation": mrr_vals[:, 1],
        }
    )


def main() -> None:
    C.ensure_dirs()

    print("[join] loading townships + buildings ...")
    t0 = time.time()
    townships = gpd.read_file(C.TOWNSHIPS_GEOJSON).to_crs(C.WORKING_CRS)
    buildings = read_gzipped_geojson(C.BUILDINGS_GZ).to_crs(C.WORKING_CRS)
    print(
        f"[join] townships={len(townships)} buildings={len(buildings):,} "
        f"(load {time.time() - t0:.1f}s)"
    )

    print("[join] computing shape metrics ...")
    t1 = time.time()
    metrics = _shape_metrics(buildings.geometry)
    buildings = buildings.reset_index(drop=True).join(metrics)
    print(f"[join] metrics done ({time.time() - t1:.1f}s)")

    print("[join] centroid-in-township spatial join ...")
    t2 = time.time()
    centroids = buildings.copy()
    centroids["geometry"] = centroids.geometry.centroid
    joined = gpd.sjoin(
        centroids,
        townships[["adm3_pcode", "adm3_name", "geometry"]],
        how="left",
        predicate="within",
    )
    # drop the index_right column, keep township cols
    joined = joined.drop(columns=["index_right"])
    # put the original polygon geometry back (not the centroid)
    joined["geometry"] = buildings.geometry.values
    print(f"[join] sjoin done ({time.time() - t2:.1f}s)")

    missing = joined["adm3_pcode"].isna().sum()
    if missing:
        # Fallback: for any centroid that didn't land inside a township (edge
        # cases, boundary slivers), attach the nearest township. Ensures 100%
        # coverage without silently dropping buildings.
        idx_missing = joined["adm3_pcode"].isna()
        print(f"[join] {missing} buildings missed by centroid-within; nearest-join fallback ...")
        fallback_centroids = gpd.GeoDataFrame(
            joined.loc[idx_missing, []].copy(),
            geometry=buildings.loc[idx_missing].geometry.centroid.values,
            crs=C.WORKING_CRS,
        )
        near = gpd.sjoin_nearest(
            fallback_centroids,
            townships[["adm3_pcode", "adm3_name", "geometry"]],
            how="left",
        )
        joined.loc[idx_missing, "adm3_pcode"] = near["adm3_pcode"].values
        joined.loc[idx_missing, "adm3_name"] = near["adm3_name"].values

    assert joined["adm3_pcode"].isna().sum() == 0, "township assignment failed"

    # Persist as Parquet (fast) + keep only the columns we need downstream.
    keep = [
        "source",
        "id",
        "adm3_pcode",
        "adm3_name",
        "area_m2",
        "perim_m",
        "compactness_pp",
        "shape_index",
        "mrr_fill",
        "mrr_elongation",
        "geometry",
    ]
    out = joined[keep]
    out.to_parquet(C.BUILDINGS_WITH_TOWNSHIP, index=False)
    print(
        f"[join] wrote {len(out):,} rows to {C.BUILDINGS_WITH_TOWNSHIP} "
        f"({time.time() - t0:.1f}s total)"
    )


if __name__ == "__main__":
    main()
