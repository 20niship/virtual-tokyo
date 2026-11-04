"""小領域スポットを生成→地面/空中視点でレンダ(追加モジュールの確認と改善の反復用)。
uv run python scripts/build_extra.py <spot> [--round N] [--per 2] [--samples 24] [--no-render] [--radius 150]
出力: out/render/extra/<spot>/round<N>/*.png"""
import argparse
import time
from pathlib import Path

from vt import city, city_render, expwy_view, spots_extra
from vt.city_render import View

ap = argparse.ArgumentParser()
ap.add_argument("spot")
ap.add_argument("--round", type=int, default=1)
ap.add_argument("--per", type=int, default=2)
ap.add_argument("--samples", type=int, default=24)
ap.add_argument("--radius", type=float, default=170)
ap.add_argument("--no-render", action="store_true")
ap.add_argument("--no-cache", action="store_true")
ap.add_argument("--only", default="")
a = ap.parse_args()

lon, lat, district, half = spots_extra.SPOTS[a.spot]
t0 = time.time()
w = city.build_world(half=half, tile=half * 2, center_ll=(lon, lat), mode="infill", district=district, use_cache=not a.no_cache, seed=11)
print(f"world {time.time() - t0:.0f}s buildings={len(w['builts'])} props={len(w['props'])} furn={len(w['furn'])}")
if a.no_render:
    raise SystemExit
tiles = city_render.make_tiles(w)
city_render.OUT = Path(__file__).resolve().parents[1] / f"out/render/extra/{a.spot}/round{a.round}"
c, T = w["center"], w["T"]
z0 = T(*c)
views = city_render.pick_ground_views(w, per=a.per, margin=30)
if a.spot.startswith("expwy"):
    views = expwy_view.views(w, per=a.per) + views[:2]
views += [View("a_oblique", (c[0] - half * 0.8, c[1] - half * 0.8, z0 + 70), (c[0], c[1], z0 + 4), 30, "aerial"),
          View("a_oblique2", (c[0] + half * 0.8, c[1] - half * 0.7, z0 + 45), (c[0], c[1], z0 + 3), 32, "aerial"),
          View("a_top", (c[0], c[1], z0 + 330), (c[0], c[1], z0), 30, "aerial")]
if a.only:
    views = [v for v in views if v.name.startswith(a.only)]
for v in views:
    t1 = time.time()
    city_render.render_view(w, tiles, v, a.radius if v.kind != "aerial" else half * 2.2, samples=a.samples)
    print("rendered", v.name, f"{time.time() - t1:.0f}s")
city_render.contact_sheet([v.name for v in views], "sheet.jpg")
print("total", f"{time.time() - t0:.0f}s")
