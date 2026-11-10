"""集落の簡易 module(手続き生成・near / "_far")。原点は敷地中心の地面、玄関側が +y、棟は x 方向。寸法は設計上の値。"""
import math

from vt.materials import MATERIALS as _MAT

from .registry import reg

_MAT["house_wall_a"] = dict(color="#d8cfba", rough=0.9, metal=0.0, bump=0.2)
_MAT["house_wall_b"] = dict(color="#e7e3d8", rough=0.9, metal=0.0, bump=0.2)
_MAT["house_wall_c"] = dict(color="#6b5a46", rough=0.85, metal=0.0, wood=1)
_MAT["house_roof_kawara"] = dict(color="#474c52", rough=0.55, metal=0.0, bump=0.6)
_MAT["house_roof_tin"] = dict(color="#8f3b2b", rough=0.45, metal=0.6, bump=0.15)
_MAT["house_roof_tin_blue"] = dict(color="#3d5a78", rough=0.45, metal=0.6, bump=0.15)
_MAT["house_glass"] = dict(color="#1a2a30", rough=0.05, metal=0.0, glass=1)
_MAT["house_found"] = dict(color="#9c9a93", rough=0.9, metal=0.0, tex="concrete.png", size=3.0, bump=0.4)
_MAT["field_soil"] = dict(color="#4a3a2a", rough=0.97, metal=0.0, tex="soil.png", size=2.5, bump=0.8)
_MAT["field_crop"] = dict(color="#5d8a3a", rough=0.8, metal=0.0, tex="grass.png", size=1.0, bump=0.5)


def _gable(m, W, D, zw, h, ov, mat, lod):
    """切妻屋根(棟が x 方向)。断面 (y, z) の三角形を x 方向に押し出す"""
    m.prism([(-D / 2 - ov, zw), (D / 2 + ov, zw), (0.0, zw + h)], "x", -W / 2 - ov, W / 2 + ov, mat)
    if lod == "near":
        m.box(-W / 2 - ov, -0.18, zw + h - 0.02, W / 2 + ov, 0.18, zw + h + 0.14, mat)           # 棟


def _hip(m, W, D, zw, h, ov, mat):
    """寄棟/入母屋風の屋根: 四方に勾配"""
    a, b, r = W / 2 + ov, D / 2 + ov, max(W / 2 - D / 2, 0.5)
    c = {"fl": (-a, -b, zw), "fr": (a, -b, zw), "br": (a, b, zw), "bl": (-a, b, zw), "rl": (-r, 0.0, zw + h), "rr": (r, 0.0, zw + h)}
    for face, out in (([c["fl"], c["fr"], c["rr"], c["rl"]], (0, -1, 1)), ([c["br"], c["bl"], c["rl"], c["rr"]], (0, 1, 1)),
                      ([c["fr"], c["br"], c["rr"]], (1, 0, 1)), ([c["bl"], c["fl"], c["rl"]], (-1, 0, 1))):
        m.oriented(face, out, mat)


