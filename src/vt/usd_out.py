"""USD出力: モジュールを1つずつ assets/modules/<name>.usdc に書き出し、建物は PointInstancer で参照する。"""
import math
from pathlib import Path

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade, Vt

from .materials import MATERIALS

ROOT = Path(__file__).resolve().parents[2]
MODDIR = ROOT / "assets/modules"
OUTDIR = ROOT / "out/usd"


def _rgb(h):
    h = h.lstrip("#")
    return Gf.Vec3f(*[int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def define_materials(stage, root="/Materials", only=None, texdir="../../assets/textures"):
    UsdGeom.Scope.Define(stage, root)
    out = {}
    for mid, d in MATERIALS.items():
        if only is not None and mid not in only:
            continue
        m = UsdShade.Material.Define(stage, f"{root}/{mid}")
        sh = UsdShade.Shader.Define(stage, f"{root}/{mid}/PBR")
        sh.CreateIdAttr("UsdPreviewSurface")
        sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(_rgb(d["color"]))
        sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(d["rough"]))
        sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(d["metal"]))
        if d.get("glass"):
            sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.25)
        if d.get("tex"):
            _tex(stage, m, sh, f"{root}/{mid}", d, texdir)
        if d.get("emit"):
            sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(_rgb(d["emit"][0]) * d["emit"][1] * 0.3)
        m.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
        out[mid] = m
    return out


def _tex(stage, mat, sh, path, d, texdir):
    """UsdUVTexture(必要ならUsdTransform2dでメートル→タイル変換)をdiffuseColor(とアルファ)へ接続"""
    rd = UsdShade.Shader.Define(stage, path + "/st")
    rd.CreateIdAttr("UsdPrimvarReader_float2"); rd.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    src = rd.ConnectableAPI()
    size = d.get("size")
    if size:
        sx, sy = (size, size) if not isinstance(size, tuple) else size
        tr = UsdShade.Shader.Define(stage, path + "/xf")
        tr.CreateIdAttr("UsdTransform2d")
        tr.CreateInput("in", Sdf.ValueTypeNames.Float2).ConnectToSource(rd.ConnectableAPI(), "result")
        tr.CreateInput("scale", Sdf.ValueTypeNames.Float2).Set(Gf.Vec2f(1 / sx, 1 / sy))
        src = tr.ConnectableAPI()
    tx = UsdShade.Shader.Define(stage, path + "/tex")
    tx.CreateIdAttr("UsdUVTexture")
    tx.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(f"{texdir}/{d['tex']}"))
    tx.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(src, "result" if size else "result")
    tx.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat" if size else "clamp")
    tx.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat" if size else "clamp")
    tx.CreateOutput("rgb", Sdf.ValueTypeNames.Float3); tx.CreateOutput("a", Sdf.ValueTypeNames.Float)
    sh.GetInput("diffuseColor").ConnectToSource(tx.ConnectableAPI(), "rgb")
    if d.get("alpha"):
        sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).ConnectToSource(tx.ConnectableAPI(), "a")
        if d.get("cutout"):
            sh.CreateInput("opacityThreshold", Sdf.ValueTypeNames.Float).Set(float(d["cutout"]))


