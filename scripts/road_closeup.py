"""歩道・縁石・鋳鉄蓋・集水桝・切り下げ・植樹桝(縁石)・落ち葉の近景(高解像度)。 uv run python scripts/road_closeup.py <out_dir> [season]
season: summer|autumn_y|autumn_r|winter(既定 autumn_y)"""
import math
import sys
from pathlib import Path

import bpy

from vt import render
from vt.modules.geom import Mesh
from vt.modules.library import get

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
season = sys.argv[2] if len(sys.argv) > 2 else "autumn_y"
litter = {"autumn_y": "y", "autumn_r": "r", "winter": "b", "summer": "g"}[season]

m = Mesh()
m.box(-12, -8, -0.3, 12, 0, 0.0, "asphalt")                                            # 車道(y<0)
m.box(-12, 0.0, -0.3, 12, 5.0, 0.15, "sidewalk_paver")                                  # 歩道(h=15cm)
m.box(-12, -0.02, -0.3, 12, 0.0, 0.15, "concrete_tex")                                  # 縁石面
m.box(-12, -0.3, 0.0, 12, -0.02, 0.012, "gutter_l")                                      # L型側溝
m.box(-12, 0.0, 0.15, 12, 0.15, 0.152, "curb_top")                                      # 縁石天端
m.box(-12, 5.0, -0.3, 12, 12, 0.0, "grass")
render.init_scene((2000, 1100), 64, sun_dir=(0.5, -0.45, 0.65), realism=True)
render.add_mesh_object("base", m)


def put(name, x, y, z=0.0, rot=0.0, s=1.0):
    o = bpy.data.objects.new(name, render.mesh_to_bpy(name, get(name)))
    o.location = (x, y, z)
    o.rotation_euler = (0, 0, rot)
    o.scale = (s, s, s)
    o["bvar"] = (x * 12.9 + y * 7.7) % 1.0
    bpy.context.scene.collection.objects.link(o)


for i, k in enumerate(("sewer", "water", "gas", "elec", "tele")):
    put(f"rd_cover_{k}", -4.5 + i * 1.1, -2.2, 0.01)
put("rd_catchbasin_cast", 1.5, -0.2, 0.01)
put("rd_catchbasin_cast", 6.5, -0.2, 0.01)
put("rd_driveway_apron_15", 4.0, 0.0, 0.0, math.pi)                                       # +y=車道側へ向けるため180度回して配置(車道側=-y)
put("rd_curb_reflector_white", -2.0, -0.02, 0.07, math.pi)
put("rd_curb_reflector_amber", 0.5, -0.02, 0.07, math.pi)
put("bollard_fixed", 1.6, 0.6, 0.15)
put("bollard_fixed", 6.4, 0.6, 0.15)
put("veg_tree_pit_curb", -5.0, 2.6, 0.15)
put(f"veg_keyaki_m_0_{season}", -5.0, 2.6, 0.15)
for i, (x, y) in enumerate([(-6.8, 1.6), (-3.5, 3.6), (-4.5, 0.9), (-7.5, 3.8), (-2.2, 1.8), (0.5, 1.6)]):
    put(f"veg_litter_{litter}", x, y, 0.15, i * 1.3, 1.0 + 0.1 * i)
put(f"veg_litter_{litter}", -5.0, -0.7, 0.0, 0.4, 1.2)                                  # 側溝・車道縁の落ち葉
render.add_camera((2.5, -5.5, 1.5), (-1.5, 1.2, 0.4), 32)
bpy.context.scene.view_settings.exposure = render.estimate_exposure(0.17)
render.render(out / f"closeup_{season}_a.png")
render.add_camera((-1.0, 1.3, 1.1), (-5.0, 2.8, 0.2), 30)
bpy.context.scene.view_settings.exposure = render.estimate_exposure(0.17)
render.render(out / f"closeup_{season}_b_litter.png")
