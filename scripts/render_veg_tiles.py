"""植生モジュール全種をタイル状(XY格子)に並べ、やや斜め上から平行投影で見た画像。 uv run python scripts/render_veg_tiles.py"""
import math
from pathlib import Path

import bpy

from vt import render
from vt.modules.library import REG, get

OUT = Path(__file__).resolve().parents[1] / "out/render"
names = [n for n, r in REG.items() if r["cat"] == "植栽"]
trees = [n for n in names if "_summer" in n or n.startswith(("veg_kuromatsu", "veg_yashi", "veg_shuro", "veg_yanagi"))]
seasons = [n for n in names if any(s in n for s in ("_spring", "_autumn", "_winter"))]
others = [n for n in names if n not in trees and n not in seasons]


def sheet(ns, out, cols, res):
    render.init_scene(res, 28, sun_dir=(0.5, 0.45, 0.75))
    sp = max(REG[n]["W"] for n in ns) * 1.05
    rows = math.ceil(len(ns) / cols)
    render.add_plane(sp * (cols + 4), -0.01, "ground", loc=(0, 0))
    for i, n in enumerate(ns):
        r, c = divmod(i, cols)
        o = bpy.data.objects.new(n, render.mesh_to_bpy(n, get(n)))
        o.location = ((c - (cols - 1) / 2) * sp, -(r - (rows - 1) / 2) * sp, 0)
        o["bvar"] = 0.4
        bpy.context.scene.collection.objects.link(o)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    bpy.context.scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(cols * sp, rows * sp * res[0] / res[1]) * 1.03
    tilt = math.radians(22)
    cam.location = (0, -math.sin(tilt) * 200, math.cos(tilt) * 200)
    cam.rotation_euler = (tilt, 0, 0)
    cam.data.clip_end = 1000
    bpy.context.scene.camera = cam
    render.render(out)


sheet(trees, OUT / "veg_tiles_trees.png", 11, (3200, 2200))
sheet(seasons, OUT / "veg_tiles_seasons.png", 12, (3200, 2200))
sheet(others, OUT / "veg_tiles_shrubs.png", 13, (3200, 2000))
