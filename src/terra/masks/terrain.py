"""地形認識マスク: 傾斜[度]・向き[度, 北=0 時計回り, 下り方向]・曲率[1/m, 凸=正]・標高帯。"""
from __future__ import annotations

import numpy as np

from ..core.node import Node, node


def slope_aspect(z, res):
    gy, gx = np.gradient(z.astype(np.float64), res)      # gy: 北向き(行が増える方向=北)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    aspect = (np.degrees(np.arctan2(-gx, -gy)) + 360) % 360     # 下り方向の方位
    return slope.astype(np.float32), aspect.astype(np.float32)


def curvature(z, res):
    zp = np.pad(z.astype(np.float64), 1, mode="edge")
    lap = (zp[1:-1, 2:] + zp[1:-1, :-2] + zp[2:, 1:-1] + zp[:-2, 1:-1] - 4 * z) / res ** 2
    return (-lap).astype(np.float32)


def band(z, lo, hi, feather=0.0):
    """lo..hi で 1、両端 feather[m] で 0 へ滑らかに落ちる"""
    if feather <= 0:
        return ((z >= lo) & (z <= hi)).astype(np.float32)
    a = np.clip((z - (lo - feather)) / feather, 0, 1) * np.clip(((hi + feather) - z) / feather, 0, 1)
    return (a * a * (3 - 2 * a)).astype(np.float32)


@node("masks.slope")
class SlopeMasks(Node):
    outputs = ("slope", "aspect", "curv")

    def run(self, doc, rng):
        s, a = slope_aspect(doc.height, doc.grid.res)
        doc.set("slope", s)
        doc.set("aspect", a)
        doc.set("curv", curvature(doc.height, doc.grid.res))


@node("masks.height_band")
class HeightBand(Node):
    """name 層に標高帯マスク(0..1)を作る"""
    defaults = dict(name="band", lo=0.0, hi=1000.0, feather=50.0)

    @property
    def outputs(self):
        return (self.params["name"],)

    def run(self, doc, rng):
        p = self.params
        doc.set(p["name"], band(doc.height, p["lo"], p["hi"], p["feather"]))
