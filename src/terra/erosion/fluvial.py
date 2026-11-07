"""河川下刻(ストリームパワー則, Braun & Willett 2013 の陰解法)。流量の大きい所ほど深く削れ、窪地の無い樹枝状の谷網ができる。
z_t+1 = z_t - K A^m S^n dt を、受け手(下流)から上流へ向けて 1 パスで解く(n=1)。無条件安定なので大きな dt を使える。"""
from __future__ import annotations

import numpy as np
from numba import njit

from ..core.node import Node, node
from ..hydro.flow import DX, DY, flow


@njit(cache=True)
def _implicit(z, rcv, area, order_asc, res, k, m):
    ny, nx = z.shape
    for n in range(order_asc.size):
        c = order_asc[n]
        r = rcv[c // nx, c % nx]
        if r < 0:
            continue
        j, i = c // nx, c % nx
        rj, ri = r // nx, r % nx
        d = res * (1.41421356 if rj != j and ri != i else 1.0)
        f = k * area[j, i] ** m / d
        zn = (z[j, i] + f * z[rj, ri]) / (1.0 + f)
        if zn < z[j, i] and z[rj, ri] < z[j, i]:
            z[j, i] = zn
    return z


def _jitter(shape, amp):
    """格子整列した平坦流を避ける決定的な微小ノイズ(整数ハッシュ)"""
    j, i = np.indices(shape).astype(np.uint64)
    h = (i * np.uint64(73856093)) ^ (j * np.uint64(19349663))
    h = (h ^ (h >> np.uint64(13))) * np.uint64(1274126177)
    return ((h % np.uint64(1000)).astype(np.float64) / 1000.0 - 0.5) * amp


def fluvial(z, res, iterations=8, k=2e-4, m=0.5, sea=-1e9, coarse=2, uplift=0.0, smooth=1.2, fill=True):
    """fill=True は最初に窪地を埋めて(閉じた盆地を作らず、必ず出口へ下る谷網にする)から彫る。coarse>1 なら coarse 倍粗い格子で解き、高さの変化量だけを元の格子へ補間して加える(速い)。uplift[m/反復] は谷網を保つ隆起"""
    from scipy.ndimage import gaussian_filter, zoom
    z = np.asarray(z, dtype=np.float64)
    if z.shape[0] % coarse or z.shape[1] % coarse:
        coarse = 1
    c = z.reshape(z.shape[0] // coarse, coarse, z.shape[1] // coarse, coarse).mean((1, 3)) if coarse > 1 else z.copy()
    rc = res * coarse
    c0 = c.copy()
    if fill:
        c = flow(c, rc, sea)[0]
    for _ in range(iterations):
        c += uplift
        jit = _jitter(c.shape, 2e-3)
        zz = c + jit
        filled, rcv, area = flow(zz, rc, sea)
        order = np.argsort(filled, axis=None, kind="stable").astype(np.int64)    # 出口(低い方)から
        zz = _implicit(zz, rcv, area, order, float(rc), k, m)
        c = zz - jit
    d = c - c0 - uplift * iterations
    d = gaussian_filter(d, smooth)      # D8 の階段状の筋を和らげる
    if coarse > 1:
        d = zoom(d, coarse, order=1)
    return (z + d).astype(np.float32)


@node("erosion.fluvial")
class Fluvial(Node):
    """k: 侵食係数(K·dt, 面積は m²)。iterations 回、流向を更新しながら下刻する"""
    outputs = ("height",)
    defaults = dict(iterations=8, k=2e-4, m=0.5, coarse=2, uplift=0.0, smooth=1.2, fill=True)

    def run(self, doc, rng):
        p = self.params
        doc.set("height", fluvial(doc.height, doc.grid.res, p["iterations"], p["k"], p["m"], coarse=p["coarse"], uplift=p["uplift"], smooth=p["smooth"], fill=p["fill"]))
