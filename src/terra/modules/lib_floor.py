"""林床の module(手続き生成・near / "_far"): 落ち葉の層・倒木・枯れ枝・ササの株・シダの株。樹冠下の無地の地面に変化と繁りを足す。原点は根元、z 上。"""
import math

import numpy as np
from vt import tree_gen as tg
from vt.materials import MATERIALS as _MAT

from .registry import reg
from .registry import tex as _tex

_MAT["floor_litter"] = _tex("forest_litter.png", 1.2, 0.95, 0.6, tint="#c9a77a")
for _n, _c in (("a", "#7b4a24"), ("b", "#a8622a"), ("c", "#b58a3a"), ("d", "#5a3d22")):
    _MAT[f"floor_leaf_{_n}"] = dict(color=_c, rough=0.8, metal=0.0)
_MAT["floor_sasa"] = dict(color="#7ea84a", rough=0.6, metal=0.0)
_MAT["floor_sasa_dry"] = dict(color="#a8a55a", rough=0.65, metal=0.0)
_MAT["floor_fern"] = dict(color="#4f8a35", rough=0.55, metal=0.0)
_MAT["floor_moss_strip"] = _tex("moss.png", 0.4, 0.98, 1.0, tint="#98ac78")
_MAT["floor_wood_end"] = dict(color="#b89870", rough=0.8, metal=0.0)


def _leaf(m, c, ang, ln, mat):
    """地面に寝た葉 1 枚(菱形)"""
    ca, sa = math.cos(ang), math.sin(ang)
    w = ln * 0.45
    pts = [(c[0] + ca * ln / 2, c[1] + sa * ln / 2, c[2]), (c[0] - sa * w / 2, c[1] + ca * w / 2, c[2] + 0.004),
           (c[0] - ca * ln / 2, c[1] - sa * ln / 2, c[2]), (c[0] + sa * w / 2, c[1] - ca * w / 2, c[2] + 0.004)]
    m.poly(pts, mat)


def _leaves(v, lod):
    def fn(m, W, H, rng):
        n = {"near": 150, "far": 24}[lod]
        R = 1.5
        base = len(m.v)
        k = 14 if lod == "near" else 6
        ang = np.linspace(0, 2 * math.pi, k, endpoint=False)
        rr = R * (0.8 + 0.2 * np.sin(3 * ang + v) * np.sin(2 * ang + 1))
        m.v.append((0.0, 0.0, 0.025))
        m.v.extend((r * math.cos(a), r * math.sin(a), 0.003) for r, a in zip(rr, ang))        # 縁は地面すれすれ、中心が少し高い落ち葉の層
        for i in range(k):
            m.f.append((base, base + 1 + i, base + 1 + (i + 1) % k))
            m.m.append("floor_litter")
            m.uv.append(None)
        for _ in range(n):
            t, a = math.sqrt(rng.random()) * R * 0.85, rng.uniform(0, 6.28)
            _leaf(m, (t * math.cos(a), t * math.sin(a), 0.03 * (1 - t / R) + 0.006 + rng.uniform(0, 0.02)), rng.uniform(0, 6.28),
                  rng.uniform(0.05, 0.1) * (3.0 if lod == "far" else 1.0), f"floor_leaf_{'abcd'[int(rng.random() * 4)]}")
    return fn


def _log(v, lod):
    def fn(m, W, H, rng):
        L, r = ((2.6, 0.16), (3.4, 0.22), (4.2, 0.28))[v]
        n = 8 if lod == "near" else 3
        pts = [np.array([x, 0.06 * math.sin(x * 1.3 + v), r * 0.8]) for x in np.linspace(-L / 2, L / 2, n)]
        tg.tube(m, pts, [r * (1 - 0.25 * (i / (n - 1))) for i in range(n)], "bark_furrow_dark", 9 if lod == "near" else 5, 1.0, True)
        if lod == "near":
            m.box(-L / 4, -r * 0.35, r * 1.5, L / 4, r * 0.35, r * 1.58, "floor_moss_strip")                  # 上面の苔
            for b in range(3):                                                                              # 折れた枝の根元
                x = rng.uniform(-L / 3, L / 3)
                tg.tube(m, [np.array([x, 0, r * 1.5]), np.array([x + 0.1, 0.05, r * 1.5 + 0.18])], [0.03, 0.015], "bark_furrow_dark", 4, 1.0, False)
    return fn


