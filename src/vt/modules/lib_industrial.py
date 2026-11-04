"""工場・倉庫・コンビナート部材。工場は波板外壁+煙突+看板+シャッター+事務所入口。プラントは配管ラック・タンク・塔・煙突・フレア・冷却塔・ポンプ・熱交換器・防液堤を部品化。
壁部材: x=壁に沿う, y=外向き(壁面y=0), z=上。単独物: 原点=設置点の地面中央, +y=正面。"""
import math

from .geom3 import beam, tube3
from .registry import T, frame, glass, hole_wall, interior, mod, reg
from .xutil import MATERIALS, M, handrail_x, ibeam_x, ladder_z, pipe, post, prism_any, sign_panel  # noqa: F401


# ============================================================ 工場・倉庫の外壁部材
def _corr_wall(m, W, H, mat):
    m.box(-W / 2, -T, 0, W / 2, 0.0, H, mat)
    m.box(-W / 2, -T, 0, W / 2, 0.04, 0.9, "rc_concrete")                                 # 腰のRC立ち上がり
    for x in (-W / 2 + 0.05, W / 2 - 0.05):
        m.box(x - 0.05, 0.0, 0.9, x + 0.05, 0.05, H, "steel_rusty")                       # 縦の見切り(柱)
    m.box(-W / 2, 0.0, H - 0.12, W / 2, 0.06, H, "steel_galv")                           # 軒先の水切り


for _c in ("gray", "blue", "green", "cream"):
    reg(f"fac_wall_corr_{_c}", (lambda c: lambda m, W, H, r: _corr_wall(m, W, H, f"corrugated_{c}"))(_c), W=3.6, H=4.0, cat="工場")


@mod("fac_wall_panel_cream", W=3.6, H=6.0, cat="工場")
def _(m, W, H, rng):
    """物流倉庫の外壁(ALC/断熱サンドイッチパネル): 水平リブとパネル目地"""
    m.box(-W / 2, -T, 0, W / 2, 0.0, H, "alc")
    z = 0.0
    while z < H:
        m.box(-W / 2, 0.0, z, W / 2, 0.012, z + 0.03, "grout")
        z += 0.6
    m.box(-W / 2, -T, 0, W / 2, 0.03, 0.6, "rc_concrete")
    m.box(-0.01, 0.0, 0.6, 0.01, 0.01, H, "grout")


@mod("fac_window_band", W=3.6, H=4.0, cat="工場")
def _(m, W, H, rng):
    """工場の連続窓(高窓)+ひさし+鉄骨の縦桟"""
    m.box(-W / 2, -T, 0, W / 2, 0.0, 2.2, "corrugated_gray")
    m.box(-W / 2, -T, 3.3, W / 2, 0.0, H, "corrugated_gray")
    m.box(-W / 2, -T, 0, W / 2, 0.04, 0.9, "rc_concrete")
    frame(m, -W / 2 + 0.05, W / 2 - 0.05, 2.2, 3.3, "alu_main", 0.05, 0.08, -0.12)
    glass(m, -W / 2 + 0.1, W / 2 - 0.1, 2.25, 3.25, -0.1)
    interior(m, -W / 2, W / 2, 2.2, 3.3)
    for i in range(1, 4):
        m.box(-W / 2 + i * W / 4 - 0.025, -0.13, 2.2, -W / 2 + i * W / 4 + 0.025, -0.05, 3.3, "alu_main")
    m.box(-W / 2, 0.0, 3.3, W / 2, 0.35, 3.34, "steel_galv")


@mod("fac_door_steel", W=3.6, H=4.0, cat="工場")
def _(m, W, H, rng):
    """工場の人用鉄扉(グレー)+庇+非常灯+ステップ"""
    hole_wall(m, W, H, -0.55, 0.55, 0.0, 2.1, "corrugated_gray")
    interior(m, -0.55, 0.55, 0.0, 2.1)
    frame(m, -0.55, 0.55, 0.0, 2.1, "steel_gray", 0.06, 0.08)
    m.box(-0.5, -0.11, 0.05, 0.5, -0.07, 2.05, "steel_gray")
    m.box(0.3, -0.07, 1.0, 0.42, 0.0, 1.06, "alu_silver")
    m.box(-0.8, 0.0, 2.3, 0.8, 0.9, 2.34, "steel_galv")
    m.box(-0.6, 0.0, 0.0, 0.6, 0.9, 0.2, "rc_concrete")
    m.box(-0.1, 0.0, 2.4, 0.1, 0.1, 2.55, "sign_green")


@mod("fac_shutter_big", W=5.0, H=5.2, cat="工場")
def _(m, W, H, rng):
    """大型の巻き上げ/オーバーヘッドシャッター(トラック搬入口)+黄黒のバンパー表示"""
    hole_wall(m, W, H, -2.0, 2.0, 0.0, 4.2, "corrugated_gray")
    interior(m, -2.0, 2.0, 0.0, 4.2)
    z = 0.0
    while z < 4.2:
        m.box(-2.0, -0.12, z, 2.0, -0.09, min(z + 0.12, 4.2), "steel_galv")
        z += 0.14
    m.box(-2.15, -0.2, 4.2, 2.15, 0.15, 4.6, "steel_gray")
    for sx in (-2.1, 2.1):
        m.box(sx - 0.1, -0.1, 0.0, sx + 0.1, 0.1, 4.2, "steel_gray")
        for k in range(6):
            m.box(sx - 0.1, 0.1, k * 0.7, sx + 0.1, 0.12, k * 0.7 + 0.35, "paint_road_yellow")
    m.box(-2.0, 0.0, 0.0, 2.0, 0.6, 0.12, "rc_concrete")


@mod("fac_entry_office", W=7.2, H=4.0, cat="工場")
def _(m, W, H, rng):
    """工場事務所棟の入口: ガラス引戸+庇+社名プレート。W=7.2(2ベイ分)"""
    hole_wall(m, W, H, -2.0, 2.0, 0.0, 2.5, "paint_white")
    interior(m, -2.0, 2.0, 0.0, 2.5)
    frame(m, -2.0, 2.0, 0.0, 2.5, "alu_silver", 0.06, 0.08, -0.12)
    glass(m, -1.94, 1.94, 0.06, 2.44, -0.1)
    for x in (-1.0, 0.0, 1.0):
        m.box(x - 0.03, -0.14, 0.0, x + 0.03, -0.05, 2.5, "alu_silver")
    m.box(-2.6, 0.0, 2.7, 2.6, 1.6, 2.78, "alu_silver")
    for sx in (-2.4, 2.4):
        m.cyl(sx, 1.4, 0.0, 0.06, 2.7, "z", "steel_white", 8)
    m.box(-2.6, 0.0, 0.0, 2.6, 1.6, 0.1, "rc_concrete")
    sign_panel(m, "fac_a", -1.6, 1.6, 3.05, 3.65, 0.01)


def _fac_sign(m, key):
    m.box(-3.1, 0.0, 0.0, 3.1, 0.18, 1.9, "alu_black")
    sign_panel(m, key, -3.0, 3.0, 0.1, 1.8, 0.185)
    for x in (-2.5, 2.5):
        m.box(x - 0.04, -0.15, 0.2, x + 0.04, 0.0, 0.3, "steel_gray")


