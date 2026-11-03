"""フェーズB: 地面 + 道路 + 線路(ゆりかもめ/モノレール/首都高) の生成 → USD → レンダ。
uv run python scripts/build_phase_b.py [--no-render]"""
import math
import sys
from collections import defaultdict
from pathlib import Path

from shapely.geometry import Point

from vt import furniture, ground, rail, render, roads, usd_out
from vt.assemble import build_building
from vt.geo import to_local
from vt.layers import load
from vt.world import Terrain

OUT = Path(__file__).resolve().parents[1] / "out/render"
OUT.mkdir(parents=True, exist_ok=True)
CENTER_LL = (139.7745, 35.6265)
RADIUS = 750

L = load()
c = to_local(*CENTER_LL)
area = Point(c).buffer(RADIUS)
T = Terrain()
land = ground.land_polygon(L, area)
W = dict(area=area, land=land, zf=T, center=c)
g = ground.build_ground(L, W)
r, edges, info = roads.build_roads(L, W)
t = rail.build_rail(L, W)
furn = furniture.build_furniture(L, W, edges, info, roads.CFG)
usd_out.write_all_modules(log=lambda s: None)
print("faces ground/roads/rail:", len(g.f), len(r.f), len(t.f), "furniture:", len(furn))
paths = [usd_out.write_furniture(furn), usd_out.write_world_mesh("ground", g), usd_out.write_world_mesh("roads", r), usd_out.write_world_mesh("rail", t)]
builts = [b for f in L["buildings"] if f.geom.centroid.within(area) for b in [build_building(f)] if b]
paths.insert(0, usd_out.write_buildings(builts))
usd_out.write_city(paths)
if "--no-render" in sys.argv:
    sys.exit()

# ---- 視点の自動選定 ----
deg = defaultdict(list)
for e in edges:
    if e.kind == "drive" and e.level == 0:
        deg[e.a].append(e); deg[e.b].append(e)
import os
DEBUG = bool(os.environ.get("DEBUG"))
el_union = __import__("shapely.ops", fromlist=["unary_union"]).unary_union([e.line for e in edges if e.level > 0] + [f.geom for f in L["rail"] if f.tags.get("name") in ("ゆりかもめ", "東京モノレール")])
cand = [(sum(x.prof.half for x in v), k, v) for k, v in deg.items() if len(v) >= 4 and area.buffer(-80).contains(Point(k)) and Point(k).distance(el_union) > 45]
cand.sort(key=lambda x: -x[0])
inter = cand[0] if cand else sorted([(sum(x.prof.half for x in v), k, v) for k, v in deg.items() if len(v) >= 3 and area.buffer(-80).contains(Point(k))], key=lambda x: -x[0])[0]
IX = inter[1]
print("intersection", IX, len(inter[2]))


def scene(samples=64, sun=(0.5, -0.45, 0.65), with_buildings=True, res=(1920, 1080)):
    if DEBUG:
        samples, with_buildings, res = 24, False, (1280, 720)
    render.init_scene(res, samples, sun_dir=sun)
    render.add_mesh_object("ground", g); render.add_mesh_object("roads", r); render.add_mesh_object("rail", t)
    render.add_mesh_object("water", ground.water_mesh(W))
    render.add_instances([i for i in furn if math.dist((i.x, i.y), IX) < 330])
    if with_buildings:
        render.add_buildings([b for b in builts if math.dist((b.insts[0].x, b.insts[0].y), IX) < 330])


def shot(name, cam, tgt, lens, **kw):
    if ONLY and not name.startswith(ONLY):
        return
    scene(**kw)
    render.add_camera(cam, tgt, lens)
    render.render(OUT / name)


