"""詳細度プロファイル。far = 全域の現行 Document(低ポリ+法線ベイク、散布は間引き)/ near = 数百 m のスポットを 0.5m 格子へ細分化し、
微細な起伏(岩の角・層理・礫・土の起伏)を足して、木・低木・岩・土・砂利の散布を高密度にしたローカル Document。"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from shapely.geometry import box

from .core.document import Document
from .core.grid import Grid
from .core.node import get_node
from .core.rng import node_rng
from .gen.noise import make_noise
from .masks.terrain import slope_aspect

# near の散布ステップ(far のステップより密)。density は間隔 r を 1/sqrt(density) にする倍率
NEAR_STEPS = [
    ("scatter.trees", dict(r_m=3.4, exclude=["river", "lake", "road", "portal", "village_pads"])),
    ("scatter.shrubs", dict(r_m=0.9, shrub_density=0.2, grass_density=0.9, scale_mul=1.1, forest_grass=0.7)),
    ("scatter.rocks", dict(cliff_deg=54, density=4.0, boulder_density=0.12)),
    ("scatter.ground", dict(density=3.0)),
    ("scatter.floor", dict(density=1.6)),
]
STRATA = np.array([0.15, 0.5, 1.0, 0.6, 0.3])        # 岩種ごとの層理の強さ [花崗岩, 安山岩, 砂岩, 石灰岩, 凝灰岩]
STEP = np.array([2.5, 1.4, 0.7, 1.1, 1.0])           # 層理の段の間隔[m]


def _smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def micro_relief(grid, rng, rock, soil, geo, z, slope):
    """微細な起伏[m]。rock/soil は 0..1 の重み。岩: 尖った凹凸(リッジ)+ 地質ごとの層理の段 + 細かい粒。土・草・落葉: 小さなこぶ"""
    crag = make_noise(grid, rng, "ridged", 7.0, 4, 2.0, 0.5, 0.3)
    grit = make_noise(grid, rng, "fbm", 0.8, 3, 2.0, 0.5)
    hum = make_noise(grid, rng, "fbm", 2.6, 3, 2.0, 0.5)
    steep = np.clip(slope / 35.0, 0.25, 1.0)
    step = STEP[geo]
    t = z / step
    stair = (np.floor(t) + _smooth((t - np.floor(t)) * 1.5 - 0.25) - t) * step * STRATA[geo]      # 段(棚): 階段状 - 元の線形
    rk = np.maximum(rock, np.clip((slope - 28) / 15.0, 0, 1) * 0.85)           # 急斜面は土の下の岩が出る
    d = rk * steep * (1.5 * (crag - 0.45) + 0.6 * stair) + (rk * 0.09 + soil * 0.035) * (grit - 0.5) * 2 + soil * 0.25 * (hum - 0.5) * 2
    return d.astype(np.float32)


def make_near_doc(doc: Document, center, half=120.0, res=0.5, seed=0, scatter=True) -> Document:
    g = doc.grid
    # 穴の縁を粗い格子のセル中心に合わせる(far メッシュとひび割れ無しでつながる)
    snap = lambda v, o: o + (round((v - o) / (2 * g.res)) * 2 + 0.5) * g.res            # 偶数番目の頂点(far を stride 2 にしても縁が合う)
    x0, y0 = snap(center[0] - half, g.x0), snap(center[1] - half, g.y0)
    n = int(round(2 * half / (2 * g.res))) * 2 * int(round(g.res / res))
    fg = Grid(n + 1, n + 1, res, x0 - res / 2, y0 - res / 2, g.crs)        # 頂点が x0..x0+2half に乗る(セル中心 = 頂点)
    X, Y = fg.xy()
    ci, cj = g.to_ij(X, Y)
    cubic = map_coordinates(doc.height, [cj, ci], order=3, mode="nearest")
    lin = map_coordinates(doc.height, [cj, ci], order=1, mode="nearest")
    edge = np.minimum.reduce([X - x0, x0 + n * res - X, Y - y0, y0 + n * res - Y])
    w = _smooth(edge / 10.0)                                               # 縁から 10m で 3 次補間へ(縁は粗いメッシュと同じ線形)
    h = w * cubic + (1 - w) * lin
    out = Document(fg, doc.seed, dict(doc.meta, detail="near", near_box=[x0, y0, x0 + n * res, y0 + n * res]))
    rs = lambda a, order=1: map_coordinates(a.astype(np.float32), [cj, ci], order=order, mode="nearest")
    L = doc.layers
    nn = lambda a: map_coordinates(a, [np.rint(cj).astype(int).clip(0, g.ny - 1), np.rint(ci).astype(int).clip(0, g.nx - 1)], order=0)
    for k in ("canopy", "soil_depth", "twi", "moss", "lichen", "water_depth"):
        if k in L:
            out.layers[k] = rs(L[k])
    for k in ("biome", "geology", "soil_type", "lake"):
        if k in L:
            out.layers[k] = nn(L[k])
    sp = {k: rs(L["splat_" + k]) for k in ("grass", "litter", "rock", "scree", "soil", "alpine") if "splat_" + k in L}
    rng = node_rng(seed, "near.micro")
    geo = out.layers.get("geology", np.zeros(fg.shape, np.uint8)).astype(int)
    s0, _ = slope_aspect(h, res)
    rockw = np.clip(sp.get("rock", 0 * h) + 0.5 * sp.get("scree", 0 * h), 0, 1) if sp else np.zeros(fg.shape)
    soilw = np.clip(sp.get("soil", 0 * h) + sp.get("litter", 0 * h) + sp.get("grass", 0 * h), 0, 1) if sp else np.ones(fg.shape)
    d = micro_relief(fg, rng, rockw, soilw, geo, h, s0) * w
    if "road" in L:                                                        # 路盤は水平なまま(微細起伏を路面から 1m 離れるまで消す)
        from scipy.ndimage import distance_transform_edt
        rd = nn(L["road"]) > 0
        out.layers["road"] = rd.astype(np.float32)
        if rd.any():
            d = d * np.clip((distance_transform_edt(~rd) * res - 1.0) / 6.0, 0, 1)
    out.set("height", h + d)
    slope, aspect = slope_aspect(out.height, res)
    out.set("slope", slope)
    out.set("aspect", aspect)
    if sp:                                                                 # 細かい傾斜で岩・礫の重みを補正
        sp["rock"] = np.clip(sp["rock"] + np.clip((slope - 48) / 12, 0, 1) * 0.6, 0, 1)
        sp["scree"] = np.clip(sp["scree"] + np.clip((slope - 30) / 8, 0, 1) * np.clip((52 - slope) / 8, 0, 1) * 0.4, 0, 1)
        tot = sum(sp.values())
        for k, v in sp.items():
            out.set("splat_" + k, gaussian_filter(v / tot, 0.6))
    if "river" in L:
        out.layers["river"] = nn(L["river"])
    out.vectors = {}
    bx = box(x0, y0, x0 + n * res, y0 + n * res)
    for k, v in doc.vectors.items():                                       # 範囲内に切り取る(範囲外の川が near の標高で水面になるのを防ぐ)
        keep = []
        for geom, pr in v:
            ig = geom.intersection(bx)
            if ig.is_empty:
                continue
            keep += [(part, pr) for part in getattr(ig, "geoms", [ig])]
        out.vectors[k] = keep
    if scatter:
        run_steps(out, NEAR_STEPS)
    return out


def run_steps(doc, steps, seed=None):
    seed = doc.seed if seed is None else seed
    for i, (name, params) in enumerate(steps):
        nd = get_node(name)(**params)
        nd.run(doc, node_rng(seed, f"near.{name}.{i}"))
    return doc


def clear_view(doc, loc, tgt, corridor=4.5, length=25.0):
    """撮影位置の周りと視線の廊下から、木を除く(カメラが幹や葉の中に入らないように)。低木・草は位置の近傍 1.5m、岩・地面パッチは 5m(大きな岩は 16m)だけ除く"""
    p0, p1 = np.array(loc[:2], float), np.array(tgt[:2], float)
    d = p1 - p0
    d = d / max(np.linalg.norm(d), 1e-9)
    for k, s in doc.scatter.items():
        q = s["pos"][:, :2].astype(float) - p0
        t = np.clip(q @ d, 0, length)
        dist = np.linalg.norm(q - t[:, None] * d, axis=1)
        near_cam = np.linalg.norm(q, axis=1)
        big = np.array([("cliff" in str(n) or "column" in str(n) or "outcrop" in str(n)) for n in s["assets"]])[s["kind"]] if k == "rocks" else None
        bad = ((near_cam < 5.0) | (big & (near_cam < 16.0))) if k == "rocks" else (near_cam < 5.0) if k == "ground" else (near_cam < 1.5) if k == "shrubs" else ((near_cam < 4.5) | ((dist < corridor) & (q @ d > 0) & (q @ d < length)))
        doc.scatter[k] = {f: (v[~bad] if f != "assets" else v) for f, v in s.items()}
