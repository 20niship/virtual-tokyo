"""材質の近接確認: uv run python scripts/realism_closeup.py out.png name1 name2 ... [--time day|dusk|night] [--legacy] [--dist 7] [--sp 3.5]"""
import sys

import bpy

from vt import render
from vt.modules.library import REG, get

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opt = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
out, names = args[0], [n for n in args[1:] if n in REG]
tm, sp, dist = opt("--time", "day"), opt("--sp", 3.5), opt("--dist", 7.0)
render.init_scene((1800, 700), opt("--samples", 48), sun_dir=(0.5, -0.45, 0.65), time=tm, realism="--legacy" not in sys.argv)
render.add_plane(200, 0.0, "asphalt")
if "--gn" in sys.argv:       # 本番と同じ GN インスタンス経由
    from vt.assemble import Inst
    render.add_instances_gn([Inst(n, (i - (len(names) - 1) / 2) * sp, 0, 0, 0.0) for i, n in enumerate(names)], [0.15 + 0.17 * i for i in range(len(names))])
else:
    for i, n in enumerate(names):
        o = bpy.data.objects.new(n, render.mesh_to_bpy(n, get(n)))
        o.location = ((i - (len(names) - 1) / 2) * sp, 0, 0)
        o["bvar"] = 0.15 + 0.17 * i
        bpy.context.scene.collection.objects.link(o)
render.add_camera((0, -dist, 1.8), (0, 0, 1.6), 40)
sc = bpy.context.scene
sc.view_settings.look = "AgX - Base Contrast"
sc.view_settings.exposure = render.estimate_exposure({"day": 0.17, "dusk": 0.1, "night": 0.03}[tm]) if "--legacy" not in sys.argv else -1.8
render.render(out)