for _k in ("fac_a", "fac_b", "fac_c", "fac_d", "fac_e", "fac_f"):
    reg(f"fac_sign_{_k[-1]}", (lambda k: lambda m, W, H, r: _fac_sign(m, k))(_k), W=6.2, H=1.9, cat="工場")


@mod("sp_fac_chimney_brick", W=3.0, H=26.0, cat="工場")
def _(m, W, H, rng):
    """レンガ煙突(古い町工場・銭湯風): 先細りの円筒+鉄バンド+頂部の笠+避雷針"""
    m.cyl(0, 0, 0, 1.4, 1.2, "z", "rc_concrete", 16)
    m.lathe(0, 0, 1.2, [(1.15, 0.0), (0.7, 22.0), (0.78, 22.6), (0.78, 23.4), (0.6, 23.6)], "brick_chimney", 16)
    for z in (4.0, 8.0, 12.0, 16.0, 20.0):
        r = 1.15 - (1.15 - 0.7) * (z - 1.2) / 22.0 + 0.02
        m.cyl(0, 0, z, r, 0.1, "z", "steel_rusty", 16)
    m.cyl(0, 0, 24.8, 0.02, 2.5, "z", "steel_galv", 5)
    ladder_z(m, 0.0, 1.2, 1.5, 22.0, 0.45, "steel_rusty", 0.35)


@mod("sp_fac_chimney_steel", W=3.0, H=24.0, cat="工場")
def _(m, W, H, rng):
    """工場の鋼製煙突(白/赤帯)+支線3本+ダクト取り合い+点検ハシゴ"""
    m.box(-0.9, -0.9, 0, 0.9, 0.9, 0.3, "rc_concrete")
    m.lathe(0, 0, 0.3, [(0.6, 0.0), (0.6, 7.0)], "stack_white", 16)
    for i in range(3):
        z0 = 7.3 + i * 5.0
        m.lathe(0, 0, 0.3 + 7.0 + i * 5.0, [(0.6, 0.0), (0.6, 5.0)], "stack_red" if i % 2 == 0 else "stack_white", 16)
    m.lathe(0, 0, 22.3, [(0.6, 0.0), (0.66, 0.1), (0.66, 0.4)], "steel_gray", 16)
    ladder_z(m, 0.0, 0.63, 1.0, 20.0, 0.4, "steel_gray", 0.3, cage=True)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        tube3(m, [(0.6 * math.cos(a), 0.6 * math.sin(a), 15.0), (7.0 * math.cos(a), 7.0 * math.sin(a), 0.2)], 0.012, "steel_galv", 4)
    pipe(m, (0.6, 0.0, 3.0), (3.0, 0.0, 3.0), 0.35, "pipe_insul", 12)


@mod("fac_vent_turbine", W=0.8, H=1.2, cat="工場")
def _(m, W, H, rng):
    """屋根のベンチレーター(回転式ルーフファン)"""
    m.cyl(0, 0, 0, 0.25, 0.15, "z", "steel_galv", 12)
    m.lathe(0, 0, 0.15, [(0.3, 0.0), (0.36, 0.3), (0.3, 0.7), (0.1, 0.95)], "alu_silver", 14)
    for k in range(12):
        a = 2 * math.pi * k / 12
        m.box(0.3 * math.cos(a) - 0.01, 0.3 * math.sin(a) - 0.01, 0.2, 0.3 * math.cos(a) + 0.01, 0.3 * math.sin(a) + 0.01, 0.8, "alu_silver")


@mod("fac_dust_collector", W=4.0, H=12.0, cat="工場")
def _(m, W, H, rng):
    """集塵機(サイクロン+バグフィルタ箱+ダクト+架台)"""
    for sx in (-1.6, 1.6):
        for sy in (-1.2, 1.2):
            m.box(sx - 0.07, sy - 0.07, 0, sx + 0.07, sy + 0.07, 3.0, "steel_gray")
    m.box(-1.8, -1.4, 3.0, 1.8, 1.4, 7.5, "steel_white")
    for z in (4.0, 5.2, 6.4):
        m.box(-1.82, -1.42, z, 1.82, 1.42, z + 0.05, "steel_galv")
    pipe(m, (0.0, 0.0, 7.5), (0.0, 0.0, 10.5), 0.35, "pipe_insul", 12)
    pipe(m, (0.0, 0.0, 10.5), (3.0, 0.0, 10.5), 0.35, "pipe_insul", 12)
    m.lathe(0, 0, 10.5, [(0.45, 0.0), (0.5, 1.0), (0.4, 1.5)], "steel_white", 12)
    ladder_z(m, 1.85, 0.0, 0.3, 7.5, 0.5, "steel_galv", 0.3)


@mod("fac_silo", W=5.0, H=18.0, cat="工場")
def _(m, W, H, rng):
    """鋼板サイロ(円筒+円錐ホッパー+脚+階段ハシゴ+頂部のベント)"""
    for k in range(4):
        a = math.pi / 4 + math.pi / 2 * k
        m.box(2.0 * math.cos(a) - 0.1, 2.0 * math.sin(a) - 0.1, 0, 2.0 * math.cos(a) + 0.1, 2.0 * math.sin(a) + 0.1, 5.0, "steel_gray")
    m.lathe(0, 0, 3.0, [(0.3, 0.0), (2.4, 3.0)], "steel_white", 20)
    m.lathe(0, 0, 6.0, [(2.4, 0.0), (2.4, 9.0), (1.6, 10.2), (0.3, 11.3), (0.3, 11.6)], "steel_white", 20)
    for z in (8.0, 10.0, 12.0, 14.0):
        m.cyl(0, 0, z, 2.43, 0.07, "z", "steel_gray", 20)
    ladder_z(m, 0.0, -2.45, 0.5, 15.0, 0.5, "steel_galv", 0.3, face=-1, cage=True)


@mod("fac_conveyor_gallery", W=14.0, H=7.0, cat="工場")
def _(m, W, H, rng):
    """ベルトコンベア廊下(傾斜トラス+屋根付きカバー+支柱)。x方向に14m"""
    for x in (-6.5, -2.0, 2.5, 6.5):
        z1 = 1.0 + (x + 7.0) / 14.0 * 5.5
        m.box(x - 0.12, -0.6, 0, x + 0.12, -0.5, z1 - 0.3, "steel_gray")
        m.box(x - 0.12, 0.5, 0, x + 0.12, 0.6, z1 - 0.3, "steel_gray")
    for sy in (-0.6, 0.6):
        beam(m, (-7.0, sy, 1.0), (7.0, sy, 6.5), 0.15, 0.4, "steel_gray")
    beam(m, (-7.0, 0.0, 1.0), (7.0, 0.0, 6.5), 0.9, 0.12, "pipe_dark")
    for i in range(8):
        x = -6.5 + i * 1.8
        z = 1.0 + (x + 7.0) / 14.0 * 5.5
        beam(m, (x, -0.6, z), (x, 0.6, z + 0.9), 0.06, 0.06, "steel_galv")
    m.box(-7.0, -0.7, 1.4, -6.8, 0.7, 2.2, "steel_gray")
    beam(m, (-7.0, 0.0, 1.9), (7.0, 0.0, 7.4), 1.7, 0.05, "corrugated_gray")


