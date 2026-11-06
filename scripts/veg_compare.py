"""植生の前後比較: 同じカメラで街路樹スポット/公園スポットを近景・見上げ・遠景でレンダし、樹木のtri数も出す。
uv run python scripts/veg_compare.py <tag> [street|park ...]   → out/render/veg/<tag>_<spot>_<view>.png
環境変数 SPP / VEG_SEASON(summer|autumn_y|...) / VEG_RADIUS / VEG_VIEWS(close,up,far,...)"""
import math
import os
import sys
from pathlib import Path

import bpy
from shapely.geometry import Point

from vt import bridges, furniture, ground, render, roads
from vt import tree_gen as tg
from vt import vegetation
from vt.layers import load, load_extra
from vt.modules.library import get
from vt.world import Terrain

OUT = Path(__file__).resolve().parents[1] / "out/render/veg"
OUT.mkdir(parents=True, exist_ok=True)
SPP = int(os.environ.get("SPP", 64))
SPOTS = {"street": (1575.0, -2175.0), "park": (3075.0, -1125.0)}   # 街路樹の多い所 / 大きな緑地(ローカル座標m)
TREES = ("ichou", "keyaki", "platanus", "sakura", "kusunoki", "shii", "tokaikaede", "hanamizuki", "kuromatsu")
tag = sys.argv[1]
spots = sys.argv[2:] or list(SPOTS)
R = float(os.environ.get("VEG_RADIUS", 170))
season = os.environ.get("VEG_SEASON", "summer")
want = os.environ.get("VEG_VIEWS", "close,up,far").split(",")

L, X = load(), load_extra()
bridges.install(L)
for spot in spots:
    c = SPOTS[spot]
    area = Point(c).buffer(R)
    T = Terrain()
    W = dict(area=area, land=ground.land_polygon(L, area), zf=T, center=c)
    g = ground.build_ground(L, W)
    r, edges, info = roads.build_roads(L, W)
    cfg = dict(roads.CFG, veg_season=season)
    furn = furniture.build_furniture(L, W, edges, info, roads.CFG, X=X)
    veg = vegetation.build_vegetation(L, X, W, edges, info, cfg, seed=3, avoid=furn)
    trees = [i for i in veg if i.name.split("_")[1] in TREES]
    tri = sum(tg.tris(get(i.name)) for i in trees)
    uniq = sum(tg.tris(get(n)) for n in {i.name for i in trees})
    print(f"[{tag}/{spot}] 樹木{len(trees)}本 全展開tri={tri:,} ユニークモジュールtri={uniq:,} 平均/本={tri // max(1, len(trees)):,} 全植栽inst={len(veg)}")
    # カメラ対象: 中心に近い大きめの樹木
    cand = sorted((i for i in trees if i.name.split("_")[2] in ("m", "l")), key=lambda i: math.dist((i.x, i.y), c))
    t = cand[0]
    print("target", t.name, round(t.x), round(t.y))
    zt = t.z
    zc = W["zf"](*c)
    views = {
        "close": ((t.x - 7.0, t.y - 4.0, zt + 1.7), (t.x, t.y, zt + 3.5), 35),
        "up": ((t.x - 2.5, t.y - 1.5, zt + 1.6), (t.x + 1.5, t.y + 1.0, zt + 9.0), 24),
        "far": ((c[0] - 85, c[1] - 85, zc + 9), (c[0], c[1], zc + 5), 32),
    }
    for vn in want:
        cam, tgt, lens = views[vn]
        render.init_scene((1400, 900), SPP, sun_dir=(0.5, -0.45, 0.65), realism=True)
        render.add_mesh_object("ground", g)
        render.add_mesh_object("roads", r)
        render.add_mesh_object("water", ground.water_mesh(W))
        render.add_instances([i for i in furn if math.dist((i.x, i.y), tgt[:2]) < 90])
        vv = [i for i in veg if math.dist((i.x, i.y), cam[:2]) < 150]
        render.add_instances_gn(vv, [((i.x * 12.9898 + i.y * 78.233) % 1.0) for i in vv])
        render.add_camera(cam, tgt, lens)
        bpy.context.scene.view_settings.exposure = render.estimate_exposure(0.17)
        p = OUT / f"{tag}_{spot}_{vn}.png"
        render.render(p)
        print("wrote", p)
