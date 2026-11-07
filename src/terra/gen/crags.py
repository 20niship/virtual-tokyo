"""地質的な細部: 急斜面に層理の段(棚)と岩の角(リッジノイズ)を足し、滑らかな円錐状の峰を尖った岩稜にする。2m 格子で表せる範囲(数 m 以上)を担当し、
それより細かい凹凸は near プロファイルの微細起伏(detail.py)が足す。"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from ..core.node import Node, node
from ..masks.terrain import slope_aspect
from .noise import make_noise


def _smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


@node("gen.crags")
class Crags(Node):
    """strata_m: 層理の段の間隔、amp: 段差[m]、noise_amp/wavelength_m: 岩の角のリッジノイズ、slope_deg: 効き始める傾斜、peak_amp: 高い所(上位 20%)の鋭さ"""
    outputs = ("height",)
    defaults = dict(strata_m=7.0, amp=1.6, noise_amp=3.5, wavelength_m=26.0, slope_deg=30.0, peak_amp=5.0)

    def run(self, doc, rng):
        p, z = self.params, doc.height.astype(np.float64)
        s, _ = slope_aspect(z, doc.grid.res)
        m = gaussian_filter(_smooth((s - p["slope_deg"]) / 12.0), 1.0)
        t = z / p["strata_m"]
        stair = (np.floor(t) + _smooth((t - np.floor(t)) * 1.7 - 0.35) - t) * p["strata_m"]      # 階段状 - 線形
        crag = make_noise(doc.grid, rng, "ridged", p["wavelength_m"], 4, 2.0, 0.5, 0.35) - 0.45
        hi = _smooth((z - np.quantile(z, 0.8)) / max(float(np.ptp(z)) * 0.15, 1.0))
        d = m * (p["amp"] * stair / p["strata_m"] * 2 + p["noise_amp"] * crag) + hi * p["peak_amp"] * (crag - 0.1)
        doc.set("height", z + d)
