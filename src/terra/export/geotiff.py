"""GeoTIFF(float32, 北が上)。CRS が EPSG の時だけ地理参照を付ける。"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin


def export_geotiff(doc, outdir, layers=("height",), name=None):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    g = doc.grid
    paths = []
    for L in layers:
        if L not in doc.layers:
            continue
        p = outdir / f"{name or L}.tif" if len(layers) == 1 else outdir / f"{L}.tif"
        crs = g.crs if g.crs.upper().startswith("EPSG") else None
        with rasterio.open(p, "w", driver="GTiff", height=g.ny, width=g.nx, count=1, dtype="float32", crs=crs,
                           transform=from_origin(g.x0, g.y0 + g.ny * g.res, g.res, g.res), compress="deflate") as f:
            f.write(np.flipud(doc.layers[L]).astype(np.float32), 1)
        paths.append(p)
    return paths
