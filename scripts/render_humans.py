"""Anny 人物のギャラリー: uv run python scripts/render_humans.py out.png [--group office|all] [--n 20] [--cols 10] [--back] [--zoom]
人物は +y 向き。カメラは +y 側から。--zoom は上半身アップ。"""
import sys

import bpy

from vt import render
from vt.modules.lib_anny import NAMES
from vt.modules.library import get

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opt = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
out = args[0]
grp, n, cols = opt("--group", "all"), opt("--n", 20), opt("--cols", 10)
sel = grp.split(",")
names = [x for g, v in NAMES.items() if "all" in sel or g in sel for x in v][::opt("--stride", 1)][opt("--start", 0):][:n]
if "--pedx" in sys.argv:
    from vt.modules.lib_city2 import PEDX
    names = [x for v in PEDX.values() for x in v][:n]
rows = (len(names) + cols - 1) // cols
sp = 1.5
W = cols * sp
render.init_scene((1920, 640 if rows == 1 else 1080), opt("--samples", 48), sun_dir=(0.5, 0.45, 0.65), time=opt("--time", "day"), realism=True)
render.add_plane(200, 0.0, "sidewalk")
for i, nm in enumerate(names):
    r, c = divmod(i, cols)
    o = bpy.data.objects.new(nm, render.mesh_to_bpy(nm, get(nm)))
    o.location = ((c - (cols - 1) / 2) * sp, -r * 1.8, 0)
    if "--back" in sys.argv:
        o.rotation_euler = (0, 0, 3.14159)
    bpy.context.scene.collection.objects.link(o)
if "--zoom" in sys.argv:
    render.add_camera((0, opt("--cam", 2.2), opt("--camz", 1.55)), (0, 0, opt("--tz", 1.2)), 40)
else:
    render.add_camera((0, 2.0 + W * 0.62 + rows * 0.6, 2.2 + rows * 0.5), (0, -(rows - 1) * 0.9, 0.85), 38)
sc = bpy.context.scene
sc.view_settings.look = "AgX - Base Contrast"
sc.view_settings.exposure = render.estimate_exposure(0.17) + opt("--ev", -0.9)
render.render(out)
