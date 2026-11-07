"""窪地充填(priority-flood + ε)・D8 流向・流量(上流面積)・TWI。Numba。
充填後の面は「各セルが受け手より厳密に高い」ので、受け手へ辿れば必ず境界/海へ達し、流量は降順処理で保存される。"""
from __future__ import annotations

import heapq  # noqa: F401  (numba が参照)

import numpy as np
from numba import njit

DY = np.array([-1, -1, -1, 0, 0, 1, 1, 1], np.int64)
DX = np.array([-1, 0, 1, -1, 1, -1, 0, 1], np.int64)
EPS = 1e-5


@njit(cache=True)
def priority_flood(z, sea):
    """z[m] → 充填後の標高(float64)。境界と z<=sea の海セルを出口とする。窪地は ε ずつ上げて平坦部も排水させる"""
    ny, nx = z.shape
    out = z.astype(np.float64)
    closed = np.zeros((ny, nx), np.bool_)
    heap = [(out[0, 0], 0)]
    heap.pop()
    for j in range(ny):
        for i in range(nx):
            if j == 0 or i == 0 or j == ny - 1 or i == nx - 1 or out[j, i] <= sea:
                closed[j, i] = True
                heapq.heappush(heap, (out[j, i], j * nx + i))
    while len(heap) > 0:
        zc, c = heapq.heappop(heap)
        cj, ci = c // nx, c % nx
        for k in range(8):
            nj, ni = cj + DY[k], ci + DX[k]
            if nj < 0 or ni < 0 or nj >= ny or ni >= nx or closed[nj, ni]:
                continue
            closed[nj, ni] = True
            if out[nj, ni] <= zc:
                out[nj, ni] = zc + EPS
            heapq.heappush(heap, (out[nj, ni], nj * nx + ni))
    return out


@njit(cache=True)
def d8_receivers(f, sea, res):
    """最急降下の受け手(平坦 index)。出口(境界・海)は -1。"""
    ny, nx = f.shape
    rcv = np.full((ny, nx), -1, np.int32)
    for j in range(ny):
        for i in range(nx):
            if j == 0 or i == 0 or j == ny - 1 or i == nx - 1 or f[j, i] <= sea:
                continue
            best, bk = 0.0, -1
            for k in range(8):
                nj, ni = j + DY[k], i + DX[k]
                d = res * (1.41421356 if DY[k] != 0 and DX[k] != 0 else 1.0)
                s = (f[j, i] - f[nj, ni]) / d
                if s > best:
                    best, bk = s, k
            if bk >= 0:
                rcv[j, i] = (j + DY[bk]) * nx + (i + DX[bk])
    return rcv


@njit(cache=True)
def accumulate(order, rcv, w):
    """order: 標高降順のセル index。w: 各セルが生む量。返り値: 上流を含む累積(受け手へ足し込む)"""
    acc = w.ravel().copy()
    r = rcv.ravel()
    for n in range(order.size):
        c = order[n]
        if r[c] >= 0:
            acc[r[c]] += acc[c]
    return acc.reshape(w.shape)


def flow(z, res, sea=-1e9):
    """返り値: filled[m], rcv(int32 平坦 index, 出口 -1), area[m²](上流面積, 自身を含む)"""
    z = np.asarray(z, np.float64)
    filled = priority_flood(z, float(sea))
    rcv = d8_receivers(filled, float(sea), float(res))
    order = np.argsort(-filled, axis=None, kind="stable").astype(np.int64)
    area = accumulate(order, rcv, np.full(z.shape, res * res))
    return filled, rcv, area


def twi(area, slope_deg, res):
    """地形湿潤指数 ln(a / tanβ)。a=単位等高線長あたりの上流面積。平地は tanβ を下限でクリップ"""
    tanb = np.tan(np.radians(np.maximum(slope_deg, 0.5)))
    return np.log(area / res / tanb).astype(np.float32)
