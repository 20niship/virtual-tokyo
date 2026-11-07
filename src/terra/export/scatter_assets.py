"""散布 asset 名 → メッシュ。terra の module(rock_*, soil_*, gravel_*, terra_*)は terra.modules、veg_* は vt の module。
LOD: 樹木は '名前|lo' に低ポリ版、terra の module は '名前_far' があればそれを '名前|lo' で返す。"""
from __future__ import annotations

from .. import modules as tm
from ..modules.lib_forest import lo_mesh


def is_tree(name):
    return name.startswith(("veg_kuromatsu", "terra_")) or (name.startswith("veg_") and name.split("_")[1] in ("shii", "kusunoki", "keyaki", "tokaikaede", "sakura"))


def mesh_of(name):
    if name in tm.REG:
        return tm.build(name)
    from vt.modules.library import get
    return get(name)


def load_protos(doc, lod=True):
    out = {}
    for s in doc.scatter.values():
        for n in map(str, s["assets"]):
            if n in out:
                continue
            out[n] = mesh_of(n)
            if lod:
                if n + "_far" in tm.REG:
                    out[n + "|lo"] = tm.build(n + "_far")
                elif is_tree(n):
                    out[n + "|lo"] = lo_mesh(n)
    return out


def module_path(name):
    """USD module の位置(リポジトリ root から)"""
    return f"assets/terra/modules/{name}.usdc" if name in tm.REG else f"assets/modules/{name}.usdc"
