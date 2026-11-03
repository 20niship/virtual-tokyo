"""フェーズC: 高架道路(首都高)・レインボーブリッジ・ゆりかもめ/モノレールの詳細化 → USD → レンダ。
uv run python scripts/build_phase_c.py [--no-render]   環境変数: DEBUG=1(低品質/高速) ONLY=<ショット名>"""
import math
import os
import sys
from pathlib import Path

from shapely.geometry import Point

from vt import bridges, ground, rails_c, render, roads, usd_out
from vt.assemble import Built
from vt.layers import load
from vt.modules.geom import Mesh
from vt.modules.library import REG, get
from vt.world import Terrain

OUT = Path(__file__).resolve().parents[1] / "out/render"
OUT.mkdir(parents=True, exist_ok=True)
DEBUG = bool(os.environ.get("DEBUG"))
ONLY = os.environ.get("ONLY", "")
NO_RENDER = "--no-render" in sys.argv

L = load()
RB = bridges.install(L)
assert RB is not None, "レインボーブリッジが見つからない"
T = Terrain()


def make_scene(center, radius, name):
    area = Point(center).buffer(radius)
    land = ground.land_polygon(L, area)
    W = dict(area=area, land=land, zf=T, center=center)
    g = ground.build_ground(L, W)
    r, edges, *_ = roads.build_roads(L, W)
    W["edges"] = edges
    bi = list(roads.elevated_roads.insts)                      # 橋脚/ハンガー金具などのモジュールInst
    t, ti = rails_c.build_rail(L, W)
    insts = bi + ti
    print(name, "faces ground/roads/rail:", len(g.f), len(r.f), len(t.f), "insts", len(insts))
    return W, g, r, t, insts


def write_usd(name, W, r, t, insts):
    p1 = usd_out.write_world_mesh(f"{name}_roads", r)
    p2 = usd_out.write_world_mesh(f"{name}_rail", t)
    for n in sorted({i.name for i in insts} | {k for k, v in REG.items() if v["cat"] in ("橋", "駅")}):
        usd_out.write_module(n, get(n), REG[n])
    b = Built(9000 + (1 if name == "bridge" else 2), insts, Mesh(), dict(style="bridge", floors=0, height=0.0, bvar=0.5))
    p3 = usd_out.write_buildings([b], usd_out.OUTDIR / f"{name}_modules.usda")
    return [p1, p2, p3]


def add_insts(insts):
    import bpy
    cache, col = {}, bpy.context.scene.collection
    for i in insts:
        me = cache.get(i.name) or cache.setdefault(i.name, render.mesh_to_bpy(i.name, get(i.name)))
        o = bpy.data.objects.new(i.name, me)
        o.location = (i.x, i.y, i.z); o.rotation_euler = (0, 0, i.rot); o.scale = (i.sx, i.sy, i.sz)
        o["bvar"] = 0.5
        col.objects.link(o)


def shot(name, scene, cam, tgt, lens, samples=72):
    if ONLY and ONLY != name:
        return
    W, g, r, t, insts = scene
    s = 24 if DEBUG else samples
    render.init_scene((1280, 720) if DEBUG else (1920, 1080), s, sun_dir=(0.5, -0.45, 0.65))
    render.add_mesh_object("ground", g); render.add_mesh_object("roads", r); render.add_mesh_object("rail", t)
    render.add_mesh_object("water", ground.water_mesh(W))
    add_insts(insts)
    render.add_camera(cam, tgt, lens)
    render.render(OUT / f"{name}.png")


# ---- シーンA: レインボーブリッジ ----
mid = RB.at(RB.Lc / 2)
sceneA = make_scene((mid[0], mid[1]), 950, "bridge")
paths = write_usd("bridge", *sceneA[0:1], sceneA[2], sceneA[3], sceneA[4])
if not NO_RENDER:
    u1 = RB.u_t[0]
    tx0, ty0, ux, uy = RB.at(RB.Lc / 2, -400)[0], RB.at(RB.Lc / 2, -400)[1], 0, 0
    # 空撮: 橋の側方(南側)・高所から
    cx, cy = RB.at(RB.Lc / 2, -520)[:2]
    shot("rainbow_aerial", sceneA, (cx, cy, 190), (mid[0], mid[1], 70), 30)
    # 主塔と橋全体を水面近くから
    px, py = RB.at(u1, -170)[:2]
    shot("rainbow_tower", sceneA, (px, py, 14), (RB.at(u1)[0], RB.at(u1)[1], 78), 28)
    # 橋上: 上段デッキから主塔を見る
    dx, dy = RB.at(u1 - 150, 5.6)[:2]
    shot("rainbow_deck", sceneA, (dx, dy, ZU + 3.0 if False else bridges.ZU + 3.2), (RB.at(u1 + 60, 5.6)[0], RB.at(u1 + 60, 5.6)[1], 70), 24)
    # 首都高の桁と橋脚(陸上の高架を下から): 陸上で高さ8m以上の高架エッジの中点を探す
    W = sceneA[0]
    for e in sorted((e for e in W["edges"] if e.kind == "drive" and e.level >= 2 and e.tags["highway"] == "motorway"), key=lambda e: -e.line.length):
        p = e.line.interpolate(0.5, normalized=True); q = e.line.interpolate(0.5, normalized=True)
        pa, pb = e.line.interpolate(e.line.length / 2 - 2), e.line.interpolate(e.line.length / 2 + 2)
        tx, ty = pb.x - pa.x, pb.y - pa.y
        d = math.hypot(tx, ty) or 1; tx, ty = tx / d, ty / d
        cam = (p.x + ty * 26 - tx * 14, p.y - tx * 26 - ty * 14)
        if W["land"].contains(p) and W["land"].contains(Point(cam)) and RB.w(p.x, p.y) < 0.05:
            zz = T(p.x, p.y)
            shot("shuto_girder", sceneA, (cam[0], cam[1], zz + 2.0), (p.x, p.y, zz + 13), 30)
            break

# ---- シーンB: ゆりかもめ台場駅周辺 ----
sx, sy = rails_c._XY["台場"]
sceneB = make_scene((sx, sy), 520, "daiba")
write_usd("daiba", sceneB[0], sceneB[2], sceneB[3], sceneB[4])
if not NO_RENDER:
    shot("station_daiba_ext", sceneB, (sx + 55, sy - 40, 6), (sx, sy, 14), 30)
    shot("station_daiba_platform", sceneB, (sx + 14, sy - 12, 17), (sx - 22, sy + 10, 14), 26)

# ---- シーンC: 東京モノレール 天王洲アイル ----
tx_, ty_ = rails_c._XY["天王洲アイル"]
sceneC = make_scene((tx_, ty_), 420, "tennozu")
if not NO_RENDER:
    shot("monorail_tennozu", sceneC, (tx_ + 40, ty_ - 30, 8), (tx_, ty_, 10), 32)