def _mesh_prims(stage, parent, mesh, mats, offset=(0, 0, 0)):
    """材質ごとに1つのUsdGeomMeshを作る(フラット法線 + ボックス投影UV[m])"""
    by = {}
    uvs = mesh.uv if len(mesh.uv) == len(mesh.f) else [None] * len(mesh.f)
    for f, m, u in zip(mesh.f, mesh.m, uvs):
        by.setdefault(m, []).append((f, u))
    for mat, faces in by.items():
        pts, counts, idx, nrm, uv = [], [], [], [], []
        for f, fuv in faces:
            P = np.array([mesh.v[i] for i in f], dtype=np.float64)
            n = np.cross(P[1] - P[0], P[2] - P[0]) if len(f) >= 3 else np.zeros(3)
            ln = np.linalg.norm(n)
            n = n / ln if ln > 1e-12 else np.array([0, 0, 1.0])
            ax = int(np.abs(n).argmax())
            base = len(pts)
            for k, p in enumerate(P):
                pts.append(Gf.Vec3f(*(p + offset)))
                nrm.append(Gf.Vec3f(*n))
                if fuv is not None:
                    u, v = fuv[k]
                else:
                    u, v = ((p[1], p[2]) if ax == 0 else (p[0], p[2]) if ax == 1 else (p[0], p[1]))
                uv.append(Gf.Vec2f(float(u), float(v)))
            counts.append(len(f))
            idx.extend(range(base, base + len(f)))
        g = UsdGeom.Mesh.Define(stage, f"{parent}/{mat}")
        g.CreatePointsAttr(Vt.Vec3fArray(pts))
        g.CreateFaceVertexCountsAttr(Vt.IntArray(counts))
        g.CreateFaceVertexIndicesAttr(Vt.IntArray(idx))
        g.CreateNormalsAttr(Vt.Vec3fArray(nrm)); g.SetNormalsInterpolation("faceVarying")
        g.CreateSubdivisionSchemeAttr("none")
        if MATERIALS.get(mat, {}).get("double_sided"):
            g.CreateDoubleSidedAttr(True)
        pv =UsdGeom.PrimvarsAPI(g).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
        pv.Set(Vt.Vec2fArray(uv))
        UsdShade.MaterialBindingAPI.Apply(g.GetPrim()).Bind(mats[mat])


def write_module(name, mesh, meta):
    MODDIR.mkdir(parents=True, exist_ok=True)
    path = MODDIR / f"{name}.usdc"
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z); UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = UsdGeom.Xform.Define(st, f"/{name}")
    st.SetDefaultPrim(root.GetPrim())
    p = root.GetPrim()
    p.SetCustomDataByKey("vt", {"category": meta["cat"], "span_w": meta["W"], "floor_h": meta["H"]})
    p.CreateAttribute("vt:module_type", Sdf.ValueTypeNames.String).Set(meta["cat"])
    p.CreateAttribute("vt:span_w", Sdf.ValueTypeNames.Float).Set(float(meta["W"]))
    p.CreateAttribute("vt:height", Sdf.ValueTypeNames.Float).Set(float(meta["H"]))
    mats = define_materials(st, f"/{name}/Materials", only=set(mesh.m), texdir="../textures")
    UsdGeom.Scope.Define(st, f"/{name}/Geom")
    _mesh_prims(st, f"/{name}/Geom", mesh, mats)
    _write_lights(st, f"/{name}/Lights", getattr(mesh, "lights", []))
    st.GetRootLayer().Save()
    return path


def _write_lights(st, root, lights):
    """UsdLux光源。光束[lm]からランバート面光源の輝度(nit)を換算: 球 Φ=4π²r²L / 円盤 Φ=π²r²L / 矩形 Φ=π·w·h·L。+Z方向を向くように回転"""
    if not lights:
        return
    UsdGeom.Scope.Define(st, root)
    for i, l in enumerate(lights):
        path = f"{root}/light{i}"
        kind, lm = l["type"], l["lumens"]
        r = max(l.get("radius", 0.05), 1e-3)
        if kind == "sphere":
            lt = UsdLux.SphereLight.Define(st, path); lt.CreateRadiusAttr(r)
            L = lm / (4 * math.pi ** 2 * r * r)
        elif kind == "disk":
            lt = UsdLux.DiskLight.Define(st, path); lt.CreateRadiusAttr(r)
            L = lm / (math.pi ** 2 * r * r)
        else:
            w, h = l.get("size", (0.1, 0.1))
            lt = UsdLux.RectLight.Define(st, path); lt.CreateWidthAttr(w); lt.CreateHeightAttr(h)
            L = lm / (math.pi * w * h)
        lt.CreateIntensityAttr(float(L))
        lt.CreateColorAttr(Gf.Vec3f(*l["color"]))
        if l.get("cct"):
            lt.CreateEnableColorTemperatureAttr(True); lt.CreateColorTemperatureAttr(float(l["cct"]))
        lt.GetPrim().CreateAttribute("vt:lumens", Sdf.ValueTypeNames.Float).Set(float(lm))
        x = UsdGeom.Xformable(lt.GetPrim())
        x.AddTranslateOp().Set(Gf.Vec3d(*l["pos"]))
        d = Gf.Vec3d(*l.get("dir", (0, 0, -1)))
        if d.GetLength() > 0:
            rot = Gf.Rotation(Gf.Vec3d(0, 0, -1), d.GetNormalized())
            x.AddOrientOp().Set(Gf.Quatf(rot.GetQuat()))


