"""ポアソンディスク(Bridson, Numba)+密度マスクによる間引き+除外領域。"""
from __future__ import annotations

import numpy as np
from numba import njit


@njit(cache=True)
def bridson(w, h, r, k, seed):
    """[0,w]x[0,h] に最小間隔 r の点集合 (N,2)。seed 固定で決定的"""
    np.random.seed(seed)
    cs = r / 1.41421356
    gw, gh = int(w / cs) + 1, int(h / cs) + 1
    grid = np.full((gh, gw), -1, np.int64)
    pts = np.empty((int(w * h / (r * r * 0.5)) + 16, 2))
    active = np.empty(pts.shape[0], np.int64)
    n, na = 0, 0
    x0, y0 = np.random.uniform(0, w), np.random.uniform(0, h)
    pts[0, 0], pts[0, 1] = x0, y0
    grid[int(y0 / cs), int(x0 / cs)] = 0
    active[0] = 0
    n, na = 1, 1
    while na > 0 and n < pts.shape[0]:
        ai = np.random.randint(0, na)
        p = pts[active[ai]]
        found = False
        for _ in range(k):
            ang = np.random.uniform(0, 6.283185307)
            rad = r * (1 + np.random.uniform(0, 1))
            x, y = p[0] + rad * np.cos(ang), p[1] + rad * np.sin(ang)
            if x < 0 or y < 0 or x >= w or y >= h:
                continue
            gi, gj = int(x / cs), int(y / cs)
            ok = True
            for jj in range(max(gj - 2, 0), min(gj + 3, gh)):
                for ii in range(max(gi - 2, 0), min(gi + 3, gw)):
                    q = grid[jj, ii]
                    if q >= 0 and (pts[q, 0] - x) ** 2 + (pts[q, 1] - y) ** 2 < r * r:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                pts[n, 0], pts[n, 1] = x, y
                grid[gj, gi] = n
                active[na] = n
                n += 1
                na += 1
                found = True
                break
        if not found:
            active[ai] = active[na - 1]
            na -= 1
    return pts[:n].copy()


def sample(grid, r, seed, density=None, allowed=None, rng=None):
    """グリッド全域のポアソンディスク点(ローカル座標 x,y)を、density(0..1)の確率で間引き、allowed(bool)外を除く。
    返り値: (N,2) の x,y と、その点のセル (j,i)。"""
    w, h = grid.nx * grid.res, grid.ny * grid.res
    p = bridson(w, h, float(r), 24, int(seed) & 0x7FFFFFFF)
    ii = np.clip((p[:, 0] / grid.res).astype(int), 0, grid.nx - 1)
    jj = np.clip((p[:, 1] / grid.res).astype(int), 0, grid.ny - 1)
    keep = np.ones(len(p), bool)
    if allowed is not None:
        keep &= allowed[jj, ii]
    if density is not None:
        keep &= rng.random(len(p)) < density[jj, ii]
    p, ii, jj = p[keep], ii[keep], jj[keep]
    return np.stack([p[:, 0] + grid.x0, p[:, 1] + grid.y0], 1), jj, ii