@mod("fac_gantry_crane", W=14.0, H=9.0, cat="工場")
def _(m, W, H, rng):
    """門型クレーン(資材置場): 脚+桁+トロリー+ホイスト"""
    for sx in (-6.5, 6.5):
        for sy in (-0.5, 0.5):
            m.box(sx - 0.1, sy - 0.1, 0, sx + 0.1, sy + 0.1, 8.0, "hazard_orange")
        m.box(sx - 0.15, -0.55, 0.0, sx + 0.15, 0.55, 0.2, "steel_gray")
        m.box(sx - 0.1, -0.5, 4.0, sx + 0.1, 0.5, 4.1, "hazard_orange")
    for sy in (-0.5, 0.5):
        m.box(-7.2, sy - 0.15, 8.0, 7.2, sy + 0.15, 8.5, "hazard_orange")
    m.box(-1.0, -0.6, 7.7, 1.0, 0.6, 8.0, "steel_gray")
    m.cyl(0.0, 0, 5.0, 0.01, 2.8, "z", "steel_galv", 4)
    m.box(-0.25, -0.2, 4.6, 0.25, 0.2, 5.0, "steel_gray")
    m.box(-6.8, -0.75, 8.5, 6.8, -0.7, 8.6, "steel_galv")


@mod("log_dock_leveler", W=3.6, H=1.4, cat="工場")
def _(m, W, H, rng):
    """トラックバースのドックレベラー+バンパー+車止め+荷捌き床(物流倉庫)。+y=トラック側"""
    m.box(-1.2, 0.0, 0.0, 1.2, 0.9, 1.2, "rc_concrete")
    m.box(-1.0, 0.0, 1.15, 1.0, 2.0, 1.22, "steel_gray")
    for sx in (-1.1, 1.1):
        m.box(sx - 0.15, 0.9, 0.7, sx + 0.15, 1.0, 1.1, "rubber")
    m.box(-1.3, 0.9, 0.0, 1.3, 3.0, 0.02, "paint_road_yellow")
    for sx in (-1.0, 1.0):
        m.box(sx - 0.03, 0.9, 1.22, sx + 0.03, 1.0, 1.3, "paint_road_yellow")


@mod("log_trailer", W=2.6, H=4.0, cat="工場")
def _(m, W, H, rng):
    """40ftコンテナ/ウイング車のトレーラー(後端をバースに付ける): 長さ12.2m。+x=後方"""
    m.box(-6.1, -1.25, 1.1, 6.1, 1.25, 1.25, "steel_gray")
    m.box(-6.1, -1.25, 1.25, 6.1, 1.25, 3.9, "car_paint_white")
    for i in range(24):
        m.box(-6.0 + i * 0.5, -1.26, 1.3, -5.96 + i * 0.5, 1.26, 3.85, "steel_white")
    for x in (3.4, 4.7, 5.4):
        for sy in (-1, 1):
            m.cyl(x, sy * 1.15, 0.5, 0.5, 0.25, "y", "car_tire", 12)
    m.box(-6.1, -1.2, 1.25, -6.0, 1.2, 2.4, "steel_gray")


# ============================================================ プラント
def _ring_rail(m, r, z, h=1.1, n=24, mat="steel_galv"):
    pts = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
    for hh in (h, h * 0.5):
        tube3(m, [(x, y, z + hh) for x, y in pts], 0.018, mat, 5, False)
    for i in range(n):
        m.cyl(pts[i][0], pts[i][1], z, 0.02, h, "z", mat, 5)


def _spiral(m, R, H, turns, width=0.9, a0=0.0, rise=0.2):
    """外周の螺旋階段(踏み板+外側の手すり)"""
    n = int(H / rise)
    da = 2 * math.pi * turns / n
    r0, r1 = R + 0.04, R + 0.04 + width
    rail, rail2 = [], []
    for i in range(n):
        a = a0 + da * i
        z = (i + 1) * rise
        pts = [(r0 * math.cos(a), r0 * math.sin(a), z), (r1 * math.cos(a), r1 * math.sin(a), z), (r1 * math.cos(a + da), r1 * math.sin(a + da), z), (r0 * math.cos(a + da), r0 * math.sin(a + da), z)]
        m.oriented(pts, (0, 0, 1), "grating")
        m.oriented([(x, y, zz - 0.05) for x, y, zz in pts], (0, 0, -1), "steel_gray")
        rail.append((r1 * math.cos(a), r1 * math.sin(a), z + 1.0))
        rail2.append((r1 * math.cos(a), r1 * math.sin(a), z + 0.5))
        if i % 6 == 0:
            m.cyl(r1 * math.cos(a), r1 * math.sin(a), z, 0.02, 1.0, "z", "steel_galv", 5)
    tube3(m, rail, 0.018, "steel_galv", 5, False)
    tube3(m, rail2, 0.015, "steel_galv", 5, False)
    return n * rise


def _tank_fixed(m, D, H):
    R = D / 2
    m.cyl(0, 0, -0.3, R + 0.4, 0.5, "z", "rc_concrete", 28)                                  # 基礎リング
    n = 28
    m.cyl(0, 0, 0.2, R, H - 0.2, "z", "tank_white", n)
    z = 0.2
    k = 0
    while z < H:
        m.cyl(0, 0, z, R + 0.012, 0.06, "z", "tank_gray", n)                                 # 板の溶接線(段)
        z += 1.8
        k += 1
    m.lathe(0, 0, H, [(R + 0.1, 0.0), (R, 0.15), (R * 0.55, 0.9), (R * 0.12, 1.3), (0.0, 1.35)], "tank_gray", n)   # 浅い円錐屋根
    _ring_rail(m, R + 0.02, H + 0.0, 1.1, 28)
    top = _spiral(m, R, H, max(0.5, H / 9.0), 0.8)
    m.cyl(R * 0.4, 0, H + 1.0, 0.45, 0.4, "z", "steel_gray", 10)                              # マンホール/ベント
    m.cyl(-R * 0.3, R * 0.2, H + 0.95, 0.25, 0.5, "z", "pipe_insul", 10)
    pipe(m, (R, 0.0, 0.8), (R + 3.0, 0.0, 0.8), 0.22, "pipe_insul", 12)                       # 払出し配管+エルボで下へ
    pipe(m, (R + 3.0, 0.0, 0.8), (R + 3.0, 0.0, -0.2), 0.22, "pipe_insul", 12)
    m.cyl(R, 0.0, 0.8, 0.34, 0.08, "x", "steel_galv", 14)                                      # フランジ
    m.cyl(0, -R, 1.0, 0.3, 0.05, "y", "steel_gray", 12)                                        # マンホール
    m.cyl(R + 0.15, -0.5, 0.2, 0.04, H - 0.5, "z", "pipe_insul", 6)                            # 液面計の立管


for _n, (_D, _H) in {"s": (12.0, 9.0), "m": (20.0, 13.0), "l": (32.0, 16.0)}.items():
    reg(f"pl_tank_fixed_{_n}", (lambda d, h: lambda m, W, H, r: _tank_fixed(m, d, h))(_D, _H), W=_D + 6, H=_H + 2, cat="プラント")


