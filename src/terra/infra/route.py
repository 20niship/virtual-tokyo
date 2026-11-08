"""最小コスト経路(A*, Numba)。粗い格子(既定 4 セル = 8m)上で、傾斜・川・保護域・既存路線・標高変化のコスト面を探索する。
1 手 = 16 方向の基本ベクトル。通常の手は縦断勾配(= 標高差/距離)が上限以内のものだけ許す(急斜面では自然に等高線沿いのつづら折りになる)。
さらに、谷・川は「橋」の弦(直線で跨ぐ)、尾根は「トンネル」の弦(直線で貫く)として長い手を許し、単価(長さ x 単価)で通常路と比較する。
弦の条件: 橋 = 弦の下に地面があり(隙間 >= 1.5m)、地面は弦を大きく突き抜けない / トンネル = 坑口付近を除き土被り >= 最小値 / どちらも弦の勾配 <= 上限。"""
from __future__ import annotations

import heapq  # noqa: F401  (numba が参照)

import numpy as np
from numba import njit

# 16 方向の基本ベクトル(dx, dy)
PRIM = np.array([(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1),
                 (2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)], np.int64)
NORMAL, BRIDGE, TUNNEL = 0, 1, 2


@njit(cache=True)
def _fine(zf, fs, x, y):
    """粗いセル座標 (x, y) の位置の細かい格子の標高(最近傍)"""
    i = min(max(int((x + 0.5) * fs), 0), zf.shape[1] - 1)
    j = min(max(int((y + 0.5) * fs), 0), zf.shape[0] - 1)
    return zf[j, i]


@njit(cache=True)
def _chord(zf, wf, rf, fs, cs, ax, ay, bx, by, za, zb, kind, p):
    """弦 a→b の可否と追加コスト(不可は -1)。p: [gmax, bridge_min_clear, max_clear, min_cover, portal_len, intrude]"""
    L = np.hypot(bx - ax, by - ay) * cs
    if abs(zb - za) / L > p[0]:
        return -1.0
    n = max(int(L / (cs * 0.5)), 2)
    maxc, minc, mincov = -1e9, 1e9, 1e9
    cross = False
    for k in range(1, n):
        t = k / n
        x, y = ax + (bx - ax) * t, ay + (by - ay) * t
        zl = za + (zb - za) * t
        zt = _fine(zf, fs, x, y)
        c = zl - zt
        maxc, minc = max(maxc, c), min(minc, c)
        if _fine(rf, fs, x, y) > 0.5:
            cross = True
        if kind == 2:
            d = min(t, 1 - t) * L
            if d > p[4] and -c < p[3]:
                return -1.0                   # 坑口付近を除いて土被り不足
            if _fine(wf, fs, x, y) > 0.5:
                return -1.0
    if kind == 1:
        if (maxc < p[1] and not cross) or maxc > p[2] or minc < -p[5]:
            return -1.0                      # 川を渡る弦は隙間が小さくてもよい(浅い川の短い橋)
        return L * (p[6] + 0.12 * max(maxc, 2.0))
    return L * p[7]


