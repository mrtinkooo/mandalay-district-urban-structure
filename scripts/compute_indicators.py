"""Step 4 — township-level urban structure indicators.

Reads the joined buildings parquet and produces:
  * outputs/tables/township_summary.csv         — the master indicator table
  * outputs/tables/township_size_classes.csv    — counts by size class × township
  * outputs/tables/size_class_definitions.csv   — class labels + breaks
  * outputs/tables/district_totals.csv          — one-row district summary
  * data_processed/mandalay_townships_indicators.geojson  — townships + indicators
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from scripts import config as C


def _compute_township_area_km2(townships: gpd.GeoDataFrame) -> pd.Series:
    """Our own area in km², computed in WORKING_CRS (EPSG:32646).

    We deliberately do NOT reuse MIMU's `area_sqkm` — we recompute it so every
    indicator uses a single consistent CRS. The two differ by <0.5% for these
    polygons; the recomputation is documented in the summary table.
    """
    return townships.to_crs(C.WORKING_CRS).geometry.area / 1e6


def compute_township_summary(
    buildings: pd.DataFrame, townships: gpd.GeoDataFrame
) -> pd.DataFrame:
    twn_area_km2 = _compute_township_area_km2(townships)
    twn_meta = pd.DataFrame(
        {
            "adm3_pcode": townships["adm3_pcode"].values,
            "adm3_name": townships["adm3_name"].values,
            "adm3_name_my": townships["adm3_name1"].values
            if "adm3_name1" in townships.columns
            else None,
            "township_area_km2": twn_area_km2.values,
        }
    )

    grp = buildings.groupby("adm3_pcode", sort=False)
    stats = grp["area_m2"].agg(
        building_count="count",
        total_builtup_area_m2="sum",
        mean_building_area_m2="mean",
        median_building_area_m2="median",
        min_building_area_m2="min",
        max_building_area_m2="max",
        std_building_area_m2="std",
    )
    shape_stats = grp[["compactness_pp", "mrr_fill", "mrr_elongation"]].mean()
    shape_stats.columns = [
        "mean_compactness_pp",
        "mean_mrr_fill",
        "mean_mrr_elongation",
    ]
    share_large = (
        grp.apply(lambda df: (df["area_m2"] >= 1000).mean(), include_groups=False)
        .rename("share_footprint_ge_1000m2")
    )

    out = (
        twn_meta.merge(stats, on="adm3_pcode", how="left")
        .merge(shape_stats, on="adm3_pcode", how="left")
        .merge(share_large, on="adm3_pcode", how="left")
    )

    out["total_builtup_area_km2"] = out["total_builtup_area_m2"] / 1e6
    out["building_density_per_km2"] = (
        out["building_count"] / out["township_area_km2"]
    )
    out["builtup_ratio"] = (
        out["total_builtup_area_m2"] / (out["township_area_km2"] * 1e6)
    )
    out["builtup_area_per_km2"] = (
        out["total_builtup_area_m2"] / out["township_area_km2"]
    )

    col_order = [
        "adm3_pcode",
        "adm3_name",
        "adm3_name_my",
        "township_area_km2",
        "building_count",
        "total_builtup_area_m2",
        "total_builtup_area_km2",
        "mean_building_area_m2",
        "median_building_area_m2",
        "min_building_area_m2",
        "max_building_area_m2",
        "std_building_area_m2",
        "building_density_per_km2",
        "builtup_ratio",
        "builtup_area_per_km2",
        "mean_compactness_pp",
        "mean_mrr_fill",
        "mean_mrr_elongation",
        "share_footprint_ge_1000m2",
    ]
    return out[col_order].sort_values("builtup_ratio", ascending=False).reset_index(drop=True)


def compute_size_class_table(buildings: pd.DataFrame) -> pd.DataFrame:
    cls = pd.cut(
        buildings["area_m2"],
        bins=C.SIZE_CLASS_BREAKS_M2,
        labels=C.SIZE_CLASS_LABELS,
        include_lowest=True,
    )
    buildings = buildings.assign(size_class=cls)
    pivot = (
        buildings.groupby(["adm3_name", "size_class"], observed=True)
        .size()
        .unstack("size_class", fill_value=0)
    )
    pivot = pivot.reindex(columns=C.SIZE_CLASS_LABELS, fill_value=0)
    pivot["total"] = pivot.sum(axis=1)
    for lbl in C.SIZE_CLASS_LABELS:
        pivot[f"{lbl}_pct"] = pivot[lbl] / pivot["total"]
    pivot = pivot.reset_index().sort_values("adm3_name")
    return pivot


def size_class_definitions() -> pd.DataFrame:
    breaks = C.SIZE_CLASS_BREAKS_M2
    rows = []
    for i, lbl in enumerate(C.SIZE_CLASS_LABELS):
        lo, hi = breaks[i], breaks[i + 1]
        rows.append(
            {
                "size_class": lbl,
                "min_m2": lo,
                "max_m2": "∞" if np.isinf(hi) else hi,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    C.ensure_dirs()

    print("[indicators] loading joined buildings ...")
    b = pd.read_parquet(C.BUILDINGS_WITH_TOWNSHIP, columns=[
        "adm3_pcode", "adm3_name", "area_m2",
        "compactness_pp", "mrr_fill", "mrr_elongation",
    ])
    townships = gpd.read_file(C.TOWNSHIPS_GEOJSON)

    summary = compute_township_summary(b, townships)
    summary_path = C.TABLES_DIR / "township_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"[indicators] wrote {summary_path}")
    print(summary.to_string(index=False))

    sizes = compute_size_class_table(b)
    sizes_path = C.TABLES_DIR / "township_size_classes.csv"
    sizes.to_csv(sizes_path, index=False)
    print(f"[indicators] wrote {sizes_path}")

    defs = size_class_definitions()
    defs.to_csv(C.TABLES_DIR / "size_class_definitions.csv", index=False)

    # district-level one-row summary
    district = pd.DataFrame(
        [
            {
                "township_count": int(len(summary)),
                "district_area_km2": float(summary["township_area_km2"].sum()),
                "building_count": int(summary["building_count"].sum()),
                "total_builtup_area_km2": float(
                    summary["total_builtup_area_km2"].sum()
                ),
                "builtup_ratio": float(
                    summary["total_builtup_area_m2"].sum()
                    / (summary["township_area_km2"].sum() * 1e6)
                ),
                "building_density_per_km2": float(
                    summary["building_count"].sum()
                    / summary["township_area_km2"].sum()
                ),
            }
        ]
    )
    district.to_csv(C.TABLES_DIR / "district_totals.csv", index=False)

    # Write township polygons enriched with indicators for maps.
    twn = gpd.read_file(C.TOWNSHIPS_GEOJSON)
    twn_ind = twn.merge(summary, on=["adm3_pcode", "adm3_name"], how="left")
    # GeoJSON doesn't like numpy NaN for all downstream readers; convert nothing —
    # we know every township has buildings, so there should be no NaNs.
    out_path = C.DATA_PROCESSED / "mandalay_townships_indicators.geojson"
    twn_ind.to_file(out_path, driver="GeoJSON")
    print(f"[indicators] wrote {out_path}")


if __name__ == "__main__":
    main()
