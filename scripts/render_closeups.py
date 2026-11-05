"""人物のクローズアップ(顔・髪の横と後ろ・上半身の服): uv run python scripts/render_closeups.py <tag> [--hero]
out/render/humans/real_<tag>/ に、人物ごとに face / hair_side / hair_back / torso / full を出す。"""
import sys

import bpy
import numpy as np
from mathutils import Vector

from vt import render
from vt.modules import lib_anny as A
from vt.modules.geom import Mesh

args = [a for a in sys.argv[1:] if not a.startswith("--")]
tag = args[0] if args else "before"
opt = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
CAST = [("casual", 3, "idle"), ("office", 1, "idle"), ("elder", 2, "idle"), ("student", 4, "idle"), ("casual", 12, "idle")]
if "--cast" in sys.argv:
    CAST = [(g, int(k), "idle") for g, k in (c.split(":") for c in opt("--cast", "casual:3").split(","))]
SHOTS = dict(face=((0, 0.75), 0.0, 1.0, 34), hair_side=((1, 0), 0.0, 1.0, 34), hair_back=((0, -0.9), 0.0, 1.0, 34), torso=((0, 1.6), -0.30, 0.55, 36), full=((0, 4.2), -0.8, 0.0, 34))
from pathlib import Path
OUT = Path(__file__).resolve().parents[1] / f"out/render/humans/real_{tag}"
OUT.mkdir(parents=True, exist_ok=True)
samples = opt("--samples", 64)
for g, k, clip in CAST:
    m = Mesh()
    A.build_mesh(m, g, k, A.LOD, pose_override=(clip, 0.0))
    V = np.array(m.v)
    top = float(V[:, 2].max())
    tris = sum(max(1, len(f) - 2) for f in m.f)
    print(g, k, "faces", len(m.f), "tris", tris, flush=True)
    for shot, ((dx, dy), dz_head, dz_t, lens) in SHOTS.items():
        render.init_scene((960, 960) if shot != "full" else (640, 960), samples, sun_dir=(0.5, 0.45, 0.65), realism=True)
        render.add_plane(50, 0.0, "sidewalk")
        o = bpy.data.objects.new("p", render.mesh_to_bpy("p", m))
        bpy.context.scene.collection.objects.link(o)
        hz = top - 0.11
        if shot == "full":
            cam, tgt = (0, 4.2, top * 0.55 + 0.4), (0, 0, top * 0.5)
        elif shot == "torso":
            cam, tgt = (0, 1.7, top - 0.5), (0, 0, top - 0.5)
        else:
            cam, tgt = (dx * 0.9 if dx else 0.0, dy if dy else 0.0, hz), (0, 0, hz)
            if shot == "hair_side":
                cam = (0.9, 0.0, hz)
        render.add_camera(cam, tgt, lens)
        sc = bpy.context.scene
        sc.view_settings.look = "AgX - Base Contrast"
        sc.view_settings.exposure = render.estimate_exposure(0.17) - 1.3
        render.render(OUT / f"{g}{k}_{shot}.png")
(OUT / "tris.txt").write_text("")
