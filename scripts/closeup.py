"""モジュールを並べて近接レンダ: uv run python scripts/closeup.py out.png name1 name2 ... [--dist 9] [--sp 6]"""
import sys

import bpy

from vt import render
from vt.modules.library import REG, get

args = [a for a in sys.argv[1:] if not a.startswith("--")]
out, names = args[0], args[1:]
sp = float(sys.argv[sys.argv.index("--sp") + 1]) if "--sp" in sys.argv else 6.0
dist = float(sys.argv[sys.argv.index("--dist") + 1]) if "--dist" in sys.argv else 10.0
if sp == float(args[0]) if False else False:
    pass
names = [n for n in names if n in REG]
render.init_scene((1800, 700), 48, sun_dir=(0.5, 0.45, 0.7))
render.add_plane(200, 0.0, "asphalt")
for i, n in enumerate(names):
    o = bpy.data.objects.new(n, render.mesh_to_bpy(n, get(n)))
    o.location = ((i - (len(names) - 1) / 2) * sp, 0, 0)
    o["bvar"] = 0.3 + 0.1 * i
    o.rotation_euler = (0, 0, 0)
    bpy.context.scene.collection.objects.link(o)
render.add_camera((dist * 0.25, -dist * 1.5, 3.2), (0, 0, 0.9), 38)
render.render(out)
