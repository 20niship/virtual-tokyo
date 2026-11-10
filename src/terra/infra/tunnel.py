"""トンネル: 経路のトンネル区間(弦)の長さ・土被り・坑口を求める。選択は route.py の探索で行う(弦の長さ x 単価 と通常路の費用を比較し、
坑口付近を除いて土被りが最小値以上になる弦だけがトンネルになれる)。坑口の整地(切り通し)は earthwork.carve、ポータル module の配置は furniture.py。"""
from __future__ import annotations

import numpy as np

from .bridge import runs
from .route import TUNNEL


def find_tunnels(xy, z, kind, doc):
    """トンネルごとに dict(i0, i1, length, min_cover(坑口付近を除く最小土被り), max_cover)"""
    hf = doc.heightfield()
    out = []
    for i0, i1 in runs(kind, TUNNEL):
        p = xy[i0:i1 + 1]
        s = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
        L = float(s[-1])
        cover = hf.sample(p[:, 0], p[:, 1]) - z[i0:i1 + 1]
        mid = (s > 25.0) & (s < L - 25.0)
        out.append(dict(i0=i0, i1=i1, length=L, min_cover=float(cover[mid].min()) if mid.any() else float(cover.max()), max_cover=float(cover.max())))
    return out


PORTAL_LEN = 16.0     # 坑口の手前の切り通し(earthwork.PORTAL_LEN と同じ)。坑口の壁は切り通しの奥端に立つ


def portals(P):
    """トンネル中心線 P(N,2) の両端の坑口位置と向き(坑内へ向く単位ベクトル): [(座標(2), 向き(2), 弧長 s)]。切り通しの長さ分だけ坑内へ入った所"""
    d = np.hypot(*np.diff(P, axis=0).T)
    s = np.r_[0, np.cumsum(d)]
    L = float(s[-1])
    pl = min(PORTAL_LEN, 0.3 * L)
    out = []
    for sc, sgn in ((pl, 1), (L - pl, -1)):
        q = np.array([np.interp(sc, s, P[:, 0]), np.interp(sc, s, P[:, 1])])
        i = int(np.clip(np.searchsorted(s, sc), 1, len(P) - 1))
        t = (P[i] - P[i - 1]) * sgn
        out.append((q, t / max(np.hypot(*t), 1e-9), sc))
    return out
