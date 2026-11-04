"""Anny 人物の USD 出力: UsdSkel(スケルトン+スキンウェイト+歩行アニメ)のヒーローアセットと、姿勢を焼いた軽量メッシュ。
座標はモジュール規約(前=+y、足元 z=0、m)。テクスチャ・材質は assets/textures を ../textures で参照する。"""
import math
import re
from pathlib import Path

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdSkel, Vt

from . import humans as H
from .usd_out import define_materials

ROOT = H.ROOT
HDIR = ROOT / "assets/humans"


def _T(ground):
    c, s = math.cos(math.pi), math.sin(math.pi)
    T = np.eye(4)
    T[0, 0], T[0, 1], T[1, 0], T[1, 1] = c, -s, s, c
    T[2, 3] = -ground
    return T


def _gf(M):
    return Gf.Matrix4d(*M.T.reshape(-1).tolist())


def _top6(cw):
    idx = np.argsort(-cw, axis=1)[:, :4]
    w = np.take_along_axis(cw, idx, axis=1)
    w = w / np.maximum(w.sum(1, keepdims=True), 1e-9)
    return idx, w


def _skin_attrs(prim, idx, w, n):
    api = UsdSkel.BindingAPI.Apply(prim)
    api.CreateGeomBindTransformAttr().Set(Gf.Matrix4d(1.0))
    ji = api.CreateJointIndicesPrimvar(False, 4)
    ji.Set(Vt.IntArray(np.asarray(idx, dtype=np.int32).reshape(-1).tolist()))
    jw = api.CreateJointWeightsPrimvar(False, 4)
    jw.Set(Vt.FloatArray(np.asarray(w, dtype=np.float32).reshape(-1).tolist()))
    return api


def _joint_paths(parents, names):
    paths = []
    for i, p in enumerate(parents):
        paths.append(names[i] if p < 0 else paths[p] + "/" + names[i])
    return paths


def _mesh(st, path, V, faces, mat_of_face, mats, uv=None, uv_idx=None, normals=None, hair=False):
    """点は共有、材質ごとに GeomSubset。faces は三角形または可変長(list[list[int]])。"""
    g = UsdGeom.Mesh.Define(st, path)
    g.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*p) for p in V.tolist()]))
    counts = [len(f) for f in faces]
    g.CreateFaceVertexCountsAttr(Vt.IntArray(counts))
    g.CreateFaceVertexIndicesAttr(Vt.IntArray([int(i) for f in faces for i in f]))
    g.CreateSubdivisionSchemeAttr("none")
    if hair:
        g.CreateDoubleSidedAttr(True)
    if normals is not None:
        g.CreateNormalsAttr(Vt.Vec3fArray([Gf.Vec3f(*n) for n in normals.tolist()])); g.SetNormalsInterpolation("vertex")
    if uv is not None:
        pv = UsdGeom.PrimvarsAPI(g).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
        pv.Set(Vt.Vec2fArray([Gf.Vec2f(*uv[j]) for f in uv_idx for j in f]))
    by = {}
    for i, m in enumerate(mat_of_face):
        by.setdefault(m, []).append(i)
    if len(by) == 1:
        UsdShade.MaterialBindingAPI.Apply(g.GetPrim()).Bind(mats[next(iter(by))])
    else:
        UsdShade.MaterialBindingAPI.Apply(g.GetPrim()).Bind(mats[next(iter(by))])
        for m, ids in by.items():
            ss = UsdGeom.Subset.Define(st, f"{path}/{m}")
            ss.CreateElementTypeAttr("face"); ss.CreateIndicesAttr(Vt.IntArray(ids)); ss.CreateFamilyNameAttr("materialBind")
            UsdShade.MaterialBindingAPI.Apply(ss.GetPrim()).Bind(mats[m])
    return g


def _body_mats(b, parts):
    of = b["outfit"]
    skin = f"anny_skin_{of['skin']}"
    out = []
    for p in parts:
        out.append("anny_iris" if p.startswith("eye_front") else "anny_sclera" if p.startswith("eye_back") else "anny_mouth" if p in ("mouth_cavity", "tongue") else "anny_eye_dark" if p.startswith("eye_cavity") else skin)
    return out