def _tank_floating(m, D, H):
    R = D / 2
    n = 36
    m.cyl(0, 0, -0.3, R + 0.4, 0.5, "z", "rc_concrete", n)
    m.cyl(0, 0, 0.2, R, H - 0.2, "z", "tank_gray", n)
    z = 0.2
    while z < H:
        m.cyl(0, 0, z, R + 0.012, 0.06, "z", "tank_white", n)
        z += 2.4
    m.cyl(0, 0, H - 0.1, R + 0.28, 0.12, "z", "steel_gray", n)                                 # ウィンドガーダ(最上部の周回歩廊)
    m.tube(0, 0, H - 0.02, R + 1.1, R + 0.02, 0.04, "z", "grating", n)
    _ring_rail(m, R + 1.1, H - 0.02, 1.1, 36)
    zf = H - 3.2                                                                               # 浮き屋根(中身の量で上下)
    m.cyl(0, 0, zf, R - 0.35, 0.18, "z", "steel_gray", n)
    m.tube(0, 0, zf + 0.18, R - 0.35, R - 0.75, 0.55, "z", "tank_white", n)                    # ポンツーン縁
    m.cyl(0, 0, zf + 0.18, R - 0.75, 0.02, "z", "steel_gray", n)
    beam(m, (R + 0.6, 0, H), (R - 8.0, 0, zf + 0.4), 0.7, 0.1, "grating")                       # 転梯(ローリングラダー)
    top = _spiral(m, R, H, max(0.6, H / 10.0), 0.9)
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.4
        m.cyl((R - 3) * math.cos(a), (R - 3) * math.sin(a), zf + 0.2, 0.15, 1.0, "z", "pipe_insul", 8)
    pipe(m, (R, 0, 1.0), (R + 4.5, 0, 1.0), 0.4, "pipe_insul", 14)
    pipe(m, (R + 4.5, 0, 1.0), (R + 4.5, 0, -0.2), 0.4, "pipe_insul", 14)


reg("pl_tank_floating_m", lambda m, W, H, r: _tank_floating(m, 38.0, 14.0), W=46.0, H=16.0, cat="プラント")
reg("pl_tank_floating_l", lambda m, W, H, r: _tank_floating(m, 60.0, 18.0), W=68.0, H=20.0, cat="プラント")


@mod("pl_sphere_tank", W=22.0, H=22.0, cat="プラント")
def _(m, W, H, rng):
    """球形タンク(LPG等): 球殻+赤道のバンド+8本の脚と筋交い+頂部の作業台+螺旋/ハシゴ"""
    R, zc = 8.0, 11.0
    prof = [(R * math.sin(math.pi * i / 16), -R * math.cos(math.pi * i / 16)) for i in range(17)]
    m.lathe(0, 0, zc, [(r, z) for r, z in prof], "tank_white", 28)
    m.cyl(0, 0, zc - 0.15, R + 0.04, 0.3, "z", "tank_gray", 28)
    for k in range(8):
        a = 2 * math.pi * k / 8
        x, y = (R * 0.94) * math.cos(a), (R * 0.94) * math.sin(a)
        m.cyl(x, y, 0.0, 0.2, zc - 0.5, "z", "pipe_insul", 10)
        m.box(x - 0.45, y - 0.45, -0.3, x + 0.45, y + 0.45, 0.2, "rc_concrete")
        a2 = 2 * math.pi * (k + 1) / 8
        x2, y2 = (R * 0.94) * math.cos(a2), (R * 0.94) * math.sin(a2)
        tube3(m, [(x, y, 2.0), (x2, y2, 8.0)], 0.03, "steel_gray", 5)
        tube3(m, [(x2, y2, 2.0), (x, y, 8.0)], 0.03, "steel_gray", 5)
    m.cyl(0, 0, zc + R - 0.15, 1.5, 0.15, "z", "grating", 12)
    _ring_rail(m, 1.5, zc + R, 1.1, 12)
    m.cyl(0, 0, zc + R, 0.3, 0.7, "z", "steel_gray", 10)
    ladder_z(m, 0.0, -(R * 0.94) - 0.25, 0.3, zc - 0.5, 0.6, "steel_galv", 0.3, face=-1, cage=True)
    pipe(m, (R * 0.94, 0, 0.5), (R + 4.0, 0, 0.5), 0.2, "pipe_insul", 10)


@mod("pl_gasholder", W=36.0, H=44.0, cat="プラント")
def _(m, W, H, rng):
    """ガスホルダー(ウェット式風): 円筒ケース+ガイドフレームの縦トラス+頂部のキャップ"""
    R = 16.0
    m.cyl(0, 0, 0, R, 6.0, "z", "tank_green", 32)
    m.cyl(0, 0, 6.0, R - 0.6, 30.0, "z", "tank_gray", 32)
    for z in (6.0, 12.0, 18.0, 24.0, 30.0, 36.0):
        m.cyl(0, 0, z, R - 0.55, 0.15, "z", "steel_white", 32)
    for k in range(16):
        a = 2 * math.pi * k / 16
        x, y = (R + 0.5) * math.cos(a), (R + 0.5) * math.sin(a)
        m.box(x - 0.2, y - 0.2, 0.0, x + 0.2, y + 0.2, 42.0, "steel_gray")
    for z in (14.0, 28.0, 42.0):
        for k in range(16):
            a, a2 = 2 * math.pi * k / 16, 2 * math.pi * (k + 1) / 16
            tube3(m, [((R + 0.5) * math.cos(a), (R + 0.5) * math.sin(a), z), ((R + 0.5) * math.cos(a2), (R + 0.5) * math.sin(a2), z)], 0.12, "steel_gray", 5, False)
    m.lathe(0, 0, 36.0, [(R - 0.6, 0.0), (R - 3.0, 0.8), (0.0, 1.4)], "tank_gray", 32)
    _ring_rail(m, R - 0.4, 36.0, 1.1, 36)


def _column(m, D, H, nplat, insulated=True):
    r = D / 2
    m.cyl(0, 0, 0, r + 0.5, 0.35, "z", "rc_concrete", 20)
    m.cyl(0, 0, 0.35, r + 0.15, 1.6, "z", "steel_gray", 20)                                     # スカート
    m.lathe(0, 0, 1.95, [(r, 0.0), (r, H - 1.95 - 1.0), (r * 0.6, H - 1.95 - 0.4), (r * 0.15, H - 1.95)], "pipe_insul" if insulated else "tank_gray", 20)
    z = 5.0
    k = 0
    while z < H - 3:
        m.cyl(0, 0, z, r + 0.03, 0.05, "z", "steel_galv", 20)                                    # 保温バンド
        z += 1.5
    for i in range(nplat):
        zp = 5.0 + (H - 9.0) * (i + 0.5) / nplat
        a = i * 1.7
        m.cyl(0, 0, zp, r + 1.2, 0.05, "z", "grating", 18)
        _ring_rail(m, r + 1.2, zp, 1.1, 18)
        beam(m, (r + 0.02, 0, zp), (r + 1.2, 0, zp), 0.1, 0.1, "steel_gray")
    ladder_z(m, 0.0, -(r + 0.35), 1.0, H - 4.0, 0.55, "steel_galv", 0.3, face=-1, cage=True)
    pipe(m, (0.0, 0.0, H - 0.6), (r + 2.5, 0.0, H - 0.6), 0.3, "pipe_insul", 12)                  # 塔頂ベーパー配管
    tube3(m, [(r + 2.5, 0.0, H - 0.6), (r + 2.5, 0.0, 2.0), (r + 5.0, 0.0, 0.8)], 0.3, "pipe_insul", 12)
    for z in (H * 0.35, H * 0.55, H * 0.75):
        pipe(m, (r - 0.05, 0.0, z), (r + 0.9, 0.0, z), 0.12, "pipe_insul", 8)
    m.box(-0.8, -0.8, H, 0.8, 0.8, H + 0.1, "steel_gray")
    beam(m, (0, 0, H + 0.1), (0.0, r + 1.0, H + 1.4), 0.15, 0.15, "pipe_red")                     # ダビット(吊りクレーン)


