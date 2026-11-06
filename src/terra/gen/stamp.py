"""スタンプ: 別ハイトフィールド(画像 / npy / 実 DEM)を、位置・回転・縮尺・ブレンド幅付きで貼る。"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import map_coordinates

from ..core.node import Node, node


def paste(doc, z, size_m, at, rot_deg=0.0, blend_m=100.0, mode="replace", z_ref="min", fit=False):
    """z: スタンプの高さ配列(行0=南)、size_m: 一辺の長さ[m]、at: 中心の格子比率。"""
    g = doc.grid
    X, Y = g.xy()
    sx, sy = g.size
    c, s = np.cos(np.radians(rot_deg)), np.sin(np.radians(rot_deg))
    dx, dy = X - g.x0 - at[0] * sx, Y - g.y0 - at[1] * sy
    u, v = c * dx + s * dy, -s * dx + c * dy               # スタンプ座標[m]
    h, w = z.shape
    fi, fj = (u / size_m + 0.5) * w - 0.5, (v / size_m + 0.5) * h - 0.5
    inside = (u > -size_m / 2) & (u < size_m / 2) & (v > -size_m / 2) & (v < size_m / 2)
    val = map_coordinates(z, [fj, fi], order=1, mode="nearest")
    edge = np.minimum(size_m / 2 - np.abs(u), size_m / 2 - np.abs(v))
    a = np.clip(edge / max(blend_m, 1e-6), 0, 1) if blend_m > 0 else inside.astype(float)
    a = a * a * (3 - 2 * a) * inside
    if fit:      # 貼り込み縁の平均高さを周囲に合わせる(段差を作らない)
        ring = (a > 0) & (a < 0.1)
        if ring.any():
            val = val + float(np.mean(doc.height[ring] - val[ring]))
    if mode == "add":
        base = val - (float(z.min()) if z_ref == "min" else 0.0)
        return doc.height + a * base
    return doc.height * (1 - a) + val * a


@node("gen.stamp")
class Stamp(Node):
    """file: .npy/.tif/画像、または dem: {center:[lon,lat], ...} で実 DEM を貼る。height_range=[lo,hi] で画像を m に換算。"""
    outputs = ("height",)
    defaults = dict(file=None, dem=None, at=[0.5, 0.5], size_m=2000.0, rot_deg=0.0, blend_m=200.0, mode="replace", fit=False,
                    height_range=[0.0, 500.0], offset=0.0)

    def run(self, doc, rng):
        p = self.params
        if p["dem"]:
            from ..source.gsi_dem import dem_array
            d = p["dem"]
            z = dem_array(d["center"], p["size_m"], d.get("res_m", doc.grid.res), d.get("layer", "auto"))
        else:
            from ..source.image import load_height
            z = load_height(p["file"], p["height_range"])
        doc.set("height", paste(doc, z + p["offset"], p["size_m"], p["at"], p["rot_deg"], p["blend_m"], p["mode"], fit=p["fit"]))
