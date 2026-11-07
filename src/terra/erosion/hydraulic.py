"""格子型パイプモデルの水力侵食(Mei et al. 2007 系)。降雨→4方向の流量→水深/流速→溶解/堆積→移流→蒸発。Numba(並列)。
dt は固定(CFL を保つよう flux スケールで安定化)。標高 b[m]、水深 d[m]、浮遊土砂 s[m]。"""
from __future__ import annotations

import numpy as np
from numba import njit, prange

from ..core.node import Node, node

G = 9.81


@njit(cache=True, parallel=True, fastmath=True)
def _step(b, d, s, fL, fR, fU, fD, vx, vy, d2, s2, nb, rain, dt, res, kc, ks, kd, ke, damp, tilt_min, max_ero, vmax):
    ny, nx = b.shape
    A = res * res
    for j in prange(ny):      # 降雨(別パス: 隣接セルの読み書きが競合して非決定的になるのを避ける)
        for i in range(nx):
            d[j, i] += rain
    for j in prange(ny):
        for i in range(nx):
            h = b[j, i] + d[j, i]
            dl = h - (b[j, i - 1] + d[j, i - 1]) if i > 0 else 0.0
            dr = h - (b[j, i + 1] + d[j, i + 1]) if i < nx - 1 else 0.0
            du = h - (b[j - 1, i] + d[j - 1, i]) if j > 0 else 0.0
            dd = h - (b[j + 1, i] + d[j + 1, i]) if j < ny - 1 else 0.0
            c = dt * G * res
            fl = max(0.0, fL[j, i] * damp + c * dl)
            fr = max(0.0, fR[j, i] * damp + c * dr)
            fu = max(0.0, fU[j, i] * damp + c * du)
            fd = max(0.0, fD[j, i] * damp + c * dd)
            tot = (fl + fr + fu + fd) * dt
            K = min(1.0, d[j, i] * A / tot) if tot > 1e-12 else 1.0
            fL[j, i], fR[j, i], fU[j, i], fD[j, i] = fl * K, fr * K, fu * K, fd * K
    # 水深更新と流速
    for j in prange(ny):
        for i in range(nx):
            inn = 0.0
            if i > 0:
                inn += fR[j, i - 1]
            if i < nx - 1:
                inn += fL[j, i + 1]
            if j > 0:
                inn += fD[j - 1, i]
            if j < ny - 1:
                inn += fU[j + 1, i]
            out = fL[j, i] + fR[j, i] + fU[j, i] + fD[j, i]
            dn = d[j, i] + dt * (inn - out) / A
            dm = 0.5 * (d[j, i] + max(dn, 0.0))
            wx = fR[j, i] - fL[j, i] + (fR[j, i - 1] if i > 0 else 0.0) - (fL[j, i + 1] if i < nx - 1 else 0.0)
            wy = fD[j, i] - fU[j, i] + (fD[j - 1, i] if j > 0 else 0.0) - (fU[j + 1, i] if j < ny - 1 else 0.0)
            vx[j, i] = 0.5 * wx / (res * max(dm, 1e-3))
            vy[j, i] = 0.5 * wy / (res * max(dm, 1e-3))
            d2[j, i] = max(dn, 0.0)
    # 溶解/堆積
    for j in prange(ny):
        for i in range(nx):
            gx = (b[j, min(i + 1, nx - 1)] - b[j, max(i - 1, 0)]) / (2 * res)
            gy = (b[min(j + 1, ny - 1), i] - b[max(j - 1, 0), i]) / (2 * res)
            sn = np.sqrt(gx * gx + gy * gy)
            sa = max(sn / np.sqrt(1 + sn * sn), tilt_min)          # sinθ
            v = min(np.sqrt(vx[j, i] ** 2 + vy[j, i] ** 2), vmax)
            cap = kc * sa * v * min(d2[j, i], 0.5) / 0.5            # 浅い所では運べない
            if s[j, i] < cap:
                dz = min(ks * (cap - s[j, i]), max_ero)
                nb[j, i] = b[j, i] - dz
                s[j, i] += dz
            else:
                dz = kd * (s[j, i] - cap)
                nb[j, i] = b[j, i] + dz
                s[j, i] -= dz
    # 土砂の移流(セミラグランジュ)と蒸発
    for j in prange(ny):
        for i in range(nx):
            x = i - vx[j, i] * dt / res
            y = j - vy[j, i] * dt / res
            x = min(max(x, 0.0), nx - 1.001)
            y = min(max(y, 0.0), ny - 1.001)
            i0, j0 = int(x), int(y)
            fx, fy = x - i0, y - j0
            s2[j, i] = ((1 - fx) * (1 - fy) * s[j0, i0] + fx * (1 - fy) * s[j0, i0 + 1] + (1 - fx) * fy * s[j0 + 1, i0] + fx * fy * s[j0 + 1, i0 + 1])
    for j in prange(ny):
        for i in range(nx):
            b[j, i] = nb[j, i]
            s[j, i] = s2[j, i]
            d[j, i] = d2[j, i] * (1.0 - ke * dt)


def hydraulic(z, res, iterations=150, rain=0.012, dissolve=0.3, deposit=0.3, capacity=0.05, evap=0.5, dt=0.1, max_ero=0.05, tilt_min=0.05, damp=0.9, vmax=3.0):
    """z[m] → 侵食後の z と、堆積/侵食量 dz[m](負=削れ)。1 ステップ最大 max_ero[m] まで削る"""
    b = np.array(z, dtype=np.float64, order="C", copy=True)
    b0 = b.copy()
    sh = b.shape
    d = np.zeros(sh)
    s = np.zeros(sh)
    z4 = [np.zeros(sh) for _ in range(4)]
    vx, vy, d2, s2, nb = (np.zeros(sh) for _ in range(5))
    for _ in range(iterations):
        _step(b, d, s, *z4, vx, vy, d2, s2, nb, rain, dt, float(res), capacity, dissolve, deposit, evap, damp, tilt_min, max_ero, vmax)
    return b.astype(np.float32), (b - b0).astype(np.float32)


@node("erosion.hydraulic")
class Hydraulic(Node):
    """mode=erode: 高さを侵食後に置換(仮想地形)/ derive: 高さは据え置き、soil_depth・bedrock・erosion だけ派生(実 DEM)"""
    outputs = ("height", "erosion")
    defaults = dict(iterations=150, rain=0.012, dissolve=0.3, deposit=0.3, capacity=0.05, evap=0.5, mode="erode", max_ero=0.05)

    def run(self, doc, rng):
        p = self.params
        z, dz = hydraulic(doc.height, doc.grid.res, p["iterations"], p["rain"], p["dissolve"], p["deposit"], p["capacity"], p["evap"], max_ero=p["max_ero"])
        doc.set("erosion", dz)
        if p["mode"] == "erode":
            doc.set("height", z)
