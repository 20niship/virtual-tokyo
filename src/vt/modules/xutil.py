"""追加モジュール(田舎/ロードサイド/工業/高架細部)共通: 材質登録と小さな作図ヘルパ。"""
import json
import math
from pathlib import Path

from ..materials import MATERIALS, M, T
from .geom3 import beam, hexa, tube3

TEX = Path(__file__).resolve().parents[3] / "assets/textures"

MATERIALS.update({
    # 屋根(UV=メートル)。bump=瓦の凹凸
    "roof_kawara": T("roof_kawara.png", 1.5, 0.42, 0.7, dirt=1),
    "roof_kawara_brown": T("roof_kawara_brown.png", 1.5, 0.45, 0.7, dirt=1),
    "roof_kawara_hon": T("roof_kawara_hon.png", 1.2, 0.4, 0.8, dirt=1),
    "roof_cement_red": T("roof_cement_red.png", 1.3, 0.6, 0.5, dirt=1),
    "roof_cement_blue": T("roof_cement_blue.png", 1.3, 0.6, 0.5, dirt=1),
    "roof_tanshiki_blue": T("roof_tanshiki_blue.png", 1.6, 0.4, 0.4),
    "roof_tanshiki_green": T("roof_tanshiki_green.png", 1.6, 0.4, 0.4),
    "roof_tanshiki_red": T("roof_tanshiki_red.png", 1.6, 0.4, 0.4),
    "roof_tanshiki_gray": T("roof_tanshiki_gray.png", 1.6, 0.4, 0.4),
    "roof_slate_dark": T("roof_slate_dark.png", 1.2, 0.75, 0.4, dirt=1),
    "roof_slate_brown": T("roof_slate_brown.png", 1.2, 0.75, 0.4, dirt=1),
    "roof_ridge": M("#2a2c2f", 0.45, 0.0, dirt=1),
    "onigawara": M("#3a3d40", 0.35),
    # 壁
    "siding_shitami": T("siding_shitami.png", 1.0, 0.85, 0.6),
    "siding_shitami_light": T("siding_shitami_light.png", 1.0, 0.85, 0.6),
    "siding_ceramic_cream": T("siding_ceramic_cream.png", 2.0, 0.7, 0.3),
    "siding_ceramic_gray": T("siding_ceramic_gray.png", 2.0, 0.7, 0.3),
    "siding_ceramic_brick": T("siding_ceramic_brick.png", 1.5, 0.7, 0.4),
    "corrugated_gray": T("corrugated_gray.png", 1.2, 0.45, 0.8),
    "corrugated_blue": T("corrugated_blue.png", 1.2, 0.45, 0.8),
    "corrugated_green": T("corrugated_green.png", 1.2, 0.45, 0.8),
    "corrugated_cream": T("corrugated_cream.png", 1.2, 0.5, 0.8),
    "cmu_block": T("cmu_block.png", (1.17, 1.14), 0.9, 0.7),
    "concrete_stained": T("concrete_stained.png", 3.0, 0.9, 0.4),
    "steel_rusty": T("steel_rusty_gray.png", 2.0, 0.6, 0.3),
    "shop_atlas": dict(color="#ffffff", rough=0.35, metal=0.0, tex="shop_atlas.png", size=None, alpha=False),
    "shop_atlas_lit": dict(color="#ffffff", rough=0.5, metal=0.0, tex="shop_atlas.png", size=None, alpha=False, emit_tex=True),
    # 日本家屋・小物
    "wood_dark": M("#4a3426", 0.7, wood=1, vary=["#4a3426", "#5e4630", "#3c2a1e"]),
    "wood_light": M("#b08a5c", 0.6, wood=1, vary=["#b08a5c", "#c4a070", "#9a7a50"]),
    "paper_shoji": M("#efe8d4", 0.9, emit=("#efe0b8", 0.6)),
    "plaster_white": M("#e8e4d6", 0.9, bump=0.3, dirt=1),
    "namako_tile": M("#25282c", 0.25, 0.1),
    "frosted_glass": M("#b8c4c4", 0.15, 0.0, glass=1),
    "polycarbonate": M("#c4d8dc", 0.1, 0.0, glass=1),
    "plastic_film": M("#d8e4dc", 0.15, 0.0, glass=1),
    "garden_stone": M("#6a6862", 0.8, bump=0.5),
    # 工業・プラント
    "tank_white": M("#d4d6d2", 0.5, 0.3, dirt=1, rust=1),
    "tank_gray": M("#a8acae", 0.5, 0.4, dirt=1, rust=1),
    "tank_green": M("#7a9684", 0.55, 0.3, dirt=1, rust=1),
    "pipe_insul": M("#c4c8ca", 0.35, 0.8, dirt=1),
    "pipe_red": M("#a8281c", 0.5, 0.5, dirt=1),
    "pipe_yellow": M("#d8aa10", 0.5, 0.4, dirt=1),
    "pipe_blue": M("#2a58a0", 0.5, 0.4, dirt=1),
    "pipe_green": M("#2e7a48", 0.5, 0.4, dirt=1),
    "pipe_dark": M("#3a3e42", 0.55, 0.6, dirt=1, rust=1),
    "hazard_orange": M("#e0701a", 0.5, 0.3),
    "stack_red": M("#c02a1c", 0.5, 0.2, dirt=1),
    "stack_white": M("#e8e8e4", 0.5, 0.2, dirt=1),
    "flare_flame": M("#ff7a10", 0.5, 0.0, emit=("#ff8a20", 30.0)),
    "grating": M("#6a6e70", 0.5, 0.8, dirt=1),
    "brick_chimney": M("#8a4a34", 0.85, bump=0.5, dirt=1),
    # 高架・土木
    "girder_steel": M("#8a9094", 0.5, 0.7, dirt=1, rust=1),
    "paint_orange_sos": M("#e8741a", 0.4, 0.2),
    "net_nylon": M("#2a2e2a", 0.9),
    "led_amber": M("#ffa010", 0.4, emit=("#ffa010", 12.0)),
    "bearing_gray": M("#6a6e72", 0.5, 0.9, rust=1),
    "anchor_galv": M("#9ea4a6", 0.35, 0.9),
    "asphalt_dark": M("#2a2a2c", 0.9),
})

