"""Step 6 — static maps (PNG) for the report and website."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

from scripts import config as C


plt.rcParams.update({
    "figure.dpi": C.FIG_DPI,
    "savefig.dpi": C.FIG_DPI,
    "savefig.bbox": "tight",
})


def _save(fig, name: str) -> None:
    out = C.MAPS_DIR / name
    fig.savefig(out)
    plt.close(fig)
    print(f"[maps] wrote {out}")


def _label_townships(ax, twn):
    for _, r in twn.iterrows():
        ax.annotate(
            r["adm3_name"],
            xy=(r.geometry.representative_point().x, r.geometry.representative_point().y),
            ha="center",
            fontsize=8,
            color="black",
            path_effects=[],
        )


def choropleth_builtup_ratio(twn: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 9))
    twn.plot(
        column="builtup_ratio",
        cmap=C.TOWNSHIP_CMAP,
        scheme="NaturalBreaks",
        k=5,
        linewidth=0.6,
        edgecolor="white",
        legend=True,
        legend_kwds={"title": "Built-up ratio", "loc": "lower left"},
        ax=ax,
    )
    _label_townships(ax, twn)
    ax.set_title("Built-up ratio by township — Mandalay District", fontweight="bold")
    ax.set_axis_off()
    _save(fig, "01_choropleth_builtup_ratio.png")


def choropleth_building_density(twn: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 9))
    twn.plot(
        column="building_density_per_km2",
        cmap="YlGnBu",
        scheme="NaturalBreaks",
        k=5,
        linewidth=0.6,
        edgecolor="white",
        legend=True,
        legend_kwds={"title": "Buildings / km²", "loc": "lower left"},
        ax=ax,
    )
    _label_townships(ax, twn)
    ax.set_title("Building density by township — Mandalay District", fontweight="bold")
    ax.set_axis_off()
    _save(fig, "02_choropleth_building_density.png")


def choropleth_mean_area(twn: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 9))
    twn.plot(
        column="mean_building_area_m2",
        cmap="Purples",
        scheme="NaturalBreaks",
        k=5,
        linewidth=0.6,
        edgecolor="white",
        legend=True,
        legend_kwds={"title": "Mean footprint (m²)", "loc": "lower left"},
        ax=ax,
    )
    _label_townships(ax, twn)
    ax.set_title("Mean building footprint by township", fontweight="bold")
    ax.set_axis_off()
    _save(fig, "03_choropleth_mean_area.png")


def all_buildings_map(twn: gpd.GeoDataFrame, b: gpd.GeoDataFrame) -> None:
    """Render all 286k footprints. Very small markers — shows the urban form."""
    fig, ax = plt.subplots(figsize=(11, 11))
    twn.boundary.plot(ax=ax, color="black", linewidth=0.6)
    b.plot(ax=ax, color="#c0504d", linewidth=0, markersize=0.02, alpha=0.6)
    _label_townships(ax, twn)
    ax.set_title(
        f"All {len(b):,} building footprints — Mandalay District",
        fontweight="bold",
    )
    ax.set_axis_off()
    _save(fig, "04_all_buildings.png")


def hexbin_density(twn: gpd.GeoDataFrame, b: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 10))
    # compute centroids in working CRS for aggregation stability
    cx = b.geometry.centroid.x.values
    cy = b.geometry.centroid.y.values
    hb = ax.hexbin(cx, cy, gridsize=110, cmap="inferno", mincnt=1, linewidths=0)
    twn.boundary.plot(ax=ax, color="white", linewidth=0.8)
    cb = fig.colorbar(hb, ax=ax, shrink=0.7, pad=0.02)
    cb.set_label("Buildings per hex cell")
    _label_townships(ax, twn)
    ax.set_title("Building-density hotspots (hex-bin)", fontweight="bold")
    # tighten to the district extent (plus a small margin)
    minx, miny, maxx, maxy = twn.total_bounds
    pad = 0.02 * max(maxx - minx, maxy - miny)
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)
    ax.set_axis_off()
    ax.set_aspect("equal")
    _save(fig, "05_hexbin_density.png")


def size_class_share_large(twn: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 9))
    twn.plot(
        column="share_footprint_ge_1000m2",
        cmap="Oranges",
        scheme="NaturalBreaks",
        k=5,
        linewidth=0.6,
        edgecolor="white",
        legend=True,
        legend_kwds={"title": "Share ≥ 1000 m²", "loc": "lower left"},
        ax=ax,
    )
    _label_townships(ax, twn)
    ax.set_title("Share of large-footprint buildings (≥ 1000 m²)", fontweight="bold")
    ax.set_axis_off()
    _save(fig, "06_choropleth_share_large.png")


def main() -> None:
    C.ensure_dirs()

    twn = gpd.read_file(
        C.DATA_PROCESSED / "mandalay_townships_indicators.geojson"
    ).to_crs(C.WORKING_CRS)

    # load buildings polygons in working CRS
    b = gpd.read_parquet(
        C.BUILDINGS_WITH_TOWNSHIP, columns=["geometry", "adm3_name"]
    )
    if b.crs is None:
        b = b.set_crs(C.WORKING_CRS)

    choropleth_builtup_ratio(twn)
    choropleth_building_density(twn)
    choropleth_mean_area(twn)
    size_class_share_large(twn)
    all_buildings_map(twn, b)
    hexbin_density(twn, b)


if __name__ == "__main__":
    main()