reg("pl_column_a", lambda m, W, H, r: _column(m, 2.6, 32.0, 4), W=10.0, H=34.0, cat="プラント")
reg("pl_column_b", lambda m, W, H, r: _column(m, 3.6, 46.0, 6), W=12.0, H=48.0, cat="プラント")
reg("pl_column_c", lambda m, W, H, r: _column(m, 1.6, 22.0, 3, False), W=8.0, H=24.0, cat="プラント")


@mod("pl_flare_stack", W=9.0, H=62.0, cat="プラント")
def _(m, W, H, rng):
    """フレアスタック(三脚トラス+立管+先端の炎)+ノックアウトドラム+配管"""
    top = 58.0
    for k in range(3):
        a = 2 * math.pi * k / 3
        tube3(m, [(3.6 * math.cos(a), 3.6 * math.sin(a), 0.0), (0.6 * math.cos(a), 0.6 * math.sin(a), top - 2)], 0.1, "pipe_red", 5, True)
        a2 = 2 * math.pi * (k + 1) / 3
        for z0, z1 in ((0, 12), (12, 26), (26, 42), (42, 56)):
            r0 = 3.6 - 3.0 * z0 / (top - 2)
            r1 = 3.6 - 3.0 * z1 / (top - 2)
            tube3(m, [(r0 * math.cos(a), r0 * math.sin(a), z0), (r1 * math.cos(a2), r1 * math.sin(a2), z1)], 0.04, "steel_gray", 4)
            tube3(m, [(r0 * math.cos(a2), r0 * math.sin(a2), z0), (r1 * math.cos(a), r1 * math.sin(a), z1)], 0.04, "steel_gray", 4)
    m.cyl(0, 0, 0.0, 0.5, top, "z", "pipe_dark", 12)
    m.cyl(0, 0, top, 0.62, 1.8, "z", "pipe_dark", 12)
    m.lathe(0, 0, top + 1.8, [(0.0, 0.0), (0.45, 1.4), (0.2, 3.2), (0.0, 4.2)], "flare_flame", 10)
    pipe(m, (0.0, 0.0, 1.2), (6.0, 0.0, 1.2), 0.3, "pipe_dark", 10)
    for sx in (-1, 1):
        m.box(7.5 + sx * 2.5, 2.3, 0.0, 7.5 + sx * 2.5 + 0.3, 3.7, 0.9, "rc_concrete")
    m.cyl(5.0, 3.0, 1.3, 1.1, 6.0, "x", "tank_gray", 14)
    ladder_z(m, 0.0, -0.6, 0.5, 52.0, 0.45, "steel_galv", 0.3, face=-1, cage=True)


@mod("pl_stack_rw", W=14.0, H=82.0, cat="プラント")
def _(m, W, H, rng):
    """発電所/製油所の紅白煙突(高さ80m): 先細りの円筒を赤白の帯で塗り分け、頂部の作業台と航空障害灯"""
    m.cyl(0, 0, -0.5, 5.8, 1.0, "z", "rc_concrete", 28)
    segs = 11
    R0, R1 = 3.8, 2.0
    zs = [0.5 + 75.0 * i / segs for i in range(segs + 1)]
    for i in range(segs):
        ra = R0 + (R1 - R0) * i / segs
        rb = R0 + (R1 - R0) * (i + 1) / segs
        m.lathe(0, 0, zs[i], [(ra, 0.0), (rb, zs[i + 1] - zs[i])], "stack_red" if i in (0, 2, 4, 6, 8, 10) else "stack_white", 24)
    zt = zs[-1]
    m.cyl(0, 0, zt, R1 + 0.35, 0.2, "z", "steel_gray", 24)
    m.tube(0, 0, zt, R1 + 1.0, R1, 0.1, "z", "grating", 24)
    _ring_rail(m, R1 + 1.0, zt, 1.1, 24)
    for z in (zs[3], zs[7]):
        m.tube(0, 0, z, R1 + 1.0, R1 + 0.3, 0.1, "z", "grating", 24)
    ladder_z(m, 0.0, -(R0 + 0.3), 2.0, zt, 0.55, "steel_galv", 0.3, face=-1, cage=True)
    m.cyl(0, R1 + 0.7, zt + 0.2, 0.2, 0.3, "z", "beacon_red", 8)
    pipe(m, (R0, 0, 4.0), (R0 + 6.0, 0, 4.0), 1.2, "pipe_insul", 16)                                # 煙道


@mod("pl_cooling_tower", W=30.0, H=13.0, cat="プラント")
def _(m, W, H, rng):
    """クロスフロー冷却塔(3セル): ルーバー外壁+ファンスタック+ファン+水槽の基礎"""
    m.box(-14.0, -5.5, 0, 14.0, 5.5, 0.9, "rc_concrete")
    m.box(-14.0, -5.5, 0.9, 14.0, 5.5, 9.0, "tank_white")
    for sy in (-5.5, 5.5):
        for i in range(60):
            m.box(-13.8 + i * 0.46, sy - (0.12 if sy < 0 else 0.0), 1.4, -13.8 + i * 0.46 + 0.32, sy + (0.0 if sy < 0 else 0.12), 8.6, "tank_gray")
    for cx in (-9.3, 0.0, 9.3):
        m.cyl(cx, 0, 9.0, 3.6, 0.2, "z", "tank_gray", 24)
        m.tube(cx, 0, 9.2, 3.55, 3.4, 2.4, "z", "tank_white", 24)
        m.lathe(cx, 0, 11.6, [(3.55, 0.0), (3.7, 0.15)], "steel_gray", 24)
        for k in range(8):
            a = 2 * math.pi * k / 8
            beam(m, (cx, 0, 9.9), (cx + 3.2 * math.cos(a), 3.2 * math.sin(a), 10.0), 0.4, 0.04, "steel_gray")
        m.cyl(cx, 0, 9.2, 0.5, 0.8, "z", "steel_gray", 10)
    pipe(m, (-14.5, 0, 6.0), (-18.0, 0, 6.0), 0.5, "pipe_insul", 12)
    pipe(m, (-18.0, 0, 6.0), (-18.0, 0, 0.0), 0.5, "pipe_insul", 12)


