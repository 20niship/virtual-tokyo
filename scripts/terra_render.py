"""Terra ドキュメントの Cycles レンダ(vt.render の写実カメラ設定を再利用)。"""
import argparse
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("dir")
ap.add_argument("--view", nargs="+", default=["oblique"], choices=["oblique", "ground", "all"])
ap.add_argument("-o", "--out", default=None)
ap.add_argument("--name", default=None)
ap.add_argument("--look", default="photoreal", choices=["photoreal", "legacy"])
ap.add_argument("--res", default="1280x720")
ap.add_argument("--samples", type=int, default=32)
ap.add_argument("--box", default="", help="x0,y0,x1,y1(ローカル m)。省略=全体")
ap.add_argument("--lens", type=float, default=0)
ap.add_argument("--fstop", type=float, default=5.6)
ap.add_argument("--no-dof", action="store_true")
ap.add_argument("--stride", type=int, default=1, help="地形メッシュの間引き")
ap.add_argument("--no-water", action="store_true")
ap.add_argument("--no-scatter", action="store_true")
ap.add_argument("--splat", action="store_true", help="biome の splat 材質(w0/w1)を使う")
ap.add_argument("--time", default="day")
ap.add_argument("--pose", default="", help="カメラ直指定 'x,y,z,tx,ty,tz'")
a = ap.parse_args()

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from terra import render as R  # noqa: E402
from terra.core import Document  # noqa: E402

from vt import render as vr  # noqa: E402

doc = Document.load(a.dir)
res = tuple(int(v) for v in a.res.split("x"))
box = tuple(float(v) for v in a.box.split(",")) if a.box else None
out = Path(a.out or a.dir)
name = a.name or Path(a.dir).name
views = ["oblique", "ground"] if "all" in a.view else a.view
for v in views:
    vr.PHOTO = a.look == "photoreal"
    R.photo_setup(doc, res, a.samples, a.time)
    splat = None
    if a.splat and "splat_w0" in doc.layers:
        splat = dict(w0=doc.layers["splat_w0"], w1=doc.layers["splat_w1"])
    R.terrain_object(doc, box=box, stride=a.stride, splat=splat)
    R.add_far_plane(doc)
    if not a.no_water:
        R.add_water(doc)
    if doc.scatter and not a.no_scatter:
        from terra.export.scatter_assets import load_protos
        n = R.add_scatter(doc, load_protos(doc))
        print("instances:", n)
    pose = None
    if a.pose:
        p = [float(x) for x in a.pose.split(",")]
        pose = (tuple(p[:3]), tuple(p[3:]))
    R.make_camera(doc, v, box, a.lens, a.fstop, not a.no_dof, pose=pose)
    ev = R.finish(out / f"{name}_{v}.png")
    print(f"{v}: exposure {ev:+.2f} EV -> {out / f'{name}_{v}.png'}")
