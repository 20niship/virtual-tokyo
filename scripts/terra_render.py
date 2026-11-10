"""Terra ドキュメントの Cycles レンダ(vt.render の写実カメラ設定を再利用)。--detail near|far|legacy で詳細度プロファイルを切り替える。"""
import argparse
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("dir")
ap.add_argument("--view", nargs="+", default=["oblique"], choices=["oblique", "ground", "all", "near", "road"])
ap.add_argument("-o", "--out", default=None)
ap.add_argument("--name", default=None)
ap.add_argument("--look", default="photoreal", choices=["photoreal", "legacy"])
ap.add_argument("--detail", default="far", choices=["far", "near", "legacy"],
                help="far=低ポリ+法線ベイク+散布を間引き+強い大気遠近 / near=視点周辺を 0.5m 格子+微細起伏+高密度散布(view=near で有効) / legacy=従来")
ap.add_argument("--half", type=float, default=110.0, help="near スポットの半幅[m]")
ap.add_argument("--near-res", type=float, default=0.5)
ap.add_argument("--res", default="1280x720")
ap.add_argument("--samples", type=int, default=32)
ap.add_argument("--box", default="", help="x0,y0,x1,y1(ローカル m)。省略=全体")
ap.add_argument("--lens", type=float, default=0)
ap.add_argument("--fstop", type=float, default=5.6)
ap.add_argument("--no-dof", action="store_true")
ap.add_argument("--stride", type=int, default=0, help="地形メッシュの間引き(0=プロファイル既定: far 4 / near の遠景 2 / legacy 1)")
ap.add_argument("--road-widen", type=float, default=0, help="路面を太らせる倍率(0=far は 1.7・それ以外は 1.0)")
ap.add_argument("--no-water", action="store_true")
ap.add_argument("--no-scatter", action="store_true")
ap.add_argument("--no-splat", action="store_true", help="biome があっても頂点色表示にする")
ap.add_argument("--hi-dist", type=float, default=150.0, help="樹木を高ポリにする距離[m]")
ap.add_argument("--time", default="day")
ap.add_argument("--pose", default="", help="カメラ直指定 'x,y,z,tx,ty,tz'")
ap.add_argument("--only", default="", help="near/road 視点のうち描くものの名前(カンマ区切り。例: road_cut,road_aerial)")
ap.add_argument("--stats", default="", help="ポリゴン数・インスタンス数・時間を JSON で追記するファイル")
a = ap.parse_args()

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import json  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from terra import detail as D  # noqa: E402
from terra import render as R  # noqa: E402
from terra.core import Document  # noqa: E402
from terra.export.scatter_assets import load_protos  # noqa: E402

from vt import render as vr  # noqa: E402

doc = Document.load(a.dir)
res = tuple(int(v) for v in a.res.split("x"))
box = tuple(float(v) for v in a.box.split(",")) if a.box else None
out = Path(a.out or a.dir)
name = a.name or Path(a.dir).name
views = ["oblique", "ground"] if "all" in a.view else a.view
poses_far = R.near_poses(doc) if "near" in views else {}
if "road" in views:
    poses_far.update(R.road_poses(doc))
if a.only:
    poses_far = {k: v for k, v in poses_far.items() if k in a.only.split(",")}
if "near" in views or "road" in views:
    views = [v for v in views if v not in ("near", "road")] + ["near_" + k for k in poses_far]


def faces_of(objs):
    return sum(len(o.data.polygons) for o in objs if o.type == "MESH")


def scatter_faces(objs):
    """インスタンスの総三角形数の概算 = オブジェクト(点群)ごとの点数 x 原形の面数"""
    tot, n = 0, 0
    for o in objs:
        if o.name.endswith("_src") or o.type != "MESH":
            continue
        if any(md.type == "NODES" for md in o.modifiers):
            src = bpy.data.objects.get(o.name + "_src")
            k = len(o.data.vertices)
            n += k
            tot += k * (len(src.data.polygons) if src else 0)
    return tot, n


