"""川のベクタ化(支流ごとの折れ線 + 幅 + 流量)と湖(充填で埋めた窪地)。"""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from shapely.geometry import LineString, MultiPolygon, Polygon, shape  # noqa: F401


def strahler(rcv_flat, is_river):
    """河川セルの Strahler 次数(同次数 2 本の合流で +1)。トポロジカル順に解く"""
    idx = np.flatnonzero(is_river)
    nxt = rcv_flat[idx]
    ok = (nxt >= 0) & is_river[np.where(nxt >= 0, nxt, 0)]
    order = np.ones(is_river.size, np.int32)
    ups = {}
    for c, n in zip(idx[ok], nxt[ok]):
        ups.setdefault(int(n), []).append(int(c))
    # 上流が全て確定してから処理(トポロジカル順)
    indeg = {int(c): len(ups.get(int(c), [])) for c in idx}
    stack = [c for c, d in indeg.items() if d == 0]
    while stack:
        c = stack.pop()
        u = [order[v] for v in ups.get(c, [])]
        if u:
            m = max(u)
            order[c] = m + 1 if u.count(m) >= 2 else m
        n = int(rcv_flat[c])
        if n >= 0 and is_river[n]:
            indeg[n] -= 1
            if indeg[n] == 0:
                stack.append(n)
    return order


def river_lines(area, rcv, grid, filled, min_area_m2, runoff_m=1.2, width_k=2.5, width_exp=0.5, smooth=2):
    """合流点ごとに分割した川の折れ線 [(LineString, props)] と幅ラスタ[m]。Q[m³/s]=面積*runoff_m/3.15e7、幅=width_k*Q^width_exp"""
    ny, nx = area.shape
    isr = (area >= min_area_m2).ravel()
    r = rcv.ravel().astype(np.int64)
    n_up = np.zeros(isr.size, np.int32)
    src = np.flatnonzero(isr & (r >= 0))
    dn_in = isr[np.where(r[src] >= 0, r[src], 0)]
    np.add.at(n_up, r[src][dn_in], 1)
    ordr = strahler(r, isr)
    q = area.ravel() * runoff_m / 3.15e7
    wid = width_k * q ** width_exp
    X, Y = grid.xy()
    xf, yf, zf = X.ravel(), Y.ravel(), filled.ravel()
    starts = np.flatnonzero(isr & (n_up != 1))     # 源頭(0)と合流点(2+)から始める
    out = []
    for s in starts:
        path = [int(s)]
        c = int(s)
        while True:
            n = int(r[c])
            if n < 0:
                break
            path.append(n)
            if not isr[n] or n_up[n] != 1:
                break
            c = n
        pts_idx = path
        pts = np.stack([xf[pts_idx], yf[pts_idx]], 1)
        for _ in range(smooth):         # Chaikin 平滑化(端点固定)
            if len(pts) < 3:
                break
            a, b = pts[:-1], pts[1:]
            q1, q2 = 0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b
            pts = np.concatenate([pts[:1], np.stack([q1, q2], 1).reshape(-1, 2)[1:-1], pts[-1:]])
        if len(pts) < 2:
            continue
        e = pts_idx[-1] if isr[pts_idx[-1]] else pts_idx[-2]
        out.append((LineString(pts), dict(q=float(q[e]), width=float(wid[e]), order=int(ordr[e]), z_top=float(zf[pts_idx[0]]), z_bot=float(zf[pts_idx[-1]]),
                                          cells=pts_idx)))
    wmap = np.where(isr, wid, 0.0).reshape(ny, nx).astype(np.float32)
    return out, wmap


def lakes(z, filled, res, min_depth=2.0, min_area_m2=2e4, sea=-1e9):
    """充填で埋まった窪地のうち、最大深さ min_depth 以上・面積 min_area 以上を湖とする。返り値: ラベル(0=なし), 水深, [(Polygon, dict(level, area, depth))]"""
    depth = (filled - z).astype(np.float32)
    cand = depth > 0.05
    lab, n = ndimage.label(cand)
    keep = np.zeros(n + 1, bool)
    info = {}
    if n:
        mx = ndimage.maximum(depth, lab, np.arange(1, n + 1))
        cnt = ndimage.sum(cand, lab, np.arange(1, n + 1))
        for i in range(n):
            if mx[i] >= min_depth and cnt[i] * res * res >= min_area_m2:
                keep[i + 1] = True
                info[i + 1] = (float(mx[i]), float(cnt[i] * res * res))
    lake = np.where(keep[lab], lab, 0).astype(np.int32)
    wd = np.where(lake > 0, depth, 0).astype(np.float32)
    return lake, wd, info
