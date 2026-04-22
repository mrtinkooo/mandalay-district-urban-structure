"""Step 8 — assemble docs/index.html (GitHub Pages).

Copies charts/maps into docs/assets/img/, formats the summary tables as HTML,
and renders a single static `index.html` using a Jinja2 template.
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import jinja2
import pandas as pd

from scripts import config as C


# -------- Jinja2 template (inline — avoids an extra templates dir) ----------
TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mandalay District — Township-level Urban Structure</title>
<link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
<header>
  <div class="wrap">
    <h1>Mandalay District — Township-level Urban Structure</h1>
    <p class="lede">
      An open, reproducible analysis of 286,818 building footprints
      across the 7 townships of Mandalay District, Myanmar — derived
      from the GlobalBuildingAtlas ODbL dataset.
    </p>
    <p class="meta">
      Source code & data:
      <a href="https://github.com/geonet-myanmar/mandalay-district-buildings">GitHub repository</a>
      · Last updated: {{ today }}
    </p>
  </div>
</header>

<main class="wrap">

<section id="intro">
  <h2>1. Introduction</h2>
  <p>
    Mandalay District is the urban core of central Myanmar. Its seven
    townships span from the dense historic grid of Chanayethazan and
    Mahaaungmyay, through the industrial suburbs of Chanmyathazi and
    Pyigyitagon, out to the large, semi-rural townships of Amarapura and
    Patheingyi. This project uses open building footprints to compare
    the urban structure of these townships on a common basis.
  </p>
</section>

<section id="data">
  <h2>2. Data</h2>
  <ul>
    <li><b>Building footprints</b> — {{ district.building_count }}
        polygons in Mandalay District, clipped from the
        <a href="https://github.com/zhu-xlab/GlobalBuildingAtlas">GlobalBuildingAtlas</a>
        ODbL tile <code>asiawest/e095_n25_e100_n20</code>. GBA merges
        OpenStreetMap and Microsoft Building Footprints; every feature
        carries a <code>source</code> attribute of <code>osm</code> or
        <code>ms</code>.</li>
    <li><b>Township boundaries (admin-3)</b> — from the MIMU/UN OCHA
        Myanmar common operational datasets, filtered to the seven
        townships with <code>adm2_pcode = MMR010D001</code>.</li>
  </ul>
  <p>
    No attribute about building <i>use</i>, <i>height</i>, <i>age</i>,
    or <i>occupancy</i> is available. All findings below are based purely
    on the geometry (footprint polygons) and the administrative overlay.
  </p>
</section>

<section id="method">
  <h2>3. Methodology</h2>
  <ol>
    <li>Reproject buildings and townships to <b>EPSG:32646</b> (UTM 46N,
        metres) — a single metric CRS used for every area, length, and
        shape measurement.</li>
    <li>For every footprint compute: area (m²), perimeter (m),
        Polsby-Popper compactness, minimum-rotated-rectangle fill ratio,
        and MRR elongation.</li>
    <li>Assign each building to a township with a point-in-polygon test
        on the footprint centroid; buildings whose centroid falls outside
        every polygon (boundary slivers) are attached to the nearest
        township by a nearest-neighbour fallback.</li>
    <li>Aggregate to township level: counts, total built-up area,
        density, built-up ratio, footprint-area summary statistics, mean
        shape indices, and size-class shares.</li>
    <li>Size classes: breaks at
        <code>30 / 80 / 200 / 1000 m²</code> (very small / small / medium
        / large / very large) — chosen from the empirical distribution
        and common urban-morphology conventions.</li>
  </ol>
  <p>
    Every step is a plain Python script under <code>scripts/</code>; the
    full pipeline is reproducible from raw inputs with
    <code>python run_all.py</code>.
  </p>
</section>

<section id="findings">
  <h2>4. Key findings</h2>
  <div class="kpi-grid">
    <div class="kpi"><div class="k-num">{{ district.township_count }}</div><div class="k-lbl">Townships</div></div>
    <div class="kpi"><div class="k-num">{{ district.building_count }}</div><div class="k-lbl">Building footprints</div></div>
    <div class="kpi"><div class="k-num">{{ district.district_area_km2 }} km²</div><div class="k-lbl">District area</div></div>
    <div class="kpi"><div class="k-num">{{ district.total_builtup_area_km2 }} km²</div><div class="k-lbl">Built-up area</div></div>
    <div class="kpi"><div class="k-num">{{ district.builtup_ratio_pct }}%</div><div class="k-lbl">Built-up ratio (district)</div></div>
    <div class="kpi"><div class="k-num">{{ district.building_density }}</div><div class="k-lbl">Buildings / km²</div></div>
  </div>

  <p>{{ findings_narrative }}</p>
</section>

<section id="maps">
  <h2>5. Maps</h2>

  <h3>5.1 Interactive choropleth</h3>
  <p>Toggle layers to compare indicators; hover for full township stats.</p>
  <iframe src="interactive/townships_choropleth.html" class="map-iframe" title="Interactive township choropleth"></iframe>

  <h3>5.2 Building-density heatmap</h3>
  <iframe src="interactive/building_heatmap.html" class="map-iframe" title="Building density heatmap"></iframe>

  <h3>5.3 Static reference maps</h3>
  <div class="map-grid">
    <figure><img src="assets/img/01_choropleth_builtup_ratio.png" alt="Built-up ratio"><figcaption>Built-up ratio</figcaption></figure>
    <figure><img src="assets/img/02_choropleth_building_density.png" alt="Building density"><figcaption>Building density</figcaption></figure>
    <figure><img src="assets/img/03_choropleth_mean_area.png" alt="Mean footprint"><figcaption>Mean footprint (m²)</figcaption></figure>
    <figure><img src="assets/img/06_choropleth_share_large.png" alt="Share ≥1000 m²"><figcaption>Share of large (≥1000 m²) footprints</figcaption></figure>
    <figure><img src="assets/img/04_all_buildings.png" alt="All buildings"><figcaption>All 286 k footprints</figcaption></figure>
    <figure><img src="assets/img/05_hexbin_density.png" alt="Hexbin density"><figcaption>Hex-bin density hotspots</figcaption></figure>
  </div>
</section>

<section id="charts">
  <h2>6. Charts</h2>
  <div class="chart-grid">
    <figure><img src="assets/img/01_histogram_footprint_area.png" alt="Footprint area histogram"></figure>
    <figure><img src="assets/img/02_bar_building_count.png" alt="Building count by township"></figure>
    <figure><img src="assets/img/03_bar_building_density.png" alt="Building density"></figure>
    <figure><img src="assets/img/04_bar_builtup_ratio.png" alt="Built-up ratio"></figure>
    <figure><img src="assets/img/05_bar_mean_median_area.png" alt="Mean vs median area"></figure>
    <figure><img src="assets/img/06_boxplot_area_by_township.png" alt="Boxplot by township"></figure>
    <figure><img src="assets/img/07_stacked_size_classes.png" alt="Size-class composition"></figure>
    <figure><img src="assets/img/08_scatter_density_vs_meanarea.png" alt="Density vs mean area"></figure>
  </div>
</section>

<section id="tables">
  <h2>7. Tables</h2>
  <h3>7.1 Township summary</h3>
  <div class="scroll">{{ table_summary | safe }}</div>
  <p><a href="../outputs/tables/township_summary.csv">Download CSV</a></p>

  <h3>7.2 Size-class composition</h3>
  <div class="scroll">{{ table_sizes | safe }}</div>
  <p><a href="../outputs/tables/township_size_classes.csv">Download CSV</a></p>

  <h3>7.3 Size-class definitions</h3>
  <div class="scroll">{{ table_defs | safe }}</div>
</section>

<section id="limits">
  <h2>8. Limitations</h2>
  <ul>
    <li><b>Footprint completeness varies by source.</b> Microsoft and OSM
        coverage is not uniform; some very small huts may be missed and
        some large compounds drawn as one polygon.</li>
    <li><b>No semantic attributes.</b> Use, height, and population are
        not in the dataset; size-class labels are shape-based proxies,
        not land-use classes.</li>
    <li><b>Centroid-based join.</b> A building split by a township
        boundary is assigned to whichever township contains its centroid
        (or, for slivers, the nearest polygon). Area double-counting is
        avoided but boundary-straddling buildings may be mis-attributed.</li>
    <li><b>Township <code>area_sqkm</code></b> recomputed in EPSG:32646;
        differs from the MIMU-published value by &lt; 0.5%.</li>
  </ul>
</section>

<section id="reproduce">
  <h2>9. Reproducibility</h2>
  <pre><code>git clone https://github.com/geonet-myanmar/mandalay-district-buildings
cd mandalay-district-buildings
pip install -r requirements.txt
python run_all.py          # full pipeline, writes outputs/ and docs/</code></pre>
  <p>
    The raw <code>clip_mandalay.py</code> step (building extraction from
    the 630 MB GBA tile) is included for completeness; the pipeline below
    starts from the already-clipped <code>data_raw/</code> files.
  </p>
</section>

<footer>
  <div class="wrap">
    <p>Code: MIT · Data: ODbL 1.0 (© OSM contributors · Microsoft Building Footprints · MIMU/UN OCHA)</p>
  </div>
</footer>

</main>
</body>
</html>
"""


