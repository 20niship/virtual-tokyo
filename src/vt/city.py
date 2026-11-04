"""全シーン生成: 領域を一括で作ってからタイルに分配(継ぎ目・重複を避ける)。タイルごとにUSDを書き、レンダは近傍だけ読む。"""
import math
import pickle
import time
from collections import defaultdict
from pathlib import Path

from shapely.geometry import box

from . import bridges, furniture, ground, rails_c, roads, vegetation
from .assemble import build_building
from .geo import to_local
from .layers import load, load_extra
from .modules.geom import Mesh
from .world import Terrain

ROOT = Path(__file__).resolve().parents[2]
CENTER_LL = (139.7745, 35.6265)


class Tiler:
    def __init__(self, bounds, size):
        self.x0, self.y0, x1, y1 = bounds
        self.size = size
        self.nx = int(math.ceil((x1 - self.x0) / size))
        self.ny = int(math.ceil((y1 - self.y0) / size))

    def idx(self, x, y):
        return (min(max(int((x - self.x0) // self.size), 0), self.nx - 1), min(max(int((y - self.y0) // self.size), 0), self.ny - 1))

    def box(self, i, j):
        return box(self.x0 + i * self.size, self.y0 + j * self.size, self.x0 + (i + 1) * self.size, self.y0 + (j + 1) * self.size)

    def all(self):
        return [(i, j) for i in range(self.nx) for j in range(self.ny)]


def split_mesh(mesh, tiler):
    """面を重心でタイルへ振り分ける(頂点は面ごとに複製されているので単純コピー)"""
    out = defaultdict(Mesh)
    uv = mesh.uv if len(mesh.uv) == len(mesh.f) else [None] * len(mesh.f)
    for f, m, u in zip(mesh.f, mesh.m, uv):
        pts = [mesh.v[i] for i in f]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        out[tiler.idx(cx, cy)].poly(pts, m, u)
    return out


def split_insts(insts, tiler):
    out = defaultdict(list)
    for i in insts:
        out[tiler.idx(i.x, i.y)].append(i)
    return out


def build_world(half=900, tile=450, seed=3, log=print, center_ll=CENTER_LL, mode="hybrid", use_cache=True, district=None):
    """領域(中心±half[m]の正方形)の全要素を生成して dict で返す"""
    t0 = time.time()
    lap = lambda s: log(f"  [{time.time() - t0:5.0f}s] {s}")
    cache = ROOT / f"out/cache/base_{round(center_ll[0], 4)}_{round(center_ll[1], 4)}_{int(half)}_{seed}.pkl"
    if use_cache and cache.exists():
        with open(cache, "rb") as fh:
            B = pickle.load(fh)
        L, X, W, g, r, t, edges, info, furn, veg, wires = (B[k] for k in ("L", "X", "W", "g", "r", "t", "edges", "info", "furn", "veg", "wires"))
        area, land, T, c = W["area"], W["land"], W["zf"], W["center"]
        lap("base loaded from cache")
    else:
        L = load()
        X = load_extra()
        bridges.install(L)
        c = to_local(*center_ll)
        area = box(c[0] - half, c[1] - half, c[0] + half, c[1] + half)
        T = Terrain()
        land = ground.land_polygon(L, area)
        W = dict(area=area, land=land, zf=T, center=c)
        lap("loaded + land")
        g = ground.build_ground(L, W)
        lap("ground")
        r, edges, info = roads.build_roads(L, W)
        lap("roads")
        W["edges"] = edges
        t, rail_insts = rails_c.build_rail(L, W)
        lap("rail")
        furn = furniture.build_furniture(L, W, edges, info, roads.CFG, X=X) + list(roads.elevated_roads.insts) + rail_insts
        wires = furniture.build_furniture.wires
        lap("furniture")
        veg = vegetation.build_vegetation(L, X, W, edges, info, roads.CFG, seed=seed, avoid=furn)
        lap("vegetation")
        if use_cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(cache, "wb") as fh:
                    pickle.dump(dict(L=L, X=X, W=W, g=g, r=r, t=t, edges=edges, info=info, furn=furn, veg=veg, wires=wires), fh, protocol=4)
            except Exception as ex:       # ponytail: pickle不可の要素があればキャッシュ無しで続行
                log(f"cache skipped: {ex!r}")
    log(f"world base {time.time() - t0:.0f}s: faces g/r/t={len(g.f)}/{len(r.f)}/{len(t.f)} furn={len(furn)} veg={len(veg)}")
    feats = [f for f in L["buildings"] if area.contains(f.geom.centroid)] if mode in ("osm", "hybrid") else []
    props = []
    if mode in ("infill", "hybrid"):
        from . import blocks
        wd = dict(area=area, land=land, info=info, L=L, edges=edges, T=T, center=c)
        if district:                      # 田舎/ロードサイド/工場/コンビナート等の地区タイプ(未指定=東京の既定)
            from . import district as dist
            inf = dist.infill(wd, district, "infill" if mode == "hybrid" else mode, seed=seed + 4, log=log)
        else:
            inf = blocks.infill(wd, mode, seed=seed + 4, log=log)
        feats += inf["features"]
        g.add(inf["pads"])
        props += inf["props"]
    builts = []
    for f in feats:
        if area.contains(f.geom.centroid):
            b = build_building(f)
            if b:
                z = T(f.geom.centroid.x, f.geom.centroid.y)
                for i in b.insts:
                    i.z += z
                b.shell.v = [(x, y, zz + z) for x, y, zz in b.shell.v]
                b.meta["foot"] = f.geom
                builts.append(b)
    log(f"buildings {len(builts)} insts={sum(len(b.insts) for b in builts)} ({time.time() - t0:.0f}s)")
    return dict(L=L, X=X, W=W, area=area, land=land, g=g, r=r, t=t, wires=wires, edges=edges, info=info, furn=furn, veg=veg,
                builts=builts, props=props, tiler=Tiler(area.bounds, tile), center=c, T=T)
