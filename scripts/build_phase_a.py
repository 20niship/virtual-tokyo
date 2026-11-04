"""フェーズA: モジュール生成(USD) → 建物生成 → USD出力 → レンダ。
uv run python scripts/build_phase_a.py [--no-render]"""
import math
import sys
from pathlib import Path

from shapely.geometry import Point

from vt import render, usd_out
from vt.assemble import build_building
from vt.geo import to_local
from vt.layers import load

OUT = Path(__file__).resolve().parents[1] / "out/render"
OUT.mkdir(parents=True, exist_ok=True)
CENTER_LL = (139.7745, 35.6265)   # お台場(アクアシティ〜フジテレビ付近)
RADIUS = 520

usd_out.write_all_modules(log=lambda s: None)
L = load()
c = to_local(*CENTER_LL)
cp = Point(c).buffer(RADIUS)
builts = []
for f in L["buildings"]:
    if f.geom.centroid.within(cp):
        b = build_building(f)
        if b:
            builts.append(b)
print(len(builts), "buildings,", sum(len(b.insts) for b in builts), "instances")
usd_out.write_buildings(builts)
if "--no-render" in sys.argv:
    sys.exit()

# ---- レンダ ----
def aerial():
    sc = render.init_scene((1920, 1080), 72, sun_dir=(0.5, -0.55, 0.62))
    render.build_district(builts, L, c, RADIUS)
    render.add_camera((c[0] - 330, c[1] - 380, 230), (c[0], c[1], 20), 32)
    render.render(OUT / "aerial.png")


def pick(style=None, lo=4, hi=12):
    cands = [b for b in builts if (style is None or b.meta["style"] == style) and lo <= b.meta["floors"] <= hi and len(b.insts) > 120]
    return max(cands, key=lambda b: len(b.insts)) if cands else None


def facade_view(b, name, dist, lens, h_cam, h_tgt, samples=96):
    # 建物の外周で最長辺の中央から外向きに距離distへ
    xs = [(i.x, i.y, i.rot) for i in b.insts if i.name.startswith(("win", "curtain", "balcony", "louver", "brise", "punching", "fin_"))]
    mx = sum(x for x, _, _ in xs) / len(xs); my = sum(y for _, y, _ in xs) / len(xs)
    # 最も多くのモジュールが並ぶ向き(回転)を選び、その外向き法線にカメラを置く
    from collections import Counter
    rot = Counter(round(r, 2) for _, _, r in xs).most_common(1)[0][0]
    pts = [(x, y) for x, y, r in xs if abs(round(r, 2) - rot) < 1e-6]
    px = sum(p[0] for p in pts) / len(pts); py = sum(p[1] for p in pts) / len(pts)
    nx, ny = -math.sin(rot), math.cos(rot)
    sc = render.init_scene((1920, 1080), samples, sun_dir=(0.5 * nx - 0.3 * ny, 0.5 * ny + 0.3 * nx, 0.6))
    render.build_district([b] + [o for o in builts if o is not b and math.dist((o.insts[0].x, o.insts[0].y), (px, py)) < 80], L, c, RADIUS)
    render.add_camera((px + nx * dist, py + ny * dist, h_cam), (px, py, h_tgt), lens)
    render.render(OUT / name)


aerial()
b1 = pick("apartment") or pick(None)
facade_view(b1, "street_apartment.png", 24, 30, 1.7, 9)
b2 = pick("commercial") or pick(None)
facade_view(b2, "facade_commercial.png", 11, 24, 2.0, 5.5)
b3 = pick("office_glass", 6, 40) or pick("office_tile", 6, 40)
if b3:
    facade_view(b3, "facade_office.png", 30, 30, 1.8, 15)
