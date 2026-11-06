"""モーションクリップの確認: uv run python scripts/render_clips.py out.png [clip,clip,...] [--phases 0.1,0.6] [--k 3]
同じ人物に各クリップの位相を当てて並べる(列=クリップ、行=位相)。"""
import sys

import bpy

from vt import humans_motion as M
from vt import render
from vt.modules import lib_anny
from vt.modules.geom import Mesh

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opt = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
out = args[0]
clips = args[1].split(",") if len(args) > 1 else M.names()
phases = [float(x) for x in opt("--phases", "0.1,0.6").split(",")]
k = opt("--k", 3)
render.init_scene((1920, 720 if len(phases) == 1 else 1080), opt("--samples", 32), sun_dir=(0.5, 0.45, 0.65), realism=True)
render.add_plane(200, 0.0, "sidewalk")
sp = 1.7
for i, c in enumerate(clips):
    for j, ph in enumerate(phases):
        m = Mesh()
        lib_anny.build_mesh(m, "casual", k, pose_override=(c, ph))
        o = bpy.data.objects.new(f"{c}_{j}", render.mesh_to_bpy(f"{c}_{j}", m))
        o.location = ((i - (len(clips) - 1) / 2) * sp, -j * 1.9, 0)
        bpy.context.scene.collection.objects.link(o)
W = len(clips) * sp
render.add_camera((0, 2.5 + W * 0.55, 2.4), (0, -(len(phases) - 1) * 0.95, 0.85), 38)
sc = bpy.context.scene
sc.view_settings.look = "AgX - Base Contrast"
sc.view_settings.exposure = render.estimate_exposure(0.17) - 0.9
render.render(out)
