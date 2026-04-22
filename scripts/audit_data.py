"""Step 1 — data audit.

Prints a structured summary of the raw inputs:
  * building footprint count, CRS, geometry types, attribute schema
  * count of invalid geometries and of duplicate (id, source) rows
  * township boundaries (admin3 features clipped to Mandalay District)

Run with:
    python -m scripts.audit_data
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd

from scripts import config as C
from scripts.io_utils import extract_admin_layer, read_gzipped_geojson


def audit_buildings() -> dict:
    print(f"[audit] reading {C.BUILDINGS_GZ.name} ...")
    b = read_gzipped_geojson(C.BUILDINGS_GZ)
    info = {
        "feature_count": int(len(b)),
        "crs": str(b.crs),
        "geom_types": b.geom_type.value_counts().to_dict(),
        "columns": list(b.columns),
        "source_counts": b["source"].value_counts().to_dict()
        if "source" in b.columns
        else {},
        "null_geoms": int(b.geometry.isna().sum()),
        "invalid_geoms": int((~b.geometry.is_valid).sum()),
        "duplicate_id_source": int(b.duplicated(subset=["id", "source"]).sum())
        if {"id", "source"}.issubset(b.columns)
        else None,
        "bbox_4326": [float(v) for v in b.total_bounds.tolist()],
    }
    return info


def audit_townships() -> dict:
    admin3_path = extract_admin_layer(
        C.ADMIN_ZIP, "mmr_admin3.geojson", C.DATA_PROCESSED
    )
    a3 = gpd.read_file(admin3_path)
    mda = a3[a3["adm2_pcode"] == C.MANDALAY_DISTRICT_PCODE].copy()
    info = {
        "admin3_total_features": int(len(a3)),
        "mandalay_townships": int(len(mda)),
        "township_names": mda["adm3_name"].tolist(),
        "township_pcodes": mda["adm3_pcode"].tolist(),
        "attributes_source_area_sqkm": {
            row["adm3_name"]: float(row["area_sqkm"]) for _, row in mda.iterrows()
        },
    }
    return info


def main() -> None:
    C.ensure_dirs()
    report = {
        "buildings": audit_buildings(),
        "townships": audit_townships(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    out = C.DATA_PROCESSED / "audit_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[audit] wrote {out}")


if __name__ == "__main__":
    main()
