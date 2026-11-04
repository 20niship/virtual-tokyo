"""街の生活感モジュール(リアリズム強化B): 自販機(架空ブランド8種)・室外機・物干し・植木鉢・駐輪・ゴミ集積所・のぼり・提灯・立て看板・足場+養生シート・仮囲い・工事用バリケード・
郵便受け・雨どい・消火設備・電柱の付属物・縁石欠け・歩道の植込み。名前は lf_*。座標: 単独物は原点=地面の設置点・+y=正面。壁付きは壁面y=0・外向き+y。"""
import json
import math
import random
from pathlib import Path

from . import lib_city2 as C2
from .registry import reg
from .xutil import pipe

TEX = Path(__file__).resolve().parents[3] / "assets/textures"


def _uv(name):
    p = TEX / name
    return json.load(open(p))["uv"] if p.exists() else None


def blob(m, x, y, z, r, h, mat, n=8, sq=1.0):
    """丸い塊(ゴミ袋・低木・花)。下すぼまりのラグビー形"""
    m.lathe(x, y, z, [(0.001, 0.0), (r * 0.7, h * 0.12), (r, h * 0.45), (r * 0.8, h * 0.8), (r * 0.3, h * 0.98), (0.001, h)], mat, n)


def _tex_quad(m, pts, outward, mat, uv4):
    u0, v0, u1, v1 = uv4
    m.oriented(pts, outward, mat, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def _cat(name, fn, W, H, cat="生活感"):
    reg(name, (lambda f: lambda m, w_, h_, r: f(m, r))(fn), W=W, H=H, cat=cat)


# ---------------- 自販機 ----------------
BODY = ["vending_body_white", "vending_body_gray", "vending_body_red", "vending_body_blue", "vending_body_black", "vending_body_white", "vending_body_gray", "vending_body_red"]


def vending(m, i):
    uvs = _uv("vending_atlas.json")
    b = BODY[i % len(BODY)]
    m.box(-0.58, -0.38, 0.0, 0.58, 0.38, 1.9, b)
    m.box(-0.6, -0.4, 1.88, 0.6, 0.4, 1.94, b)                                           # 天板の庇
    m.box(-0.58, 0.375, 0.0, 0.58, 0.4, 0.1, "car_trim")                                    # 足元
    if uvs:
        _tex_quad(m, [(0.54, 0.382, 0.14), (-0.54, 0.382, 0.14), (-0.54, 0.382, 1.84), (0.54, 0.382, 1.84)], (0, 1, 0), "vending_atlas", uvs[i % len(uvs)])
    else:
        m.box(-0.54, 0.38, 0.14, 0.54, 0.384, 1.84, "vending_glow")
    m.box(-0.54, 0.384, 1.78, 0.54, 0.39, 1.84, "vending_glow")                           # 上部ライトボックス
    m.box(-0.58, 0.376, 0.1, 0.58, 0.384, 0.14, "car_trim")


def recycle_bin(m, r):
    m.box(-0.3, -0.22, 0.0, 0.3, 0.22, 1.0, "pole_dark")
    for k, c in enumerate(("sheet_blue", "sheet_gray", "fire_red")):
        m.box(-0.28 + k * 0.19, 0.22, 0.62, -0.12 + k * 0.19, 0.225, 0.9, c)
        m.box(-0.25 + k * 0.19, 0.222, 0.72, -0.15 + k * 0.19, 0.228, 0.8, "car_under")


for _i in range(8):
    _cat(f"lf_vend_{_i}", (lambda i: lambda m, r: vending(m, i))(_i), 1.1, 1.9, "自販機")
_cat("lf_vend_recycle", recycle_bin, 0.7, 1.1, "自販機")


# ---------------- 室外機 ----------------
def ac_unit(m, x=0.0, z=0.0, w=0.78, h=0.55, d=0.3):
    m.box(x - w / 2, 0.0, z, x + w / 2, d, z + h, "ac_body")
    cx, cz = x - w * 0.12, z + h * 0.52
    m.cyl(cx, d - 0.002, cz, h * 0.4, 0.006, "y", "ac_grille", 18)                        # ファングリル(円形の凹み)
    for k in (0.12, 0.22, 0.32):
        m.tube(cx, d, cz, h * k + 0.008, h * k, 0.01, "y", "ac_grille", 18)
    m.box(x + w * 0.18, d - 0.003, z + h * 0.1, x + w * 0.44, d + 0.003, z + h * 0.9, "ac_grille")       # 熱交換器の吹出し側
    for k in range(9):
        m.box(x + w * 0.19, d + 0.003, z + h * 0.12 + k * h * 0.09, x + w * 0.43, d + 0.007, z + h * 0.15 + k * h * 0.09, "ac_body")
    m.box(x + w / 2 - 0.09, -0.04, z + 0.06, x + w / 2 - 0.02, 0.0, z + 0.2, "ac_insul")            # 配管カバー


def ac(m, kind):
    if kind == 0:                                                                          # 地置き1台(据付脚)
        for sx in (-0.3, 0.3):
            m.box(sx - 0.05, 0.02, 0.0, sx + 0.05, 0.28, 0.08, "pole_concrete")
        ac_unit(m, 0, 0.08)
        pipe(m, (0.34, -0.02, 0.2), (0.34, -0.02, 1.1), 0.014, "ac_insul", 6)
        pipe(m, (0.38, -0.02, 0.2), (0.38, -0.02, 1.1), 0.01, "ac_pipe", 6)
    elif kind == 1:                                                                        # 2台並び(マンションのベランダ用 壁掛け)
        for sx in (-0.45, 0.45):
            ac_unit(m, sx, 0.15)
        for sx in (-0.5, 0.5):
            m.box(sx - 0.38, 0.0, 0.1, sx + 0.38, 0.3, 0.15, "steel_galv")
    else:                                                                                  # 2段積み
        ac_unit(m, 0, 0.08)
        ac_unit(m, 0, 0.7, 0.78, 0.55, 0.3)
        m.box(-0.45, 0.0, 0.62, 0.45, 0.3, 0.7, "steel_galv")


for _k in range(3):
    _cat(f"lf_ac_{_k}", (lambda k: lambda m, r: ac(m, k))(_k), 1.2, 1.4, "設備")


# ---------------- 物干し ----------------
def laundry(m, kind):
    for sx in (-0.9, 0.9):
        m.box(sx - 0.03, -0.25, 0.0, sx + 0.03, 0.25, 0.04, "steel_galv")
        pipe(m, (sx, 0, 0), (sx, 0, 1.85), 0.018, "steel_galv", 6)
    pipe(m, (-0.95, 0, 1.8), (0.95, 0, 1.8), 0.014, "steel_galv", 6)
    pipe(m, (-0.95, 0.06, 1.7), (0.95, 0.06, 1.7), 0.014, "steel_galv", 6)
    items = [("ped_tex_stripe_navy", 0.5, 0.68), ("ped_cloth_white", 0.55, 0.7), ("ped_tex_plaid_red", 0.5, 0.66), ("ped_tex_denim", 0.4, 0.6), ("ped_cloth_sky", 0.5, 0.66), ("ped_tex_floral", 0.55, 0.6)]
    rg = random.Random(kind)
    x = -0.8
    for k in range(5):
        mt, w, h = items[(k + kind * 2) % len(items)]
        h *= rg.uniform(0.9, 1.1)
        if k == 3 and kind == 1:                                                           # 布団(2本掛け)
            m.box(x - 0.1, -0.12, 1.1, x + 0.9, 0.12, 1.8, "ped_tex_knit_beige")
            x += 1.0
            continue
        m.box(x, -0.012, 1.78 - h, x + w, 0.012, 1.8, mt)
        if h > 0.62:                                                                        # 袖
            m.box(x - 0.18, -0.012, 1.78 - 0.26, x, 0.012, 1.78, mt)
            m.box(x + w, -0.012, 1.78 - 0.26, x + w + 0.18, 0.012, 1.78, mt)
        m.box(x + w * 0.45, -0.02, 1.76, x + w * 0.55, 0.02, 1.84, "pole_plate")           # ハンガー
        x += w + 0.14
        if x > 0.7:
            break


for _k in range(2):
    _cat(f"lf_laundry_{_k}", (lambda k: lambda m, r: laundry(m, k))(_k), 2.0, 1.9)


# ---------------- 植木鉢 ----------------
def plant_pot(m, x, y, r, h, pot, kind, rg):
    m.lathe(x, y, 0.0, [(r * 0.62, 0.0), (r * 0.8, h * 0.08), (r * 1.02, h * 0.92), (r * 1.1, h)], pot, 12)
    m.cyl(x, y, h - 0.02, r * 1.0, 0.02, "z", "soil_dark", 12)
    if kind == "shrub":
        for k in range(3):
            blob(m, x + rg.uniform(-r, r) * 0.4, y + rg.uniform(-r, r) * 0.4, h, r * rg.uniform(0.7, 1.0), r * rg.uniform(1.4, 2.2), "plant_green", 8)
    elif kind == "flower":
        blob(m, x, y, h, r * 0.9, r * 1.1, "plant_green", 8)
        for k in range(7):
            a = rg.uniform(0, 6.28)
            blob(m, x + math.cos(a) * r * rg.uniform(0.2, 0.7), y + math.sin(a) * r * rg.uniform(0.2, 0.7), h + r * rg.uniform(0.5, 1.0), r * 0.18, r * 0.2,
                 rg.choice(["flower_pink", "flower_red", "flower_yellow", "flower_white", "flower_purple"]), 6)
    else:                                                                                  # 背の高い観葉
        for k in range(5):
            a = k * 1.256
            pipe(m, (x, y, h), (x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5, h + r * 2.4), 0.012, "plant_green", 4)
            blob(m, x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5, h + r * 1.8, r * 0.5, r * 0.9, "plant_green", 6)


def pots(m, kind):
    rg = random.Random(kind * 7 + 1)
    if kind == 0:                                                                          # 玄関先の鉢3つ
        for k, (r, h, pot, pk) in enumerate([(0.17, 0.3, "pot_terracotta", "flower"), (0.14, 0.24, "pot_plastic", "shrub"), (0.2, 0.36, "pot_terracotta", "shrub")]):
            plant_pot(m, (k - 1) * 0.5, 0.05 * k, r, h, pot, pk, rg)
    elif kind == 1:                                                                        # 発泡スチロール箱の家庭菜園
        for k in range(3):
            x = (k - 1) * 0.62
            m.box(x - 0.27, -0.18, 0.0, x + 0.27, 0.18, 0.3, "styrofoam")
            m.box(x - 0.25, -0.16, 0.28, x + 0.25, 0.16, 0.31, "soil_dark")
            for j in range(4):
                blob(m, x - 0.18 + j * 0.12, rg.uniform(-0.05, 0.05), 0.31, 0.07, 0.25, "plant_green", 6)
    else:                                                                                  # 大鉢+観葉
        plant_pot(m, 0, 0, 0.3, 0.55, "pot_dark", "tall", rg)
        plant_pot(m, 0.7, 0.1, 0.18, 0.3, "pot_terracotta", "flower", rg)


for _k in range(3):
    _cat(f"lf_pot_{_k}", (lambda k: lambda m, r: pots(m, k))(_k), 1.8, 1.6)


# ---------------- 駐輪 ----------------
def _tilt(mesh, ang):
    """x軸まわりに ang[rad] 回転(転倒自転車用)。重心を地面に合わせる"""
    c, s = math.cos(ang), math.sin(ang)
    mesh.v = [(x, y * c - z * s, y * s + z * c) for x, y, z in mesh.v]
    return mesh


def bike_row(m, kind):
    from .geom import Mesh
    rg = random.Random(kind + 3)
    n = 6 if kind == 0 else 5
    frames = ["bike_frame_silver", "bike_frame_black", "bike_frame_blue", "bike_frame_red", "bike_frame_white"]
    if kind == 1:                                                                          # ラック式(前輪を固定する直線レール)
        m.box(-0.95, -0.03, 0.0, 0.95, 0.03, 0.04, "steel_galv")
    for i in range(n):
        b = Mesh()
        C2.bike(b, rg.choice(frames), rg.random() < 0.7, rg.random() < 0.2, rg.random() < 0.08)
        b = b.transformed(math.pi / 2 + rg.uniform(-0.1, 0.1), 0, 0)                      # 前方を+yへ
        m.add(b.transformed(0, -(n - 1) * 0.27 + i * 0.54, 0), 0, 0, 0)
    if kind == 0:
        m.box(-n * 0.27, -0.9, 0.0, n * 0.27, -0.86, 0.04, "steel_galv")


def bike_fallen(m, r):
    from .geom import Mesh
    b = Mesh()
    C2.bike(b, "bike_frame_silver", True, False, True)
    b = _tilt(b, 1.35).transformed(0.3, 0, 0, 0.0)
    zmin = min(v[2] for v in b.v)
    m.add(b, 0, 0, -zmin)


def bike_group(m, r):
    from .geom import Mesh
    rg = random.Random(11)
    for i in range(4):
        b = Mesh()
        C2.bike(b, rg.choice(["bike_frame_silver", "bike_frame_black", "bike_frame_red"]), True, False, i == 3)
        if i == 3:
            b = _tilt(b, 1.1)
            b = b.transformed(rg.uniform(-0.4, 0.4), 0, 0, -min(v[2] for v in b.v))
        else:
            b = b.transformed(math.pi / 2 + rg.uniform(-0.25, 0.25), 0, 0)
        m.add(b.transformed(0, (i - 1.5) * 0.7, rg.uniform(-0.1, 0.1)), 0, 0, 0)


_cat("lf_bike_row_a", lambda m, r: bike_row(m, 0), 3.4, 1.2, "駐輪")
_cat("lf_bike_row_b", lambda m, r: bike_row(m, 1), 3.0, 1.2, "駐輪")
_cat("lf_bike_fallen", bike_fallen, 1.8, 0.9, "駐輪")
_cat("lf_bike_group", bike_group, 3.0, 1.2, "駐輪")


# ---------------- ゴミ集積所 ----------------
def garbage(m, kind):
    rg = random.Random(kind * 5 + 2)
    bag_m = ["garbage_bag", "garbage_bag", "garbage_bag_yellow", "garbage_bag_green", "garbage_bag_blue"]
    if kind == 0:                                                                          # ワイヤーケージ型(折りたたみ式)
        W, D, H = 1.6, 0.8, 0.9
        for sx in (-W / 2, W / 2):
            for sy in (0.0, D):
                pipe(m, (sx, sy, 0.0), (sx, sy, H), 0.012, "wire_cage", 5)
        for z in (0.0, 0.3, 0.6, H):
            for (a, b) in (((-W / 2, 0.0), (W / 2, 0.0)), ((-W / 2, D), (W / 2, D)), ((-W / 2, 0.0), (-W / 2, D)), ((W / 2, 0.0), (W / 2, D))):
                pipe(m, (a[0], a[1], z + 0.01), (b[0], b[1], z + 0.01), 0.005, "wire_cage", 4)
        for i in range(14):
            blob(m, rg.uniform(-W / 2 + 0.2, W / 2 - 0.2), rg.uniform(0.15, D - 0.15), rg.choice([0.0, 0.0, 0.38]), rg.uniform(0.17, 0.24), rg.uniform(0.35, 0.5), rg.choice(bag_m), 8)
        m.box(-W / 2 + 0.01, 0.01, 0.0, W / 2 - 0.01, D - 0.01, 0.02, "wire_cage")
    elif kind == 1:                                                                        # 路上の山積み+青い防鳥ネット
        for i in range(16):
            blob(m, rg.uniform(-0.7, 0.7), rg.uniform(-0.3, 0.3), rg.choice([0.0, 0.0, 0.3]), rg.uniform(0.18, 0.26), rg.uniform(0.38, 0.5), rg.choice(bag_m), 8)
        prof = [(0.0, -0.9), (0.55, -0.75), (0.85, 0.0), (0.55, 0.75), (0.0, 0.9)]
        m.prism(prof, "y", -0.42, 0.42, "net_blue", caps=False)                              # ネット(帯状の山形)
        for sx in (-0.9, 0.9):
            m.box(sx - 0.04, -0.42, 0.0, sx + 0.04, 0.42, 0.06, "rope_white")
    elif kind == 2:                                                                        # 黄色いカラス除けボックス
        m.box(-0.7, 0.0, 0.0, 0.7, 0.65, 0.82, "sign_yellow")
        m.box(-0.72, -0.04, 0.8, 0.72, 0.69, 0.86, "sign_yellow")
        m.box(-0.64, 0.655, 0.12, 0.64, 0.66, 0.74, "car_under")
        for k in range(4):
            m.box(-0.6 + k * 0.32, 0.66, 0.15, -0.34 + k * 0.32, 0.664, 0.7, "roadwork_black")
    else:                                                                                  # 集合住宅前の分別ポリバケツ+ストッカー
        for k, lid in enumerate(("sheet_blue", "sheet_green", "fire_red", "sign_yellow")):
            x = (k - 1.5) * 0.52
            m.cyl(x, 0, 0.0, 0.22, 0.68, "z", "pot_dark", 14)
            m.cyl(x, 0, 0.68, 0.235, 0.05, "z", lid, 14)
            m.box(x - 0.03, 0.2, 0.7, x + 0.03, 0.26, 0.72, "pot_dark")


for _k in range(4):
    _cat(f"lf_garb_{_k}", (lambda k: lambda m, r: garbage(m, k))(_k), 2.4 if _k != 2 else 1.6, 1.2)


# ---------------- のぼり旗・提灯・立て看板 ----------------
def nobori(m, i, x0=0.0, with_pole=True):
    uvs = _uv("nobori_atlas.json")
    top, w, h = 2.7, 0.5, 1.5
    if with_pole:
        m.box(x0 - 0.2, -0.2, 0.0, x0 + 0.2, 0.2, 0.05, "steel_galv")                      # 水ベース(台)
        m.cyl(x0, 0.0, 0.05, 0.08, 0.2, "z", "pole_dark", 8)
        pipe(m, (x0, 0.0, 0.0), (x0, 0.0, top + 0.05), 0.012, "steel_galv", 6)
        pipe(m, (x0, 0.0, top), (x0 + w + 0.04, 0.0, top), 0.009, "steel_galv", 5)
    u = uvs[i % len(uvs)] if uvs else None
    rows = 9
    for j in range(rows):
        za, zb = top - h * j / rows, top - h * (j + 1) / rows
        ya, yb = 0.05 * math.sin(j * 0.9 + i) * (j / rows), 0.05 * math.sin((j + 1) * 0.9 + i) * ((j + 1) / rows)
        pts = [(x0 + 0.02, ya, za), (x0 + 0.02 + w, ya, za), (x0 + 0.02 + w, yb, zb), (x0 + 0.02, yb, zb)]
        v0 = u[3] - (u[3] - u[1]) * j / rows if u else 0
        v1 = u[3] - (u[3] - u[1]) * (j + 1) / rows if u else 0
        if u:
            uv = [(u[0], v0), (u[2], v0), (u[2], v1), (u[0], v1)]
            m.poly(pts, "nobori_atlas", [(u[2], v0), (u[0], v0), (u[0], v1), (u[2], v1)])
            m.poly(pts[::-1], "nobori_atlas", uv[::-1])
        else:
            m.poly(pts, "barricade_red")


for _i in range(8):
    _cat(f"lf_nobori_{_i}", (lambda i: lambda m, r: nobori(m, i))(_i), 0.8, 2.8, "店先")


def nobori_row(m, r):
    for k in range(3):
        nobori(m, k * 3 + 1, k * 0.9)


_cat("lf_nobori_row", nobori_row, 2.6, 2.8, "店先")


def lantern(m, i, x=0.0, z=0.0, hang=True):
    uvs = _uv("lantern_atlas.json")
    n, h, rmax = 14, 0.42, 0.14
    prof = [(0.07, 0.0), (0.12, 0.05), (rmax, 0.2), (0.12, 0.36), (0.07, h)]
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        am = (a0 + a1) / 2
        rel = math.atan2(math.sin(am - math.pi / 2), math.cos(am - math.pi / 2))
        for p in range(len(prof) - 1):
            (r0, d0), (r1, d1) = prof[p], prof[p + 1]
            q = [(x + r0 * math.cos(a0), r0 * math.sin(a0), z + d0), (x + r0 * math.cos(a1), r0 * math.sin(a1), z + d0),
                 (x + r1 * math.cos(a1), r1 * math.sin(a1), z + d1), (x + r1 * math.cos(a0), r1 * math.sin(a0), z + d1)]
            if uvs:
                c = uvs[i % len(uvs)]
                if abs(rel) > math.pi / 2:
                    ua = ub = c[0] + 0.01
                else:
                    ua = c[0] + (c[2] - c[0]) * (0.5 + (a0 - math.pi / 2) / math.pi * 0.9)
                    ub = c[0] + (c[2] - c[0]) * (0.5 + (a1 - math.pi / 2) / math.pi * 0.9)
                v0, v1 = (d0 / h), (d1 / h)
                m.oriented(q, (math.cos(am), math.sin(am), 0), "lantern_atlas", [(ua, v0), (ub, v0), (ub, v1), (ua, v1)])
            else:
                m.oriented(q, (math.cos(am), math.sin(am), 0), "barricade_red")
    m.cyl(x, 0, z + h, 0.075, 0.025, "z", "car_trim", 12)
    m.cyl(x, 0, z - 0.025, 0.075, 0.025, "z", "car_trim", 12)
    if hang:
        pipe(m, (x, 0, z + h + 0.02), (x, 0, z + h + 0.3), 0.004, "rope_white", 4)


def lantern_hung(m, i):
    pipe(m, (-0.02, 0.0, 2.75), (-0.02, 0.5, 2.75), 0.012, "pole_dark", 6)
    pipe(m, (-0.02, 0.5, 2.75), (-0.02, 0.5, 2.66), 0.004, "rope_white", 4)
    from .geom import Mesh
    b = Mesh()
    lantern(b, i, 0.0, 0.0, False)
    m.add(b.transformed(0, -0.02, 0.5), 0, 0, 2.24)


def lantern_row(m, i):
    for k in range(5):
        from .geom import Mesh
        b = Mesh()
        lantern(b, i + k, 0.0, 0.0, False)
        m.add(b.transformed(0, -1.0 + k * 0.5, 0), 0, 0, 2.3)
    pipe(m, (-1.2, 0, 2.78), (1.2, 0, 2.78), 0.005, "rope_white", 4)
    for k in range(5):
        pipe(m, (-1.0 + k * 0.5, 0, 2.78), (-1.0 + k * 0.5, 0, 2.74), 0.004, "rope_white", 4)


for _i in range(4):
    _cat(f"lf_chou_{_i}", (lambda i: lambda m, r: lantern_hung(m, i))(_i), 0.6, 3.0, "店先")
_cat("lf_chou_row", lambda m, r: lantern_row(m, 0), 2.6, 3.0, "店先")


def stand_sign(m, kind):
    if kind == 1:                                                                          # 置き看板(スタンド+パネル)
        m.box(-0.3, -0.18, 0.0, 0.3, 0.18, 0.04, "steel_galv")
        pipe(m, (-0.22, 0, 0.0), (-0.22, 0, 1.0), 0.012, "steel_galv", 6)
        pipe(m, (0.22, 0, 0.0), (0.22, 0, 1.0), 0.012, "steel_galv", 6)
        m.box(-0.3, -0.02, 0.5, 0.3, 0.02, 1.1, "barricade_red")
        m.box(-0.26, 0.02, 0.9, 0.26, 0.024, 1.06, "barricade_white")
        m.box(-0.26, 0.02, 0.56, 0.26, 0.024, 0.82, "roadwork_yellow")
    else:                                                                                  # 電柱沿いの小さな案内板
        m.box(-0.2, -0.2, 0.0, 0.2, 0.2, 0.05, "pole_concrete")
        pipe(m, (0, 0, 0.0), (0, 0, 1.4), 0.014, "pole_dark", 6)
        m.box(-0.3, -0.015, 0.9, 0.3, 0.015, 1.4, "sign_white")
        m.box(-0.26, 0.015, 1.18, 0.26, 0.019, 1.34, "fire_red")


def a_frame(m, r):
    """A型の立て看板(黒板メニュー): 前後2枚の傾斜板+頂部ヒンジ+前面の白い手書き風の文字行"""
    H = 0.9
    for sy in (-1, 1):
        a, b = (-0.28, sy * 0.3, 0.0), (-0.28, sy * 0.015, H)
        c, d = (0.28, sy * 0.015, H), (0.28, sy * 0.3, 0.0)
        m.oriented([a, d, c, b], (0, sy, 0.2), "stand_sign_black")
        for k in range(6):
            z = 0.18 + k * 0.12
            y = sy * (0.3 - (0.3 - 0.015) * z / H) + sy * 0.003
            w = 0.34 if k % 3 else 0.2
            m.oriented([(-w, y, z), (w, y, z), (w, y, z + 0.02), (-w, y, z + 0.02)], (0, sy, 0), "pole_plate")
        m.box(-0.28, sy * 0.3 - 0.02, 0.0, -0.26, sy * 0.3 + 0.02, 0.03, "stand_sign_black")
        m.box(0.26, sy * 0.3 - 0.02, 0.0, 0.28, sy * 0.3 + 0.02, 0.03, "stand_sign_black")
    m.box(-0.29, -0.03, H - 0.02, 0.29, 0.03, H + 0.02, "stand_sign_black")


_cat("lf_stand_a", a_frame, 0.7, 1.0, "店先")
_cat("lf_stand_panel", lambda m, r: stand_sign(m, 1), 0.7, 1.2, "店先")
_cat("lf_stand_pole", lambda m, r: stand_sign(m, 2), 0.7, 1.5, "店先")


# ---------------- 足場・養生シート・仮囲い ----------------
def scaffold_bay(m, r, w=1.8, d=0.9, h=1.9):
    for sx in (-w / 2, w / 2):
        for sy in (0.0, d):
            pipe(m, (sx, sy, 0.0), (sx, sy, h), 0.0243, "scaffold_steel", 6)
    for z in (0.45, 0.9):                                                                  # 手すり・中桟(外側)
        pipe(m, (-w / 2, d, z), (w / 2, d, z), 0.0243, "scaffold_steel", 6)
    pipe(m, (-w / 2, 0.0, 0.03), (w / 2, 0.0, 0.03), 0.0243, "scaffold_steel", 6)
    pipe(m, (-w / 2, d, 0.03), (w / 2, d, 0.03), 0.0243, "scaffold_steel", 6)
    for sx in (-w / 2, w / 2):
        pipe(m, (sx, 0, 0.03), (sx, d, 0.03), 0.0243, "scaffold_steel", 6)                  # 根がらみ
        pipe(m, (sx, 0, 1.0), (sx, d, 1.0), 0.0243, "scaffold_steel", 6)
    pipe(m, (-w / 2, d, 0.1), (w / 2, d, h - 0.1), 0.0165, "scaffold_steel", 5)            # ブレース
    m.box(-w / 2, 0.08, 0.0, w / 2, d - 0.08, 0.04, "scaffold_plank")                     # 作業床(アンチ)
    m.box(-w / 2, d - 0.02, 0.04, w / 2, d, 0.19, "scaffold_plank")                         # 幅木
    for sx in (-w / 2, w / 2):
        for sy in (0.0, d):
            m.box(sx - 0.03, sy - 0.03, 0.0, sx + 0.03, sy + 0.03, 0.04, "scaffold_clamp")


def scaffold_base(m, r):
    for sx in (-0.9, 0.9):
        for sy in (0.0, 0.9):
            m.box(sx - 0.07, sy - 0.07, 0.0, sx + 0.07, sy + 0.07, 0.01, "scaffold_clamp")
            m.cyl(sx, sy, 0.01, 0.015, 0.22, "z", "scaffold_steel", 6)
    pipe(m, (-0.9, 0, 0.25), (0.9, 0, 0.25), 0.0243, "scaffold_steel", 6)


def scaffold_sheet(m, r, mat="sheet_gray", w=1.8, h=1.9):
    for i in range(10):                                                                    # たるみのある養生シート(外面)
        x0, x1 = -w / 2 + w * i / 10, -w / 2 + w * (i + 1) / 10
        y0, y1 = 0.02 * math.sin(i * 0.9), 0.02 * math.sin((i + 1) * 0.9)
        m.oriented([(x0, y0, 0.0), (x1, y1, 0.0), (x1, y1, h), (x0, y0, h)], (0, 1, 0), mat)
        m.oriented([(x0, y0 - 0.004, 0.0), (x1, y1 - 0.004, 0.0), (x1, y1 - 0.004, h), (x0, y0 - 0.004, h)], (0, -1, 0), mat)
    for k in range(5):                                                                     # ハトメ・結束バンド(上端)
        m.box(-w / 2 + 0.15 + k * 0.38, 0.01, h - 0.05, -w / 2 + 0.2 + k * 0.38, 0.02, h - 0.02, "rope_white")


_cat("lf_scaf_bay", scaffold_bay, 1.9, 2.8, "工事")
_cat("lf_scaf_base", scaffold_base, 1.9, 0.3, "工事")
for _c in ("white", "gray", "blue", "green"):
    _cat(f"lf_scaf_sheet_{_c}", (lambda c: lambda m, r: scaffold_sheet(m, r, "sheet_" + c))(_c), 1.9, 1.9, "工事")


def hoarding(m, mat):
    W, H = 3.0, 3.0
    n = 12
    for i in range(n):                                                                      # 波形鋼板の仮囲い
        x0, x1 = -W / 2 + W * i / n, -W / 2 + W * (i + 1) / n
        yy = 0.02 if i % 2 == 0 else 0.0
        m.oriented([(x0, yy, 0.0), (x1, yy, 0.0), (x1, yy, H), (x0, yy, H)], (0, 1, 0), mat)
        m.oriented([(x0, yy - 0.01, 0.0), (x1, yy - 0.01, 0.0), (x1, yy - 0.01, H), (x0, yy - 0.01, H)], (0, -1, 0), mat)
    for sx in (-W / 2, 0.0, W / 2):
        pipe(m, (sx, -0.05, 0.0), (sx, -0.05, H + 0.1), 0.03, "steel_galv", 6)
        m.box(sx - 0.1, -0.5, 0.0, sx + 0.1, 0.02, 0.06, "pole_concrete")                  # 控えの足(単管)
    m.box(-W / 2, -0.06, H, W / 2, 0.03, H + 0.05, "steel_galv")
    for z in (0.9, 1.9):                                                                     # 補強の横リブ(コの字鋼)
        m.box(-W / 2, 0.025, z, W / 2, 0.045, z + 0.06, "steel_galv")
    m.box(-W / 2, 0.02, 0.0, W / 2, 0.035, 0.14, "pole_concrete")                           # 足元の巾木
    m.box(-1.0, 0.025, 1.15, 0.2, 0.03, 1.75, "sign_white")                                 # 工事看板(文字なしのパネル)
    m.box(-1.0, 0.03, 1.55, 0.2, 0.034, 1.75, "tarp_blue")
    m.box(-0.95, 0.03, 1.2, 0.15, 0.034, 1.4, "sign_yellow")


def hoarding_gate(m, r):
    W, H = 4.0, 3.0
    for sx in (-W / 2, W / 2):
        pipe(m, (sx, 0, 0.0), (sx, 0, H + 0.1), 0.05, "steel_galv", 8)
    for k, sx in enumerate((-1, 1)):
        for i in range(8):
            x0 = sx * 0.02 + sx * (i * 0.25)
            x1 = sx * 0.02 + sx * ((i + 1) * 0.25)
            m.oriented([(x0, 0.0, 0.0), (x1, 0.0, 0.0), (x1, 0.0, 2.6), (x0, 0.0, 2.6)][::sx], (0, 1, 0), "hoard_gray")
    m.box(-W / 2, -0.03, 2.6, W / 2, 0.03, 2.66, "steel_galv")
    m.box(-0.3, 0.02, 1.2, 0.3, 0.03, 1.8, "sign_yellow")                                    # 入口標識
    m.box(-0.28, 0.03, 1.5, 0.28, 0.034, 1.7, "roadwork_black")
    m.box(-0.05, 0.0, 3.0, 0.05, 0.1, 3.3, "pole_dark")
    m.cyl(0, 0.05, 3.3, 0.08, 0.12, "z", "sig_red", 10)                                      # 回転灯


for _c in ("white", "gray", "green"):
    _cat(f"lf_hoard_{_c}", (lambda c: lambda m, r: hoarding(m, "hoard_" + c))(_c), 3.0, 3.2, "工事")
_cat("lf_hoard_gate", hoarding_gate, 4.0, 3.4, "工事")


def barricade(m, r):
    """工事用バリケード(横長の赤白ボード+脚)"""
    for i in range(6):
        c = "barricade_red" if i % 2 == 0 else "barricade_white"
        x0 = -0.9 + i * 0.3
        m.box(x0, -0.015, 0.55, x0 + 0.3, 0.015, 0.9, c)
    for sx in (-0.85, 0.85):
        m.box(sx - 0.03, -0.3, 0.0, sx + 0.03, 0.3, 0.05, "steel_galv")
        pipe(m, (sx, -0.25, 0.04), (sx, 0, 0.9), 0.014, "steel_galv", 5)
        pipe(m, (sx, 0.25, 0.04), (sx, 0, 0.9), 0.014, "steel_galv", 5)
    m.box(-0.06, -0.02, 0.9, 0.06, 0.02, 1.0, "sig_yellow")                                    # 警告灯


def cone_bar(m, r):
    for sx in (-0.8, 0.8):
        m.box(sx - 0.18, -0.18, 0, sx + 0.18, 0.18, 0.03, "rubber")
        m.lathe(sx, 0, 0.03, [(0.12, 0), (0.05, 0.62), (0.03, 0.66)], "cone_orange", 12)
        m.cyl(sx, 0, 0.3, 0.085, 0.1, "z", "reflector_white", 12)
        pipe(m, (sx, 0, 0.64), (sx, 0, 0.7), 0.04, "cone_orange", 8)
    for i in range(8):
        c = "roadwork_yellow" if i % 2 == 0 else "roadwork_black"
        m.box(-0.8 + i * 0.2, -0.02, 0.62, -0.6 + i * 0.2, 0.02, 0.68, c)


def roadwork_sign(m, r):
    """工事中の看板(黄色い三角警戒標識+支柱+土嚢)"""
    pipe(m, (0, 0, 0.0), (0, 0, 1.6), 0.02, "steel_galv", 6)
    m.poly([(-0.35, 0.02, 1.15), (0.35, 0.02, 1.15), (0.0, 0.02, 1.76)], "roadwork_yellow")
    m.poly([(0.0, 0.016, 1.76), (0.35, 0.016, 1.15), (-0.35, 0.016, 1.15)], "steel_gray")
    m.box(-0.1, 0.022, 1.3, 0.1, 0.026, 1.4, "roadwork_black")
    for sx in (-0.3, 0.3):
        m.box(sx - 0.2, -0.15, 0.0, sx + 0.2, 0.15, 0.14, "rope_white")


_cat("lf_barri_fence", barricade, 2.0, 1.1, "工事")
_cat("lf_cone_bar", cone_bar, 2.0, 0.8, "工事")
_cat("lf_barri_sign", roadwork_sign, 1.0, 1.9, "工事")


# ---------------- 郵便受け・雨どい・消火設備 ----------------
def mailbox(m, kind):
    if kind == 0:                                                                          # 門柱の埋込郵便受け+インターホン
        m.box(-0.2, -0.15, 0.0, 0.2, 0.15, 1.3, "pole_concrete")
        m.box(-0.14, 0.15, 0.85, 0.14, 0.18, 1.1, "mailbox_steel")
        m.box(-0.1, 0.18, 0.95, 0.1, 0.182, 1.0, "car_under")
        m.box(-0.05, 0.15, 1.15, 0.05, 0.17, 1.25, "ac_body")
    elif kind == 1:                                                                        # ポール式ポスト(赤・小)
        pipe(m, (0, 0, 0.0), (0, 0, 1.1), 0.025, "pole_dark", 6)
        m.box(-0.14, -0.1, 1.0, 0.14, 0.1, 1.28, "mailbox_red")
        m.box(-0.1, 0.1, 1.15, 0.1, 0.105, 1.18, "car_under")
    else:                                                                                  # 木製門扉に付く郵便受け
        m.box(-0.2, -0.04, 0.0, 0.2, 0.04, 1.2, "mailbox_brown")
        m.box(-0.15, 0.04, 0.8, 0.15, 0.12, 1.0, "mailbox_steel")
        pipe(m, (0.2, 0.08, 0.7), (0.2, 0.08, 1.15), 0.025, "mailbox_steel", 6)            # 新聞受け筒


for _k in range(3):
    _cat(f"lf_mail_{_k}", (lambda k: lambda m, r: mailbox(m, k))(_k), 0.5, 1.4, "外構")


def downpipe(m, r, mat="pipe_gray", h=3.0):
    for z in [z for z in (0.3, 1.5, 2.7) if z < h - 0.1]:
        m.box(-0.03, 0.0, z, 0.03, 0.05, z + 0.03, "mailbox_steel")                       # 受け金具
        m.box(-0.045, 0.045, z - 0.01, 0.045, 0.06, z + 0.04, mat)
    pipe(m, (0, 0.07, 0.0), (0, 0.07, h), 0.03, mat, 10)
    for z in (0.0, h - 0.02):
        m.cyl(0, 0.07, z, 0.036, 0.02, "z", mat, 10)                                       # 継手の膨らみ


def downpipe_base(m, r, mat="pipe_gray"):
    downpipe(m, r, mat, 0.9)
    pipe(m, (0, 0.07, 0.15), (0, 0.15, 0.1), 0.03, mat, 10)
    pipe(m, (0, 0.15, 0.1), (0.0, 0.5, 0.04), 0.03, mat, 10)                                # 地面へ出す曲がり
    m.box(-0.12, 0.45, 0.0, 0.12, 0.7, 0.01, "steel_galv")                                  # 雨水ます蓋


def gutter(m, r, mat="pipe_gray"):
    """軒樋(半円断面)3.6m+集水器(縦樋への落とし口)+吊り金具"""
    n = 8
    L = 3.6
    for i in range(n):
        a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
        c = lambda a: (0.09 + 0.07 * math.cos(a), -0.07 * math.sin(a))
        p0, p1 = c(a0), c(a1)
        m.oriented([(-L / 2, p0[0], p0[1]), (L / 2, p0[0], p0[1]), (L / 2, p1[0], p1[1]), (-L / 2, p1[0], p1[1])], (0, p0[0] - 0.09, p0[1]), mat)
    for k in range(5):
        x = -L / 2 + 0.3 + k * 0.75
        m.box(x - 0.01, 0.0, -0.02, x + 0.01, 0.17, 0.0, "mailbox_steel")
    m.box(-L / 2 - 0.01, 0.02, -0.08, -L / 2, 0.16, 0.0, mat)
    m.box(L / 2, 0.02, -0.08, L / 2 + 0.01, 0.16, 0.0, mat)


for _m, _mat in (("gray", "pipe_gray"), ("brown", "pipe_brown"), ("white", "pipe_white")):
    _cat(f"lf_down_{_m}_3m", (lambda mt: lambda m, r: downpipe(m, r, mt))(_mat), 0.2, 3.0, "外構")
    _cat(f"lf_down_{_m}_base", (lambda mt: lambda m, r: downpipe_base(m, r, mt))(_mat), 0.3, 1.0, "外構")
    _cat(f"lf_down_{_m}_gutter", (lambda mt: lambda m, r: gutter(m, r, mt))(_mat), 3.6, 0.3, "外構")


def hyd_box(m, r):
    m.box(-0.3, 0.0, 0.0, 0.3, 0.3, 1.0, "fire_red")
    m.box(-0.28, 0.3, 0.1, 0.28, 0.31, 0.95, "fire_red")
    m.box(-0.2, 0.31, 0.72, 0.2, 0.314, 0.85, "sign_white")
    m.box(-0.2, 0.31, 0.2, 0.2, 0.314, 0.6, "car_under")
    m.box(-0.34, -0.02, 1.0, 0.34, 0.32, 1.04, "fire_red")
    pipe(m, (-0.1, 0.32, 0.64), (0.1, 0.32, 0.64), 0.012, "mailbox_steel", 6)


def extinguisher_box(m, r):
    m.box(-0.2, 0.0, 0.0, 0.2, 0.25, 0.8, "fire_red")
    m.box(-0.18, 0.25, 0.2, 0.18, 0.254, 0.7, "sign_white")
    m.box(-0.2, -0.02, 0.8, 0.2, 0.27, 0.84, "fire_red")


def cistern_sign(m, r):
    """防火水槽の標識(青地白文字の角板) + 支柱"""
    pipe(m, (0, 0, 0.0), (0, 0, 1.6), 0.025, "pole_dark", 6)
    m.box(-0.3, -0.015, 1.25, 0.3, 0.015, 1.75, "tarp_blue")
    m.box(-0.22, 0.015, 1.4, 0.22, 0.019, 1.6, "sign_white")
    m.box(-0.26, 0.015, 1.65, 0.26, 0.019, 1.7, "fire_red")


_cat("lf_hyd_box", hyd_box, 0.7, 1.1, "消防")
_cat("lf_fire_ext_box", extinguisher_box, 0.5, 0.9, "消防")
_cat("lf_fire_cistern_sign", cistern_sign, 0.7, 1.8, "消防")


# ---------------- 電柱の付属物(電柱軸が原点、半径約0.17m) ----------------
def pole_banner(m, kind):
    """巻き看板(電柱に巻く 黄色+黒文字風の縞 / 赤白)。z=2.6〜3.4"""
    r0 = 0.17
    n = 16
    mats = [("pole_band_yellow", "pole_band_black"), ("barricade_red", "barricade_white"), ("sign_white", "stand_sign_black")][kind % 3]
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        am = (a0 + a1) / 2
        for j, (z0, z1) in enumerate(((2.6, 2.85), (2.85, 3.1), (3.1, 3.4))):
            mt = mats[0] if (j == 1 or (k % 3 == 0 and j != 1)) else mats[1]
            if j == 1 and k % 2 == 0:
                mt = mats[1]
            m.oriented([(r0 * math.cos(a0), r0 * math.sin(a0), z0), (r0 * math.cos(a1), r0 * math.sin(a1), z0),
                        (r0 * math.cos(a1), r0 * math.sin(a1), z1), (r0 * math.cos(a0), r0 * math.sin(a0), z1)], (math.cos(am), math.sin(am), 0), mt)
    m.cyl(0, 0, 2.58, r0 + 0.01, 0.02, "z", "pipe_gray", 16)


def pole_plate(m, r):
    m.box(-0.07, 0.15, 3.6, 0.07, 0.16, 3.9, "pole_plate")
    m.box(-0.06, 0.16, 3.65, 0.06, 0.162, 3.72, "roadwork_black")
    m.box(-0.06, 0.16, 3.78, 0.06, 0.162, 3.84, "fire_red")
    m.box(-0.07, -0.16, 2.2, 0.07, -0.15, 2.4, "sign_white")                               # 反対側: 地名札


def pole_lamp(m, r):
    """防犯灯(LED)。電柱から0.9mのアーム+灯具"""
    pipe(m, (0.1, 0, 5.3), (0.1, 0.9, 5.45), 0.02, "pole_dark", 6)
    m.box(-0.12, 0.7, 5.35, 0.12, 1.15, 5.5, "pole_white")
    m.box(-0.1, 0.72, 5.34, 0.1, 1.12, 5.35, "lamp_lens")


def pole_steps(m, r):
    """昇柱用の足場ボルト(柱の2方向に交互)。電柱の脇に添える"""
    for k in range(12):
        a = 0 if k % 2 == 0 else math.pi
        z = 2.2 + k * 0.3
        pipe(m, (math.cos(a) * 0.1, math.sin(a) * 0.1 - 0.17, z), (math.cos(a) * 0.1 + 0.0, math.sin(a) * 0.1 - 0.32, z), 0.01, "steel_galv", 4)


def pole_guard(m, r):
    """支線ガード(黄黒の縞)+支線(斜めのワイヤ)"""
    for k in range(8):
        m.box(-0.04, -0.04 + 0.0, 0.0 + k * 0.2, 0.04, 0.04, 0.2 + k * 0.2, "pole_band_yellow" if k % 2 == 0 else "pole_band_black")
    pipe(m, (0, 0, 1.6), (-3.0, 0, 6.8), 0.007, "wire", 4)


def pole_closure(m, r):
    """通信ケーブルの接続箱(円筒)+たるんだ予備ケーブルのループ+共架の添架バンド"""
    m.cyl(0.0, 0.2, 5.6, 0.07, 0.55, "z", "pipe_gray", 10)
    for z in (5.7, 6.0):
        m.box(-0.02, 0.05, z, 0.02, 0.2, z + 0.03, "steel_galv")
    loop = [(0.0, -0.2 - 0.1 * math.sin(math.pi * k / 10) * 2.0, 5.5 - 0.5 * math.sin(math.pi * k / 10)) for k in range(11)]
    for a, b in zip(loop, loop[1:]):
        pipe(m, a, b, 0.012, "wire", 5)


def pole_trans(m, r):
    """柱上変圧器(円筒缶+ブッシング)と高圧カットアウト"""
    m.cyl(0.0, 0.32, 8.3, 0.22, 0.8, "z", "pipe_gray", 12)
    for k in (-1, 0, 1):
        m.cyl(k * 0.1, 0.32, 9.1, 0.025, 0.12, "z", "insulator", 8)
    for sx in (-0.5, 0.0, 0.5):
        m.box(sx - 0.04, 0.1, 9.6, sx + 0.04, 0.2, 9.9, "insulator")
        pipe(m, (sx, 0.12, 9.9), (sx, 0.12, 10.2), 0.012, "steel_galv", 5)


for _k in range(3):
    _cat(f"lf_pole_banner_{_k}", (lambda k: lambda m, r: pole_banner(m, k))(_k), 0.5, 3.5, "電柱付属")
_cat("lf_pole_plate", pole_plate, 0.5, 4.0, "電柱付属")
_cat("lf_pole_lamp", pole_lamp, 0.6, 5.6, "電柱付属")
_cat("lf_pole_steps", pole_steps, 0.5, 6.0, "電柱付属")
_cat("lf_pole_guard", pole_guard, 0.5, 1.7, "電柱付属")
_cat("lf_pole_closure", pole_closure, 0.6, 6.2, "電柱付属")
_cat("lf_pole_trans", pole_trans, 1.2, 10.3, "電柱付属")


# ---------------- 縁石の欠け・歩道の植込み ----------------
def curb_chip(m, r):
    """縁石の道路側面(+y向き, y=0が面)に付く欠け: 不規則な凹み+破片+露出した砂利の色"""
    rg = random.Random(4)
    poly = [(-0.08, 0.02), (-0.03, 0.12), (0.04, 0.14), (0.09, 0.06), (0.06, -0.01), (-0.02, -0.02)]
    m.oriented([(x, 0.004, 0.04 + z) for x, z in poly], (0, 1, 0), "curb_chip_dark")
    m.oriented([(x * 0.7, 0.006, 0.05 + z * 0.8) for x, z in poly], (0, 1, 0), "curb_chip")
    for k in range(3):
        m.box(rg.uniform(-0.1, 0.1), 0.0, 0.0, rg.uniform(-0.1, 0.1) + 0.03, 0.04, 0.02, "curb_chip")


_cat("lf_curb_chip", curb_chip, 0.3, 0.2, "地面")


def planter_strip(m, kind):
    """歩道の植込み(幅0.8m×長さ2.0m): コンクリート縁+土+低木(ツツジ系)/花"""
    rg = random.Random(kind + 20)
    m.box(-1.0, -0.4, 0.0, 1.0, -0.34, 0.3, "pole_concrete")
    m.box(-1.0, 0.34, 0.0, 1.0, 0.4, 0.3, "pole_concrete")
    for sx in (-1.0, 0.94):
        m.box(sx, -0.4, 0.0, sx + 0.06, 0.4, 0.3, "pole_concrete")
    m.box(-0.94, -0.34, 0.0, 0.94, 0.34, 0.26, "soil_dark")
    for i in range(7):
        blob(m, -0.8 + i * 0.27 + rg.uniform(-0.04, 0.04), rg.uniform(-0.12, 0.12), 0.26, rg.uniform(0.2, 0.28), rg.uniform(0.32, 0.5), "plant_green", 8)
    if kind == 1:
        for i in range(12):
            blob(m, rg.uniform(-0.85, 0.85), rg.uniform(-0.25, 0.25), 0.5 + rg.uniform(0, 0.12), 0.05, 0.06, rg.choice(["flower_pink", "flower_white", "flower_red"]), 6)


_cat("lf_planter_strip_a", lambda m, r: planter_strip(m, 0), 2.1, 0.9, "植込み")
_cat("lf_planter_strip_b", lambda m, r: planter_strip(m, 1), 2.1, 0.9, "植込み")
