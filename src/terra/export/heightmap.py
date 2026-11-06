"""ハイトマップ書き出し: RAW16(リトルエンディアン、北が上) / PNG16。min/max は json サイドカー。"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image


def to_u16(z):
    lo, hi = float(np.min(z)), float(np.max(z))
    s = (hi - lo) or 1.0
    u = np.rint((z - lo) / s * 65535).astype("<u2")
    return np.flipud(u), lo, hi     # 行0=南 → 画像は北が上


def export_heightmap(doc, outdir, fmt="raw16", name="height"):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    u, lo, hi = to_u16(doc.height)
    g = doc.grid
    meta = dict(min_m=lo, max_m=hi, res_m=g.res, width=g.nx, height=g.ny, x0=g.x0, y0=g.y0, crs=g.crs, north_up=True)
    paths = []
    if fmt in ("raw16", "both"):
        p = outdir / f"{name}.r16"
        p.write_bytes(u.tobytes())
        paths.append(p)
    if fmt in ("png16", "both"):
        p = outdir / f"{name}.png"
        Image.fromarray(u.astype(np.uint16)).save(p, compress_level=6)
        paths.append(p)
    (outdir / f"{name}.json").write_text(json.dumps(meta, indent=1))
    return paths
