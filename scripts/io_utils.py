"""I/O helpers shared across the pipeline."""

from __future__ import annotations

import gzip
import shutil
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd


def read_gzipped_geojson(path: Path) -> gpd.GeoDataFrame:
    """Read a gzip-compressed GeoJSON.

    pyogrio does not transparently stream gzip, so we decompress to a temp
    file first. This is still faster and less memory-hungry than holding the
    decompressed bytes in Python.
    """
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        with gzip.open(path, "rb") as src:
            shutil.copyfileobj(src, tmp)
        tmp_path = Path(tmp.name)
    try:
        return gpd.read_file(tmp_path, engine="pyogrio")
    finally:
        tmp_path.unlink(missing_ok=True)


def extract_admin_layer(zip_path: Path, layer_name: str, dest_dir: Path) -> Path:
    """Extract a single layer from the admin-boundaries zip and return its path.

    Idempotent: skips extraction if the file already exists at dest_dir.
    """
    dest = dest_dir / layer_name
    if dest.exists():
        return dest
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extract(layer_name, path=dest_dir)
    return dest