# ---- 配管ラックと配管 ----
def _rack(m, L, Wd, Hr, pipes, cable_tray=False, drop=False):
    """配管ラック1ベイ(長さL, 幅Wd, 高さHr): 柱+梁、上段/下段に配管群、サポート"""
    for sx in (-L / 2, L / 2):
        for sy in (-Wd / 2, Wd / 2):
            m.box(sx - 0.1, sy - 0.1, 0, sx + 0.1, sy + 0.1, Hr, "steel_gray")
            m.box(sx - 0.25, sy - 0.25, -0.1, sx + 0.25, sy + 0.25, 0.15, "rc_concrete")
        for z in (Hr * 0.5, Hr):
            m.box(sx - 0.07, -Wd / 2, z - 0.15, sx + 0.07, Wd / 2, z + 0.15, "steel_gray")
        tube3(m, [(sx, -Wd / 2, 0.3), (sx, Wd / 2, Hr * 0.5 - 0.15)], 0.03, "steel_gray", 4)
    for sy in (-Wd / 2, Wd / 2):
        for z in (Hr * 0.5, Hr):
            m.box(-L / 2, sy - 0.07, z - 0.12, L / 2, sy + 0.07, z + 0.12, "steel_gray")
    n = len(pipes)
    for i, (r, mat, lvl) in enumerate(pipes):
        y = -Wd / 2 + 0.35 + (Wd - 0.7) * (i + 0.5) / n
        z = (Hr if lvl else Hr * 0.5) + 0.15 + r
        pipe(m, (-L / 2 - 0.3, y, z), (L / 2 + 0.3, y, z), r, mat, 12)
        for sx in (-L / 4, L / 4):
            m.box(sx - 0.1, y - r * 0.8, z - r - 0.04, sx + 0.1, y + r * 0.8, z - r + 0.02, "steel_galv")
        for fx in (-L / 2 + 0.2, L / 2 - 0.2):
            m.cyl(fx, y, z, r + 0.05, 0.05, "x", "steel_galv", 12)                                # フランジ
    if cable_tray:
        for sx in range(-int(L / 2), int(L / 2), 1):
            m.box(sx, -0.4, Hr + 0.4, sx + 0.9, 0.4, Hr + 0.46, "grating")
        m.box(-L / 2, -0.4, Hr + 0.4, L / 2, -0.37, Hr + 0.55, "steel_galv")
        m.box(-L / 2, 0.37, Hr + 0.4, L / 2, 0.4, Hr + 0.55, "steel_galv")
    if drop:
        pipe(m, (L / 2, 0.4, Hr + 0.45), (L / 2, 0.4, 0.4), 0.18, "pipe_yellow", 10)


P_A = [(0.2, "pipe_insul", 1), (0.14, "pipe_red", 1), (0.3, "pipe_dark", 1), (0.1, "pipe_green", 1), (0.16, "pipe_blue", 0), (0.1, "pipe_yellow", 0)]
P_B = [(0.22, "pipe_insul", 1), (0.34, "pipe_insul", 1), (0.12, "pipe_red", 1), (0.2, "pipe_dark", 1), (0.12, "pipe_blue", 1), (0.14, "pipe_green", 0), (0.09, "pipe_yellow", 0), (0.18, "pipe_insul", 0)]
reg("pl_pipe_rack_a", lambda m, W, H, r: _rack(m, 6.0, 4.0, 5.0, P_A), W=6.6, H=6.0, cat="プラント")
reg("pl_pipe_rack_b", lambda m, W, H, r: _rack(m, 6.0, 6.0, 6.5, P_B, True), W=6.6, H=8.0, cat="プラント")
reg("pl_pipe_rack_low", lambda m, W, H, r: _rack(m, 6.0, 3.0, 3.2, P_A[:4]), W=6.6, H=4.0, cat="プラント")
reg("pl_pipe_rack_riser", lambda m, W, H, r: _rack(m, 6.0, 4.0, 5.0, P_A, False, True), W=6.6, H=6.0, cat="プラント")


@mod("pl_pipe_loop", W=6.6, H=6.5, cat="プラント")
def _(m, W, H, rng):
    """配管ラック上の伸縮ループ(U字ベンド)"""
    _rack(m, 6.0, 4.0, 5.0, P_A[:3])
    for y, r in ((-1.2, 0.2), (-0.3, 0.14)):
        tube3(m, [(-3.3, y, 5.4), (-2.0, y, 5.4), (-2.0, y, 6.6), (2.0, y, 6.6), (2.0, y, 5.4), (3.3, y, 5.4)], r, "pipe_insul", 10)


@mod("pl_pipe_ground", W=6.0, H=1.6, cat="プラント")
def _(m, W, H, rng):
    """地上配管(枕木式サポート上の3本)+エルボ+フランジ+バルブ"""
    for x in (-2.7, 0.0, 2.7):
        m.box(x - 0.2, -1.1, 0, x + 0.2, 1.1, 0.3, "rc_concrete")
    for i, (y, r, mat) in enumerate(((-0.7, 0.18, "pipe_insul"), (0.0, 0.12, "pipe_red"), (0.7, 0.24, "pipe_dark"))):
        pipe(m, (-3.0, y, 0.3 + r), (3.0, y, 0.3 + r), r, mat, 12)
        for x in (-2.8, 2.8):
            m.cyl(x, y, 0.3 + r, r + 0.05, 0.05, "x", "steel_galv", 12)
    m.cyl(0.0, 0.0, 0.5, 0.03, 0.55, "z", "steel_gray", 6)
    m.cyl(0.0, 0.0, 1.05, 0.22, 0.03, "z", "pipe_red", 12)


@mod("pl_valve_group", W=3.0, H=2.2, cat="プラント")
def _(m, W, H, rng):
    """バルブ群(ゲートバルブ3基+圧力計+ヘッダー配管)"""
    pipe(m, (-1.5, 0, 0.9), (1.5, 0, 0.9), 0.14, "pipe_dark", 12)
    for i, x in enumerate((-1.0, 0.0, 1.0)):
        m.box(x - 0.2, -0.12, 0.76, x + 0.2, 0.12, 1.04, "pipe_dark")
        m.cyl(x, 0, 1.04, 0.05, 0.45, "z", "steel_gray", 8)
        m.cyl(x, 0, 1.5, 0.22, 0.04, "z", "pipe_red", 14)
        pipe(m, (x, 0, 0.9), (x, 0.9, 0.9), 0.08, "pipe_dark", 8)
        m.cyl(x, 0.9, 0.9, 0.12, 0.04, "z", "steel_galv", 10)
    m.cyl(-0.5, 0, 1.04, 0.08, 0.3, "z", "steel_gray", 8)
    m.cyl(-0.5, -0.0, 1.34, 0.1, 0.03, "y", "sign_white", 14)
    for sx in (-1.4, 1.4):
        m.box(sx - 0.08, -0.15, 0, sx + 0.08, 0.15, 0.82, "steel_gray")


