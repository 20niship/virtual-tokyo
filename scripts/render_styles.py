"""全スタイル×複数seedの建物サンプルを並べてレンダ(多様性の確認): uv run python scripts/render_styles.py [seed数]"""
import sys
from pathlib import Path

from shapely.geometry import Polygon

from vt import render
from vt.assemble import build_building
from vt.layers import Feature

OUT = Path(__file__).resolve().parents[1] / "out/render"
OUT.mkdir(parents=True, exist_ok=True)
DIMS = {  # スタイル → (幅, 奥行, 高さ)
    "office_glass": (26, 20, 70), "office_tile": (22, 16, 34), "tower_mansion": (24, 24, 85), "apartment": (26, 12, 26), "danchi_stair": (44, 11, 15), "danchi_corridor": (46, 10, 20),
    "zakkyo": (8, 14, 20), "commercial": (20, 14, 17), "mall": (60, 34, 24), "warehouse": (55, 30, 14), "parking": (44, 24, 16), "school": (50, 14, 13),
    "hotel": (28, 20, 48), "public": (30, 18, 16), "house": (9, 8, 7), "shrine": (10, 7, 6),
}
n_seed = int(sys.argv[1]) if len(sys.argv) > 1 else 3
names = list(DIMS)
groups = [names[i:i + 4] for i in range(0, len(names), 4)]
for gi, group in enumerate(groups):
    builts, x = [], 0.0
    for style in group:
        w, d, h = DIMS[style]
        si = names.index(style)
        y = 0.0
        for k in range(n_seed):
            f = Feature(1000 * si + k + 1, Polygon([(0, 0), (w, 0), (w, d), (0, d)]), {"building": "yes", "_top": float(h), "_min": 0.0})
            b = build_building(f, seed=k * 17 + si, style=style)
            for i in b.insts:
                i.x += x
                i.y += y
            b.shell.v = [(vx + x, vy + y, vz) for vx, vy, vz in b.shell.v]
            builts.append(b)
            y += d + 8
        x += w + 14
    render.init_scene((2000, 1000), 48, sun_dir=(0.5, -0.6, 0.62))
    render.add_plane(3000, 0.0, "ground", loc=(x / 2, 40))
    render.add_buildings(builts)
    render.add_camera((x / 2 + 10, -x * 0.62, x * 0.32), (x / 2, 30, 14), 30)
    render.render(OUT / f"styles_sheet_{gi}.png")
    print("sheet", gi, group, len(builts), sum(len(b.insts) for b in builts))