CSS = """
:root {
  --fg: #1a1a1a;
  --muted: #5a6472;
  --accent: #b03030;
  --bg: #fafafa;
  --card: #ffffff;
  --border: #e3e6ea;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               "Helvetica Neue", Arial, sans-serif;
  color: var(--fg);
  background: var(--bg);
  line-height: 1.55;
}
.wrap { max-width: 1100px; margin: 0 auto; padding: 0 20px; }
header {
  background: linear-gradient(180deg, #24343f, #0f1a22);
  color: #f5f5f5;
  padding: 42px 0 30px;
  border-bottom: 4px solid var(--accent);
}
header h1 { font-size: 2.1rem; margin: 0 0 10px; }
header .lede { font-size: 1.05rem; margin: 6px 0; color: #dfe6ec; }
header .meta { font-size: 0.9rem; color: #a4b0ba; margin-top: 14px; }
header a { color: #ffb8b0; }
main { padding: 24px 0 60px; }
h2 { border-bottom: 2px solid var(--accent); padding-bottom: 6px; margin-top: 42px; }
h3 { margin-top: 28px; color: var(--muted); }
a { color: var(--accent); }
pre, code { font-family: "SFMono-Regular", Menlo, Consolas, monospace; }
pre { background: #1f2933; color: #f3f3f3; padding: 14px 16px; border-radius: 6px; overflow-x: auto; }
pre code { background: none; padding: 0; color: inherit; }
code { background: #f0eded; padding: 1px 5px; border-radius: 3px; color: var(--accent); }
.map-iframe {
  width: 100%; height: 540px; border: 1px solid var(--border);
  border-radius: 6px; background: #fff; margin: 12px 0 22px;
}
.map-grid, .chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 18px;
  margin-top: 16px;
}
figure {
  margin: 0;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px;
}
figure img { width: 100%; height: auto; display: block; }
figure figcaption { font-size: 0.88rem; color: var(--muted); margin-top: 6px; text-align: center; }
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin: 20px 0 28px;
}
.kpi {
  background: var(--card);
  border: 1px solid var(--border);
  border-left: 4px solid var(--accent);
  border-radius: 6px;
  padding: 14px 16px;
}
.kpi .k-num { font-size: 1.55rem; font-weight: 700; }
.kpi .k-lbl { font-size: 0.82rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }
.scroll { overflow-x: auto; border: 1px solid var(--border); border-radius: 6px; background: var(--card); }
.scroll table { border-collapse: collapse; width: 100%; font-size: 0.85rem; }
.scroll th, .scroll td { padding: 6px 10px; text-align: right; border-bottom: 1px solid var(--border); white-space: nowrap; }
.scroll th { background: #eef2f5; text-align: left; position: sticky; top: 0; }
.scroll td:first-child, .scroll th:first-child { text-align: left; font-weight: 600; }
footer {
  border-top: 1px solid var(--border);
  padding: 18px 0;
  font-size: 0.85rem;
  color: var(--muted);
  text-align: center;
  background: var(--card);
  margin-top: 40px;
}
"""


