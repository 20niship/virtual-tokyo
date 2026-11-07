"""地形統計(実 DEM との比較用): 傾斜ヒストグラム・河川密度・電力スペクトル傾き・比高。"""
from __future__ import annotations

import numpy as np

from .hydro.flow import flow
from .hydro.rivers import river_lines
from .masks.terrain import slope_aspect


def coarsen(z, k):
    return z[: z.shape[0] // k * k, : z.shape[1] // k * k].reshape(z.shape[0] // k, k, z.shape[1] // k, k).mean((1, 3))


def psd_slope(z, res):
    """放射平均した電力スペクトルの log-log 傾き(波長 8*res〜領域/4 の範囲で回帰)。自然地形は約 -2〜-3(高さの PSD)"""
    z = z - np.polyval(np.polyfit(np.arange(z.shape[1]), z.mean(0), 1), np.arange(z.shape[1]))[None, :]
    w = np.hanning(z.shape[0])[:, None] * np.hanning(z.shape[1])[None, :]
    f = np.abs(np.fft.fftshift(np.fft.fft2((z - z.mean()) * w))) ** 2
    ky, kx = np.indices(f.shape)
    r = np.hypot(ky - f.shape[0] / 2, kx - f.shape[1] / 2).astype(int)
    p = np.bincount(r.ravel(), f.ravel()) / np.maximum(np.bincount(r.ravel()), 1)
    k = np.arange(len(p))
    sel = (k >= 4) & (k <= min(f.shape) // 2 // 2)
    return float(np.polyfit(np.log(k[sel]), np.log(p[sel]), 1)[0])


def terrain_stats(z, res, grid, min_area_km2=0.03):
    s, _ = slope_aspect(z, res)
    filled, rcv, area = flow(z, res)
    lines, _ = river_lines(area, rcv, grid, filled, min_area_km2 * 1e6)
    km2 = z.size * res * res / 1e6
    return dict(
        relief_m=float(z.max() - z.min()), z_std=float(z.std()),
        slope_p10=float(np.percentile(s, 10)), slope_p50=float(np.percentile(s, 50)), slope_p90=float(np.percentile(s, 90)),
        slope_hist=np.histogram(s, bins=np.arange(0, 91, 5), density=True)[0],
        drainage_km_per_km2=float(sum(ln.length for ln, _ in lines) / 1000 / km2),
        n_reaches=len(lines), max_order=max((p["order"] for _, p in lines), default=0),
        max_basin_km2=float(area[rcv < 0].max() / 1e6), psd_slope=psd_slope(z.astype(np.float64), res))