def _branch(v, lod):
    def fn(m, W, H, rng):
        L = 0.9 + 0.3 * v
        main = [np.array([x, 0.03 * math.sin(x * 5 + v), 0.02 + 0.01 * x]) for x in np.linspace(-L / 2, L / 2, 5)]
        tg.tube(m, main, [0.014, 0.012, 0.01, 0.008, 0.005], "bark_smooth", 4, 1.0, False)
        for _ in range(2 + v if lod == "near" else 1):
            i = rng.randint(1, 3)
            a = rng.uniform(0.5, 1.1) * rng.choice([-1, 1])
            q = main[i]
            tg.tube(m, [q, q + np.array([0.18 * math.cos(a), 0.18 * math.sin(a), 0.02]), q + np.array([0.34 * math.cos(a), 0.34 * math.sin(a), 0.03])], [0.007, 0.005, 0.003], "bark_smooth", 3, 1.0, False)
    return fn


def _sasa(v, lod):
    """ササ(クマイザサ風)の株: 細長い葉が放射状に弧を描いて立つ"""
    def fn(m, W, H, rng):
        for i in range(22 if lod == "near" else 6):
            a = rng.uniform(0, 6.28)
            ln = rng.uniform(0.5, 0.9) * (1.0 + 0.2 * v)
            lean = rng.uniform(0.35, 0.9)
            mat = "floor_sasa_dry" if rng.random() < 0.12 else "floor_sasa"
            seg = 4 if lod == "near" else 1
            ca, sa = math.cos(a), math.sin(a)
            pts = [(ca * ln * lean * (j / seg) ** 1.6, sa * ln * lean * (j / seg) ** 1.6, ln * (1 - lean * 0.5) * math.sin(math.pi / 2 * j / seg * 1.1)) for j in range(seg + 1)]
            w = 0.035
            for j in range(seg):
                w0, w1 = w * math.sin(math.pi * (j + 0.5) / (seg + 1) + 0.3), w * math.sin(math.pi * (j + 1.5) / (seg + 1) + 0.3)
                px, py = -sa, ca
                m.poly([(pts[j][0] - px * w0, pts[j][1] - py * w0, pts[j][2]), (pts[j][0] + px * w0, pts[j][1] + py * w0, pts[j][2]),
                        (pts[j + 1][0] + px * w1, pts[j + 1][1] + py * w1, pts[j + 1][2]), (pts[j + 1][0] - px * w1, pts[j + 1][1] - py * w1, pts[j + 1][2])], mat)
    return fn


def _fern(v, lod):
    """シダの株: 弧を描く葉軸に左右の羽片"""
    def fn(m, W, H, rng):
        for i in range(7 if lod == "near" else 4):
            a = 2 * math.pi * i / 7 + rng.uniform(-0.3, 0.3)
            ln = rng.uniform(0.55, 0.85) * (1.0 + 0.25 * v)
            ca, sa = math.cos(a), math.sin(a)
            n = 8 if lod == "near" else 2
            P = [(ca * ln * 0.75 * (t / n) ** 1.3, sa * ln * 0.75 * (t / n) ** 1.3, 0.1 + ln * 0.5 * math.sin(math.pi * 0.85 * t / n) * 0.9) for t in range(n + 1)]
            for t in range(1, n + 1):
                wd = 0.11 * math.sin(math.pi * (t / (n + 1))) + 0.015
                p0, p1 = np.array(P[t - 1]), np.array(P[t])
                side = np.array([-sa, ca, 0.0])
                m.poly([tuple(p0 - side * wd), tuple(p0 + side * wd), tuple(p1 + side * wd * 0.8), tuple(p1 - side * wd * 0.8)], "floor_fern")
    return fn


for _lod in ("near", "far"):
    _s = "" if _lod == "near" else "_far"
    for _v in range(3):
        reg(f"floor_leaves_{_v}{_s}", _leaves(_v, _lod), W=3.0, H=0.1, cat="林床", lod=_lod)
        reg(f"floor_log_{_v}{_s}", _log(_v, _lod), W=4.2, H=0.6, cat="林床", lod=_lod)
        reg(f"floor_branch_{_v}{_s}", _branch(_v, _lod), W=1.2, H=0.2, cat="林床", lod=_lod)
        reg(f"floor_sasa_{_v}{_s}", _sasa(_v, _lod), W=1.4, H=0.9, cat="林床", lod=_lod)
        reg(f"floor_fern_{_v}{_s}", _fern(_v, _lod), W=1.5, H=0.6, cat="林床", lod=_lod)