def _fmt_float(x, nd=2):
    return f"{x:,.{nd}f}" if pd.notna(x) else ""


def _fmt_int(x):
    return f"{int(x):,}" if pd.notna(x) else ""


def _summary_table_html(df: pd.DataFrame) -> str:
    d = df.copy()
    # user-friendly column labels; round/format numeric columns
    fmt = {
        "township_area_km2": ("Area (km²)", lambda v: _fmt_float(v, 2)),
        "building_count": ("Buildings", _fmt_int),
        "total_builtup_area_km2": ("Built-up area (km²)", lambda v: _fmt_float(v, 3)),
        "builtup_ratio": ("Built-up ratio", lambda v: f"{v * 100:.1f}%"),
        "building_density_per_km2": ("Density (/km²)", lambda v: _fmt_float(v, 0)),
        "mean_building_area_m2": ("Mean footprint (m²)", lambda v: _fmt_float(v, 0)),
        "median_building_area_m2": ("Median footprint (m²)", lambda v: _fmt_float(v, 0)),
        "share_footprint_ge_1000m2": ("Share ≥1000 m²", lambda v: f"{v * 100:.1f}%"),
        "mean_compactness_pp": ("Mean compactness", lambda v: _fmt_float(v, 3)),
    }
    cols = ["adm3_name"] + list(fmt.keys())
    t = d[cols].copy()
    for k, (lbl, fn) in fmt.items():
        t[k] = t[k].apply(fn)
    t.columns = ["Township"] + [lbl for lbl, _ in fmt.values()]
    return t.to_html(index=False, escape=False, border=0, classes="tbl")


