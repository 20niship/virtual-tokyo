"""Terra の動画: orbit(ゆっくり回転)/ fly(最長の川に沿ったフライスルー)。H.264 yuv420p faststart 1280x720。"""
import argparse
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("dir")
ap.add_argument("-o", "--out", required=True)
ap.add_argument("--mode", default="orbit", choices=["orbit", "fly"])
ap.add_argument("--frames", type=int, default=96)
ap.add_argument("--fps", type=int, default=16)
ap.add_argument("--samples", type=int, default=12)
ap.add_argument("--res", default="1280x720")
ap.add_argument("--sweep", type=float, default=100.0, help="orbit の回転角[度]")
ap.add_argument("--alt", type=float, default=35.0, help="fly の対地高度[m]")
ap.add_argument("--stride", type=int, default=2, help="地形メッシュの間引き(動画は 2 で十分)")
ap.add_argument("--splat", action="store_true")
a = ap.parse_args()

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import bpy  # noqa: E402
from terra import render as R  # noqa: E402
from terra.core import Document  # noqa: E402

from vt import render as vr  # noqa: E402

doc = Document.load(a.dir)
res = tuple(int(v) for v in a.res.split("x"))
vr.PHOTO = True
R.photo_setup(doc, res, a.samples)
splat = dict(w0=doc.layers["splat_w0"], w1=doc.layers["splat_w1"]) if a.splat and "splat_w0" in doc.layers else None
R.terrain_object(doc, splat=splat, stride=a.stride)
R.add_far_plane(doc)
R.add_water(doc)
if doc.scatter:
    from terra.export.scatter_assets import load_protos
    print("instances:", R.add_scatter(doc, load_protos(doc)))
g = doc.grid
cx, cy = g.x0 + g.nx * g.res / 2, g.y0 + g.ny * g.res / 2
half = g.nx * g.res / 2
hf = doc.heightfield()
zat = lambda x, y: float(hf.sample(np.array([x]), np.array([y]))[0])
cam = vr.add_camera((cx, cy, 500), (cx, cy, 0), 40 if a.mode == "orbit" else 28)
cam.data.clip_end = 60000
if a.mode == "fly":
    lines = sorted(doc.vectors["rivers"], key=lambda t: -t[0].length)
    pts = np.concatenate([np.asarray(ln.coords) for ln, _ in lines[:1]])
    pts = pts[::-1] if hf.sample(pts[:1, 0], pts[:1, 1])[0] < hf.sample(pts[-1:, 0], pts[-1:, 1])[0] else pts
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    from scipy.ndimage import gaussian_filter1d
    sm = np.stack([gaussian_filter1d(pts[:, 0], 6, mode="nearest"), gaussian_filter1d(pts[:, 1], 6, mode="nearest")], 1)
    t = np.linspace(0, s[-1], a.frames + 40)
    path = np.stack([np.interp(t, s, sm[:, 0]), np.interp(t, s, sm[:, 1])], 1)


def pose(f):
    if a.mode == "orbit":
        ang = math.radians(-20 + a.sweep * f / max(a.frames - 1, 1))
        d = half * 3.0
        x, y = cx + d * math.sin(ang), cy - d * math.cos(ang)
        return (x, y, zat(cx, cy) + d * 0.5 + 60), (cx, cy, zat(cx, cy) + 20)
    p, q = path[f], path[min(f + 40, len(path) - 1)]
    return (p[0], p[1], zat(*p) + a.alt), (q[0], q[1], zat(*q) + a.alt * 0.5)


from mathutils import Vector  # noqa: E402

work = Path(tempfile.mkdtemp(prefix="terra_vid_"))
ev = None
for f in range(a.frames):
    loc, tgt = pose(f)
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    if ev is None:
        ev = R.estimate_ev(0.2)
    sc = bpy.context.scene
    sc.view_settings.look = "AgX - Base Contrast"
    sc.view_settings.exposure = ev
    vr.set_glare_threshold(ev)
    p = work / f"f{f:04d}.png"
    vr.render(p)
    vr.postprocess(p, seed=f)
    print("frame", f, flush=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", str(work / "f%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "26", "-preset", "medium", "-movflags", "+faststart", "-vf", "scale=1280:720", a.out], check=True)
print("wrote", a.out, Path(a.out).stat().st_size // 1024, "KB")