def write_all_modules(log=print):
    """モジュールを登録順に1つずつ生成。"""
    from .modules.library import REG, get
    paths = []
    for i, (n, r) in enumerate(REG.items(), 1):
        m = get(n)
        paths.append(write_module(n, m, r))
        log(f"[{i}/{len(REG)}] {n}: {len(m.f)} faces -> {paths[-1].relative_to(ROOT)}")
    return paths


def write_world_mesh(name, mesh, path=None):
    """地面/道路/線路など1つの大きなメッシュ → out/usd/<name>.usda (材質ごとにMesh、テクスチャは相対パス)"""
    OUTDIR.mkdir(parents=True, exist_ok=True)
    path = path or OUTDIR / f"{name}.usdc"
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z); UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = UsdGeom.Xform.Define(st, f"/City/{name.capitalize()}")
    UsdGeom.Xform.Define(st, "/City"); st.SetDefaultPrim(st.GetPrimAtPath("/City"))
    mats = define_materials(st, "/City/Materials", only=set(mesh.m))
    UsdGeom.Scope.Define(st, f"/City/{name.capitalize()}/Geom")
    _mesh_prims(st, f"/City/{name.capitalize()}/Geom", mesh, mats)
    st.GetRootLayer().Save()
    return path


def write_city(layers, path=None):
    """各レイヤーUSDを束ねるルート(city.usda)"""
    path = path or OUTDIR / "city.usda"
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z); UsdGeom.SetStageMetersPerUnit(st, 1.0)
    for p in layers:
        st.GetRootLayer().subLayerPaths.append(f"./{Path(p).name}")
    st.GetRootLayer().Save()
    return path


def write_furniture(insts, path=None):
    """道路ファニチャ(信号/街灯/標識)の全インスタンスを1つのPointInstancerで。モジュール側に UsdLux 光源を持つ"""
    OUTDIR.mkdir(parents=True, exist_ok=True)
    path = path or OUTDIR / "furniture.usda"
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z); UsdGeom.SetStageMetersPerUnit(st, 1.0)
    UsdGeom.Xform.Define(st, "/City"); st.SetDefaultPrim(st.GetPrimAtPath("/City"))
    UsdGeom.Xform.Define(st, "/City/Furniture")
    pi = UsdGeom.PointInstancer.Define(st, "/City/Furniture/Instances")
    UsdGeom.Scope.Define(st, "/City/Furniture/Instances/Prototypes")
    names = sorted({i.name for i in insts})
    protos = []
    for n in names:
        pp = f"/City/Furniture/Instances/Prototypes/{n}"
        st.DefinePrim(pp, "Xform").GetReferences().AddReference(f"../../assets/modules/{n}.usdc")
        protos.append(Sdf.Path(pp))
    pi.CreatePrototypesRel().SetTargets(protos)
    ix = {n: i for i, n in enumerate(names)}
    pi.CreateProtoIndicesAttr(Vt.IntArray([ix[i.name] for i in insts]))
    pi.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(i.x, i.y, i.z) for i in insts]))
    pi.CreateOrientationsAttr(Vt.QuathArray([Gf.Quath(math.cos(i.rot / 2), 0, 0, math.sin(i.rot / 2)) for i in insts]))
    pi.CreateScalesAttr(Vt.Vec3fArray([Gf.Vec3f(i.sx, i.sy, i.sz) for i in insts]))
    st.GetRootLayer().Save()
    return path


BLDDIR = ROOT / "assets/buildings"


