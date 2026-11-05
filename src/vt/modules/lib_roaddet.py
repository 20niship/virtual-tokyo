"""道路ディテールのモジュール: 鋳鉄蓋のマンホール(下水/水道/ガス/電気/通信)・集水桝(スリット蓋)・縁石反射板・車両出入口の切り下げ(すりつけ)。
単独物は原点=設置点の地面、+y=車道側(正面)。蓋は舗装面に面一(上端+1.2cm)。"""
import math

from ..materials import M, MATERIALS
from .registry import reg

CAT = "道路"
MATERIALS.setdefault("cast_iron", M("#2c2c2e", 0.55, 0.75, dirt=1, rust=1))
MATERIALS.setdefault("reflector_amber", M("#e8a020", 0.25))
MATERIALS.setdefault("reflector_white", M("#e8e8e0", 0.25))


def _cover(kind):
    """円形マンホール蓋(直径0.6m): 受枠リング+蓋盤+種別ごとの模様(下水=格子+二重円、水道=十字+円、ガス=平行リブ、電気=升目、通信=円+横リブ)"""
    def fn(m, W, H, rng):
        m.tube(0, 0, 0.0, 0.34, 0.30, 0.014, "z", "rc_concrete", 28)                  # 受枠(コンクリ側の縁)
        m.tube(0, 0, 0.0, 0.30, 0.285, 0.012, "z", "cast_iron", 28)                   # 蓋の受枠
        m.cyl(0, 0, 0.0, 0.285, 0.010, "z", "cast_iron", 28)                          # 蓋盤(1cm沈み)
        z, t = 0.010, 0.006                                                           # 模様の高さ
        if kind == "sewer":
            m.tube(0, 0, z, 0.2, 0.185, t, "z", "cast_iron", 24)
            m.tube(0, 0, z, 0.1, 0.085, t, "z", "cast_iron", 20)
            for i in range(-3, 4):
                m.box(i * 0.07 - 0.008, -0.27, z, i * 0.07 + 0.008, 0.27, z + t, "cast_iron")
        elif kind == "water":
            m.tube(0, 0, z, 0.22, 0.2, t, "z", "cast_iron", 24)
            m.box(-0.27, -0.015, z, 0.27, 0.015, z + t, "cast_iron")
            m.box(-0.015, -0.27, z, 0.015, 0.27, z + t, "cast_iron")
            m.cyl(0, 0, z, 0.05, t, "z", "cast_iron", 12)
        elif kind == "gas":
            for i in range(-4, 5):
                m.box(i * 0.06 - 0.012, -0.26, z, i * 0.06 + 0.012, 0.26, z + t, "cast_iron")
        elif kind == "elec":
            for i in range(-3, 4):
                m.box(i * 0.075 - 0.008, -0.25, z, i * 0.075 + 0.008, 0.25, z + t, "cast_iron")
                m.box(-0.25, i * 0.075 - 0.008, z, 0.25, i * 0.075 + 0.008, z + t, "cast_iron")
        else:                                                                           # tele
            m.tube(0, 0, z, 0.24, 0.22, t, "z", "cast_iron", 24)
            for i in (-2, -1, 0, 1, 2):
                m.box(-0.2, i * 0.07 - 0.012, z, 0.2, i * 0.07 + 0.012, z + t, "cast_iron")
        for a in (0.7, 3.84):                                                           # 開閉用の穴(暗い)
            m.cyl(math.cos(a) * 0.2, math.sin(a) * 0.2, z, 0.018, t, "z", "sig_lens_dark", 8)
    return fn


for _k in ("sewer", "water", "gas", "elec", "tele"):
    reg(f"rd_cover_{_k}", _cover(_k), W=0.7, H=0.03, cat=CAT)


def _catchbasin(m, W, H, rng):
    """雨水の集水桝: 鋳鉄のスリット蓋(0.5×0.35m、横桟ピッチ4cm)+コンクリ枠。桝の中は暗い"""
    m.box(-0.30, -0.22, 0.0, 0.30, 0.22, 0.012, "rc_concrete")
    m.box(-0.25, -0.175, 0.002, 0.25, 0.175, 0.012, "sig_lens_dark")
    m.box(-0.25, -0.175, 0.006, 0.25, -0.155, 0.016, "cast_iron")
    m.box(-0.25, 0.155, 0.006, 0.25, 0.175, 0.016, "cast_iron")
    for i in range(-5, 6):
        m.box(i * 0.04 - 0.009, -0.175, 0.006, i * 0.04 + 0.009, 0.175, 0.016, "cast_iron")


reg("rd_catchbasin_cast", _catchbasin, W=0.6, H=0.03, cat=CAT)


def _reflector(mat):
    def fn(m, W, H, rng):
        m.box(-0.06, 0.0, 0.0, 0.06, 0.012, 0.07, mat)
    return fn


reg("rd_curb_reflector_amber", _reflector("reflector_amber"), W=0.14, H=0.08, cat=CAT)
reg("rd_curb_reflector_white", _reflector("reflector_white"), W=0.14, H=0.08, cat=CAT)


def _apron(h):
    """車両出入口の切り下げ(すりつけ): 縁石線(y=0)から車道側へ0.9mで縁石天端(h)→路面へ下るくさび+歩道側の幅1.2mの帯。幅4m、両脇は三角の袖"""
    def fn(m, W, H, rng):
        w = W / 2
        L = 0.9
        m.oriented([(-w, 0, h), (w, 0, h), (w, L, 0.0), (-w, L, 0.0)], (0, 0.3, 1), "concrete_tex", [(0, 0), (W, 0), (W, L), (0, L)])
        m.oriented([(-w, -1.2, h + 0.004), (w, -1.2, h + 0.004), (w, 0, h + 0.004), (-w, 0, h + 0.004)], (0, 0, 1), "concrete_tex", [(0, 0), (W, 0), (W, 1.2), (0, 1.2)])
        for sx in (-1, 1):                                                              # 袖(三角の側面)
            m.oriented([(sx * w, 0, h), (sx * w, L, 0.0), (sx * w, 0, 0.0)], (sx, 0, 0), "concrete_tex")
    return fn


for _h, _nm in ((0.05, "05"), (0.15, "15")):
    reg(f"rd_driveway_apron_{_nm}", _apron(_h), W=4.0, H=_h + 0.01, cat=CAT)