_ATLAS = {}


def shop_uv(key):
    """店舗看板アトラスのUV(u0,v0,u1,v1) と 縦横比"""
    if not _ATLAS:
        try:
            _ATLAS.update(json.loads((TEX / "shop_atlas.json").read_text())["panels"])
        except FileNotFoundError:
            pass
    p = _ATLAS.get(key)
    return (p["uv"], p["aspect"]) if p else (None, 2.0)


def sign_panel(m, key, x0, x1, z0, z1, y, mat="shop_atlas", flip=False):
    """+y向きの看板面(アトラスUV)。flip=Trueで-y向き"""
    uv, _ = shop_uv(key)
    if uv is None:
        m.box(x0, y - 0.005, z0, x1, y, z1, "sign_white")
        return
    u0, v0, u1, v1 = uv
    if not flip:
        m.oriented([(x1, y, z0), (x0, y, z0), (x0, y, z1), (x1, y, z1)], (0, 1, 0), mat, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    else:
        m.oriented([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], (0, -1, 0), mat, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def ngon(r, n, cx=0.0, cy=0.0, a0=0.0):
    return [(cx + r * math.cos(a0 + 2 * math.pi * i / n), cy + r * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n)]


def pipe(m, a, b, r, mat, n=8):
    """a→b の円管(3D)"""
    tube3(m, [a, b], r, mat, n)


def pipe_bent(m, pts, r, mat, n=8):
    tube3(m, pts, r, mat, n)


def post(m, x, y, z0, z1, w, mat):
    m.box(x - w / 2, y - w / 2, z0, x + w / 2, y + w / 2, z1, mat)


def ibeam_x(m, x0, x1, y, z, h, w, mat):
    """x方向のH形鋼(上下フランジ+ウェブ)の簡易形"""
    m.box(x0, y - w / 2, z + h - 0.02 * h - 0.01, x1, y + w / 2, z + h, mat)
    m.box(x0, y - w / 2, z, x1, y + w / 2, z + 0.02 * h + 0.01, mat)
    m.box(x0, y - 0.012, z, x1, y + 0.012, z + h, mat)


def ladder_z(m, x, y, z0, z1, w=0.45, mat="steel_galv", rung=0.3, face=1, cage=False):
    """垂直ハシゴ(face=+1: yの+側が壁と反対)"""
    for sx in (-w / 2, w / 2):
        m.box(x + sx - 0.015, y - 0.015, z0, x + sx + 0.015, y + 0.015, z1, mat)
    z = z0 + 0.25
    while z < z1:
        m.cyl(x - w / 2, y, z, 0.011, w, "x", mat, 6)
        z += rung
    if cage:
        zz = z0 + 2.2
        while zz < z1 - 0.3:
            for k in range(8):
                a0, a1 = math.pi * (-0.3 + 1.6 * k / 8), math.pi * (-0.3 + 1.6 * (k + 1) / 8)
                if face < 0:
                    a0, a1 = -a0, -a1
                p0 = (x + 0.36 * math.sin(a0), y + face * 0.36 * math.cos(a0))
                p1 = (x + 0.36 * math.sin(a1), y + face * 0.36 * math.cos(a1))
                pipe(m, (p0[0], p0[1], zz), (p1[0], p1[1], zz), 0.01, mat, 4)
            zz += 0.9
        for k in range(5):
            a = math.pi * (-0.3 + 1.6 * k / 7)
            if face < 0:
                a = -a
            pipe(m, (x + 0.36 * math.sin(a), y + face * 0.36 * math.cos(a), z0 + 2.2), (x + 0.36 * math.sin(a), y + face * 0.36 * math.cos(a), z1), 0.008, mat, 4)


def handrail_x(m, x0, x1, y, z, h=1.05, mat="steel_galv", post_every=1.5):
    n = max(1, int(abs(x1 - x0) / post_every))
    for i in range(n + 1):
        px = x0 + (x1 - x0) * i / n
        m.cyl(px, y, z, 0.018, h, "z", mat, 6)
    for zz in (h, h * 0.55):
        m.cyl(x0, y, z + zz, 0.016, x1 - x0, "x", mat, 6)


def arc_roof(m, x0, x1, r, z0, mat, n=10, y0=0.0, a=math.pi):
    """x方向に押し出したかまぼこ屋根(断面は半径rの円弧、中心高さz0)"""
    prof = [(y0 + r * math.cos(math.pi * i / n), z0 + r * math.sin(math.pi * i / n)) for i in range(n + 1)]
    outer = prof
    inner = [(y0 + (r - 0.04) * math.cos(math.pi * i / n), z0 + (r - 0.04) * math.sin(math.pi * i / n)) for i in range(n + 1)][::-1]
    prism_any(m, outer + inner, "x", x0, x1, mat)


def prism_any(m, prof, axis, a0, a1, mat, caps=True):
    """向きを自動補正した押し出し(輪郭がCCWでもCWでも可)"""
    area = sum(prof[i][0] * prof[(i + 1) % len(prof)][1] - prof[(i + 1) % len(prof)][0] * prof[i][1] for i in range(len(prof)))
    m.prism(prof if area > 0 else prof[::-1], axis, a0, a1, mat, caps)
