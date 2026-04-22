"""Step 7 — interactive Folium maps for the GitHub Pages site.

Produces two HTML files in docs/interactive/:
  * townships_choropleth.html  — township layers (built-up ratio, density, mean area)
  * building_heatmap.html      — heatmap of building centroids

The full footprint layer (286k polygons) is NOT embedded — that would bloat
the HTML beyond 50 MB. Instead we provide the choropleth + heatmap, which are
enough to tell the urban-structure story and stay under 5 MB.
"""

from __future__ import annotations

import folium
from folium.plugins import HeatMap
import geopandas as gpd
import pandas as pd

from scripts import config as C


MANDALAY_CENTER = [21.95, 96.10]


def _base_map(zoom: int = 11) -> folium.Map:
    m = folium.Map(
        location=MANDALAY_CENTER,
        zoom_start=zoom,
        tiles="CartoDB positron",
        control_scale=True,
    )
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
    return m


def _choropleth_layer(
    m: folium.Map,
    gdf: gpd.GeoDataFrame,
    column: str,
    name: str,
    caption: str,
    fill_color: str = "YlOrRd",
) -> None:
    folium.Choropleth(
        geo_data=gdf.__geo_interface__,
        data=gdf,
        columns=["adm3_pcode", column],
        key_on="feature.properties.adm3_pcode",
        fill_color=fill_color,
        fill_opacity=0.75,
        line_opacity=0.4,
        legend_name=caption,
        name=name,
        highlight=True,
    ).add_to(m)


def build_townships_map(twn: gpd.GeoDataFrame) -> folium.Map:
    m = _base_map()
    _choropleth_layer(
        m, twn, "builtup_ratio", "Built-up ratio", "Built-up ratio", "YlOrRd"
    )
    _choropleth_layer(
        m,
        twn,
        "building_density_per_km2",
        "Building density (per km²)",
        "Buildings per km²",
        "YlGnBu",
    )
    _choropleth_layer(
        m,
        twn,
        "mean_building_area_m2",
        "Mean footprint (m²)",
        "Mean footprint (m²)",
        "Purples",
    )

    # tooltip-enabled transparent layer on top
    tooltip_fields = [
        "adm3_name",
        "building_count",
        "township_area_km2",
        "builtup_ratio",
        "building_density_per_km2",
        "mean_building_area_m2",
        "median_building_area_m2",
    ]
    aliases = [
        "Township:",
        "Buildings:",
        "Area (km²):",
        "Built-up ratio:",
        "Density (/km²):",
        "Mean footprint (m²):",
        "Median footprint (m²):",
    ]
    folium.GeoJson(
        twn.__geo_interface__,
        name="Township info (hover)",
        style_function=lambda _: {
            "fillColor": "transparent",
            "color": "#333",
            "weight": 1.1,
        },
        highlight_function=lambda _: {"weight": 3, "color": "black"},
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=aliases,
            localize=True,
            labels=True,
            sticky=True,
        ),
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def build_heatmap(buildings_pq_path) -> folium.Map:
    """Heatmap of a random 40k-sample of building centroids — keeps file small."""
    gdf = gpd.read_parquet(buildings_pq_path, columns=["geometry"])
    if gdf.crs is None:
        gdf = gdf.set_crs(C.WORKING_CRS)
    pts = gdf.geometry.centroid.to_crs(C.DISPLAY_CRS)
    sample = pts.sample(n=min(40000, len(pts)), random_state=0)
    data = [[p.y, p.x] for p in sample]

    m = _base_map(zoom=11)
    HeatMap(
        data,
        radius=6,
        blur=7,
        min_opacity=0.25,
        max_zoom=14,
    ).add_to(m)
    return m


def main() -> None:
    C.ensure_dirs()

    twn = gpd.read_file(
        C.DATA_PROCESSED / "mandalay_townships_indicators.geojson"
    ).to_crs(C.DISPLAY_CRS)

    m1 = build_townships_map(twn)
    p1 = C.DOCS_INTERACTIVE / "townships_choropleth.html"
    m1.save(str(p1))
    print(f"[interactive] wrote {p1}")

    m2 = build_heatmap(C.BUILDINGS_WITH_TOWNSHIP)
    p2 = C.DOCS_INTERACTIVE / "building_heatmap.html"
    m2.save(str(p2))
    print(f"[interactive] wrote {p2}")


if __name__ == "__main__":
    main()
