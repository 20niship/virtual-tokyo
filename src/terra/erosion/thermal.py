"""熱侵食(タラス崩壊): 安息角を超える斜面の土を、低い隣接 8 セルへ比例配分して移す。Jacobi 方式で並列・決定的。"""
from __future__ import annotations

import numpy as np
from numba import njit, prange

from ..core.node import Node, node

DY = np.array([-1, -1, -1, 0, 0, 1, 1, 1], np.int64)
DX = np.array([-1, 0, 1, -1, 1, -1, 0, 1], np.int64)


@njit(cache=True, parallel=True)
def _iter(z, out, res, tan_t, rate):
    ny, nx = z.shape
    mv = np.zeros((8, ny, nx))
    for j in prange(ny):
        for i in range(nx):
            tot, mx = 0.0, 0.0
            ex = np.zeros(8)
            for k in range(8):
                nj, ni = j + DY[k], i + DX[k]
                if nj < 0 or ni < 0 or nj >= ny or ni >= nx:
                    continue
                dist = res * (1.41421356 if DY[k] != 0 and DX[k] != 0 else 1.0)
                e = z[j, i] - z[nj, ni] - tan_t * dist
                if e > 0:
                    ex[k] = e
                    tot += e
                    mx = max(mx, e)
            if tot > 0:
                amt = rate * 0.5 * mx
                for k in range(8):
                    mv[k, j, i] = amt * ex[k] / tot
    for j in prange(ny):
        for i in range(nx):
            v = 0.0
            for k in range(8):
                v -= mv[k, j, i]
                nj, ni = j - DY[k], i - DX[k]       # 隣(nj,ni)が方向 k で自分へ送る量
                if 0 <= nj < ny and 0 <= ni < nx:
                    v += mv[k, nj, ni]
            out[j, i] = z[j, i] + v


def thermal(z, res, talus_deg=34.0, iterations=60, rate=0.5):
    a = np.array(z, dtype=np.float64, order="C", copy=True)
    b = np.empty_like(a)
    t = np.tan(np.radians(talus_deg))
    for _ in range(iterations):
        _iter(a, b, float(res), t, rate)
        a, b = b, a
    return a.astype(np.float32)


@node("erosion.thermal")
class Thermal(Node):
    outputs = ("height",)
    defaults = dict(talus_deg=34.0, iterations=60, rate=0.5)

    def run(self, doc, rng):
        p = self.params
        doc.set("height", thermal(doc.height, doc.grid.res, p["talus_deg"], p["iterations"], p["rate"]))