def _house(var, lod):
    def fn(m, W, H, rng):
        Wd, D = (10.0, 7.0) if var != 1 else (9.0, 8.0)
        floors = 2 if var == 1 else 1
        zw = 0.45 + 2.7 * floors                               # 軒高
        wall = ("house_wall_a", "house_wall_b", "house_wall_c")[var]
        roof = ("house_roof_kawara", "house_roof_kawara", "house_roof_tin")[var]
        m.box(-Wd / 2 - 0.1, -D / 2 - 0.1, 0.0, Wd / 2 + 0.1, D / 2 + 0.1, 0.45, "house_found")      # 基礎
        m.box(-Wd / 2, -D / 2, 0.45, Wd / 2, D / 2, zw, wall)                                           # 壁
        if var == 1:
            _hip(m, Wd, D, zw, 2.2, 0.7, roof)
        else:
            _gable(m, Wd, D, zw, 2.6 if var == 0 else 2.2, 0.7, roof, lod)
        if lod == "far":
            return
        yf = D / 2                                                                                      # 前面(玄関側)
        m.box(-0.5, yf, 0.45, 0.5, yf + 0.04, 2.3, "house_wall_c")                                      # 玄関戸
        m.box(-0.6, yf, 2.3, 0.6, yf + 0.05, 2.38, "house_wall_c")
        for fl in range(floors):                                                                        # 窓(前後)
            z = 0.45 + 2.7 * fl + 0.9
            for sd, y in ((1, yf), (-1, -yf)):
                for x in (-3.2, -1.6, 1.8, 3.4):
                    if abs(x) < Wd / 2 - 0.6:
                        m.box(x - 0.55, min(y, y + 0.03 * sd), z, x + 0.55, max(y, y + 0.03 * sd), z + 1.1, "house_glass")
                        m.box(x - 0.6, min(y, y + 0.04 * sd), z - 0.05, x + 0.6, max(y, y + 0.04 * sd), z, "alu_silver")
        m.box(-Wd / 2, yf, 0.45, Wd / 2, yf + 1.0, 0.55, "wood")                                         # 縁側(濡れ縁)
        for x in (-Wd / 2 + 0.1, Wd / 2 - 0.1, 0.0):
            m.box(x - 0.05, yf + 0.9, 0.55, x + 0.05, yf + 1.0, 2.5, "wood")
        m.box(-Wd / 2 - 0.2, yf, 2.45, Wd / 2 + 0.2, yf + 1.15, 2.52, roof)                              # 庇
        if var != 1:
            m.box(Wd / 2 - 1.4, -0.4, zw, Wd / 2 - 1.0, 0.0, zw + 3.0, "house_found")                    # 煙突
        if floors == 2:
            m.box(-Wd / 2 - 0.05, -D / 2 - 0.05, 3.1, Wd / 2 + 0.05, D / 2 + 0.05, 3.2, "wood")         # 胴差し
    return fn


def _barn(lod):
    def fn(m, W, H, rng):
        Wd, D = 12.0, 7.0
        m.box(-Wd / 2 - 0.1, -D / 2 - 0.1, 0.0, Wd / 2 + 0.1, D / 2 + 0.1, 0.3, "house_found")
        m.box(-Wd / 2, -D / 2, 0.3, Wd / 2, D / 2, 3.6, "metal_siding")
        _gable(m, Wd, D, 3.6, 1.6, 0.4, "house_roof_tin_blue", lod)
        if lod == "near":
            m.box(-2.2, D / 2, 0.3, 2.2, D / 2 + 0.06, 3.1, "alu_black")                                  # 大きな引き戸
            m.box(0.0 - 0.03, D / 2 + 0.06, 0.3, 0.03, D / 2 + 0.08, 3.1, "alu_silver")
            for x in (-5.0, 5.0):
                m.box(x - 0.4, D / 2, 1.8, x + 0.4, D / 2 + 0.04, 2.8, "house_glass")
    return fn


def _field(crop, lod):
    """畑 20m x 14m: 畝(うね)を y 方向に並べる。作物は畝の上の緑の帯(crop) / 畝だけ(soil)"""
    def fn(m, W, H, rng):
        Wd, D = 20.0, 14.0
        m.box(-Wd / 2, -D / 2, -0.05, Wd / 2, D / 2, 0.0, "field_soil")
        pitch = 0.9 if lod == "near" else 2.0
        n = int(Wd / pitch)
        for i in range(n):
            x = -Wd / 2 + (i + 0.5) * pitch
            m.box(x - 0.3 * pitch, -D / 2 + 0.3, 0.0, x + 0.3 * pitch, D / 2 - 0.3, 0.2, "field_soil")
            if crop:
                m.box(x - 0.22 * pitch, -D / 2 + 0.5, 0.2, x + 0.22 * pitch, D / 2 - 0.5, 0.2 + (0.25 if lod == "near" else 0.2) + 0.08 * math.sin(i), "field_crop")
    return fn


for _lod in ("near", "far"):
    _s = "" if _lod == "near" else "_far"
    for _v in range(3):
        reg(f"house_jp_{'abc'[_v]}{_s}", _house(_v, _lod), W=12.0, H=7.0, cat="集落", lod=_lod)
    reg(f"barn_jp{_s}", _barn(_lod), W=12.0, H=6.0, cat="集落", lod=_lod)
    reg(f"field_rows_green{_s}", _field(True, _lod), W=20.0, H=0.5, cat="集落", lod=_lod)
    reg(f"field_rows_soil{_s}", _field(False, _lod), W=20.0, H=0.3, cat="集落", lod=_lod)
