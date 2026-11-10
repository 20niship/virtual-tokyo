"""針葉樹(スギ・シラビソ風の円錐樹形)と、遠景用の低ポリ樹木。vt の tree_gen を使い、広葉樹は vt の植栽 module(veg_*)をそのまま参照する。
terra_<種>_<s|m|l>: 針葉樹(hi) / lo_<module 名>: 低ポリ版(三角形 約 1/8。遠景用)"""
import json
import re
from contextlib import contextmanager
from pathlib import Path

from vt import tree_gen as tg
from vt.materials import MATERIALS as _MAT
from vt.modules.library import get as vt_get

from .registry import REG, reg

# 針葉樹専用の葉アトラス(scripts/terra_textures_conifer.py で手続き生成: スギ・シラビソ・ヒノキ・カラマツ・マツの小枝カード)。広葉の葉アトラスは使わない
_MAT["conifer_atlas"] = dict(color="#ffffff", rough=0.6, metal=0.0, tex="conifer_atlas.png", size=None, alpha=True, cutout=0.45, double_sided=True, foliage=True)
_CONIFER_CARDS = json.loads((Path(__file__).resolve().parents[3] / "assets/terra/textures/conifer_atlas.json").read_text())["cards"]
_LEAF_POOL = tg.leaf_pool


def _leaf_pool(sp, kind, season):
    if kind.startswith("conifer_"):
        p = tg.pool(kind)
        return p, p
    return _LEAF_POOL(sp, kind, season)


tg.leaf_pool = _leaf_pool


@contextmanager
def conifer_atlas():
    """針葉樹のメッシュを作る間だけ、カードの参照先と材質を針葉アトラスにする"""
    tg.atlas()["cards"].update(_CONIFER_CARDS)
    old = tg.LEAF
    tg.LEAF = "conifer_atlas"
    try:
        yield
    finally:
        tg.LEAF = old


tg.SPECIES["sugi"] = tg.Spec(bark="bark_furrow_dark", crown="cone", crown_w=0.17, crown_base=0.16, n_main=26, ang=64, ang_var=10, grav=0.08, up=0.0,
                             leaf="conifer_sugi", leaf_size=0.12, evergreen=True, shell=170, dens=2.2, girth=0.8, leaf_m=0.45, tip_m=0.3, trunk_taper=0.12, roots=3)
tg.SPECIES["shirabiso"] = tg.Spec(bark="bark_furrow_dark", crown="cone", crown_w=0.2, crown_base=0.08, n_main=22, ang=70, ang_var=8, grav=0.04, up=0.04,
                                  leaf="conifer_fir", leaf_size=0.11, evergreen=True, shell=150, dens=2.0, girth=0.8, leaf_m=0.4, tip_m=0.28, trunk_taper=0.1, roots=0)
tg.SPECIES["hinoki"] = tg.Spec(bark="bark_furrow", crown="cone", crown_w=0.15, crown_base=0.12, n_main=24, ang=62, ang_var=9, grav=0.07, up=0.0,
                               leaf="conifer_hinoki", leaf_size=0.12, evergreen=True, shell=170, dens=2.2, girth=0.75, leaf_m=0.42, tip_m=0.3, trunk_taper=0.1, roots=2)
tg.SPECIES["karamatsu"] = tg.Spec(bark="bark_furrow_dark", crown="cone", crown_w=0.13, crown_base=0.22, n_main=18, ang=78, ang_var=10, grav=0.0, up=0.06,
                                  leaf="conifer_larch", leaf_size=0.1, evergreen=True, shell=120, dens=1.5, girth=0.7, leaf_m=0.4, tip_m=0.3, trunk_taper=0.12, roots=0)
CONIFER_H = {"sugi": {"s": 12.0, "m": 20.0, "l": 28.0}, "shirabiso": {"s": 6.0, "m": 10.0, "l": 15.0}, "hinoki": {"s": 10.0, "m": 17.0, "l": 24.0},
             "karamatsu": {"s": 9.0, "m": 15.0, "l": 22.0}}


def _conifer(sp, h):
    def fn(m, W, H, rng):
        with conifer_atlas():
            mesh, _ = tg.build_tree(sp, h, 0, "summer")
        m.add(mesh)
    return fn


for _sp, _hs in CONIFER_H.items():
    for _sz, _h in _hs.items():
        reg(f"terra_{_sp}_{_sz}", _conifer(_sp, _h), W=_h * tg.SPECIES[_sp].crown_w * 2.1, H=_h + 1, cat="植栽")


def lo_mesh(name):
    """name(veg_<種>_<s|m|l>_.. / terra_<種>_<s|m|l> / veg_kuromatsu_..)の低ポリ版。種・樹高は hi と同じ"""
    m = re.match(r"veg_([a-z]+)_([sml])_(\d)_([a-z_]+)$", name)
    if name.startswith("veg_kuromatsu"):
        h = {"s": 5.0, "m": 8.0, "l": 12.0}[m.group(2)]
        return tg.build_pine(h * 0.9, 0)[0] if False else vt_get(name)      # 松は元から低ポリ
    if m:
        sp, sz = m.group(1), m.group(2)
        h = round({"s": 5.0, "m": 9.0, "l": 14.0}[sz] * __import__("vt.modules.lib_veg", fromlist=["BIG"]).BIG[sp], 1)
    else:
        mm = re.match(r"terra_([a-z]+)_([sml])$", name)
        sp, sz = mm.group(1), mm.group(2)
        h = CONIFER_H[sp][sz]
    base = tg.SPECIES[sp]
    key = f"{sp}__lo"
    if key not in tg.SPECIES:
        d = dict(base.__dict__)
        d.update(shell=40, dens=0.25, sub=1, twigs=1, n_main=max(5, base.n_main // 3), roots=0, leaf_m=base.leaf_m * 1.5, tip_m=base.tip_m * 1.5)
        tg.SPECIES[key] = tg.Spec(**d)
    with conifer_atlas():
        return tg.build_tree(key, h, 0, "summer")[0]


_ = REG
