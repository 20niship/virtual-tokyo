"""砂利・礫 module(粒径別: 砂・細礫・中礫・玉石、河原の丸い礫、砕石、ガレ場、バラスト)。
単体: gravel_stone_<round|angular|flat>_<fine|medium|cobble>_<0..3>(散布用の 1 粒)。
パッチ: gravel_patch_<sand|fine|medium|cobble|river|crushed|talus|ballast>_<0..2>(混合サイズ。基盤面 + 粒を並べた塊)。near / "_far"(ポリ数 約 1/10)。"""
import math

import numpy as np

from .lib_rock import rock_mesh
from .registry import reg
from .registry import tex as _tex
from vt.materials import MATERIALS as _MAT

SIZE = {"fine": (0.012, 0.03), "medium": (0.035, 0.08), "cobble": (0.1, 0.22)}      # 粒の半径 [m]
SHAPE = {"round": dict(cuts=0, rough=0.06, flat=0.65, mat="rk_river"), "angular": dict(cuts=7, rough=0.22, flat=0.7, mat="rk_andesite"),
         "flat": dict(cuts=5, rough=0.12, flat=0.32, mat="rk_sandstone")}
PATCH = {   # kind: (基盤テクスチャ, 粒 [(割合, 形, サイズ)], 粒数(near), 寸法[m], 基盤テクスチャ周期)
    "sand": ("gravel_sand.png", [], 0, 2.0, 0.5),
    "fine": ("gravel_fine.png", [(1.0, "round", "fine")], 70, 2.0, 0.6),
    "medium": ("gravel_medium.png", [(0.7, "round", "medium"), (0.3, "round", "fine")], 90, 2.0, 0.8),
    "cobble": ("gravel_cobble.png", [(0.6, "round", "cobble"), (0.4, "round", "medium")], 50, 2.0, 1.2),
    "river": ("gravel_river.png", [(0.5, "round", "cobble"), (0.3, "round", "medium"), (0.2, "flat", "medium")], 70, 2.0, 1.0),
    "crushed": ("gravel_crushed.png", [(0.7, "angular", "medium"), (0.3, "angular", "fine")], 120, 2.0, 0.8),
    "talus": ("gravel_crushed.png", [(0.25, "angular", "cobble"), (0.45, "angular", "medium"), (0.3, "flat", "medium")], 90, 4.0, 1.6),
    "ballast": ("gravel_crushed.png", [(1.0, "angular", "medium")], 150, 2.0, 0.6),
}
for _k, (_t, *_r) in PATCH.items():
    _MAT[f"gravel_{_k}"] = _tex(_t, _r[3], 0.96, 0.9)


def stone(m, r, rng, shape, sub, ctr=(0, 0, 0), sink=0.3):
    s = SHAPE[shape]
    rock_mesh(m, r, rng, s["flat"], s["cuts"], s["rough"], s["mat"], ctr, sink, sub)


def _single(shape, size, v, lod):
    def fn(m, W, H, rng):
        lo, hi = SIZE[size]
        stone(m, (lo + hi) / 2 * (0.8 + 0.1 * v), rng, shape, 1 if lod == "near" else 0)
    return fn


def _patch(kind, v, lod):
    tx, mix, count, L, per = PATCH[kind]

    def fn(m, W, H, rng):
        n = 12 if lod == "near" else 4
        xs = np.linspace(-L / 2, L / 2, n + 1)
        base = len(m.v)
        for y in xs:
            for x in xs:
                edge = min(1.0, (L / 2 - max(abs(x), abs(y))) / 0.25)
                m.v.append((x, y, 0.012 + 0.01 * edge * math.sin(x * 9 + v) * math.sin(y * 7)))
        for i in range(n):
            for j in range(n):
                a = base + i * (n + 1) + j
                cx, cy = (xs[j] + xs[j + 1]) / 2, (xs[i] + xs[i + 1]) / 2
                th = math.atan2(cy, cx)
                if math.hypot(cx, cy) > L / 2 * (0.76 + 0.14 * math.sin(3 * th + 2 * v) + 0.1 * math.sin(5 * th + 1)):
                    continue                                              # 縁は不規則な円形
                m.f.append((a, a + 1, a + n + 2, a + n + 1))
                m.m.append(f"gravel_{kind}")
                m.uv.append(None)
        cnt = count if lod == "near" else count // 5
        if mix:
            w = np.array([t[0] for t in mix])
            w = w / w.sum()
            for _ in range(cnt):
                _, shape, size = mix[int(np.searchsorted(np.cumsum(w), rng.random()))]
                lo, hi = SIZE[size]
                x, y = rng.uniform(-L / 2 + 0.1, L / 2 - 0.1), rng.uniform(-L / 2 + 0.1, L / 2 - 0.1)
                r = math.exp(rng.uniform(math.log(lo), math.log(hi))) * (1.6 if kind == "talus" else 1.0)
                stone(m, r, rng, shape, 1 if (lod == "near" and r > 0.05) else 0, (x, y, 0.0), 0.35)
    return fn


for _shape in SHAPE:
    for _size in SIZE:
        for _v in range(4):
            reg(f"gravel_stone_{_shape}_{_size}_{_v}", _single(_shape, _size, _v, "near"), W=SIZE[_size][1] * 2, H=SIZE[_size][1], cat="砂利", lod="near")
            reg(f"gravel_stone_{_shape}_{_size}_{_v}_far", _single(_shape, _size, _v, "far"), W=SIZE[_size][1] * 2, H=SIZE[_size][1], cat="砂利", lod="far")
for _k in PATCH:
    for _v in range(3):
        reg(f"gravel_patch_{_k}_{_v}", _patch(_k, _v, "near"), W=PATCH[_k][3], H=0.25, cat="砂利", lod="near")
        reg(f"gravel_patch_{_k}_{_v}_far", _patch(_k, _v, "far"), W=PATCH[_k][3], H=0.25, cat="砂利", lod="far")
