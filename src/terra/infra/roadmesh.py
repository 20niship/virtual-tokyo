"""道路の路面メッシュ(vt の Mesh): 曲面のリボン(アスファルト、UV はメートル)+ 外側線 + 中央線(破線)。橋・トンネル区間は module 側が受け持つので作らない。"""
from __future__ import annotations

import numpy as np
from vt.materials import MATERIALS as _MAT
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


_MAT["road_asphalt_aged"] = dict(color="#808080", rough=0.88, metal=0.0, tex="road_asphalt.png", size=4.0, bump=0.6)
_MAT["road_shoulder"] = dict(color="#808080", rough=0.95, metal=0.0, tex="gravel.png", size=2.5, bump=0.8, tint="#c8c2b4")


def road_mesh(doc, width=6.5, widen=1.0):
    """widen: 遠景 LOD で路面・路肩・線を太らせる倍率(遠くでも道が線として見える。1.0 = 実寸)"""
    m = Mesh()
    for ln, pr in doc.vectors.get("roads", []):
        if pr["kind"] != "road":
            continue
        P = np.asarray(ln.coords)
        if len(P) < 2:
            continue
        z = np.asarray(pr["z"])
        w = pr.get("width", width) * widen
        for sgn in (1, -1):                                                           # 路肩(砂利混じりの帯)
            _ribbon(m, P, z, 0.45 * widen, sgn * (w / 2 + 0.3 * widen), "road_shoulder", 0.06)
        _ribbon(m, P, z, w / 2 - 0.1, 0.0, "road_asphalt_aged", 0.10)
        for sgn in (1, -1):
            _ribbon(m, P, z, 0.08 * widen, sgn * (w / 2 - 0.55 * widen), "paint_white", 0.13)       # 外側線
        _ribbon(m, P, z, 0.08 * widen, 0.0, "paint_white", 0.13, dash=(4.0, 6.0))                   # 中央線(破線)
    for ln, pr in doc.vectors.get("tunnels", []):                                    # 坑口の手前の切り通し(トンネル本体の路面は module 側)
        P, z = np.asarray(ln.coords), np.asarray(pr["z"])
        s = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
        pl = min(16.0, 0.3 * s[-1])
        w = pr.get("width", width) * widen
        for sel in (s <= pl + 1.0, s >= s[-1] - pl - 1.0):
            if sel.sum() < 2:
                continue
            Q, zq = P[sel], z[sel]
            for sgn in (1, -1):
                _ribbon(m, Q, zq, 0.45 * widen, sgn * (w / 2 + 0.3 * widen), "road_shoulder", 0.06)
            _ribbon(m, Q, zq, w / 2 - 0.1, 0.0, "road_asphalt_aged", 0.10)
            for sgn in (1, -1):
                _ribbon(m, Q, zq, 0.08 * widen, sgn * (w / 2 - 0.55 * widen), "paint_white", 0.13)
            _ribbon(m, Q, zq, 0.08 * widen, 0.0, "paint_white", 0.13, dash=(4.0, 6.0))
    for ln, pr in doc.vectors.get("lanes", []):                                       # 集落の取り付け道(砂利)
        P = np.asarray(ln.coords)
        _ribbon(m, P, np.asarray(pr["z"]), pr["width"] / 2 * max(widen, 1.0), 0.0, "road_shoulder", 0.07)
    return m
