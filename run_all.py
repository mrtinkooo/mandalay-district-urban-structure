"""End-to-end pipeline for the Mandalay urban-structure analysis.

Runs, in order:
  1. audit_data              — inspect raw inputs, write audit_report.json
  2. prepare_townships       — extract 7 Mandalay District townships
  3. spatial_join            — assign each building to a township, compute metrics
  4. compute_indicators      — township-level summary tables
  5. make_charts             — PNG charts
  6. make_maps               — PNG maps
  7. make_interactive_map    — Folium HTML maps
  8. build_site              — docs/index.html + CSS

Run with:
    python run_all.py
"""

from __future__ import annotations

import time

from scripts import (
    audit_data,
    build_site,
    compute_indicators,
    make_charts,
    make_interactive_map,
    make_maps,
    prepare_townships,
    spatial_join,
)


STEPS = [
    ("audit_data", audit_data.main),
    ("prepare_townships", prepare_townships.main),
    ("spatial_join", spatial_join.main),
    ("compute_indicators", compute_indicators.main),
    ("make_charts", make_charts.main),
    ("make_maps", make_maps.main),
    ("make_interactive_map", make_interactive_map.main),
    ("build_site", build_site.main),
]


def main() -> None:
    t_all = time.time()
    for name, fn in STEPS:
        print(f"\n=== {name} ===")
        t0 = time.time()
        fn()
        print(f"=== {name} done in {time.time() - t0:.1f}s ===")
    print(f"\nAll done in {time.time() - t_all:.1f}s")


if __name__ == "__main__":
    main()
