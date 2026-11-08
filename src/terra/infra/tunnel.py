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
