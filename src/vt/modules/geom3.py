"""任意方向の梁/ケーブル/台形ブロックなど、軸に揃わない部材の作成ヘルパ(橋・駅用)。"""
import math

from .geom import Mesh

_BOX_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    L = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2) or 1.0
    return (a[0] / L, a[1] / L, a[2] / L)


def hexa(m, P, mat):
    """凸6面体(下面0..3, 上面4..7をMesh.boxと同じ順) → 各面を重心から外向きに揃えて追加"""
    c = tuple(sum(p[i] for p in P) / 8 for i in range(3))
    for f in _BOX_FACES:
        pts = [P[i] for i in f]
        fc = tuple(sum(p[i] for p in pts) / 4 for i in range(3))
        m.oriented(pts, _sub(fc, c), mat)


def beam(m, a, b, w, h, mat, up=(0, 0, 1)):
    """a→bを軸とする角材(幅w, 高さh)。upで断面の向きを指定"""
    d = _norm(_sub(b, a))
    s = _cross(d, up)
    if abs(s[0]) + abs(s[1]) + abs(s[2]) < 1e-6:
        s = _cross(d, (0, 1, 0))
    s = _norm(s)
    u = _norm(_cross(s, d))
    def p(o, sx, uy):
        return (o[0] + s[0] * sx * w / 2 + u[0] * uy * h / 2, o[1] + s[1] * sx * w / 2 + u[1] * uy * h / 2, o[2] + s[2] * sx * w / 2 + u[2] * uy * h / 2)
    P = [p(a, -1, -1), p(a, 1, -1), p(b, 1, -1), p(b, -1, -1), p(a, -1, 1), p(a, 1, 1), p(b, 1, 1), p(b, -1, 1)]
    hexa(m, P, mat)


def tube3(m, pts, r, mat, n=8, caps=True):
    """3D折れ線に沿う円管(ケーブル/ロープ)。接線フレームで各点にn角形のリング"""
    rings = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
        t = _norm(_sub(b, a))
        s = _cross(t, (0, 0, 1))
        if abs(s[0]) + abs(s[1]) + abs(s[2]) < 1e-6:
            s = (1, 0, 0)
        s = _norm(s); u = _norm(_cross(s, t))
        rings.append([(p[0] + r * (math.cos(2 * math.pi * k / n) * s[0] + math.sin(2 * math.pi * k / n) * u[0]),
                       p[1] + r * (math.cos(2 * math.pi * k / n) * s[1] + math.sin(2 * math.pi * k / n) * u[1]),
                       p[2] + r * (math.cos(2 * math.pi * k / n) * s[2] + math.sin(2 * math.pi * k / n) * u[2])) for k in range(n)])
    for i in range(len(rings) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            q = [rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]]
            c = tuple(sum(v[j] for v in q) / 4 for j in range(3))
            m.oriented(q, _sub(c, pts[i]) if True else (0, 0, 1), mat)
    if caps and len(pts) > 1:
        for ring, p, sg in ((rings[0], pts[0], -1), (rings[-1], pts[-1], 1)):
            t = _sub(pts[-1], pts[0])
            m.oriented(ring, (t[0] * sg, t[1] * sg, t[2] * sg), mat)


def frustum(m, cx, cy, z0, z1, w0, d0, w1, d1, rot, mat, ox=0.0, oy=0.0):
    """台形柱(下w0×d0 → 上w1×d1, 上面は(ox,oy)ずらし)。rotはz回転(ローカルx=w方向)"""
    c, s = math.cos(rot), math.sin(rot)
    def P(x, y, z, off):
        return (cx + (x + off[0]) * c - (y + off[1]) * s, cy + (x + off[0]) * s + (y + off[1]) * c, z)
    lo, hi = (0, 0), (ox, oy)
    B = [P(-w0 / 2, -d0 / 2, z0, lo), P(w0 / 2, -d0 / 2, z0, lo), P(w0 / 2, d0 / 2, z0, lo), P(-w0 / 2, d0 / 2, z0, lo),
         P(-w1 / 2, -d1 / 2, z1, hi), P(w1 / 2, -d1 / 2, z1, hi), P(w1 / 2, d1 / 2, z1, hi), P(-w1 / 2, d1 / 2, z1, hi)]
    hexa(m, B, mat)