zc = T(*IX)
e0 = inter[2][0]
arm = e0.line if e0.a == IX else type(e0.line)(list(e0.line.coords)[::-1])
p25 = arm.interpolate(min(30, arm.length / 2)); p0 = arm.interpolate(1)
dx, dy = p25.x - p0.x, p25.y - p0.y
d = math.hypot(dx, dy); dx, dy = dx / d, dy / d
ONLY = os.environ.get("ONLY", "")
shot("road_intersection.png", (IX[0] + dx * 38 + dy * 2, IX[1] + dy * 38 - dx * 2, zc + 3.2), (IX[0], IX[1], zc + 0.5), 28, samples=96)
shot("road_topdown.png", (IX[0] + dx * 18, IX[1] + dy * 18, zc + 34), (IX[0], IX[1], zc), 40, samples=96, with_buildings=False)
shot("aerial_world.png", (c[0] - 520, c[1] - 560, 260), (c[0] + 60, c[1] + 40, 8), 32, samples=72)
# ゆりかもめ高架: 軌道を結合し、陸上の点を選んで側方から見上げる
from shapely.ops import linemerge, unary_union as _uu
ym = linemerge(_uu([f.geom for f in L["rail"] if f.tags.get("name") == "ゆりかもめ"]).intersection(area.buffer(-120)))
cands = [ym] if ym.geom_type == "LineString" else sorted(getattr(ym, "geoms", []), key=lambda g: -g.length)
done = False
for ln in cands:
    for fr in (0.5, 0.4, 0.6, 0.3, 0.7):
        yp, yq = ln.interpolate(fr, normalized=True), ln.interpolate(min(ln.length, ln.length * fr + 3))
        tx, ty = yq.x - yp.x, yq.y - yp.y
        d = math.hypot(tx, ty) or 1; tx, ty = tx / d, ty / d
        for side in (1, -1):
            cam = (yp.x - ty * side * 26 - tx * 18, yp.y + tx * side * 26 - ty * 18)
            if land.contains(Point(cam)):
                zz = T(yp.x, yp.y)
                shot("yurikamome.png", (cam[0], cam[1], zz + 2.2), (yp.x, yp.y, zz + 11), 28, samples=96)
                done = True
                break
        if done:
            break
    if done:
        break
print("yurikamome shot:", done)
# 護岸: 水側から見る
from shapely.geometry.polygon import orient as _orient
big = max(land.geoms, key=lambda x: x.area) if land.geom_type != "Polygon" else land
ring = _orient(big, 1.0).exterior
for fr in (0.15, 0.3, 0.45, 0.6, 0.75):
    qp = ring.interpolate(fr, normalized=True); qq = ring.interpolate(min(ring.length, ring.length * fr + 2))
    tx, ty = qq.x - qp.x, qq.y - qp.y
    d = math.hypot(tx, ty) or 1; tx, ty = tx / d, ty / d
    ox, oy = ty, -tx          # 水側
    cam = Point(qp.x + ox * 16 - tx * 10, qp.y + oy * 16 - ty * 10)
    if area.buffer(-60).contains(qp) and not land.buffer(1).contains(cam):
        shot("quay.png", (cam.x, cam.y, 2.4), (qp.x, qp.y, T(qp.x, qp.y)), 30, samples=64, with_buildings=False)
        break

# ---- 道路ファニチャの接写(信号/街灯/標識) ----
def furn_shot(prefix, name, dist, lens, side=3.0, skip=0, samples=96, with_buildings=False, sel=None):
    c0 = [i for i in furn if i.name.startswith(prefix) and area.buffer(-90).contains(Point(i.x, i.y)) and (sel is None or sel(i))]
    if len(c0) <= skip:
        return
    i = c0[skip]
    fx, fy = -math.sin(i.rot), math.cos(i.rot)
    tz = i.z if (prefix.startswith(("sigv", "sigp", "sign_"))) else i.z + 4.5
    cx, cy = i.x + fx * dist + fy * side, i.y + fy * dist - fx * side
    shot(name, (cx, cy, T(cx, cy) + 1.8), (i.x, i.y, tz), lens, samples=samples, with_buildings=with_buildings)


furn_shot("sigv_h3_led", "furn_signal_led.png", 14, 50, 3.0)
furn_shot("sigv_h3_old", "furn_signal_old.png", 14, 50, 3.0)
furn_shot("sigv_h3_slim", "furn_signal_slim.png", 14, 50, 3.0)
furn_shot("light_cobra", "furn_light.png", 18, 40, 6.0)
furn_shot("sign_reg_speed", "furn_sign.png", 9, 45, 2.0)
furn_shot("sigp_led", "furn_signal_ped.png", 8, 45, 2.0)
furn_shot("sign_gd_", "furn_sign_guide.png", 12, 40, 3.0)