for v in views:
    t0 = time.time()
    vr.PHOTO = a.look == "photoreal"
    R.photo_setup(doc, res, a.samples, a.time)
    if a.detail == "far":
        vr.HAZE_K["day"] = 1.3e-4        # 遠景は大気遠近(霞・青み)を強める
    near = None
    pose = None
    splat = R.splat_from_doc(doc) if not a.no_splat else None
    terr = []
    if v.startswith("near_"):
        pose = poses_far[v[5:]]
        if a.detail == "near":
            near = D.make_near_doc(doc, pose[1][:2], a.half, a.near_res, doc.seed)
            D.clear_view(near, pose[0], pose[1])
            terr, big = R.terrain_parts(doc, near.meta["near_box"], a.stride or 2, splat)
            terr.append(R.terrain_object(near, "terrain_near", stride=1, splat=R.splat_from_doc(near), pad=0))
            R.add_far_plane(doc)
        else:
            terr.append(R.terrain_object(doc, box=box, stride=a.stride or 1, splat=splat))
            R.add_far_plane(doc)
    else:
        stride = a.stride or {"far": 4, "legacy": 1, "near": 2}[a.detail]
        nrm = None
        if a.detail == "far" and splat is not None:
            big, _, _ = R._padded(doc, None, splat, 0.35)
            nrm = R.bake_normal_image(big)
        terr.append(R.terrain_object(doc, box=box, stride=stride, splat=splat, normal_image=nrm))
        R.add_far_plane(doc)
    R.add_roads(doc, a.road_widen or (1.7 if a.detail == "far" else 1.0))
    if not a.no_water:
        R.add_water(doc)
        if near is not None:
            R.add_water(near)
    if a.pose:
        p = [float(x) for x in a.pose.split(",")]
        pose = (tuple(p[:3]), tuple(p[3:]))
    cam = R.make_camera(doc, v if not v.startswith("near_") else "ground", box, a.lens, a.fstop, not a.no_dof, pose=pose)
    ninst = 0
    if doc.scatter and not a.no_scatter:
        camp = tuple(cam.location)
        far_doc = doc
        if near is not None:                                          # 穴の中の far 散布は除く
            bx = near.meta["near_box"]
            far_doc = Document(doc.grid, doc.seed)
            for k, s in doc.scatter.items():
                m = np.ones(len(s["pos"]), bool) if k in ("road_furniture", "village") else ~((s["pos"][:, 0] > bx[0]) & (s["pos"][:, 0] < bx[2]) & (s["pos"][:, 1] > bx[1]) & (s["pos"][:, 1] < bx[3]))
                far_doc.scatter[k] = {f: (val[m] if f != "assets" else val) for f, val in s.items()}
        if a.detail == "far":                                          # 遠景用: 低木・草・地面パッチを省き、木は 2 割間引く
            rs = np.random.default_rng(1)
            far_doc.scatter = {k: ({f: (val[m] if f != "assets" else val) for f, val in s.items()} if k not in ("shrubs", "ground", "floor") else None) for k, s in far_doc.scatter.items()
                               for m in [rs.random(len(s["pos"])) < (0.8 if k == "trees" else 1.0)]}
            far_doc.scatter = {k: s for k, s in far_doc.scatter.items() if s is not None}
        ninst += R.add_scatter(far_doc, load_protos(far_doc), camp, a.hi_dist)
        if near is not None:
            ninst += R.add_scatter(near, load_protos(near), camp, 1e9)
    ev = R.finish(out / f"{name}_{v}.png", *((0.8, 92) if v.startswith("near_") else (0.2, 50)))
    tf = faces_of(terr)
    objs = list(bpy.data.objects)
    sf, sn = scatter_faces(objs)
    st = dict(view=v, detail=a.detail, terrain_faces=tf, instances=ninst, instance_faces_total=sf, secs=round(time.time() - t0, 1), exposure=round(ev, 2))
    print(json.dumps(st))
    if a.stats:
        with open(a.stats, "a") as f:
            f.write(json.dumps(st) + "\n")
