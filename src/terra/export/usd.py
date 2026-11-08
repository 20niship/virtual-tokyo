"""USD 出力: 地形タイル(UsdGeomMesh, 頂点色に材質重みを焼き込み)+水面+散布(PointInstancer, module は assets の usdc を参照)。スプラットマップは PNG で併せて出す。"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt

from ..biome.jp_forest import SPLAT
from ..render import default_colors, water_geometry
from .scatter_assets import module_path

ROOT = Path(__file__).resolve().parents[3]
ALBEDO = dict(grass=(0.20, 0.30, 0.10), litter=(0.16, 0.11, 0.06), rock=(0.45, 0.42, 0.38), scree=(0.50, 0.47, 0.42), soil=(0.30, 0.22, 0.14), alpine=(0.35, 0.36, 0.18))
TILE = 250


def bake_colors(doc):
    if "splat_grass" not in doc.layers:
        return default_colors(doc)[..., :3]
    c = sum(doc.layers["splat_" + n][..., None] * np.array(ALBEDO[n]) for n in SPLAT)
    return np.clip(c, 0, 1)


def _material(st, path, color_primvar=True, rough=0.93, color=(0.5, 0.5, 0.5), opacity=1.0):
    m = UsdShade.Material.Define(st, path)
    sh = UsdShade.Shader.Define(st, path + "/PBR")
    sh.CreateIdAttr("UsdPreviewSurface")
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(rough)
    if color_primvar:
        rd = UsdShade.Shader.Define(st, path + "/color")
        rd.CreateIdAttr("UsdPrimvarReader_float3")
        rd.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("displayColor")
        rd.CreateOutput("result", Sdf.ValueTypeNames.Float3)
        sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(rd.ConnectableAPI(), "result")
    else:
        sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(opacity)
    m.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    return m


def _vnormals(z, res):
    gy, gx = np.gradient(z.astype(np.float64), res)
    n = np.stack([-gx, -gy, np.ones_like(z, dtype=np.float64)], -1)
    return (n / np.linalg.norm(n, axis=-1, keepdims=True)).astype(np.float32)


def write_terrain(st, doc, root="/Terra/Terrain", tile=TILE):
    g = doc.grid
    X, Y = g.xy()
    col = bake_colors(doc).astype(np.float32)
    nrm = _vnormals(doc.height, g.res)
    mat = _material(st, "/Terra/Materials/Terrain")
    UsdGeom.Scope.Define(st, root)
    n = 0
    for j0 in range(0, g.ny - 1, tile):
        for i0 in range(0, g.nx - 1, tile):
            sl = (slice(j0, min(j0 + tile + 1, g.ny)), slice(i0, min(i0 + tile + 1, g.nx)))   # 1 セル重ねて継ぎ目を無くす
            ny, nx = X[sl].shape
            P = np.stack([X[sl], Y[sl], doc.height[sl]], -1).reshape(-1, 3).astype(np.float32)
            q = (np.arange(ny - 1)[:, None] * nx + np.arange(nx - 1)[None, :]).ravel()
            idx = np.stack([q, q + 1, q + nx + 1, q + nx], 1).astype(np.int32)
            m = UsdGeom.Mesh.Define(st, f"{root}/tile_{j0 // tile}_{i0 // tile}")
            m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(P))
            m.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(idx), 4, np.int32)))
            m.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(idx.ravel()))
            m.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(nrm[sl].reshape(-1, 3)))
            m.SetNormalsInterpolation("vertex")
            m.CreateSubdivisionSchemeAttr("none")
            pv = UsdGeom.PrimvarsAPI(m).CreatePrimvar("displayColor", Sdf.ValueTypeNames.Color3fArray, UsdGeom.Tokens.vertex)
            pv.Set(Vt.Vec3fArray.FromNumpy(col[sl].reshape(-1, 3)))
            UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(mat)
            n += 1
    return n


def write_water(st, doc, root="/Terra/Water"):
    V, F = water_geometry(doc)
    if not V:
        return 0
    mat = _material(st, "/Terra/Materials/Water", False, 0.05, (0.05, 0.11, 0.13))
    m = UsdGeom.Mesh.Define(st, root)
    m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(V, np.float32)))
    m.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(F), 4, np.int32)))
    m.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(F, np.int32).ravel()))
    m.CreateSubdivisionSchemeAttr("none")
    UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(mat)
    return len(F)


def write_scatter(st, doc, usd_path, root="/Terra/Scatter"):
    """散布 1 グループ = PointInstancer 1 つ(prototype は module の usdc への参照)。位置 float3・向き quath(Z 回り yaw と X 回り pitch)・スケール"""
    UsdGeom.Scope.Define(st, root)
    total = 0
    for name, s in doc.scatter.items():
        pi = UsdGeom.PointInstancer.Define(st, f"{root}/{name}")
        UsdGeom.Scope.Define(st, f"{root}/{name}/Prototypes")
        names = [str(a) for a in s["assets"]]
        used = sorted(set(int(k) for k in np.unique(s["kind"])))
        remap = {k: i for i, k in enumerate(used)}
        protos = []
        for k in used:
            pp = f"{root}/{name}/Prototypes/{names[k]}"
            st.DefinePrim(pp, "Xform").GetReferences().AddReference(os.path.relpath(ROOT / module_path(names[k]), Path(usd_path).parent))
            protos.append(Sdf.Path(pp))
        pi.CreatePrototypesRel().SetTargets(protos)
        pi.CreateProtoIndicesAttr(Vt.IntArray.FromNumpy(np.array([remap[int(k)] for k in s["kind"]], np.int32)))
        pi.CreatePositionsAttr(Vt.Vec3fArray.FromNumpy(s["pos"].astype(np.float32)))
        yaw, pit = s["yaw"].astype(np.float64) / 2, s.get("pitch", np.zeros(len(s["yaw"]))).astype(np.float64) / 2
        # q = qz(yaw) * qx(pitch)
        q = np.stack([np.cos(yaw) * np.cos(pit), np.cos(yaw) * np.sin(pit), np.sin(yaw) * np.sin(pit), np.sin(yaw) * np.cos(pit)], 1)    # (w,x,y,z)
        pi.CreateOrientationsAttr(Vt.QuathArray([Gf.Quath(float(a), float(b), float(c), float(d)) for a, b, c, d in q]))
        pi.CreateScalesAttr(Vt.Vec3fArray.FromNumpy(np.repeat(s["scale"].astype(np.float32)[:, None], 3, 1)))
        total += len(s["yaw"])
    return total


def write_roads(st, doc, usd_path, root="/Terra/Roads"):
    """路面(アスファルト+白線)の曲面メッシュ。橋・トンネル・付属物は road_furniture の PointInstancer(module 参照)"""
    from vt import usd_out as uo

    from ..infra.roadmesh import road_mesh
    m = road_mesh(doc)
    if not m.f:
        return 0
    mats = uo.define_materials(st, "/Terra/Materials/Road", only=set(m.m), texdir=os.path.relpath(ROOT / "assets/textures", Path(usd_path).parent))
    UsdGeom.Scope.Define(st, root)
    uo._mesh_prims(st, root, m, mats)
    return len(m.f)


def ensure_modules(doc):
    from .. import modules as tm
    for s in doc.scatter.values():
        for n in map(str, s["assets"]):
            if n in tm.REG and not (ROOT / module_path(n)).exists():
                tm.write_module(n)


def export_usd(doc, out, name="terra.usdc"):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ensure_modules(doc)
    path = out / name
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = UsdGeom.Xform.Define(st, "/Terra")
    st.SetDefaultPrim(root.GetPrim())
    UsdGeom.Scope.Define(st, "/Terra/Materials")
    nt = write_terrain(st, doc)
    nw = write_water(st, doc)
    nr = write_roads(st, doc, path)
    ni = write_scatter(st, doc, path)
    root.GetPrim().SetCustomDataByKey("terra", dict(tiles=nt, water_quads=nw, road_faces=nr, instances=ni, res_m=doc.grid.res, crs=doc.grid.crs, x0=doc.grid.x0, y0=doc.grid.y0))
    st.GetRootLayer().Save()
    return [path]


def export_splat(doc, out):
    """スプラットマップ(RGBA 8bit, 北が上): splat0=(grass,litter,rock,scree)、splat1=(soil,alpine,-,-)。層のテクスチャと 4m 周期の対応は splat.json"""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if "splat_grass" not in doc.layers:
        return []
    L = [doc.layers["splat_" + n] for n in SPLAT]
    z = np.zeros_like(L[0])
    paths = []
    for nm, ch in (("splat0", L[:4]), ("splat1", L[4:] + [z, z])):
        a = np.stack(ch[:4], -1)
        p = out / f"{nm}.png"
        Image.fromarray(np.flipud((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))).save(p, compress_level=6)
        paths.append(p)
    (out / "splat.json").write_text(json.dumps(dict(
        splat0=SPLAT[:4], splat1=SPLAT[4:] + ["unused", "unused"], tile_period_m=[4.0, 11.0],
        textures=dict(grass="assets/textures/grass.png", litter="assets/terra/textures/forest_litter.png", rock="assets/terra/textures/rock_cliff.png",
                      scree="assets/textures/gravel.png", soil="assets/textures/soil.png", alpine="assets/terra/textures/alpine_turf.png")), indent=1))
    paths.append(out / "splat.json")
    return paths

