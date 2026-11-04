"""生活感/車/人/路面の近接ビューを自動選定してレンダ: realismB_views.py SPOT ROUND [--only feat,..] [--samples N] → out/render/realismB/SPOT/roundROUND/"""
import math
import random
import sys
import time
from pathlib import Path

from vt import city, city_props, city_render
from vt.city_render import View

sys.path.insert(0, str(Path(__file__).parent))
SPOTS = {"odaiba_intersection": (139.7762, 35.6272), "west_intersection": (139.7478, 35.6448), "west_highrise": (139.7468, 35.6425), "yurikamome": (139.77141, 35.62589),
         "shuto": (139.7585, 35.6410)}
FEAT = {"vend": "lf_vend_", "ac": "lf_ac_", "pots": "lf_pot_", "bike": "lf_bike_", "garb": "lf_garb_", "nobori": "lf_nobori", "chou": "lf_chou", "stand": "lf_stand_", "scaf": "lf_scaf_bay",
        "hoard": "lf_hoard_", "barri": "lf_barri_", "mail": "lf_mail_", "down": "lf_down_", "hyd": "lf_hyd_", "pole": "lf_pole_banner", "planter": "lf_planter_", "chip": "lf_curb_chip",
        "weed": "veg_grass_", "cars": "car_", "peds": "pedx_", "cyc": "cyclist_"}
spot, rnd = sys.argv[1], sys.argv[2]
only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else list(FEAT) + ["low"]
samples = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 32
city_render.OUT = Path(__file__).resolve().parents[1] / f"out/render/realismB/{spot}/round{rnd}"
t0 = time.time()
w = city.build_world(200, 200, center_ll=SPOTS[spot], mode="hybrid", log=lambda s: None)
w["props"] = city_props.build_props(w)
tiles = city_render.make_tiles(w)
print("built", f"{time.time() - t0:.0f}s", "props", len(w["props"]), "overlay", w.get("overlay_stats"))
T = w["T"]
rng = random.Random(5)
allp = [i for i in w["props"]] + [i for lst in tiles["furn"].values() for i in lst]
cx0, cy0 = w["center"]


def front(i):
    return -math.sin(i.rot), math.cos(i.rot)


def view_for(name, i, dist, h, lens=26, side=0.0):
    fx, fy = front(i)
    px, py = i.x + fx * dist - fy * side, i.y + fy * dist + fx * side
    z = T(i.x, i.y)
    return View(name, (px, py, z + h), (i.x, i.y, z + 0.9), lens, "ground")


def shoot(v, radius=70):
    for dx, dy in [(0, 0), (0, 0)]:
        city_render.render_view(w, tiles, v, radius, samples=samples, dmin=0.0)
        break
    print("rendered", v.name, f"{time.time() - t0:.0f}s")


made = []
for f in only:
    if f == "low":                                                                       # 低い視点で路面を見る
        es = [e for e in w["edges"] if e.kind == "drive" and e.level == 0 and e.prof is not None and e.line.length > 60 and w["area"].buffer(-20).contains(e.line.interpolate(e.line.length * 0.5))]
        rng.shuffle(es)
        for k, e in enumerate(es[:3]):
            s = e.line.length * rng.uniform(0.25, 0.5)
            a, b = e.line.interpolate(s), e.line.interpolate(s + 8)
            d = math.hypot(b.x - a.x, b.y - a.y) or 1
            t = e.prof.lane_w * 0.5 + (e.prof.median / 2 if not e.prof.oneway else 0)
            cx, cy = a.x - (b.y - a.y) / d * t, a.y + (b.x - a.x) / d * t
            z = T(cx, cy)
            v = View(f"low_{k}", (cx, cy, z + 0.9), (cx + (b.x - a.x) / d * 14, cy + (b.y - a.y) / d * 14, z + 0.1), 28, "ground")
            shoot(v)
            made.append(v.name)
        continue
    pat = FEAT[f]
    cand = [i for i in allp if i.name.startswith(pat) and w["area"].buffer(-14).contains(__import__("shapely.geometry", fromlist=["Point"]).Point(i.x, i.y))]
    rng.shuffle(cand)
    if f in ("cars", "peds", "cyc"):
        cand = cand[:2]
        for k, i in enumerate(cand):
            fx, fy = front(i)
            v = view_for(f"{f}_{k}", i, 5.0 if f != "cars" else 9.0, 1.5 if f != "cars" else 1.7, 30, 1.0)
            shoot(v, 60)
            made.append(v.name)
        continue
    for k, i in enumerate(cand[:2]):
        d = 7.0 if f in ("scaf", "hoard", "planter", "bike", "pole") else 5.0
        v = view_for(f"{f}_{k}", i, d, 1.7 if f != "pole" else 2.5, 30 if f in ("scaf", "pole") else 28, 0.8)
        shoot(v, 60)
        made.append(v.name)
if made:
    for k in range(0, len(made), 6):
        city_render.contact_sheet(made[k:k + 6], f"sheet_{k // 6}.jpg")
print("total", f"{time.time() - t0:.0f}s")
