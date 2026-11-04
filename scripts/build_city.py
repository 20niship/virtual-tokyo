"""最終フェーズ: 領域の全要素(地面/道路/線路/橋/ファニチャ/植栽/全建物/小物)を生成 → タイル別USD(PointInstancer) → 検証レンダ。
uv run python scripts/build_city.py [--half 900] [--tile 450] [--no-usd] [--render] [--per 2] [--tag r1] [--no-props]"""
import argparse
import sys
import time
from collections import defaultdict

from vt import city, city_render, usd_out

SPOTS = {   # lon, lat
    "odaiba_intersection": (139.7762, 35.6272),
    "west_intersection": (139.7478, 35.6448),
    "west_highrise": (139.7468, 35.6425),
    "yurikamome": (139.77141, 35.62589),
    "shuto": (139.7585, 35.6410),
    "rainbow": (139.7606, 35.6374),         # 芝浦側の取り付け(アンカレイジ付近)
    "rainbow_pier": (139.7620, 35.6370),    # 橋脚・主塔付近(水上)

}
PRIORITY = {"yurikamome": ["station", "sidewalk", "roadway", "intersection"], "shuto": ["underdeck", "roadway", "sidewalk", "alley"],
            "rainbow": ["underdeck", "waterfront", "roadway", "sidewalk"], "rainbow_pier": ["waterfront", "underdeck", "roadway"], "west_highrise": ["sidewalk", "alley", "roadway", "intersection"]}
ap = argparse.ArgumentParser()
ap.add_argument("--half", type=float, default=900)
ap.add_argument("--tile", type=float, default=450)
ap.add_argument("--no-usd", action="store_true")
ap.add_argument("--render", action="store_true")
ap.add_argument("--per", type=int, default=2)
ap.add_argument("--no-props", action="store_true")
ap.add_argument("--samples", type=int, default=24)
ap.add_argument("--radius", type=float, default=260)
ap.add_argument("--only", default="")
ap.add_argument("--mode", default="hybrid", choices=["osm", "infill", "hybrid"], help="建物: OSMのみ/全自動(街区→ロット)/OSM優先+空き地だけ自動")
ap.add_argument("--region", default="odaiba", choices=["odaiba", "west"], help="west=お台場の対岸(田町〜芝浦〜品川の本土側)")
ap.add_argument("--spot", default="", help="地点プリセット名(小領域 half=200)。" + ",".join(SPOTS))
ap.add_argument("--center", default="", help="lon,lat(--half と併用)")
ap.add_argument("--round", default="1", help="out/render/spots/<spot>/round<N>/ に保存")
a = ap.parse_args()

CENTERS = {"odaiba": (139.7745, 35.6265), "west": (139.7455, 35.6405)}
center, tag = CENTERS[a.region], ""
if a.spot:
    center, tag = SPOTS[a.spot], a.spot
    if "--half" not in sys.argv:
        a.half = 200
    if "--tile" not in sys.argv:
        a.tile = 200
elif a.center:
    center, tag = tuple(float(x) for x in a.center.split(",")), "c" + a.center.replace(",", "_")
if tag:
    from pathlib import Path
    city_render.OUT = Path(__file__).resolve().parents[1] / f"out/render/spots/{tag}/round{a.round}"
t0 = time.time()
w = city.build_world(a.half, a.tile, center_ll=center, mode=a.mode)
if not a.no_props:
    from vt import city_props
    w["props"] = city_props.build_props(w)
    print("props:", len(w["props"]), f"({time.time() - t0:.0f}s)")

tiles = city_render.make_tiles(w)
tiler = w["tiler"]

if not a.no_usd:
    usd_out.write_all_modules(log=lambda s: None)
    bt = defaultdict(list)
    for b in w["builts"]:
        bt[tiler.idx(b.insts[0].x, b.insts[0].y)].append(b)
    layers = []
    for (i, j) in tiler.all():
        k = f"t{i}_{j}"
        for kind in ("g", "r", "t"):
            m = tiles[kind].get((i, j))
            if m is not None and m.f:
                layers.append(usd_out.write_world_mesh(f"city_{k}_{ {'g': 'ground', 'r': 'roads', 't': 'rail'}[kind] }", m))
        for kind, nm in (("furn", "furniture"), ("veg", "vegetation"), ("props", "props")):
            lst = tiles[kind].get((i, j))
            if lst:
                layers.append(usd_out.write_instances(lst, usd_out.OUTDIR / f"city_{k}_{nm}.usdc", f"{nm.capitalize()}_{k}"))
        if bt.get((i, j)):
            layers.append(usd_out.write_buildings(bt[(i, j)], usd_out.OUTDIR / f"city_{k}_buildings.usdc"))
    usd_out.write_city(layers, usd_out.OUTDIR / "city_all.usda")
    print("USD tiles:", len(tiler.all()), "layers:", len(layers), f"({time.time() - t0:.0f}s)")

if a.render:
    gv = city_render.pick_ground_views(w, per=a.per)
    av = city_render.pick_aerial_views(w)
    if tag:     # 小領域: 地点の主題に合う地面視点3〜4枚+空中2枚
        pri = PRIORITY.get(a.spot, ["intersection", "roadway", "sidewalk", "alley", "park", "plaza"])
        gv = sorted(gv, key=lambda v: (pri.index(v.kind) if v.kind in pri else 99, v.name))[:4]
        av = [v for v in av if v.name in ("a_oblique_0", "a_oblique_2")]
    views = gv + av
    if a.only:
        views = [v for v in views if v.name.startswith(a.only)]
    for v in views:
        r = a.radius if v.kind != "aerial" else 700
        t1 = time.time()
        city_render.render_view_checked(w, tiles, v, r, samples=a.samples)
        print("rendered", v.name, f"{time.time() - t1:.0f}s")
    names = [v.name for v in views]
    for k in range(0, len(names), 6):
        city_render.contact_sheet(names[k:k + 6], f"sheet_{k // 6}.jpg")
print("total", f"{time.time() - t0:.0f}s")
