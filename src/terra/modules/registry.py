"""Terra の module 規約(vt と同じ: 1 module 1 usdc、原点=根元、z 上)。メッシュは vt.modules.geom.Mesh、出力は assets/terra/modules/<name>.usdc。
材質は vt.materials.MATERIALS へ追加登録する(vt の USD 書き出し・Blender 材質生成をそのまま使うため)。"""
import random
from pathlib import Path

from vt.materials import MATERIALS
from vt.modules.geom import Mesh

ROOT = Path(__file__).resolve().parents[3]
MODDIR = ROOT / "assets/terra/modules"
REG: dict = {}


def tex(png, size, rough=0.9, bump=0.0, **kw):
    return dict(color="#808080", rough=rough, metal=0.0, tex=png, size=size, bump=bump, **kw)


MATERIALS.update({
    "rock_granite": tex("rock_cliff.png", 2.5, 0.92, 0.8),
    "rock_dark": tex("rock_cliff.png", 3.0, 0.9, 0.8, tint="#b5b0a8"),
    "rock_warm": tex("rock_cliff.png", 2.2, 0.93, 0.7, tint="#b0a090"),
    "rock_pebble": tex("rock_cliff.png", 0.8, 0.55, 0.3, tint="#b8b4a8"),
})


def reg(name, fn, W=1.0, H=1.0, cat="岩", **meta):
    REG[name] = dict(fn=fn, W=W, H=H, cat=cat, **meta)


def build(name) -> Mesh:
    r = REG[name]
    m = Mesh()
    r["fn"](m, r["W"], r["H"], random.Random(name))
    return m


def write_module(name):
    """vt.usd_out の材質・メッシュ書き出しを使い、assets/terra/modules/<name>.usdc を作る(テクスチャは ../textures = assets/terra/textures)"""
    from pxr import Sdf, Usd, UsdGeom

    from vt import usd_out as uo
    MODDIR.mkdir(parents=True, exist_ok=True)
    mesh, meta = build(name), REG[name]
    path = MODDIR / f"{name}.usdc"
    st = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = UsdGeom.Xform.Define(st, f"/{name}")
    st.SetDefaultPrim(root.GetPrim())
    p = root.GetPrim()
    p.CreateAttribute("vt:module_type", Sdf.ValueTypeNames.String).Set(meta["cat"])
    p.CreateAttribute("vt:span_w", Sdf.ValueTypeNames.Float).Set(float(meta["W"]))
    p.CreateAttribute("vt:height", Sdf.ValueTypeNames.Float).Set(float(meta["H"]))
    mats = uo.define_materials(st, f"/{name}/Materials", only=set(mesh.m), texdir="../textures")
    UsdGeom.Scope.Define(st, f"/{name}/Geom")
    uo._mesh_prims(st, f"/{name}/Geom", mesh, mats)
    st.GetRootLayer().Save()
    return path