@mod("pl_pump_skid", W=3.6, H=1.6, cat="プラント")
def _(m, W, H, rng):
    """遠心ポンプ+モーター+共通ベース+吸込/吐出配管+カップリングガード"""
    m.box(-1.6, -0.6, 0, 1.6, 0.6, 0.18, "rc_concrete")
    m.box(-1.5, -0.45, 0.18, 1.5, 0.45, 0.3, "steel_gray")
    m.cyl(-1.45, 0, 0.75, 0.38, 1.3, "x", "pipe_blue", 16)                                           # モーター
    for k in range(8):
        m.box(-1.4 + k * 0.15, -0.4, 0.34, -1.35 + k * 0.15, 0.4, 0.38, "pipe_blue")
    m.box(-0.2, -0.25, 0.4, 0.2, 0.25, 0.9, "steel_gray")                                              # カップリングガード
    m.lathe(0.95, 0, 0.55, [(0.4, 0.0), (0.4, 0.5)], "pipe_dark", 14)                                 # ポンプケーシング
    m.box(0.55, -0.35, 0.38, 1.4, 0.35, 0.58, "pipe_dark")
    pipe(m, (1.4, 0, 0.62), (1.9, 0, 0.62), 0.14, "pipe_dark", 10)
    tube3(m, [(0.95, 0, 1.2), (0.95, 0, 1.7), (1.9, 0, 1.7)], 0.1, "pipe_insul", 10)
    m.cyl(1.9, 0.0, 0.62, 0.2, 0.05, "x", "steel_galv", 10)


@mod("pl_heat_exchanger", W=9.0, H=3.4, cat="プラント")
def _(m, W, H, rng):
    """横型シェル&チューブ熱交換器: 胴+バンドル引出しフランジ+チャネルヘッド+サドル+ノズル"""
    z = 1.5
    m.cyl(-4.0, 0, z, 0.9, 7.2, "x", "pipe_insul", 22)
    m.cyl(-3.9, 0, z, 1.05, 0.12, "x", "steel_galv", 22)
    m.cyl(3.2, 0, z, 0.75, 1.0, "x", "pipe_insul", 20)
    m.cyl(4.2, 0, z, 0.3, 0.1, "x", "steel_gray", 12)
    for x in (-2.8, 2.0):
        m.box(x - 0.3, -0.8, 0, x + 0.3, 0.8, z - 0.5, "steel_gray")
        m.box(x - 0.5, -0.9, 0, x + 0.5, 0.9, 0.2, "rc_concrete")
    for x, h in ((-2.5, 2.7), (1.5, 2.7)):
        pipe(m, (x, 0, z + 0.85), (x, 0, z + 1.3), 0.2, "pipe_insul", 10)
        pipe(m, (x, 0, z + 1.3), (x + 0.0, 0.8, z + 1.3), 0.2, "pipe_insul", 10)
    pipe(m, (3.4, 0, z + 0.7), (3.4, 0, z + 1.5), 0.15, "pipe_red", 8)
    pipe(m, (3.4, 0, z - 0.7), (3.4, 0, 0.3), 0.15, "pipe_red", 8)


@mod("pl_drum_horizontal", W=9.0, H=3.6, cat="プラント")
def _(m, W, H, rng):
    """横型ドラム/受槽: 胴+楕円鏡板+サドル+マンホール+液面計+ノズル"""
    z = 1.7
    m.cyl(-3.6, 0, z, 1.4, 7.2, "x", "tank_white", 22)
    m.cyl(-3.9, 0, z, 1.3, 0.35, "x", "tank_white", 22)
    m.cyl(3.55, 0, z, 1.2, 0.35, "x", "tank_white", 20)
    for x in (-2.3, 2.3):
        m.box(x - 0.3, -1.2, 0, x + 0.3, 1.2, z - 0.6, "steel_gray")
    m.cyl(0, 0, z + 1.4, 0.45, 0.35, "z", "steel_gray", 12)
    m.cyl(0, 0, z + 1.75, 0.5, 0.06, "z", "steel_galv", 12)
    m.cyl(2.4, 0.9, z + 1.1, 0.12, 0.7, "z", "pipe_insul", 8)
    m.cyl(-2.0, 1.4, 0.5, 0.05, 2.5, "z", "pipe_insul", 6)
    pipe(m, (-2.0, -0.8, z - 1.2), (-2.0, -0.8, 0.0), 0.16, "pipe_dark", 8)
    ladder_z(m, 0.0, -1.8, 0.0, z + 1.4, 0.5, "steel_galv", 0.3, face=-1)


@mod("pl_bund_wall", W=6.0, H=1.6, cat="プラント")
def _(m, W, H, rng):
    """防液堤(RC壁1.5m)の1セグメント+笠+水抜きバルブ。y厚0.4m"""
    m.box(-W / 2, -0.35, 0, W / 2, 0.35, 1.5, "concrete_stained")
    m.box(-W / 2, -0.45, 1.5, W / 2, 0.45, 1.6, "rc_concrete")
    m.box(-W / 2, -0.5, -0.1, W / 2, 0.5, 0.2, "rc_concrete")
    m.cyl(1.5, 0.45, 0.45, 0.04, 0.25, "z", "pipe_red", 8)
    m.cyl(1.5, 0.45, 0.7, 0.12, 0.03, "z", "pipe_red", 12)


@mod("pl_bund_stairs", W=3.6, H=1.8, cat="プラント")
def _(m, W, H, rng):
    """防液堤をまたぐ鋼製ステップ(階段)"""
    for i in range(7):
        m.box(-0.6, -1.6 + i * 0.2, i * 0.22, 0.6, -1.4 + i * 0.2, i * 0.22 + 0.04, "grating")
    m.box(-0.6, -0.2, 1.5, 0.6, 0.2, 1.54, "grating")
    for i in range(7):
        m.box(-0.6, 1.4 - i * 0.2, i * 0.22, 0.6, 1.6 - i * 0.2, i * 0.22 + 0.04, "grating")
    for sx in (-0.62, 0.62):
        tube3(m, [(sx, -1.6, 0.9), (sx, -0.2, 2.5), (sx, 0.2, 2.5), (sx, 1.6, 0.9)], 0.02, "steel_galv", 5)
        tube3(m, [(sx, -1.6, 0.0), (sx, -0.2, 1.5), (sx, 0.2, 1.5), (sx, 1.6, 0.0)], 0.02, "steel_galv", 5)


@mod("pl_loading_rack", W=10.0, H=6.5, cat="プラント")
def _(m, W, H, rng):
    """タンクローリー出荷スタンド: 屋根付きの鉄骨+ローディングアーム2基+配管+昇降ステップ。+y=ローリー側"""
    for sx in (-4.0, 4.0):
        for sy in (-1.0, 1.0):
            m.box(sx - 0.12, sy - 0.12, 0, sx + 0.12, sy + 0.12, 5.0, "steel_gray")
    m.box(-4.5, -1.5, 5.0, 4.5, 1.5, 5.14, "steel_white")
    m.box(-4.5, -1.5, 5.14, 4.5, -1.4, 5.5, "sign_red")
    m.box(-3.0, 0.0, 3.6, 3.0, 0.5, 3.7, "grating")
    pipe(m, (-4.0, -0.7, 4.2), (4.0, -0.7, 4.2), 0.18, "pipe_insul", 10)
    for x in (-1.8, 1.8):
        tube3(m, [(x, -0.7, 4.2), (x, -0.7, 3.2), (x, 0.8, 3.4), (x, 1.4, 2.8)], 0.07, "alu_silver", 8)
        m.cyl(x, 1.4, 2.6, 0.1, 0.25, "z", "steel_gray", 8)
    m.box(-4.4, 0.0, 0.0, -3.2, 0.9, 0.2, "paint_road_yellow")
    m.box(-4.2, 0.0, 0.0, 4.2, 0.2, 0.15, "rc_concrete")


