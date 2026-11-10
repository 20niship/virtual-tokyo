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
    """strata_m: 層理の平均間隔、amp: 段差[m]、noise_amp/wavelength_m: 岩の角のリッジノイズ、slope_deg: 効き始める傾斜、peak_amp: 高い所(上位 20%)の鋭さ。
    hardness_var: 層ごとの硬さ・厚さのばらつき(0 で従来の等間隔)、dip_deg: 層の傾き(見かけ)、joint_m: 垂直節理のブロック間隔(0 で無し)、joint_amp: ブロックごとの上下差と節理の溝[m]"""
    outputs = ("height",)
    defaults = dict(strata_m=7.0, amp=1.6, noise_amp=3.5, wavelength_m=26.0, slope_deg=30.0, peak_amp=5.0, hardness_var=0.8, dip_deg=2.0, joint_m=14.0, joint_amp=0.9)

    def run(self, doc, rng):
        p, z = self.params, doc.height.astype(np.float64)
        s, _ = slope_aspect(z, doc.grid.res)
        m = gaussian_filter(_smooth((s - p["slope_deg"]) / 12.0), 1.0)
        X, Y = doc.grid.xy()
        stair = self._stair(z + np.tan(np.radians(p["dip_deg"])) * (X - X.mean()), p, rng) if p["hardness_var"] > 0 else self._stair0(z, p)
        crag = make_noise(doc.grid, rng, "ridged", p["wavelength_m"], 4, 2.0, 0.5, 0.35) - 0.45
        hi = _smooth((z - np.quantile(z, 0.8)) / max(float(np.ptp(z)) * 0.15, 1.0))
        d = m * (p["amp"] * stair / p["strata_m"] * 2 + p["noise_amp"] * crag) + hi * p["peak_amp"] * (crag - 0.1)
        if p["joint_m"] > 0:
            d = d + m * self._joints(X, Y, z, p, rng)
        doc.set("height", z + d)

    @staticmethod
    def _stair0(z, p):
        t = z / p["strata_m"]
        return (np.floor(t) + _smooth((t - np.floor(t)) * 1.7 - 0.35) - t) * p["strata_m"]      # 階段状 - 線形

    @staticmethod
    def _stair(z, p, rng):
        """層ごとに厚さ・硬さが違う階段: 硬い層は平らな棚(段の上下に長い平坦部)、軟らかい層は急で凹む(差別侵食)"""
        s, v = p["strata_m"], p["hardness_var"]
        zb = np.concatenate([[z.min() - s], z.min() - s + np.cumsum(s * rng.uniform(1 - 0.6 * v, 1 + 0.6 * v, int(np.ptp(z) / (s * 0.4)) + 3))])
        hard = rng.uniform(0, 1, len(zb))
        k = np.clip(np.searchsorted(zb, z) - 1, 0, len(zb) - 2)
        frac = (z - zb[k]) / (zb[k + 1] - zb[k])
        a = 0.08 + 0.4 * v * hard[k]                                                    # 硬い層ほど平坦部(棚)が広い
        return (zb[k] + (zb[k + 1] - zb[k]) * _smooth((frac - a) / (1 - 2 * a)) - z)

    @staticmethod
    def _joints(X, Y, z, p, rng):
        """垂直節理 2 方向でブロックに割る: ブロックごとの上下差と、節理線に沿う溝(崩れ落ちた欠け跡の凹凸)"""
        out = 0.0
        for ang, sc in ((rng.uniform(0, np.pi), 1.0), (rng.uniform(0, np.pi), 1.7)):
            u = (X * np.cos(ang) + Y * np.sin(ang)) / (p["joint_m"] * sc) + rng.uniform(0, 50)
            c = np.floor(u).astype(np.int64)
            h = ((c * 73856093 + int(rng.integers(1 << 20))) * 2654435761) & 0xFFFF
            off = (h / 65535.0 - 0.5) * 2.0
            du = np.abs(u - np.round(u)) * p["joint_m"] * sc
            out = out + 0.5 * p["joint_amp"] * (off - 1.4 * np.exp(-(du / 2.5) ** 2))
        return gaussian_filter(out, 1.0)                                              # 格子(2m)で解像できない鋭い段は丸めて、尖った破片状にならないようにする
