"""scatter.floor: 樹冠下の林床(落ち葉の層・倒木・枯れ枝・ササ・シダ)を散布。樹冠が濃く傾斜が緩いほど多い。要 biome.jp_forest"""
from __future__ import annotations

import numpy as np

from ..core.node import Node, node
from ..masks.terrain import slope_aspect
from .nodes import _put, exclusion
from .poisson import sample

# (module 接頭辞, 間隔 r[m], 密度の重み, 傾き(最大傾斜[度]), スケール範囲, 斜面に沿わせる)
LAYERS = [
    ("floor_leaves", 5.0, 0.9, 40.0, (0.9, 1.5)),
    ("floor_sasa", 4.0, 0.55, 36.0, (0.8, 1.5)),
    ("floor_fern", 5.0, 0.5, 38.0, (0.8, 1.4)),
    ("floor_branch", 6.0, 0.7, 45.0, (0.8, 1.4)),
    ("floor_log", 18.0, 0.4, 32.0, (0.9, 1.3)),
]


@node("scatter.floor")
class Floor(Node):
    """density: 全体の密度倍率(near は 3〜4 倍にする)"""
    inputs = ("canopy", "biome")
    scatter_outputs = ("floor",)
    defaults = dict(density=1.0, exclude=["river", "lake", "road", "portal", "powerline", "village_pads"], min_canopy=0.3)

    def run(self, doc, rng):
        p, g = self.params, doc.grid
        D = p["density"]
        slope, _ = slope_aspect(doc.height, g.res)
        can = doc.layers["canopy"]
        moist = np.clip((doc.layers.get("twi", np.full(g.shape, 7.0, np.float32)) - 6.0) / 5.0, 0, 1)
        allowed = ~exclusion(doc, p["exclude"], 0.8)
        xs, ys, ks, yaws, scs, names = [], [], [], [], [], []
        for prefix, r, w, smax, sc in LAYERS:
            dens = (can > p["min_canopy"]) * np.clip(can * 1.2, 0, 1) * w * (slope < smax)
            if prefix == "floor_fern":
                dens = dens * (0.4 + moist)
            if prefix == "floor_sasa":
                dens = dens * (1.1 - 0.5 * moist)
            xy, jj, ii = sample(g, r / np.sqrt(D), int(rng.integers(1 << 30)), dens.astype(np.float32), allowed, rng)
            if not len(xy):
                continue
            v = rng.integers(3, size=len(xy))
            for n in range(3):
                if f"{prefix}_{n}" not in names:
                    names.append(f"{prefix}_{n}")
            xs.append(xy)
            ks.append(np.array([names.index(f"{prefix}_{q}") for q in v], np.int16))
            yaws.append(rng.uniform(0, 2 * np.pi, len(xy)))
            scs.append(rng.uniform(*sc, len(xy)))
        xy = np.concatenate(xs) if xs else np.zeros((0, 2))
        _put(doc, "floor", xy, np.concatenate(yaws) if yaws else np.zeros(0), np.concatenate(scs) if scs else np.zeros(0),
             np.concatenate(ks) if ks else np.zeros(0, np.int16), names or ["floor_leaves_0"], zoff=0.0)