@mod("pl_fire_monitor", W=1.0, H=2.6, cat="プラント")
def _(m, W, H, rng):
    """固定式放水銃(防消火設備)+消火栓箱"""
    m.cyl(0, 0, 0, 0.22, 0.2, "z", "rc_concrete", 10)
    m.cyl(0, 0, 0.2, 0.1, 1.3, "z", "pipe_red", 10)
    beam(m, (0, 0, 1.5), (0.0, 0.7, 1.8), 0.1, 0.1, "pipe_red")
    m.box(0.35, -0.2, 0.0, 0.85, 0.15, 1.3, "pipe_red")


@mod("pl_pipeline_marker", W=0.4, H=2.0, cat="プラント")
def _(m, W, H, rng):
    """埋設パイプラインの位置標識(黄色の支柱+警告板)"""
    m.cyl(0, 0, 0, 0.04, 1.8, "z", "sign_yellow", 8)
    m.box(-0.2, 0.0, 1.35, 0.2, 0.02, 1.85, "sign_yellow")
    m.box(-0.18, 0.02, 1.4, 0.18, 0.025, 1.5, "sign_red")
    m.box(-0.18, 0.02, 1.6, 0.18, 0.025, 1.8, "alu_black")


@mod("pl_pig_launcher", W=8.0, H=2.6, cat="プラント")
def _(m, W, H, rng):
    """ピグ発射受信設備(クイックオープニングクロージャー+バルブ+圧力計+サポート)"""
    z = 1.3
    m.cyl(-3.5, 0, z, 0.28, 5.5, "x", "pipe_dark", 16)
    m.cyl(-3.55, 0, z, 0.42, 0.5, "x", "pipe_blue", 16)
    m.cyl(-3.8, 0, z, 0.46, 0.1, "x", "steel_gray", 16)
    m.cyl(-3.9, 0, z, 0.06, 0.4, "x", "steel_gray", 6)
    for x in (-2.8, 0.2, 2.4):
        m.box(x - 0.2, -0.5, 0, x + 0.2, 0.5, z - 0.3, "steel_gray")
    pipe(m, (2.0, 0, z), (4.0, 0, z), 0.28, "pipe_dark", 12)
    tube3(m, [(4.0, 0, z), (4.0, 0, 0.3), (4.0, 3.0, 0.3)], 0.28, "pipe_dark", 12)
    m.box(1.5, -0.2, z + 0.2, 1.9, 0.2, z + 0.5, "pipe_red")
    m.cyl(1.7, 0, z + 0.5, 0.2, 0.05, "z", "pipe_red", 12)


@mod("pl_transformer", W=6.0, H=6.0, cat="プラント")
def _(m, W, H, rng):
    """屋外変圧器(油入): タンク+放熱器パネル+ブッシング碍子3本+コンサベータ+防油堤"""
    m.box(-3.0, -2.5, 0, 3.0, 2.5, 0.25, "rc_concrete")
    m.box(-2.0, -1.4, 0.25, 2.0, 1.4, 3.2, "tank_gray")
    for i in range(8):
        m.box(2.0, -1.2 + i * 0.3, 0.6, 2.4, -1.2 + i * 0.3 + 0.12, 3.0, "tank_gray")
    for x in (-1.0, 0.0, 1.0):
        m.cyl(x, 0.0, 3.2, 0.1, 1.0, "z", "ceramic", 10)
        for k in range(6):
            m.cyl(x, 0.0, 3.4 + k * 0.14, 0.17, 0.05, "z", "ceramic", 10)
    m.cyl(-1.5, 0.0, 3.5, 0.5, 2.4, "x", "tank_gray", 12)
    pipe(m, (-1.0, 0.0, 3.3), (-1.0, 0.0, 3.6), 0.07, "pipe_dark", 6)


@mod("pl_control_room", W=10.0, H=4.2, cat="プラント")
def _(m, W, H, rng):
    """プラントの計器室(耐爆構造の無窓RC箱+空調+ドア+階段)。+y=正面"""
    m.box(-5.0, -3.0, 0, 5.0, 3.0, 4.0, "rc_concrete")
    m.box(-5.1, -3.1, 4.0, 5.1, 3.1, 4.2, "paint_white")
    m.box(-0.5, 3.0, 0.2, 0.5, 3.1, 2.2, "steel_gray")
    m.box(-1.0, 3.0, 2.3, 1.0, 3.8, 2.36, "steel_galv")
    for i in range(5):
        m.box(-1.0, 3.1 + i * 0.28, i * 0.04, 1.0, 3.28 + i * 0.28, 0.2 + i * 0.04, "rc_concrete")
    for x in (-3.5, -2.2, 3.0):
        m.box(x - 0.45, -3.4, 0.0, x + 0.45, -3.0, 1.1, "ac_white")
    for x in (2.0, 3.0, 4.0):
        m.cyl(x, 2.0, 4.2, 0.1, 0.6, "z", "pipe_insul", 8)


@mod("pl_light_tower", W=1.0, H=14.0, cat="プラント")
def _(m, W, H, rng):
    """プラント用の投光器塔(14m): 鋼管ポール+LED投光器4基+昇降ハシゴ"""
    m.cyl(0, 0, 0, 0.18, 0.3, "z", "rc_concrete", 10)
    m.cyl(0, 0, 0.3, 0.1, 13.0, "z", "steel_galv", 8)
    for k in range(4):
        a = math.pi / 2 * k
        beam(m, (0, 0, 13.0), (0.7 * math.cos(a), 0.7 * math.sin(a), 13.1), 0.08, 0.08, "steel_galv")
        m.box(0.7 * math.cos(a) - 0.25, 0.7 * math.sin(a) - 0.25, 13.1, 0.7 * math.cos(a) + 0.25, 0.7 * math.sin(a) + 0.25, 13.4, "alu_black")
        m.box(0.7 * math.cos(a) - 0.2, 0.7 * math.sin(a) - 0.2, 13.4, 0.7 * math.cos(a) + 0.2, 0.7 * math.sin(a) + 0.2, 13.43, "led_white")
    ladder_z(m, 0.0, -0.14, 0.4, 11.0, 0.35, "steel_galv", 0.3, face=-1)


@mod("pl_stairs_tower", W=3.0, H=14.0, cat="プラント")
def _(m, W, H, rng):
    """プラント内の独立階段塔(鉄骨4本柱+折返し階段+踊り場)"""
    for sx in (-1.2, 1.2):
        for sy in (-1.2, 1.2):
            m.box(sx - 0.08, sy - 0.08, 0, sx + 0.08, sy + 0.08, 12.0, "steel_gray")
    for z in (3.0, 6.0, 9.0, 12.0):
        m.box(-1.3, -1.3, z - 0.05, 1.3, 1.3, z, "grating")
        for sx in (-1.3, 1.3):
            tube3(m, [(sx, -1.3, z + 1.0), (sx, 1.3, z + 1.0)], 0.018, "steel_galv", 4, False)
    for k, z in enumerate((0.0, 3.0, 6.0, 9.0)):
        for i in range(15):
            y = -1.1 + i * 0.15 if k % 2 == 0 else 1.1 - i * 0.15
            m.box(-0.45, y - 0.1, z + i * 0.2, 0.45, y + 0.1, z + i * 0.2 + 0.04, "grating")
