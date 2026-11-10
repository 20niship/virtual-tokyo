"""都市のフォトリアルレンダを最小のコードで再現する例(docs/city_rendering.md)。
uv run python scripts/render_city_minimal.py                          # 昼、西岸の交差点、地上視点1枚
uv run python scripts/render_city_minimal.py --time dusk --kind aerial
uv run python scripts/render_city_minimal.py --center 139.7478,35.6448 --half 200 --samples 64 --res 1920x1080
出力: out/render/minimal/<time>/<視点名>.png
"""
import argparse
import time
from pathlib import Path

from vt import city, city_props, city_render, render

ap = argparse.ArgumentParser()
ap.add_argument("--center", default="139.7478,35.6448", help="lon,lat(既定: 西岸の交差点)")
ap.add_argument("--half", type=float, default=200, help="生成範囲の半幅[m]")
ap.add_argument("--time", default="day", choices=["day", "dusk", "night"])
ap.add_argument("--kind", default="ground", choices=["ground", "aerial"], help="ground=目線1.65m / aerial=俯瞰")
ap.add_argument("--view", default="roadway", help="ground のとき選ぶ視点の種類(roadway/intersection/sidewalk/alley/park/...)")
ap.add_argument("--samples", type=int, default=24, help="Cycles サンプル数(24=確認用、64〜128=仕上げ)")
ap.add_argument("--res", default="1280x720")
ap.add_argument("--lens", type=float, default=0, help="焦点距離[mm]。0=自動(地上28/35、俯瞰60)")
ap.add_argument("--fstop", type=float, default=5.6)
ap.add_argument("--no-dof", action="store_true")
ap.add_argument("--legacy", action="store_true", help="写実ルックを切る(従来の広角・ピンホール・後処理なし)")
a = ap.parse_args()

# 1) ルックの設定(これだけで写実ルックの on/off・レンズ・絞りが決まる)
render.PHOTO = not a.legacy        # 焦点距離/DoF/太陽サイズ/ブルーム/ポスト処理をまとめて切替
render.FSTOP = a.fstop
render.DOF = not a.no_dof
city_render.LENS = a.lens
city_render.TIME = a.time          # day / dusk / night(空・露出・霞・窓と看板の発光が切り替わる)
city_render.REALISM = True         # 雲・霞・水面・壁の汚れ・窓の室内・自動露出
city_render.OUT = Path("out/render/minimal") / a.time

# 2) 街の生成(OSM は data/osm にキャッシュ済み。無ければ初回だけ取得)
t0 = time.time()
lon, lat = (float(x) for x in a.center.split(","))
w = city.build_world(a.half, a.half * 2, center_ll=(lon, lat), mode="hybrid")
w["props"] = city_props.build_props(w, life=True)
tiles = city_render.make_tiles(w)
print(f"world {time.time() - t0:.0f}s buildings={len(w['builts'])} props={len(w['props'])}")

# 3) 視点を選ぶ(地上: 目線 1.65m / 俯瞰: 最も高い建物の上から)
if a.kind == "aerial":
    views = [v for v in city_render.pick_aerial_views(w) if v.name == "a_oblique_0"]
    radius = a.half * 3.5
else:
    views = [v for v in city_render.pick_ground_views(w, per=2, margin=30) if v.kind == a.view][:1]
    radius = 170
if not views:
    raise SystemExit(f"視点 '{a.view}' が領域内に見つからない。--view を変えるか --half を広げる")

# 4) レンダ(カメラ周辺だけを Blender へ読み込み、露出を試し撮りで決め、Cycles→ブルーム→ポスト処理)
res = tuple(int(x) for x in a.res.split("x"))
for v in views:
    t1 = time.time()
    city_render.render_view_checked(w, tiles, v, radius, samples=a.samples, res=res, min_luma=22.0 if a.time == "day" else 6.0)
    print(f"rendered {v.name} {time.time() - t1:.0f}s -> {city_render.OUT / (v.name + '.png')}")