@njit(cache=True)
def search(zc, slope, blocked, river, exist, zf, wf, rf, fs, cs, start, goal, gmax, p, allow_tunnel, allow_bridge, w_slope, w_grade, w_exist, w_dz, bridge_lens, tunnel_lens):
    """返り値: 経路の頂点列(粗い格子の index)・各頂点へ入る手の種類・各手の長さ倍率。見つからなければ空"""
    ny, nx = zc.shape
    n = ny * nx
    INF = 1e30
    g = np.full(n, INF)
    par = np.full(n, -1, np.int64)
    kin = np.zeros(n, np.int8)
    s = start[1] * nx + start[0]
    t = goal[1] * nx + goal[0]
    g[s] = 0.0
    heap = [(0.0, s)]
    done = np.zeros(n, np.bool_)
    while len(heap) > 0:
        f, c = heapq.heappop(heap)
        if done[c]:
            continue
        done[c] = True
        if c == t:
            break
        cx, cy = c % nx, c // nx
        for q in range(16):
            vx, vy = PRIM[q, 0], PRIM[q, 1]
            # --- 通常の手
            ex, ey = cx + vx, cy + vy
            if 0 <= ex < nx and 0 <= ey < ny and not blocked[ey, ex] and river[ey, ex] == 0:
                d = np.hypot(vx, vy) * cs
                gr = abs(zc[ey, ex] - zc[cy, cx]) / d
                if gr <= gmax:
                    sl = 0.5 * (slope[ey, ex] + slope[cy, cx]) / 30.0
                    cost = d * (1.0 + w_slope * sl * sl + w_grade * (gr / gmax) ** 2 + (w_exist if exist[ey, ex] else 0.0)) + w_dz * abs(zc[ey, ex] - zc[cy, cx])
                    e = ey * nx + ex
                    if g[c] + cost < g[e]:
                        g[e] = g[c] + cost
                        par[e] = c
                        kin[e] = 0
                        h = np.hypot(goal[0] - ex, goal[1] - ey) * cs
                        heapq.heappush(heap, (g[e] + h, e))
            # --- 橋・トンネルの弦(基本ベクトルの k 倍)
            for kind in range(1, 3):
                if (kind == 1 and not allow_bridge) or (kind == 2 and not allow_tunnel):
                    continue
                lens = bridge_lens if kind == 1 else tunnel_lens
                for li in range(lens.size):
                    k = lens[li]
                    ex, ey = cx + vx * k, cy + vy * k
                    if not (0 <= ex < nx and 0 <= ey < ny) or blocked[ey, ex] or river[ey, ex] != 0:
                        continue
                    if np.hypot(vx * k, vy * k) < 1.9:
                        continue
                    extra = _chord(zf, wf, rf, fs, cs, float(cx), float(cy), float(ex), float(ey), zc[cy, cx], zc[ey, ex], kind, p)
                    if extra < 0:
                        continue
                    e = ey * nx + ex
                    if g[c] + extra < g[e]:
                        g[e] = g[c] + extra
                        par[e] = c
                        kin[e] = kind
                        h = np.hypot(goal[0] - ex, goal[1] - ey) * cs
                        heapq.heappush(heap, (g[e] + h, e))
    if not done[t]:
        return np.empty(0, np.int64), np.empty(0, np.int8)
    path = [t]
    kinds = [kin[t]]
    while path[-1] != s:
        q = par[path[-1]]
        path.append(q)
        kinds.append(kin[q])
    out = np.empty(len(path), np.int64)
    ok = np.empty(len(path), np.int8)
    for i in range(len(path)):
        out[i] = path[len(path) - 1 - i]
        ok[i] = kinds[len(path) - 1 - i]
    return out, ok


def find_route(z, res, slope, water, river, start_xy, goal_xy, grid, gmax=0.10, factor=4, allow_tunnel=True, allow_bridge=True,
               exist=None, min_cover=10.0, tunnel_cost=22.0, bridge_cost=10.0, max_clear=45.0, w_slope=3.0, w_grade=1.5, w_exist=-0.6, w_dz=0.02):
    """z: 細かい標高(行 0 = 南)。start/goal: ローカル座標[m]。返り値: [(x, y, kind_in, z)] 粗い格子の頂点(kind_in: その頂点へ入る手の種類、z: 探索に使った標高。隣り合う頂点間の勾配は上限以内)。gmax は縦断勾配の上限(0.10 = 10%)"""
    from scipy.ndimage import gaussian_filter, zoom
    f = factor
    ny, nx = z.shape[0] // f, z.shape[1] // f
    zc = gaussian_filter(z[: ny * f, : nx * f].reshape(ny, f, nx, f).mean((1, 3)).astype(np.float64), 0.7)
    sl = slope[: ny * f, : nx * f].reshape(ny, f, nx, f).mean((1, 3))
    blocked = water[: ny * f, : nx * f].reshape(ny, f, nx, f).max((1, 3)) > 0.05
    rv = (river[: ny * f, : nx * f].reshape(ny, f, nx, f).max((1, 3)) > 0).astype(np.uint8)
    ex = np.zeros((ny, nx), np.bool_) if exist is None else exist[: ny * f, : nx * f].reshape(ny, f, nx, f).max((1, 3)) > 0
    cs = res * f
    to = lambda p: (int(np.clip((p[0] - grid.x0) / cs - 0.5, 0, nx - 1)), int(np.clip((p[1] - grid.y0) / cs - 0.5, 0, ny - 1)))
    s, t = to(start_xy), to(goal_xy)
    for cx, cy in (s, t):                       # 端点は水・川から外す
        blocked[cy, cx] = False
        rv[cy, cx] = 0
    gmax = gmax * 0.94                  # 弦の端点の標高のずれで 0.1 を超えないよう余裕を持たせる
    p = np.array([gmax, 4.0, max_clear, min_cover, 25.0, 1.0, bridge_cost, tunnel_cost], np.float64)
    bl = np.array([2, 3, 4, 6, 9, 14], np.int64)
    tl = np.array([3, 4, 6, 9, 13, 18], np.int64)
    idx, kinds = search(zc, sl.astype(np.float64), blocked, rv, ex, z.astype(np.float64), (water > 0.05).astype(np.float64), (river > 0).astype(np.float64), float(f), float(cs),
                        np.array(s, np.int64), np.array(t, np.int64), gmax, p, allow_tunnel, allow_bridge, w_slope, w_grade, w_exist, w_dz, bl, tl)
    if idx.size == 0:
        return []
    return [(grid.x0 + (i % nx + 0.5) * cs, grid.y0 + (i // nx + 0.5) * cs, int(k), float(zc[i // nx, i % nx])) for i, k in zip(idx, kinds)]
