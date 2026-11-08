"""module のカタログ(コンタクトシート): 種類 × 状態を格子に並べて Cycles で 1 枚に描く。例: terra_modules_sheet.py rocks -o out/terra/modules"""
import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from terra import modules as M  # noqa: E402
from terra import render as R  # noqa: E402
from terra.core import Document  # noqa: E402
from terra.core.grid import Grid  # noqa: E402

from vt import render as vr  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("sheet", choices=["rocks", "forms", "soils", "gravel", "far", "hi", "hi_forms", "road"])
ap.add_argument("-o", "--out", default="out/terra/modules")
ap.add_argument("--only", default="", help="カンマ区切りで行ラベルを絞る(近影用)")
ap.add_argument("--cols", type=int, default=0, help="先頭から何列使うか")
ap.add_argument("--samples", type=int, default=32)
ap.add_argument("--res", default="1800x1100")
a = ap.parse_args()

KS = ["granite", "andesite", "sandstone", "limestone", "tuff", "river", "seashore"]
SOILS = ["kuroboku", "redyellow", "clay", "sandy", "scoria", "masa", "humus", "mud"]
GR = ["sand", "fine", "medium", "cobble", "river", "crushed", "talus", "ballast"]
ST = ["fresh", "weathered", "mossy", "stained"]
if a.sheet == "rocks":
    rows = [(k, [f"rock_{k}_boulder_m_{v}" for v in range(4)], ST) for k in KS]
    sp, sc = 3.2, 1.0
elif a.sheet == "forms":
    rows = [(k, [f"rock_{k}_boulder_s_1", f"rock_{k}_boulder_l_2", f"rock_{k}_outcrop_1", f"rock_{k}_cliff_1"] + ([f"rock_{k}_column_0"] if k == "andesite" else []), ["boulder_s", "boulder_l", "outcrop", "cliff", "column"]) for k in KS[:5]]
    sp, sc = 8.0, 1.0
elif a.sheet == "soils":
    rows = [(k, [f"soil_{k}_patch_0", f"soil_{k}_patch_1", f"soil_{k}_patch_2", f"soil_{k}_clod_0", f"soil_{k}_clod_2"], ["patch0", "patch1", "patch2", "clod0", "clod2"]) for k in SOILS]
    sp, sc = 3.2, 1.0
elif a.sheet == "gravel":
    rows = [(k, [f"gravel_patch_{k}_0", f"gravel_patch_{k}_1"] + ([f"gravel_stone_{s}_{z}_0" for s, z in (("round", "fine"), ("angular", "medium"), ("round", "cobble"))] if i < 3 else []), ["patch0", "patch1", "round/fine", "angular/medium", "round/cobble"]) for i, k in enumerate(GR)]
    sp, sc = 4.4, 1.0
elif a.sheet == "hi":   # 超高ポリ(_hi): 岩種 × 状態(新鮮・風化・苔・苔に覆われた)の転石 l
    rows = [(k, [f"rock_{k}_boulder_l_{v}_hi" for v in (0, 1, 2, 4)], ["fresh", "weathered", "mossy", "overgrown"]) for k in ("granite", "andesite", "seashore", "limestone", "sandstone")]
    sp, sc = 8.0, 1.0
elif a.sheet == "hi_forms":   # 形違い: 露頭・崖・中型の転石
    rows = [(k, [f"rock_{k}_outcrop_2_hi", f"rock_{k}_boulder_m_1_hi", f"rock_{k}_cliff_2_hi"], ["outcrop", "boulder m", "cliff"]) for k in ("granite", "andesite", "seashore")]
    sp, sc = 9.0, 1.0
elif a.sheet == "road":
    rows = [("furniture", ["road_guardrail_4m", "road_retwall_4m", "road_rocknet_8m", "road_curve_mirror"], ["guardrail", "retaining wall", "rockfall net", "curve mirror"]),
            ("portal", ["tunnel_portal_0", "tunnel_portal_1", "tunnel_portal_2", "tunnel_portal_2_far"], ["portal0", "portal1(canopy)", "portal2(wing)", "portal2 far"]),
            ("bridge", ["bridge_deck_8m", "bridge_chinka_8m", "bridge_pier_8", "bridge_pier_24"], ["deck 8m", "chinka", "pier 8", "pier 24"])]
    sp, sc = 14.0, 1.0
else:   # far: near と far のポリ数比較(同じ module)
    rows = [(k, [f"rock_{k}_boulder_m_1", f"rock_{k}_boulder_m_1_far", f"rock_{k}_outcrop_1", f"rock_{k}_outcrop_1_far"], ["near", "far", "outcrop near", "outcrop far"]) for k in KS[:5]]
    sp, sc = 6.0, 1.0

if a.only:
    rows = [r for r in rows if r[0] in a.only.split(",")]
if a.cols:
    rows = [(l, n[:a.cols], c[:a.cols]) for l, n, c in rows]
res = tuple(int(v) for v in a.res.split("x"))
vr.PHOTO = False
g = Grid.from_size(40, 10)
doc = Document(g, 0)
doc.layers["height"] = np.zeros(g.shape, np.float32)
R.photo_setup(doc, res, a.samples)
vr.HAZE_K["day"] = 0
ncol = max(len(r[1]) for r in rows)
W, Hh = ncol * sp, len(rows) * sp
me = bpy.data.meshes.new("ground")
me.from_pydata([(-W, -Hh, 0), (W * 2, -Hh, 0), (W * 2, Hh * 2, 0), (-W, Hh * 2, 0)], [], [(0, 1, 2, 3)])
gm = bpy.data.materials.new("g")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.22, 0.24, 0.20, 1)
me.materials.append(gm)
bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", me))
cells = []
for r, (label, names, cols) in enumerate(rows):
    for c, n in enumerate(names):
        mesh = M.build(n) if n in M.REG else None
        if mesh is None:
            from vt.modules.library import get
            mesh = get(n)
        s = 0.28 if "cliff" in n else sc
        o = bpy.data.objects.new(n, vr.mesh_to_bpy(n, mesh))
        o.location = (c * sp, (len(rows) - 1 - r) * sp, 0)
        o.scale = (s, s, s)
        bpy.context.scene.collection.objects.link(o)
        cells.append((o.location.x, o.location.y, f"{label}  {cols[c]}  [{len(mesh.f)}f]"))
cx, cy = (ncol - 1) * sp / 2, (len(rows) - 1) * sp / 2
cam = vr.add_camera((cx, cy - 60, 70), (cx, cy, 0), 50)
cam.data.type = "ORTHO"
cam.data.ortho_scale = max(W * 1.08, Hh * 1.45)
cam.data.clip_end = 5000
sc_ = bpy.context.scene
ev = R.estimate_ev(0.22)
sc_.view_settings.exposure = ev
sc_.view_settings.look = "AgX - Base Contrast"
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
p = out / f"sheet_{a.sheet}.png"
vr.render(p)
im = Image.open(p).convert("RGB")
d = ImageDraw.Draw(im)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
except OSError:
    font = ImageFont.load_default()
for x, y, t in cells:
    co = world_to_camera_view(sc_, cam, bpy.data.objects[0].location.__class__((x, y - sp * 0.42, 0)))
    px, py = co.x * res[0], (1 - co.y) * res[1]
    d.text((px - 60, py), t, fill=(255, 255, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0))
im.save(p)
print("wrote", p, "exposure", round(ev, 2))
_ = math
