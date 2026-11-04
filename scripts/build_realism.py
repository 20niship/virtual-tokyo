"""リアリズム検証: 小領域スポットを生成→地面/空中レンダ。時間帯(day/dusk/night)切替可。
uv run python scripts/build_realism.py <spot> [--round N] [--time day|dusk|night] [--samples 24] [--only g_]
spot は build_city.py の SPOTS と spots_extra.SPOTS の両方から選べる。出力: out/render/realismA/<spot>[_time]/round<N>/"""
import argparse
import importlib.util
import time
from pathlib import Path

from vt import city, city_render, spots_extra
from vt.city_render import View

ROOT = Path(__file__).resolve().parents[1]
_sp = importlib.util.spec_from_file_location("_bc_consts", ROOT / "scripts/_spots.py")
_m = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_m)
SPOTS, PRIORITY = _m.SPOTS, _m.PRIORITY

ap = argparse.ArgumentParser()
ap.add_argument("spot")
ap.add_argument("--round", default="1")
ap.add_argument("--time", default="day", choices=["day", "dusk", "night"])
ap.add_argument("--samples", type=int, default=24)
ap.add_argument("--radius", type=float, default=170)
ap.add_argument("--per", type=int, default=2)
ap.add_argument("--only", default="")
a = ap.parse_args()

if a.spot in spots_extra.SPOTS:
    lon, lat, district, half = spots_extra.SPOTS[a.spot]
    kw = dict(mode="infill", district=district, seed=11)
else:
    (lon, lat), district, half = SPOTS[a.spot], None, 200
    kw = dict(mode="hybrid")
t0 = time.time()
w = city.build_world(half=half, tile=half * 2, center_ll=(lon, lat), **kw)
print(f"world {time.time() - t0:.0f}s buildings={len(w['builts'])} props={len(w['props'])}")
tiles = city_render.make_tiles(w)
city_render.OUT = ROOT / f"out/render/realismA/{a.spot}{'' if a.time == 'day' else '_' + a.time}/round{a.round}"
city_render.TIME = a.time
c, T = w["center"], w["T"]
z0 = T(*c)
gv = city_render.pick_ground_views(w, per=a.per, margin=30)
pri = PRIORITY.get(a.spot, ["intersection", "roadway", "sidewalk", "alley", "park", "plaza"])
gv = sorted(gv, key=lambda v: (pri.index(v.kind) if v.kind in pri else 99, v.name))[:5]
if a.spot.startswith("expwy"):
    from vt import expwy_view
    gv = expwy_view.views(w, per=a.per) + gv[:2]
av = [View("a_oblique", (c[0] - half * 0.8, c[1] - half * 0.8, z0 + 70), (c[0], c[1], z0 + 4), 30, "aerial"),
      View("a_oblique2", (c[0] + half * 0.8, c[1] - half * 0.7, z0 + 45), (c[0], c[1], z0 + 3), 32, "aerial")]
views = gv + av
if a.only:
    views = [v for v in views if v.name.startswith(a.only)]
for v in views:
    t1 = time.time()
    city_render.render_view_checked(w, tiles, v, a.radius if v.kind != "aerial" else half * 2.2, samples=a.samples, min_luma=22.0 if a.time == "day" else 6.0)
    print("rendered", v.name, f"{time.time() - t1:.0f}s")
city_render.contact_sheet([v.name for v in views], "sheet.jpg")
print("total", f"{time.time() - t0:.0f}s")