def _size_table_html(df: pd.DataFrame) -> str:
    from scripts.config import SIZE_CLASS_LABELS

    cols_cnt = SIZE_CLASS_LABELS
    cols_pct = [f"{c}_pct" for c in SIZE_CLASS_LABELS]
    d = df.copy()
    # build two-level column: count + pct side by side
    t = pd.DataFrame({"Township": d["adm3_name"], "Total": d["total"].map(_fmt_int)})
    for lbl in SIZE_CLASS_LABELS:
        t[lbl] = d[lbl].map(_fmt_int) + " (" + (d[f"{lbl}_pct"] * 100).round(1).astype(str) + "%)"
    return t.to_html(index=False, escape=False, border=0, classes="tbl")


def _defs_table_html(df: pd.DataFrame) -> str:
    d = df.copy()
    d.columns = ["Size class", "Min (m²)", "Max (m²)"]
    return d.to_html(index=False, escape=False, border=0, classes="tbl")


def _copy_assets() -> None:
    # charts and maps → docs/assets/img
    C.DOCS_IMG.mkdir(parents=True, exist_ok=True)
    for src in list(C.CHARTS_DIR.glob("*.png")) + list(C.MAPS_DIR.glob("*.png")):
        shutil.copy2(src, C.DOCS_IMG / src.name)


def _findings_narrative(summary: pd.DataFrame) -> str:
    """Write a 3-sentence plain-English narrative of the key patterns."""
    top_br = summary.sort_values("builtup_ratio", ascending=False).iloc[0]
    lowest_br = summary.sort_values("builtup_ratio", ascending=False).iloc[-1]
    top_dens = summary.sort_values("building_density_per_km2", ascending=False).iloc[0]
    top_mean = summary.sort_values("mean_building_area_m2", ascending=False).iloc[0]

    return (
        f"<b>{top_br['adm3_name']}</b> is the most built-up township "
        f"(built-up ratio ≈ {top_br['builtup_ratio'] * 100:.1f}%), while "
        f"<b>{lowest_br['adm3_name']}</b> is the least "
        f"({lowest_br['builtup_ratio'] * 100:.1f}%). "
        f"The highest building density belongs to <b>{top_dens['adm3_name']}</b> "
        f"({top_dens['building_density_per_km2']:,.0f} buildings per km²). "
        f"The largest mean footprint — a proxy for the share of industrial, "
        f"institutional or larger compound buildings — is found in "
        f"<b>{top_mean['adm3_name']}</b> "
        f"(mean {top_mean['mean_building_area_m2']:,.0f} m²)."
    )


def main() -> None:
    C.ensure_dirs()
    _copy_assets()

    summary = pd.read_csv(C.TABLES_DIR / "township_summary.csv")
    sizes = pd.read_csv(C.TABLES_DIR / "township_size_classes.csv")
    defs = pd.read_csv(C.TABLES_DIR / "size_class_definitions.csv")
    district = pd.read_csv(C.TABLES_DIR / "district_totals.csv").iloc[0]

    district_ctx = {
        "township_count": int(district["township_count"]),
        "building_count": f"{int(district['building_count']):,}",
        "district_area_km2": f"{district['district_area_km2']:.1f}",
        "total_builtup_area_km2": f"{district['total_builtup_area_km2']:.2f}",
        "builtup_ratio_pct": f"{district['builtup_ratio'] * 100:.1f}",
        "building_density": f"{district['building_density_per_km2']:,.0f}",
    }

    env = jinja2.Environment(autoescape=False)
    html = env.from_string(TEMPLATE).render(
        today=date.today().isoformat(),
        district=district_ctx,
        findings_narrative=_findings_narrative(summary),
        table_summary=_summary_table_html(summary),
        table_sizes=_size_table_html(sizes),
        table_defs=_defs_table_html(defs),
    )

    (C.DOCS / "index.html").write_text(html, encoding="utf-8")
    (C.DOCS_CSS / "style.css").write_text(CSS, encoding="utf-8")
    print(f"[site] wrote {C.DOCS / 'index.html'}")
    print(f"[site] wrote {C.DOCS_CSS / 'style.css'}")


if __name__ == "__main__":
    main()
