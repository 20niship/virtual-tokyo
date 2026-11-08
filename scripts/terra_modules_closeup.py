"""module 1 個の近影(数 m 先から)を Cycles で描く。例: terra_modules_closeup.py rock_seashore_boulder_l_4_hi --dist 3.2 -o out/terra/modules/closeup"""
import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from terra import modules as M  # noqa: E402
from terra import render as R  # noqa: E402
from terra.core import Document  # noqa: E402
from terra.core.grid import Grid  # noqa: E402

from vt import render as vr  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("name")
ap.add_argument("--dist", type=float, default=3.0, help="カメラまでの距離[m]")
ap.add_argument("--height", type=float, default=0.9, help="カメラの高さ[m]")
ap.add_argument("--target-z", type=float, default=0.7)
ap.add_argument("--azimuth", type=float, default=-35, help="度(0=+y から見る、負=右から)")
ap.add_argument("--lens", type=float, default=50)
ap.add_argument("--ground", default="soil_humus")
ap.add_argument("-o", "--out", default="out/terra/modules/closeup")
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--res", default="2000x1400")
a = ap.parse_args()

res = tuple(int(v) for v in a.res.split("x"))
vr.PHOTO = False
doc = Document(Grid.from_size(40, 10), 0)
doc.layers["height"] = np.zeros(doc.grid.shape, np.float32)
R.photo_setup(doc, res, a.samples)
vr.HAZE_K["day"] = 0
me = bpy.data.meshes.new("ground")
me.from_pydata([(-60, -60, 0), (60, -60, 0), (60, 60, 0), (-60, 60, 0)], [], [(0, 1, 2, 3)])
me.materials.append(vr.get_material(a.ground))
uv = me.uv_layers.new(name="UVMap")
uv.data.foreach_set("uv", np.array([(-60, -60), (60, -60), (60, 60), (-60, 60)], np.float32)[[0, 1, 2, 3]].ravel())
bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", me))
o = bpy.data.objects.new(a.name, vr.mesh_to_bpy(a.name, M.build(a.name)))
bpy.context.scene.collection.objects.link(o)
az = math.radians(a.azimuth)
tgt = (0, 0, a.target_z)
cam = vr.add_camera((a.dist * math.sin(-az), -a.dist * math.cos(az), a.height), tgt, a.lens)
cam.data.dof.use_dof = True
cam.data.dof.focus_distance = math.dist(cam.location, tgt)
cam.data.dof.aperture_fstop = 8.0
sc = bpy.context.scene
sc.view_settings.exposure = R.estimate_ev(0.22)
sc.view_settings.look = "AgX - Base Contrast"
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
p = out / f"{a.name}.png"
vr.render(p)
print("wrote", p)
