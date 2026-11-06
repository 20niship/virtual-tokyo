"""Hero USD(UsdSkel)を Blender に読み込んで確認する: uv run python scripts/render_hero_usd.py out.png assets/humans/<id>.usdc [frame]"""
import sys
from pathlib import Path

import bpy

from vt import render

out, usd = sys.argv[1], sys.argv[2]
frame = int(sys.argv[3]) if len(sys.argv) > 3 else 0
render.init_scene((900, 1200), 48, sun_dir=(0.5, 0.45, 0.65), realism=True)
render.add_plane(50, 0.0, "sidewalk")
bpy.ops.wm.usd_import(filepath=str(Path(usd).resolve()), import_skeletons=True, import_materials=True, import_usd_preview=True, set_material_blend=True)
bpy.context.scene.frame_set(frame)
render.add_camera((0, 3.2, 1.0), (0, 0, 0.9), 32)
sc = bpy.context.scene
sc.view_settings.look = "AgX - Base Contrast"
sc.view_settings.exposure = render.estimate_exposure(0.17) - 2.2
render.render(out)