def write_building_asset(b, path):
    """1棟を単体の USD アセットとして書く(assets/buildings/b<id>.usda)。
    シェル(躯体メッシュ)+モジュールは assets/modules/*.usdc への参照を持つ PointInstancer。座標は都市ローカル(m)のまま。"""
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z); UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = UsdGeom.Xform.Define(st, "/B"); st.SetDefaultPrim(root.GetPrim())
    pr = root.GetPrim()
    for k, v, t in (("vt:osm_id", b.id, Sdf.ValueTypeNames.Int64), ("vt:style", b.meta["style"], Sdf.ValueTypeNames.String),
                    ("vt:levels", b.meta["floors"], Sdf.ValueTypeNames.Int), ("vt:height", float(b.meta["height"]), Sdf.ValueTypeNames.Float),
                    ("vt:bvar", float(b.meta["bvar"]), Sdf.ValueTypeNames.Float)):
        pr.CreateAttribute(k, t).Set(v)
    mats = define_materials(st, "/B/Materials", only={"core", "roof_membrane"} | set(b.shell.m), texdir="../textures")
    UsdGeom.Scope.Define(st, "/B/Shell")
    _mesh_prims(st, "/B/Shell", b.shell, mats)
    names = sorted({i.name for i in b.insts})
    pi = UsdGeom.PointInstancer.Define(st, "/B/Modules")
    UsdGeom.Scope.Define(st, "/B/Modules/Prototypes")
    protos = []
    for n in names:
        pp = f"/B/Modules/Prototypes/{n}"
        st.DefinePrim(pp, "Xform").GetReferences().AddReference(f"../modules/{n}.usdc")
        protos.append(Sdf.Path(pp))
    pi.CreatePrototypesRel().SetTargets(protos)
    ix = {n: i for i, n in enumerate(names)}
    pi.CreateProtoIndicesAttr(Vt.IntArray([ix[i.name] for i in b.insts]))
    pi.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(i.x, i.y, i.z) for i in b.insts]))
    pi.CreateOrientationsAttr(Vt.QuathArray([Gf.Quath(math.cos(i.rot / 2), 0, 0, math.sin(i.rot / 2)) for i in b.insts]))
    pi.CreateScalesAttr(Vt.Vec3fArray([Gf.Vec3f(i.sx, i.sy, i.sz) for i in b.insts]))
    st.GetRootLayer().Save()
    return path


def write_buildings_ref(builts, path=None, assets=True):
    """建物ごとの単体アセット(assets/buildings/)を書き、都市側は references で束ねる軽量レイヤを書く。"""
    OUTDIR.mkdir(parents=True, exist_ok=True); BLDDIR.mkdir(parents=True, exist_ok=True)
    path = path or OUTDIR / "buildings.usda"
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z); UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = UsdGeom.Xform.Define(st, "/City"); st.SetDefaultPrim(root.GetPrim())
    UsdGeom.Xform.Define(st, "/City/Buildings")
    for b in builts:
        f = write_building_asset(b, BLDDIR / f"b{b.id}.usda")
        st.DefinePrim(f"/City/Buildings/b{b.id}", "Xform").GetReferences().AddReference(f"../../assets/buildings/{f.name}")
    st.GetRootLayer().Save()
    return path


def write_buildings(builts, path=None):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    path = path or OUTDIR / "buildings.usda"
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z); UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = UsdGeom.Xform.Define(st, "/City"); st.SetDefaultPrim(root.GetPrim())
    mats = define_materials(st, "/City/Materials", only={"core", "roof_membrane"}.union(*(set(b.shell.m) for b in builts)))
    UsdGeom.Xform.Define(st, "/City/Buildings")
    for b in builts:
        bp = f"/City/Buildings/b{b.id}"
        x = UsdGeom.Xform.Define(st, bp)
        pr = x.GetPrim()
        for k, v, t in (("vt:osm_id", b.id, Sdf.ValueTypeNames.Int64), ("vt:style", b.meta["style"], Sdf.ValueTypeNames.String),
                        ("vt:levels", b.meta["floors"], Sdf.ValueTypeNames.Int), ("vt:height", float(b.meta["height"]), Sdf.ValueTypeNames.Float),
                        ("vt:bvar", float(b.meta["bvar"]), Sdf.ValueTypeNames.Float)):
            pr.CreateAttribute(k, t).Set(v)
        UsdGeom.Scope.Define(st, bp + "/Shell")
        _mesh_prims(st, bp + "/Shell", b.shell, mats)
        names = sorted({i.name for i in b.insts})
        pi = UsdGeom.PointInstancer.Define(st, bp + "/Modules")
        UsdGeom.Scope.Define(st, bp + "/Modules/Prototypes")
        protos = []
        for n in names:
            pp = f"{bp}/Modules/Prototypes/{n}"
            prim = st.DefinePrim(pp, "Xform")
            rel = Path("../..").joinpath(MODDIR.relative_to(ROOT)) / f"{n}.usdc"
            prim.GetReferences().AddReference(f"../../assets/modules/{n}.usdc")
            protos.append(Sdf.Path(pp))
        pi.CreatePrototypesRel().SetTargets(protos)
        ix = {n: i for i, n in enumerate(names)}
        pi.CreateProtoIndicesAttr(Vt.IntArray([ix[i.name] for i in b.insts]))
        pi.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(i.x, i.y, i.z) for i in b.insts]))
        pi.CreateOrientationsAttr(Vt.QuathArray([Gf.Quath(math.cos(i.rot / 2), 0, 0, math.sin(i.rot / 2)) for i in b.insts]))
        pi.CreateScalesAttr(Vt.Vec3fArray([Gf.Vec3f(i.sx, i.sy, i.sz) for i in b.insts]))
    st.GetRootLayer().Save()
    return path


