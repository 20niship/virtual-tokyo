"""参照写真に近い構図で岩 module を 1 個描く検証用。coast = 海面から海食崖を中距離で(転石つき) / peak = 岩山の頂部を近接+遠景の緑地。
例: terra_rock_ref.py coast rock_seacliff_seacliff_1_hi -o out/terra/rock/after_coast.png"""
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
ap.add_argument("scene", choices=["coast", "peak"])
ap.add_argument("module")
ap.add_argument("-o", "--out", required=True)
ap.add_argument("--res", default="")
ap.add_argument("--samples", type=int, default=48)
ap.add_argument("--rot", type=float, default=0.0, help="module の z 回転[deg]")
ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--boulders", type=int, default=6, help="coast: 水際の転石 module の数")
ap.add_argument("--cam", default="", help="x,y,z,tx,ty,tz で上書き")
a = ap.parse_args()
res = tuple(int(v) for v in (a.res or ("1400x900" if a.scene == "coast" else "1100x1460")).split("x"))
vr.PHOTO = True
g = Grid.from_size(40, 10)
doc = Document(g, 0)
doc.layers["height"] = np.zeros(g.shape, np.float32)
R.photo_setup(doc, res, a.samples)
vr.HAZE_K["day"] = 8e-6


def plane(name, z, col, rough=0.9, size=3e4, loc=(0, 0)):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-size, -size, z), (size, -size, z), (size, size, z), (-size, size, z)], [], [(0, 1, 2, 3)])
    mt = bpy.data.materials.new(name)
    mt.use_nodes = True
    b = mt.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    me.materials.append(mt)
    o = bpy.data.objects.new(name, me)
    o.location = (loc[0], loc[1], 0)
    bpy.context.scene.collection.objects.link(o)
    return o


def put(name, loc, rot=0.0, scale=1.0):
    mesh = M.build(name)
    o = bpy.data.objects.new(name, vr.mesh_to_bpy(name, mesh))
    o.location, o.rotation_euler, o.scale = loc, (0, 0, math.radians(rot)), (scale,) * 3
    bpy.context.scene.collection.objects.link(o)
    return len(mesh.f)


nf = put(a.module, (0, 0, 0), a.rot, a.scale)
cam = a.cam.split(",") if a.cam else None
if a.scene == "coast":
    plane("sea", 0.0, (0.01, 0.17, 0.2), 0.08)                      # ターコイズの海
    rng = np.random.default_rng(3)
    for i in range(a.boulders):                                       # 水際の暗い転石
        x = (i - a.boulders / 2) * 3.3 + rng.uniform(-1, 1)
        nf += put(f"rock_seashore_boulder_{'ml'[i % 2]}_{1 + 2 * (i % 2)}", (x, -3.2 - rng.uniform(0, 1.8), 0.0), rng.uniform(0, 360), rng.uniform(0.7, 1.4))
    loc, tgt = (tuple(map(float, cam[:3])), tuple(map(float, cam[3:]))) if cam else ((-4, -46, 3.0), (0, 0, 6.2))
    lens = 50
else:
    plane("forest", -45.0, (0.07, 0.12, 0.04), 1.0)                  # 眼下の森
    plane("hill", -30.0, (0.06, 0.1, 0.05), 1.0, size=2000, loc=(0, 600))
    loc, tgt = (tuple(map(float, cam[:3])), tuple(map(float, cam[3:]))) if cam else ((0, -5.5, 4.2), (0, 0, 0.5))
    lens = 32
c = vr.add_camera(loc, tgt, lens)
c.data.clip_end = 6e4
ev = R.finish(a.out, 0.2, 60)
print("faces", nf, "ev", round(ev, 2), a.out)