def walk_clip(spec, frames=24):
    """歩行1周期: (frames,B,4,4) のワールド骨行列(Anny座標)"""
    from . import humans_motion as HM
    return np.array([H.run(spec["p"], "anny", HM.pose_at("walk", i / frames), spec.get("local"), spec.get("expr"))["bone_poses"] for i in range(frames)])


def write_hero(spec, path=None, outfit=None, anim=True):
    """UsdSkel の人物1体(体+服+髪+靴)を assets/humans/<id>.usdc へ"""
    HDIR.mkdir(parents=True, exist_ok=True)
    path = Path(path or HDIR / f"{spec['id']}.usdc")
    b = H.build(spec, outfit, topology="anny", posename="stand")
    m = H.model("anny")
    g = float(b["rest"][:, 2].min()) - 0.007
    T = _T(g)
    of = b["outfit"]
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z); UsdGeom.SetStageMetersPerUnit(st, 1.0)
    st.SetStartTimeCode(0); st.SetEndTimeCode(23); st.SetTimeCodesPerSecond(24)
    root = UsdSkel.Root.Define(st, f"/{spec['id']}")
    st.SetDefaultPrim(root.GetPrim())
    P = f"/{spec['id']}"
    pr = root.GetPrim()
    for k, v, t in (("vt:group", spec["group"], Sdf.ValueTypeNames.String), ("vt:years", float(spec["years"]), Sdf.ValueTypeNames.Float),
                    ("vt:female", bool(spec["female"]), Sdf.ValueTypeNames.Bool), ("vt:height_m", float(b["rest"][:, 2].max() - b["rest"][:, 2].min()), Sdf.ValueTypeNames.Float)):
        pr.CreateAttribute(k, t).Set(v)
    used = {"anny_iris", "anny_sclera", "anny_mouth", "anny_eye_dark", f"anny_skin_{of['skin']}", f"anny_shoe_{of['shoe_color']}"}
    for c in b["cloth"]:
        used.add(c["mat"])
    mats = define_materials(st, f"{P}/Materials", only=used, texdir="../textures")
    # スケルトン
    names = list(m.bone_labels)
    joints = _joint_paths(m.bone_parents, names)
    sk = UsdSkel.Skeleton.Define(st, f"{P}/Skel")
    sk.CreateJointsAttr(Vt.TokenArray(joints))
    bind = np.einsum("ij,bjk->bik", T, b["bones_rest"])
    sk.CreateBindTransformsAttr(Vt.Matrix4dArray([_gf(M) for M in bind]))
    rest_local = [bind[i] if m.bone_parents[i] < 0 else np.linalg.inv(bind[m.bone_parents[i]]) @ bind[i] for i in range(len(names))]
    sk.CreateRestTransformsAttr(Vt.Matrix4dArray([_gf(M) for M in rest_local]))
    bapi = UsdSkel.BindingAPI.Apply(root.GetPrim())
    bapi.CreateSkeletonRel().SetTargets([Sdf.Path(f"{P}/Skel")])
    # 体
    V = H.to_world(b["rest"], ground=g)
    uv = m.texture_coordinates.numpy()
    fu = m.face_texture_coordinate_indices.numpy()
    nrm = H._vnormals(V, b["faces"])
    body = _mesh(st, f"{P}/Body", V, b["faces"].tolist(), _body_mats(b, b["parts"]), mats, None, None, nrm)
    ab = _skin_attrs(body.GetPrim(), *_top6(b["W"]), len(V))
    ab.CreateSkeletonRel().SetTargets([Sdf.Path(f"{P}/Skel")])
    # 服・髪
    for c in b["cloth"]:
        Vc = H.to_world(c["Vrest"], ground=g)
        faces = [[vi for vi, _ in f] for f in c["cl"]["faces"]]
        hair = c["uv"]
        mat = c["mat"]
        vt = c["cl"]["vt"]
        uvi = [[t for _, t in f] for f in c["cl"]["faces"]] if hair else None
        # 三角形/四角形の頂点法線
        tri = [f if len(f) == 3 else f[:3] for f in faces]
        nc = H._vnormals(Vc, np.array(tri))
        pn = re.sub(r"\W", "_", c["name"])[:16]
        gm = _mesh(st, f"{P}/{c['slot'].capitalize()}_{pn}", Vc, faces, [mat] * len(faces), mats, vt if hair else None, uvi, nc, hair=hair)
        idx, w = _top6(c["cw"])
        ac = _skin_attrs(gm.GetPrim(), idx, w, len(Vc))
        ac.CreateSkeletonRel().SetTargets([Sdf.Path(f"{P}/Skel")])
    # 靴(足の面を押し出し)
    F, parts = b["full"]["faces"], b["full"]["parts"]
    sel = [i for i, p in enumerate(parts) if p.startswith("foot")]
    vi = np.unique(F[sel])
    rm = {int(v): i for i, v in enumerate(vi)}
    Vs = H.to_world(b["rest"][vi] + H._vnormals(b["rest"], F)[vi] * 0.007, ground=g)
    gs = _mesh(st, f"{P}/Shoes", Vs, [[rm[int(v)] for v in F[i]] for i in sel], [f"anny_shoe_{of['shoe_color']}"] * len(sel), mats)
    Wd = b["W"][vi]
    idx, w = _top6(Wd)
    asx = _skin_attrs(gs.GetPrim(), idx, w, len(Vs))
    asx.CreateSkeletonRel().SetTargets([Sdf.Path(f"{P}/Skel")])
    # 歩行アニメ
    if anim:
        clip = walk_clip(spec)
        an = UsdSkel.Animation.Define(st, f"{P}/Skel/WalkAnim")
        an.CreateJointsAttr(Vt.TokenArray(joints))
        from scipy.spatial.transform import Rotation as Rot
        for fi, bones in enumerate(clip):
            Wm = np.einsum("ij,bjk->bik", T, bones)
            loc = [Wm[i] if m.bone_parents[i] < 0 else np.linalg.inv(Wm[m.bone_parents[i]]) @ Wm[i] for i in range(len(names))]
            q = Rot.from_matrix(np.array([l[:3, :3] for l in loc])).as_quat()
            an.GetTranslationsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*l[:3, 3]) for l in loc]), fi)
            an.GetRotationsAttr().Set(Vt.QuatfArray([Gf.Quatf(float(x[3]), float(x[0]), float(x[1]), float(x[2])) for x in q]), fi)
            an.GetScalesAttr().Set(Vt.Vec3hArray([Gf.Vec3h(1, 1, 1)] * len(loc)), fi)
        bapi.CreateAnimationSourceRel().SetTargets([Sdf.Path(f"{P}/Skel/WalkAnim")])
    st.GetRootLayer().Save()
    return path


def write_baked(group, k, posename, path=None):
    """姿勢を焼いた軽量メッシュ版(モジュールと同じ低ポリ)を assets/humans/baked/<group>_<k>_<pose>.usdc へ"""
    from .modules import lib_anny
    from .modules.geom import Mesh
    from .usd_out import _mesh_prims
    (HDIR / "baked").mkdir(parents=True, exist_ok=True)
    path = Path(path or HDIR / "baked" / f"{group}_{k}_{posename}.usdc")
    m = Mesh()
    lib_anny.build_mesh(m, group, k, lib_anny.LOD, pose_override=(posename, 0.9))
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z); UsdGeom.SetStageMetersPerUnit(st, 1.0)
    nm = path.stem
    root = UsdGeom.Xform.Define(st, f"/{nm}")
    st.SetDefaultPrim(root.GetPrim())
    mats = define_materials(st, f"/{nm}/Materials", only=set(m.m), texdir="../../textures")
    UsdGeom.Scope.Define(st, f"/{nm}/Geom")
    _mesh_prims(st, f"/{nm}/Geom", m, mats)
    st.GetRootLayer().Save()
    return path
