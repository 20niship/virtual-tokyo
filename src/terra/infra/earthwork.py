"""切土・盛土: 中心線の各点で路盤(幅 width の水平面)を作り、その外側を法面で地形へすり付ける。
切土面 z = z_road + (d - 半幅)/切土比(水平/鉛直)、盛土面 z = z_road - (d - 半幅)/盛土比。地形との min / max を取るので、影響範囲の縁で地形と連続する。
橋の区間は地形を触らない。トンネルは坑口の手前 PORTAL_LEN だけ急な切土(坑口の切り通し)を作る。川の上は変えない。"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from .route import NORMAL, TUNNEL

STEEP = ((30.0, 1.0), (42.0, 0.5), (90.0, 0.25))   # 地形の傾斜[度]の上限 → 法面比の倍率(急斜面は擁壁・岩盤切土で法面を立てる)
PORTAL_LEN = 16.0     # 坑口の切り通し長[m]
WALL_BAY = 1.4        # 擁壁を置く平場の追加幅[m]
COVER = 7.0           # 坑口の奥で確保する地形の高さ(路面から。覆工の頂部 5.5m + 土 1.5m)
REACH = 70.0          # 法面の最大水平距離[m]


def densify(xy, z, kind, step=1.0):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    t = np.arange(0, d[-1], step)
    k = kind[np.minimum(np.searchsorted(d, t, side="right") - 1, len(kind) - 1)]
    return np.interp(t, d, xy[:, 0]), np.interp(t, d, xy[:, 1]), np.interp(t, d, z), k, d, t


def _round_toe(new, zt, dist, ok, wet, hw, shape, res):
    """法尻・法肩の折れ(地形との min/max の尾根・格子の階段)をガウスで丸める。路盤は触らず、変更のあった所とその周囲 ~3 セルだけ、路盤から 3m 離れた所(擁壁の外)から徐々に混ぜる"""
    from scipy.ndimage import binary_dilation, gaussian_filter
    n2, z2, d2 = new.reshape(shape), zt.reshape(shape), dist.reshape(shape)
    sm = gaussian_filter(n2, 3.0 / res, mode="nearest")
    near = binary_dilation(np.abs(n2 - z2) > 1e-3, iterations=3)
    w = np.clip((d2 - hw - 3.0) / 4.0, 0.0, 1.0) * near * (~(wet.reshape(shape))) * ok.reshape(shape)
    return (n2 * (1 - w) + sm * w).ravel()


def carve(doc, xy, z, kind, width, cut_ratio, fill_ratio, river, road_mask, portal_ratio=0.3, shoulder=0.8):
    """doc.height を書き換える。返り値: dict(cut_m3, fill_m3)"""
    g = doc.grid
    x, y, zr, k, d, t = densify(xy, z, kind)
    # 構造物の端からの距離(坑口の切り通し判定)
    ratio = np.full(len(x), cut_ratio)
    use = k == NORMAL
    tun = k == TUNNEL
    deep = np.zeros(len(x), bool)
    if tun.any():
        idx = np.flatnonzero(tun)
        runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
        for r in runs:
            near = (t >= t[r[0]]) & (t <= t[r[0]] + PORTAL_LEN) | (t <= t[r[-1]]) & (t >= t[r[-1]] - PORTAL_LEN)
            sel = near & tun
            use |= sel
            ratio[sel] = portal_ratio
            mine = np.zeros(len(x), bool)
            mine[r] = True
            a0, a1 = t[r[0]] + PORTAL_LEN, t[r[-1]] - PORTAL_LEN          # 坑口の位置(弧長)。盛土は坑口の壁(の位置)から奥へ。点の 5m 手前まで 1、6m で 0
            deep |= mine & (((t >= a0 + 5) & (t <= a0 + 86)) | ((t <= a1 - 5) & (t >= a1 - 86)))
    if not use.any():
        return dict(cut_m3=0.0, fill_m3=0.0)
    from ..masks.terrain import slope_aspect
    sl_all, _ = slope_aspect(doc.height, g.res)
    ii = np.clip(((x - g.x0) / g.res).astype(int), 0, g.nx - 1)
    jj = np.clip(((y - g.y0) / g.res).astype(int), 0, g.ny - 1)
    sl = sl_all[jj, ii]
    mult = np.where(sl <= STEEP[0][0], STEEP[0][1], np.where(sl <= STEEP[1][0], STEEP[1][1], STEEP[2][1]))
    ratio = ratio * mult                                              # 傾斜に応じて切土法面を立てる
    fmult = mult
    xs, ys, zs, rs, fs = x[use], y[use], zr[use], ratio[use], fmult[use]
    tree = cKDTree(np.stack([xs, ys], 1))
    pad = REACH
    i0, i1 = max(int((xs.min() - pad - g.x0) / g.res), 0), min(int((xs.max() + pad - g.x0) / g.res) + 1, g.nx)
    j0, j1 = max(int((ys.min() - pad - g.y0) / g.res), 0), min(int((ys.max() + pad - g.y0) / g.res) + 1, g.ny)
    X, Y = g.xy()
    sl2 = (slice(j0, j1), slice(i0, i1))
    sl = sl2
    dist, nn = tree.query(np.stack([X[sl].ravel(), Y[sl].ravel()], 1), distance_upper_bound=REACH)
    ok = np.isfinite(dist)
    nn = np.where(ok, nn, 0)
    zt = doc.height[sl].ravel().astype(np.float64)
    hw = width / 2.0 + shoulder          # 舗装の外側の路肩(水平)まで路盤。側溝・縁石・ガードレールはこの上に置く
    zro = zs[nn]
    hwa = hw + np.where(fs[nn] < 0.3, WALL_BAY, 0.0)      # 急斜面(擁壁・岩盤切土)は法面を擁壁の厚み分だけ後ろへ下げ、擁壁が地形に埋もれないようにする
    off = np.maximum(dist - hwa, 0.0)
    new = np.where(dist <= hwa, zro,
                   np.where(zt > zro, np.minimum(zt, zro + off / rs[nn]), np.maximum(zt, zro - off / (fill_ratio * fs[nn]))))
    new = np.where(ok, new, zt)
    wet = (river[sl].ravel() > 0) | (doc.layers.get("water_depth", np.zeros(g.shape, np.float32))[sl].ravel() > 0.05)
    new = np.where(wet, zt, new)
    if deep.any():              # 坑口の奥の土被り不足(探索は坑口付近の土被りを免除する)を、地形を盛って坑口の壁の高さ(7m)以上にする
        dt = cKDTree(np.stack([x[deep], y[deep]], 1))
        d2, n2 = dt.query(np.stack([X[sl].ravel(), Y[sl].ravel()], 1), distance_upper_bound=6.0)
        w = np.where(np.isfinite(d2), np.clip(6.0 - np.where(np.isfinite(d2), d2, 6.0), 0, 1), 0.0)
        floor = zr[deep][np.where(np.isfinite(d2), n2, 0)] + COVER
        new = np.where(w > 0, new + (np.maximum(new, floor) - new) * w, new)
    new = _round_toe(new, zt, dist, ok, wet, hw, (j1 - j0, i1 - i0), g.res)
    dz = new - zt
    cell = g.res ** 2
    cut, fill = float(-dz[dz < 0].sum() * cell), float(dz[dz > 0].sum() * cell)
    h = doc.layers["height"].astype(np.float32).copy()
    h[sl] = new.reshape(h[sl].shape).astype(np.float32)
    doc.layers["height"] = h
    plat = ((dist <= hw) & ok & ~wet).reshape(h[sl].shape)
    road_mask[sl] = np.maximum(road_mask[sl], plat.astype(np.float32))
    return dict(cut_m3=cut, fill_m3=fill)
