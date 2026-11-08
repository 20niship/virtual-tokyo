"""橋: 経路の橋区間(弦)から、径間・橋脚・種類を決める。浅い川の短い橋は橋脚なし(1 径間)、床が水面近くで短ければ沈下橋、深い谷は高い橋脚。
径間は最大 SPAN_MAX[m]。橋脚の高さは桁の下面から地面まで(module は高さ段階 PIER_HEIGHTS から上側を選び、根元を地中へ沈める)。"""
from __future__ import annotations

import numpy as np

from ..modules.lib_road import PIER_HEIGHTS
from .route import BRIDGE

SPAN_MAX = 32.0
DECK_T = 1.6          # 桁の厚さ(下面 = 路面 - 1.6m)
CHINKA_CLEAR = 2.5    # この高さ未満・長さ 40m 未満なら沈下橋


def runs(kind, which):
    idx = np.flatnonzero(kind == which)
    if not len(idx):
        return []
    return [(int(r[0]), int(r[-1]) + 1) for r in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)]


def classify(P, z, hf):
    """1 本の橋(折れ線 P, 路面高 z)の dict(length, kind=chinka|beam|tall, max_clear, piers=[(s, 地面高, 桁下面高)])"""
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    L = float(s[-1])
    zg = hf.sample(P[:, 0], P[:, 1])
    mc = float((z - zg).max())
    k = "chinka" if (mc < CHINKA_CLEAR and L < 40.0) else ("beam" if mc < 10.0 else "tall")
    piers = []
    if k != "chinka" and L > SPAN_MAX * 0.8:
        n = int(np.ceil(L / SPAN_MAX))
        for q in range(1, n):
            sq = L * q / n
            piers.append((sq, float(np.interp(sq, s, zg)), float(np.interp(sq, s, z)) - DECK_T))
    return dict(length=L, kind=k, max_clear=mc, piers=piers)


def find_bridges(xy, z, kind, doc):
    hf = doc.heightfield()
    return [dict(i0=i0, i1=i1, **classify(xy[i0:i1 + 1], z[i0:i1 + 1], hf)) for i0, i1 in runs(kind, BRIDGE)]


def pier_module(h):
    """桁下面から地面までの高さ h を覆う橋脚 module の高さ段階と名前"""
    H = next((x for x in PIER_HEIGHTS if x >= h + 1.0), PIER_HEIGHTS[-1])
    return H, f"bridge_pier_{H}"
