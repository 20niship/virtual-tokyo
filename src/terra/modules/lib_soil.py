"""土・地面 module(種類ごとに色・粒度・形状・材質): 黒ボク土・赤黄色土・粘土・砂質土・火山灰/スコリア・マサ土・腐植/落葉層・ぬかるみ。
soil_<種>_patch_<0..2>(3m 角の地面パッチ。near=24x24 分割 / "_far"=6x6)、soil_<種>_clod_<0..2>(土塊の単体。散布用)。
パッチの形状: 土塊の起伏(全種)、粘土の乾燥亀裂、ぬかるみの水たまり(濡れ材質)と轍、スコリアの粗い凹凸、腐植の落葉片の盛り上がり。縁は高さ 0 へ落として地面になじませる。"""
import math

import numpy as np

from ..geology.tables import SOILS
from .lib_rock import _ICO, _ico, _noise_dir
from .registry import reg
from .registry import tex as _tex
from vt.materials import MATERIALS as _MAT

PARAM = {   # 起伏の大きさ[m], 起伏の細かさ, 粗さ
    "kuroboku": (0.09, 1.4), "redyellow": (0.08, 1.7), "clay": (0.05, 1.0), "sandy": (0.06, 2.2),
    "scoria": (0.14, 2.8), "masa": (0.09, 2.4), "humus": (0.10, 1.8), "mud": (0.08, 1.0),
}
for _k in SOILS:
    _MAT[f"soil_{_k}"] = _tex(f"soil_{_k}.png", 0.7, 0.5 if _k == "mud" else 0.95, 0.7)
_MAT["soil_mud_wet"] = _tex("soil_mud.png", 1.2, 0.06, 0.2, tint="#707070")


def _patch(kind, v, lod):
    amp, fq = PARAM[kind]

    def fn(m, W, H, rng):
        n = {"near": 32, "far": 6, "hi": 200}[lod]      # hi: 1.5cm 格子(約 4 万四角形)+粒・小石の微細起伏
        xs = np.linspace(-1.5, 1.5, n + 1)
        nz = _noise_dir(rng, 7)
        X, Y = np.meshgrid(xs, xs)
        h = np.zeros_like(X)
        for i in range(n + 1):
            for j in range(n + 1):
                d = np.array([X[i, j] * fq, Y[i, j] * fq, v * 0.9])
                d = d / (np.linalg.norm(d) + 1e-9)
                h[i, j] = amp * nz(d * 3.1)
        if kind == "clay":                                                       # 乾燥亀裂: 多角形の縁を低くする
            pts = np.array([[rng.uniform(-1.5, 1.5), rng.uniform(-1.5, 1.5)] for _ in range(14)])
            dd = np.sqrt(((X[..., None] - pts[:, 0]) ** 2 + (Y[..., None] - pts[:, 1]) ** 2))
            ds = np.sort(dd, axis=-1)
            h -= 0.04 * np.clip(1 - (ds[..., 1] - ds[..., 0]) / 0.07, 0, 1)
        if kind == "mud" and v == 2:                                             # 轍(車輪の溝)
            h -= 0.07 * np.exp(-((Y - 0.55) / 0.13) ** 2) - 0.0 * X
            h -= 0.07 * np.exp(-((Y + 0.55) / 0.13) ** 2)
        if kind == "humus":                                                      # 落ち葉の盛り上がり
            h += 0.03 * np.clip(_noise_dir(rng, 9)(np.stack([X, Y, X * 0 + v], -1).reshape(-1, 3) * 2.5).reshape(X.shape) - 0.2, 0, 1)
        if lod == "hi":
            from .lib_rock_geo import _fbm
            P3 = np.stack([X.ravel(), Y.ravel(), np.full(X.size, v * 0.7)], -1)
            h = h + amp * 0.16 * _fbm(P3, rng, 0.5, 0.04, kind in ("scoria", "masa", "clay")).reshape(X.shape)       # 土の粒・小石の凹凸
            h = h + amp * 0.03 * _fbm(P3, rng, 0.06, 0.03, True, 3).reshape(X.shape)
        th = np.arctan2(Y, X)
        lim = 1.5 * (0.72 + 0.14 * np.sin(3 * th + 2 * v) + 0.1 * np.sin(5 * th + 1))     # 縁は不規則な円形(四角いタイルに見えない)
        edge = np.clip((lim - np.hypot(X, Y)) / 0.4, 0, 1)                         # 縁を 0 へ(地面になじませる)
        h = (h - h.min()) * edge + 0.012                                           # 地面の下へ潜らない(最低でも地面より 1cm 上)
        rel = (h - h.min()) / max(float(np.ptp(h)), 1e-6)
        base = len(m.v)
        m.v.extend(zip(X.ravel(), Y.ravel(), h.ravel()))
        for i in range(n):
            for j in range(n):
                a = base + i * (n + 1) + j
                cx, cy = X[i:i + 2, j:j + 2].mean(), Y[i:i + 2, j:j + 2].mean()
                tc = math.atan2(cy, cx)
                if math.hypot(cx, cy) > 1.5 * (0.72 + 0.14 * math.sin(3 * tc + 2 * v) + 0.1 * math.sin(5 * tc + 1)):
                    continue
                m.f.append((a, a + 1, a + n + 2, a + n + 1))
                wet = kind == "mud" and rel[i:i + 2, j:j + 2].mean() < 0.3
                m.m.append("soil_mud_wet" if wet else f"soil_{kind}")
                m.uv.append(None)
        if kind == "scoria" and lod == "near":                                    # 小さな噴石
            from .lib_rock import rock_mesh
            for _ in range(10):
                rock_mesh(m, rng.uniform(0.03, 0.09), rng, 0.7, 4, 0.3, "soil_scoria", (rng.uniform(-1.2, 1.2), rng.uniform(-1.2, 1.2), 0.0), 0.3, 1)
    return fn


def _clod(kind, v, lod):
    def fn(m, W, H, rng):
        sub = 1 if lod == "near" else 0
        if sub not in _ICO:
            _ICO[sub] = _ico(sub)
        V, F = _ICO[sub]
        nz = _noise_dir(rng)
        R = (0.08, 0.13, 0.2)[v]
        P = V * (R * (1 + 0.3 * nz(V)))[:, None]
        P[:, 2] *= 0.6
        P[:, 2] -= 0.2 * R
        b = len(m.v)
        m.v.extend(map(tuple, P))
        for a, bb, c in F:
            m.f.append((b + a, b + bb, b + c))
            m.m.append(f"soil_{kind}")
            m.uv.append(None)
    return fn


for _k in SOILS:
    for _v in range(3):
        for _lod in ("near", "far", "hi"):
            _s = {"near": "", "far": "_far", "hi": "_hi"}[_lod]
            reg(f"soil_{_k}_patch_{_v}{_s}", _patch(_k, _v, _lod), W=3.0, H=0.15, cat="土", lod=_lod, kind=_k)
            if _lod != "hi":
                reg(f"soil_{_k}_clod_{_v}{_s}", _clod(_k, _v, _lod), W=0.4, H=0.15, cat="土", lod=_lod, kind=_k)
_ = math