def write_instances(insts, path, root):
    """任意の Inst 列を1つの PointInstancer(/City/<root>/Instances)で書く。root をタイルごとに変えて sublayer 同士のprimが衝突しないようにする。
    ファイルは out/usd 直下に置く前提(モジュール参照は ../../assets/modules)。"""
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z); UsdGeom.SetStageMetersPerUnit(st, 1.0)
    UsdGeom.Xform.Define(st, "/City"); st.SetDefaultPrim(st.GetPrimAtPath("/City"))
    UsdGeom.Xform.Define(st, f"/City/{root}")
    pi = UsdGeom.PointInstancer.Define(st, f"/City/{root}/Instances")
    UsdGeom.Scope.Define(st, f"/City/{root}/Instances/Prototypes")
    names = sorted({i.name for i in insts})
    protos = []
    for n in names:
        pp = f"/City/{root}/Instances/Prototypes/{n}"
        st.DefinePrim(pp, "Xform").GetReferences().AddReference(f"../../assets/modules/{n}.usdc")
        protos.append(Sdf.Path(pp))
    pi.CreatePrototypesRel().SetTargets(protos)
    ix = {n: i for i, n in enumerate(names)}
    pi.CreateProtoIndicesAttr(Vt.IntArray([ix[i.name] for i in insts]))
    pi.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(i.x, i.y, i.z) for i in insts]))
    pi.CreateOrientationsAttr(Vt.QuathArray([Gf.Quath(math.cos(i.rot / 2), 0, 0, math.sin(i.rot / 2)) for i in insts]))
    pi.CreateScalesAttr(Vt.Vec3fArray([Gf.Vec3f(i.sx, i.sy, i.sz) for i in insts]))
    st.GetRootLayer().Save()
    return path


def write_vegetation(insts, path=None):
    """植栽(樹木・低木・生垣・地被)の全インスタンスを1つのPointInstancerで。各モジュールUSDは葉アトラス(alpha cutout・両面)を参照"""
    OUTDIR.mkdir(parents=True, exist_ok=True)
    path = path or OUTDIR / "vegetation.usda"
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z); UsdGeom.SetStageMetersPerUnit(st, 1.0)
    UsdGeom.Xform.Define(st, "/City"); st.SetDefaultPrim(st.GetPrimAtPath("/City"))
    UsdGeom.Xform.Define(st, "/City/Vegetation")
    pi = UsdGeom.PointInstancer.Define(st, "/City/Vegetation/Instances")
    UsdGeom.Scope.Define(st, "/City/Vegetation/Instances/Prototypes")
    names = sorted({i.name for i in insts})
    protos = []
    for n in names:
        pp = f"/City/Vegetation/Instances/Prototypes/{n}"
        st.DefinePrim(pp, "Xform").GetReferences().AddReference(f"../../assets/modules/{n}.usdc")
        protos.append(Sdf.Path(pp))
    pi.CreatePrototypesRel().SetTargets(protos)
    ix = {n: i for i, n in enumerate(names)}
    pi.CreateProtoIndicesAttr(Vt.IntArray([ix[i.name] for i in insts]))
    pi.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(i.x, i.y, i.z) for i in insts]))
    pi.CreateOrientationsAttr(Vt.QuathArray([Gf.Quath(math.cos(i.rot / 2), 0, 0, math.sin(i.rot / 2)) for i in insts]))
    pi.CreateScalesAttr(Vt.Vec3fArray([Gf.Vec3f(i.sx, i.sy, i.sz) for i in insts]))
    st.GetRootLayer().Save()
    return path
