"""道路の路面メッシュ(vt の Mesh): 曲面のリボン(アスファルト、UV はメートル)+ 外側線 + 中央線(破線)。橋・トンネル区間は module 側が受け持つので作らない。"""
from __future__ import annotations

import numpy as np
from vt.modules.geom import Mesh


def _ribbon(m, P, z, half, off, mat, lift, v0=0.0, dash=None):
    """中心線 P(N,2)・路面高 z から、中心から off の位置に幅 2*half のリボン。dash=(on, off) で破線"""
    d = np.gradient(P, axis=0)
    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    n = np.stack([d[:, 1], -d[:, 0]], 1)
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    for i in range(len(P) - 1):
        if dash and (s[i] % (dash[0] + dash[1])) > dash[0]:
            continue
        pts = []
        for k, sgn in ((i, 1), (i, -1), (i + 1, -1), (i + 1, 1)):
            c = P[k] + n[k] * (off + sgn * half)
            pts.append((float(c[0]), float(c[1]), float(z[k]) + lift))
        uv = [(float(off + sgn * half), float(s[k] + v0)) for k, sgn in ((i, 1), (i, -1), (i + 1, -1), (i + 1, 1))]
        m.poly(pts, mat, uv)


def road_mesh(doc, width=6.5):
    m = Mesh()
    for ln, pr in doc.vectors.get("roads", []):
        if pr["kind"] != "road":
            continue
        P = np.asarray(ln.coords)
        if len(P) < 2:
            continue
        z = np.asarray(pr["z"])
        w = pr.get("width", width)
        _ribbon(m, P, z, w / 2 - 0.1, 0.0, "asphalt", 0.10)
        for sgn in (1, -1):
            _ribbon(m, P, z, 0.08, sgn * (w / 2 - 0.55), "paint_white", 0.13)       # 外側線
        _ribbon(m, P, z, 0.08, 0.0, "paint_white", 0.13, dash=(4.0, 6.0))            # 中央線(破線)
    return m
