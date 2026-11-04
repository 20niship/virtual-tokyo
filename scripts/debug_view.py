"""特定ビューの切り分け: uv run python scripts/debug_view.py g_park_0 [gn|obj] [veg|furn|props|bld|ground]..."""
import sys

from vt import city, city_render, render
from vt.city_props import build_props

name, mode, parts = sys.argv[1], sys.argv[2], sys.argv[3:]
w = city.build_world(700, 350, center_ll=(139.7455, 35.6405), mode="hybrid", log=lambda s: None)
w["props"] = build_props(w)
tiles = city_render.make_tiles(w)
v = [x for x in city_render.pick_ground_views(w, per=1) if x.name == name][0]
cx, cy = v.cam[0], v.cam[1]
render.init_scene((960, 540), 16, sun_dir=(0.5, -0.45, 0.65))
if "ground" in parts:
    for key in ("g", "r"):
        for ij, m in tiles[key].items():
            if w["tiler"].box(*ij).distance(__import__("shapely.geometry", fromlist=["Point"]).Point(cx, cy)) < 240:
                render.add_mesh_object(key, m)
for key in ("veg", "furn", "props"):
    if key in parts:
        sel = [i for lst in tiles[key].values() for i in lst if (i.x - cx) ** 2 + (i.y - cy) ** 2 < 240 ** 2]
        (render.add_instances_gn if mode == "gn" else render.add_instances)(sel)
if "bld" in parts:
    bl = [b for b in w["builts"] if (b.insts[0].x - cx) ** 2 + (b.insts[0].y - cy) ** 2 < 300 ** 2]
    (render.add_buildings_gn if mode == "gn" else render.add_buildings)(bl)
render.add_camera(v.cam, v.tgt, v.lens)
render.render(f"out/render/dbg_{mode}_{'_'.join(parts)}.png")
