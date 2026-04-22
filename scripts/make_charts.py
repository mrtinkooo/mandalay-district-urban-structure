"""Step 5 — charts (PNG, matplotlib) for the report and the website."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scripts import config as C


plt.rcParams.update(
    {
        "figure.dpi": C.FIG_DPI,
        "savefig.dpi": C.FIG_DPI,
        "savefig.bbox": "tight",
        "font.size": 10,
        "axes.titleweight": "bold",
        "axes.titlesize": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def _save(fig, name: str) -> None:
    out = C.CHARTS_DIR / name
    fig.savefig(out)
    plt.close(fig)
    print(f"[charts] wrote {out}")


def histogram_footprint_area(buildings: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    # log-x is essential — distribution spans >4 orders of magnitude
    area = buildings["area_m2"].clip(lower=1)
    bins = np.logspace(np.log10(1), np.log10(area.quantile(0.9999)), 60)
    ax.hist(area, bins=bins, color="#c0504d", edgecolor="white", linewidth=0.3)
    ax.set_xscale("log")
    ax.set_xlabel("Footprint area (m²), log scale")
    ax.set_ylabel("Number of buildings")
    ax.set_title(
        f"Distribution of building footprint areas — Mandalay District "
        f"(n = {len(area):,})"
    )
    # annotate medians and size-class breaks
    for b in C.SIZE_CLASS_BREAKS_M2[1:-1]:
        ax.axvline(b, color="grey", linestyle="--", linewidth=0.8, alpha=0.7)
        ax.text(
            b, ax.get_ylim()[1] * 0.95, f"{b} m²",
            ha="center", va="top", fontsize=8, color="grey",
        )
    _save(fig, "01_histogram_footprint_area.png")


def bar_building_count(summary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    d = summary.sort_values("building_count", ascending=True)
    ax.barh(d["adm3_name"], d["building_count"], color="#4f81bd")
    ax.set_xlabel("Number of buildings")
    ax.set_title("Building count by township")
    for i, v in enumerate(d["building_count"]):
        ax.text(v, i, f"  {v:,}", va="center", fontsize=9)
    _save(fig, "02_bar_building_count.png")


def bar_building_density(summary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    d = summary.sort_values("building_density_per_km2", ascending=True)
    ax.barh(d["adm3_name"], d["building_density_per_km2"], color="#c0504d")
    ax.set_xlabel("Buildings per km²")
    ax.set_title("Building density by township")
    for i, v in enumerate(d["building_density_per_km2"]):
        ax.text(v, i, f"  {v:,.0f}", va="center", fontsize=9)
    _save(fig, "03_bar_building_density.png")


def bar_builtup_ratio(summary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    d = summary.sort_values("builtup_ratio", ascending=True)
    ax.barh(d["adm3_name"], d["builtup_ratio"] * 100, color="#9bbb59")
    ax.set_xlabel("Built-up share of township area (%)")
    ax.set_title("Built-up ratio by township")
    for i, v in enumerate(d["builtup_ratio"] * 100):
        ax.text(v, i, f"  {v:.1f}%", va="center", fontsize=9)
    _save(fig, "04_bar_builtup_ratio.png")


def bar_mean_median_area(summary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    d = summary.sort_values("mean_building_area_m2", ascending=True)
    y = np.arange(len(d))
    ax.barh(y - 0.2, d["mean_building_area_m2"], 0.4, label="mean", color="#4f81bd")
    ax.barh(y + 0.2, d["median_building_area_m2"], 0.4, label="median", color="#c0504d")
    ax.set_yticks(y, d["adm3_name"])
    ax.set_xlabel("Footprint area (m²)")
    ax.set_title("Mean vs. median building footprint area")
    ax.legend()
    _save(fig, "05_bar_mean_median_area.png")


def boxplot_area_by_township(buildings: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    order = (
        buildings.groupby("adm3_name")["area_m2"].median().sort_values().index.tolist()
    )
    data = [buildings.loc[buildings["adm3_name"] == t, "area_m2"].values for t in order]
    bp = ax.boxplot(
        data,
        labels=order,
        vert=True,
        showfliers=False,
        patch_artist=True,
    )
    for patch in bp["boxes"]:
        patch.set_facecolor("#4f81bd")
        patch.set_alpha(0.7)
    ax.set_yscale("log")
    ax.set_ylabel("Footprint area (m²), log scale")
    ax.set_title("Footprint-area distribution by township (outliers hidden)")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    _save(fig, "06_boxplot_area_by_township.png")


def stacked_size_classes(sizes: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    pct_cols = [f"{lbl}_pct" for lbl in C.SIZE_CLASS_LABELS]
    d = sizes.set_index("adm3_name")[pct_cols] * 100
    # order townships by share of large + very large (proxy for industrial
    # / institutional presence)
    d = d.assign(large_sum=d[f"large_pct"] + d[f"very large_pct"]).sort_values(
        "large_sum"
    ).drop(columns="large_sum")
    colors = ["#deebf7", "#9ecae1", "#4292c6", "#2171b5", "#084594"]
    bottom = np.zeros(len(d))
    for col, color, label in zip(pct_cols, colors, C.SIZE_CLASS_LABELS):
        ax.barh(d.index, d[col], left=bottom, color=color, label=label)
        bottom += d[col].values
    ax.set_xlabel("Share of buildings (%)")
    ax.set_title("Building-size composition by township")
    ax.legend(
        title="size class",
        bbox_to_anchor=(1.01, 1),
        loc="upper left",
        frameon=False,
    )
    ax.set_xlim(0, 100)
    _save(fig, "07_stacked_size_classes.png")


def scatter_density_vs_meanarea(summary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.scatter(
        summary["building_density_per_km2"],
        summary["mean_building_area_m2"],
        s=summary["building_count"] / 50,
        alpha=0.6,
        c="#c0504d",
        edgecolor="black",
    )
    for _, r in summary.iterrows():
        ax.annotate(
            r["adm3_name"],
            (r["building_density_per_km2"], r["mean_building_area_m2"]),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=9,
        )
    ax.set_xlabel("Building density (per km²)")
    ax.set_ylabel("Mean footprint area (m²)")
    ax.set_title(
        "Townships on a density–size plane\n"
        "(bubble size ∝ total building count)"
    )
    _save(fig, "08_scatter_density_vs_meanarea.png")


def main() -> None:
    C.ensure_dirs()

    summary = pd.read_csv(C.TABLES_DIR / "township_summary.csv")
    sizes = pd.read_csv(C.TABLES_DIR / "township_size_classes.csv")
    buildings = pd.read_parquet(
        C.BUILDINGS_WITH_TOWNSHIP, columns=["adm3_name", "area_m2"]
    )

    histogram_footprint_area(buildings)
    bar_building_count(summary)
    bar_building_density(summary)
    bar_builtup_ratio(summary)
    bar_mean_median_area(summary)
    boxplot_area_by_township(buildings)
    stacked_size_classes(sizes)
    scatter_density_vs_meanarea(summary)


if __name__ == "__main__":
    main()
