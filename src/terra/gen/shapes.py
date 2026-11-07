"""形状: 2D プリミティブ + 距離場(山・火山・台地・クレーター・尾根)。位置は at=[0..1,0..1] の格子比率、長さはメートル。"""
from __future__ import annotations

import numpy as np

from ..core.node import Node, node


def _smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def seg_dist(X, Y, pts):
    """折れ線までの距離(各セグメントで最小)と線に沿った位置 t(0..1)"""
    d = np.full(X.shape, np.inf)
    ts = np.zeros(X.shape)
    L = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    for a, b, la in zip(pts[:-1], pts[1:], L):
        ab = b - a
        l2 = float(ab @ ab) or 1e-9
        t = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1]) / l2, 0, 1)
        dd = np.hypot(X - (a[0] + t * ab[0]), Y - (a[1] + t * ab[1]))
        m = dd < d
        d = np.where(m, dd, d)
        ts = np.where(m, (la + t * np.sqrt(l2)) / L[-1], ts)
    return d, ts


@node("gen.shape")
class Shape(Node):
    """kind: mountain | volcano | plateau | crater | ridge。height はメートル。mode: add | max"""
    outputs = ("height",)
    defaults = dict(kind="mountain", at=[0.5, 0.5], radius_m=1500.0, height=800.0, sharp=1.0, asym=0.0,
                    crater_frac=0.25, path=[[0.1, 0.5], [0.9, 0.5]], mode="add")

    def run(self, doc, rng):
        p, g = self.params, doc.grid
        X, Y = g.xy()
        sx, sy = g.size
        X, Y = X - g.x0, Y - g.y0
        cx, cy = p["at"][0] * sx, p["at"][1] * sy
        R = p["radius_m"]
        k = p["kind"]
        if k == "ridge":
            pts = np.array([[a * sx, b * sy] for a, b in p["path"]])
            d, t = seg_dist(X, Y, pts)
            prof = np.exp(-(d / R) ** 2 * 2) ** p["sharp"]
            h = p["height"] * prof * (0.75 + 0.25 * np.sin(t * np.pi))
        else:
            dx, dy = X - cx, Y - cy
            if p["asym"]:
                dx = dx * (1 + p["asym"] * np.clip(dx / R, -1, 1))
            r = np.hypot(dx, dy) / R
            if k == "mountain":
                h = p["height"] * np.exp(-(r ** 2) * 2.5 * p["sharp"])
            elif k == "volcano":
                cone = np.clip(1 - r, 0, 1) ** (1.4 * p["sharp"])
                cf = p["crater_frac"]
                cone = np.where(r < cf, (1 - cf) ** (1.4 * p["sharp"]) * (0.8 + 0.2 * (r / cf) ** 2), cone)
                h = p["height"] * cone
            elif k == "plateau":
                h = p["height"] * (1 - _smooth((r - 0.6) / 0.4))
            elif k == "crater":
                rim = np.exp(-((r - 0.8) / 0.18) ** 2)
                bowl = 1 - _smooth(r / 0.8)
                h = p["height"] * (rim - 1.2 * bowl) * (r < 1.6)
            else:
                raise ValueError(f"unknown shape kind {k}")
        doc.set("height", np.maximum(doc.height, h) if p["mode"] == "max" else doc.height + h)


@node("gen.tilt")
class Tilt(Node):
    """一様な傾斜面(m/m)を足す。slope=[dz/dx, dz/dy]。盆地が閉じず、水が領域の外へ抜ける"""
    outputs = ("height",)
    defaults = dict(slope=[-0.1, -0.1])

    def run(self, doc, rng):
        X, Y = doc.grid.xy()
        doc.set("height", doc.height + self.params["slope"][0] * (X - X.mean()) + self.params["slope"][1] * (Y - Y.mean()))
