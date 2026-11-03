"""ドア・1階(基壇部)ファサード。"""
import math

from .registry import T, frame, glass, hole_wall, interior, mod, reg


def _door_leaf(m, x0, x1, z0, z1, fm, glazed=True, y=-0.16):
    frame(m, x0, x1, z0, z1, fm, 0.06, 0.07, y)
    if glazed:
        glass(m, x0 + 0.06, x1 - 0.06, z0 + 0.35, z1 - 0.06, y + 0.02)
        m.box(x0 + 0.06, y, z0 + 0.06, x1 - 0.06, y + 0.07, z0 + 0.35, fm)
    else:
        m.box(x0 + 0.06, y + 0.01, z0 + 0.06, x1 - 0.06, y + 0.06, z1 - 0.06, fm)


@mod("door_auto", H=4.0, cat="door")
def _(m, W, H, rng):  # 自動ドア(両引き) + ヘッダー + センサー
    hole_wall(m, W, H, -1.2, 1.2, 0, 2.6, "paint_main")
    interior(m, -1.2, 1.2, 0, 2.6)
    _door_leaf(m, -1.2, 0.0, 0.0, 2.5, "alu_main"); _door_leaf(m, 0.0, 1.2, 0.0, 2.5, "alu_main", y=-0.12)
    m.box(-1.3, -0.2, 2.5, 1.3, 0.1, 2.75, "alu_main")
    m.box(-0.1, 0.1, 2.55, 0.1, 0.16, 2.65, "rubber")
    for x in (-1.15, 1.0):
        m.box(x, -0.14, 0.9, x + 0.15, -0.12, 1.0, "alu_silver")  # 押し板
    m.box(-1.4, 0.0, -0.02, 1.4, 0.8, 0.04, "stone_main")  # 玄関ステップ


@mod("door_swing_steel", H=3.0, cat="door")
def _(m, W, H, rng):
    hole_wall(m, W, H, -0.5, 0.5, 0, 2.15, "paint_main")
    interior(m, -0.5, 0.5, 0, 2.15)
    m.box(-0.55, -0.2, 0, -0.5, 0.05, 2.2, "steel_gray"); m.box(0.5, -0.2, 0, 0.55, 0.05, 2.2, "steel_gray")
    m.box(-0.55, -0.2, 2.15, 0.55, 0.05, 2.2, "steel_gray")
    m.box(-0.5, -0.1, 0, 0.5, -0.04, 2.15, "steel_gray")
    m.box(-0.45, -0.04, 0, 0.45, 0.0, 0.3, "steel_galv")  # キックプレート
    m.cyl(0.35, -0.04, 1.0, 0.012, 0.1, "y", "steel_galv", 8)
    m.box(0.3, 0.05, 0.95, 0.4, 0.12, 1.05, "steel_galv")
    m.box(-0.3, 0.0, 2.5, 0.3, 0.08, 2.65, "plastic_gray")


@mod("door_emergency", H=3.0, cat="door")
def _(m, W, H, rng):  # 非常口 + 誘導灯
    hole_wall(m, W, H, -0.5, 0.5, 0, 2.1, "paint_main")
    interior(m, -0.5, 0.5, 0, 2.1)
    m.box(-0.5, -0.1, 0, 0.5, -0.04, 2.1, "steel_green")
    m.box(-0.55, -0.2, 0, 0.55, 0.04, 0.0, "steel_gray")
    m.box(-0.3, 0.0, 2.25, 0.3, 0.1, 2.55, "sign_green")
    m.box(0.3, -0.04, 0.95, 0.4, 0.06, 1.05, "steel_galv")
    m.box(-0.45, 0.0, -0.02, 0.45, 0.3, 0.04, "rc_concrete")


@mod("door_residential", H=3.0, cat="door")
def _(m, W, H, rng):  # 住戸玄関 + 表札 + ポスト + ひさし
    hole_wall(m, W, H, -0.5, 0.5, 0, 2.1, "paint_main")
    interior(m, -0.5, 0.5, 0, 2.1)
    m.box(-0.5, -0.1, 0, 0.5, -0.03, 2.05, "alu_black")
    m.box(-0.58, -0.2, 0, -0.5, 0.05, 2.15, "alu_black"); m.box(0.5, -0.2, 0, 0.58, 0.05, 2.15, "alu_black")
    m.box(-0.58, -0.2, 2.1, 0.58, 0.05, 2.18, "alu_black")
    m.box(0.3, -0.03, 0.9, 0.4, 0.05, 1.5, "alu_silver")
    m.box(-0.9, 0.0, 1.4, -0.6, 0.03, 1.6, "alu_silver")
    m.box(-0.45, 0.0, 2.3, 0.45, 0.6, 2.34, "alu_main")
    m.box(-0.6, 0.0, -0.02, 0.6, 0.6, 0.05, "rc_concrete")


@mod("door_shutter_rollup", H=3.5, cat="door")
def _(m, W, H, rng):  # 電動巻上げシャッター(スラット)
    hole_wall(m, W, H, -1.4, 1.4, 0, 2.8, "paint_main")
    interior(m, -1.4, 1.4, 0, 2.8)
    z = 0.0
    while z < 2.7:
        m.box(-1.4, -0.12, z, 1.4, -0.09, z + 0.075, "steel_galv"); z += 0.08
    m.box(-1.4, -0.12, 0, 1.4, -0.05, 0.1, "steel_gray")
    m.box(-1.5, -0.22, 2.7, 1.5, 0.15, 3.1, "steel_gray")
    for x in (-1.5, 1.4):
        m.box(x, -0.2, 0, x + 0.1, 0.05, 2.8, "steel_gray")


@mod("door_dock_overhead", H=5.0, W=4.5, cat="door")
def _(m, W, H, rng):  # 搬入口(オーバーヘッドドア) + ドックレベラ
    hole_wall(m, W, H, -1.6, 1.6, 0.0, 3.6, "metal_siding")
    interior(m, -1.6, 1.6, 0, 3.6)
    for i in range(4):
        z = i * 0.9
        m.box(-1.6, -0.14, z + 0.01, 1.6, -0.08, z + 0.89, "steel_white")
        for x in (-1.2, -0.4, 0.4, 1.2):
            m.box(x - 0.25, -0.08, z + 0.5, x + 0.25, -0.05, z + 0.78, "glass_clear" if i == 2 else "steel_white")
    for x in (-1.7, 1.6):
        m.box(x, -0.2, 0, x + 0.1, 0.1, 3.7, "steel_gray")
    m.box(-1.7, -0.2, 3.6, 1.7, 0.1, 3.7, "steel_gray")
    m.box(-1.8, 0.1, 0.0, 1.8, 0.45, 0.1, "rubber")  # バンパー
    m.box(-1.8, 0.0, 0.0, 1.8, 0.1, 1.2, "rc_concrete")  # 荷捌きレベル(段)


@mod("door_revolving", W=4.5, H=4.0, cat="door")
def _(m, W, H, rng):  # 回転ドア + 両脇スイングドア
    hole_wall(m, W, H, -1.9, 1.9, 0, 3.0, "paint_main")
    interior(m, -1.9, 1.9, 0, 3.0)
    m.tube(0, 0.1, 0.05, 1.05, 1.0, 2.7, "z", "glass_clear", 28)
    m.cyl(0, 0.1, 2.75, 1.08, 0.08, "z", "alu_main", 28)
    m.cyl(0, 0.1, 0, 1.08, 0.05, "z", "alu_main", 28)
    for a in (0, 90, 180, 270):
        t = math.radians(a + 25)
        m.box(-0.015, 0.1, 0.1, 0.015, 1.0 + 0.1, 2.65, "glass_clear") if False else None
        px, py = 0.95 * math.cos(t), 0.1 + 0.95 * math.sin(t)
        m.prism([(0, 0), (px, py - 0.1), (px + 0.03, py - 0.1), (0.03, 0)], "z", 0.1, 2.65, "glass_clear") if False else None
    for sx in (-1.6, 1.6):
        _door_leaf(m, sx - 0.4, sx + 0.4, 0, 2.4, "alu_main")
    m.box(-2.0, -0.2, 3.0, 2.0, 0.2, 3.3, "alu_main")


@mod("door_main_stone", H=4.5, W=4.5, cat="door")
def _(m, W, H, rng):  # 石張り玄関ポーチ(列柱 + 庇 + 大型扉)
    hole_wall(m, W, H, -1.0, 1.0, 0, 3.0, "stone_main")
    interior(m, -1.0, 1.0, 0, 3.0)
    _door_leaf(m, -1.0, 0.0, 0, 2.9, "alu_black"); _door_leaf(m, 0.0, 1.0, 0, 2.9, "alu_black", y=-0.12)
    for x in (-1.6, 1.6):
        m.cyl(x, 1.0, 0, 0.22, H - 0.5, "z", "stone_main", 20)
        m.cyl(x, 1.0, 0, 0.3, 0.2, "z", "stone_main", 20)
    m.box(-2.0, -0.1, H - 0.5, 2.0, 1.4, H, "stone_main")
    m.box(-2.0, 0.0, -0.02, 2.0, 1.6, 0.1, "stone_main")
    m.box(-1.2, 1.6, -0.02, 1.2, 2.0, 0.05, "stone_main")  # 階段


# ---- 1階(基壇部)ファサード ----
def _gf_base(m, W, H, mat):
    m.box(-W / 2, -T, 0, W / 2, 0, H, mat)


def _shopfront(m, W, H, sign=True, bulk="paint_dark", mat_wall="paint_dark"):
    h_sign = 0.9 if sign else 0.35
    m.box(-W / 2, -T, 0, W / 2, 0, H, mat_wall)
    m.box(-W / 2 + 0.1, -0.1, 0.0, W / 2 - 0.1, 0.0, 0.5, "stone_main")  # 腰壁
    z1 = H - h_sign - 0.1
    for i, (a, b) in enumerate(((-W / 2 + 0.1, 0.0), (0.0, W / 2 - 0.1))):
        glass(m, a + 0.05, b - 0.05 if i == 0 else b - 0.05, 0.5, z1, -0.1, "glass_clear")
    for x in (-W / 2 + 0.1, 0.0, W / 2 - 0.1):
        m.box(x - 0.04, -0.14, 0.5, x + 0.04, 0.05, z1, "alu_black")
    m.box(-W / 2 + 0.1, -0.14, z1, W / 2 - 0.1, 0.05, z1 + 0.06, "alu_black")
    m.box(-W / 2 + 0.05, -0.12, H - h_sign, W / 2 - 0.05, 0.28, H - 0.05, "paint_white")  # 看板帯
    if sign:
        m.box(-W / 2 + 0.3, 0.28, H - h_sign + 0.12, W / 2 - 0.3, 0.3, H - 0.17, "led_white")
    interior(m, -W / 2 + 0.15, W / 2 - 0.15, 0.5, z1, -0.3)
    m.box(W / 2 - 0.9, -0.1, 0.0, W / 2 - 0.15, 0.0, 2.2, "alu_black") if False else None


reg("gf_storefront", lambda m, W, H, r: _shopfront(m, W, H), H=4.2, cat="gf")
reg("gf_storefront_nosign", lambda m, W, H, r: _shopfront(m, W, H, False, mat_wall="stone_main"), H=4.2, cat="gf")


@mod("gf_entrance_hall", H=5.0, cat="gf")
def _(m, W, H, rng):  # ガラスエントランスホール(大開口 + 庇)
    m.box(-W / 2, -T, 0, W / 2, 0, H, "core")
    m.box(-W / 2, -0.14, 0, W / 2, 0.02, 0.2, "stone_main")
    n = 3
    for i in range(n):
        xa, xb = -W / 2 + i * W / n, -W / 2 + (i + 1) * W / n
        glass(m, xa + 0.03, xb - 0.03, 0.2, H - 0.7, -0.1, "glass_clear")
    for i in range(n + 1):
        x = -W / 2 + i * W / n
        m.box(x - 0.04, -0.14, 0.2, x + 0.04, 0.1, H - 0.7, "alu_black")
    m.box(-W / 2, -0.14, H - 0.75, W / 2, 0.2, H - 0.65, "alu_black")
    m.box(-W / 2, -0.2, H - 0.65, W / 2, 0.5, H, "paint_white")
    interior(m, -W / 2 + 0.1, W / 2 - 0.1, 0.2, H - 0.7, -0.4)


@mod("gf_stone_base", H=4.5, cat="gf")
def _(m, W, H, rng):  # 石張り基壇 + 縦長窓2 + 笠石
    for z0 in range(0, 1):
        pass
    hole_wall(m, W, H, -0.2, 0.2, 1.0, 1.1, "stone_main") if False else None
    m.box(-W / 2, -T, 0, W / 2, -0.03, H, "mortar")
    zs = [0.0]
    while zs[-1] < H - 0.01:
        zs.append(min(H, zs[-1] + rng.choice([0.3, 0.45, 0.6])))
    wins = [(-1.2, -0.5), (0.5, 1.2)]
    for a, b in zip(zs, zs[1:]):
        x = -W / 2
        while x < W / 2 - 0.01:
            w = min(rng.choice([0.6, 0.9, 1.2]), W / 2 - x)
            xa, xb = x + 0.006, x + w - 0.006
            in_win = any(xa < wb and xb > wa and a >= 0.7 and b <= 3.7 for wa, wb in wins)
            if not in_win:
                m.box(xa, -0.03, a + 0.006, xb, rng.uniform(-0.01, 0.01), b - 0.006, "stone_main")
            x += w
    for wa, wb in wins:
        m.box(wa, -0.2, 0.7, wb, -0.03, 3.7, "core")
        glass(m, wa + 0.04, wb - 0.04, 0.8, 3.6, -0.12, "glass_clear")
        frame(m, wa, wb, 0.7, 3.7, "alu_black", 0.06, 0.1)
        interior(m, wa, wb, 0.8, 3.6, -0.3)
        m.box(wa - 0.06, -0.03, 3.7, wb + 0.06, 0.06, 3.82, "stone_main")
        m.box(wa - 0.06, -0.03, 0.64, wb + 0.06, 0.08, 0.7, "stone_main")
    m.box(-W / 2, -0.03, H - 0.01, W / 2, 0.1, H + 0.0, "stone_main") if False else None


@mod("gf_brick_base", H=4.0, cat="gf")
def _(m, W, H, rng):  # レンガ基壇 + アーチ窓風(矩形+まぐさ) + 鎧戸
    from .lib_wall import _grid_wall
    _grid_wall(m, W, H, "mortar", "brick_main", 0.22, 0.075, 0.01, 0.03, True, 0.008, rng)
    for a, b in ((-1.3, -0.3), (0.3, 1.3)):
        m.box(a - 0.1, -0.05, 0.9, b + 0.1, 0.06, 3.0, "stone_main")  # 見切り石枠
        m.box(a, -0.3, 1.0, b, 0.0, 2.9, "core")
        frame(m, a, b, 1.0, 2.9, "alu_black", 0.06, 0.09, -0.12)
        glass(m, a + 0.06, b - 0.06, 1.06, 2.84, -0.07, "glass_clear")
        interior(m, a, b, 1.0, 2.9, -0.35)
    m.box(-W / 2, 0.0, 0, W / 2, 0.06, 0.5, "stone_main")


@mod("gf_metal_base", H=4.0, cat="gf")
def _(m, W, H, rng):  # 金属パネル基壇 + 帯窓
    m.box(-W / 2, -T, 0, W / 2, 0, H, "core")
    n = int(W / 0.6)
    for i in range(n):
        xa, xb = -W / 2 + i * W / n, -W / 2 + (i + 1) * W / n
        m.box(xa + 0.005, 0.0, 0.0, xb - 0.005, 0.03, 1.0, "alu_main")
        m.box(xa + 0.005, 0.0, H - 0.8, xb - 0.005, 0.03, H, "alu_main")
    glass(m, -W / 2, W / 2, 1.0, H - 0.8, -0.05, "glass_clear")
    interior(m, -W / 2, W / 2, 1.0, H - 0.8, -0.3)
    for x in (-W / 2, 0, W / 2 - 0.05):
        m.box(x, -0.05, 1.0, x + 0.05, 0.1, H - 0.8, "alu_black")


@mod("gf_rc_base", H=4.0, cat="gf")
def _(m, W, H, rng):  # 打放しRC基壇 + 深い窓 + 階段取付
    from .lib_wall import _grid_wall
    m.box(-W / 2, -T, 0, W / 2, 0, H, "rc_concrete")
    hole_wall(m, W, H, -1.4, 1.4, 0.4, 3.2, "rc_concrete", t=0.6)
    m.box(-1.4, -0.5, 0.4, 1.4, -0.48, 3.2, "interior")
    glass(m, -1.4, 1.4, 0.4, 3.2, -0.45, "glass_clear")
    for x in (-1.4, -0.47, 0.47, 1.35):
        m.box(x, -0.5, 0.4, x + 0.05, -0.35, 3.2, "alu_black")


@mod("gf_piloti", H=4.5, cat="gf")
def _(m, W, H, rng):  # ピロティ(1階吹抜け: 後退壁 + 円柱 + 駐車)
    m.box(-W / 2, -2.5, 0, W / 2, -2.3, H, "paint_dark")
    m.box(-W / 2, -2.5, 0, W / 2, 0.0, 0.01, "asphalt")
    for x in (-W / 2 + 0.01, W / 2 - 0.01):
        m.cyl(x, 0.0, 0, 0.3, H, "z", "rc_concrete", 20)
    m.box(-W / 2, -2.5, H - 0.4, W / 2, 0, H, "rc_concrete")
    m.box(-0.6, -2.3, 0.0, 0.6, -2.28, 2.2, "steel_galv")  # 奥の扉


@mod("gf_garage_louver", H=4.0, cat="gf")
def _(m, W, H, rng):  # 駐車場開口(縦格子) + 開口内スロープ
    hole_wall(m, W, H, -1.6, 1.6, 0, 2.7, "paint_main")
    m.box(-1.6, -3.0, 0, 1.6, -0.01, 0.01, "asphalt")
    m.box(-1.6, -3.0, 0, 1.6, -2.95, 2.7, "core")
    n = int(3.2 / 0.1)
    for i in range(n):
        x = -1.6 + (i + 0.5) * 3.2 / n
        m.box(x - 0.015, -0.1, 0.1, x + 0.015, -0.05, 2.65, "steel_white")
    for z in (0.1, 1.35, 2.62):
        m.box(-1.6, -0.12, z, 1.6, -0.03, z + 0.05, "steel_white")
    m.box(-1.7, -0.2, 2.7, 1.7, 0.3, 3.0, "paint_dark")


@mod("gf_arcade", H=4.5, cat="gf")
def _(m, W, H, rng):  # アーケード(列柱 + 張出し庇 + 後退した店舗面)
    m.box(-W / 2, -0.2, 0, W / 2, 0.0, 0.5, "stone_main")
    m.box(-W / 2, -0.4, 0.5, W / 2, -0.2, H - 1.0, "glass_clear")
    m.box(-W / 2, -0.4, 0, W / 2, 0.0, 0.01, "stone_main")
    for x in (-W / 2 + 0.2, W / 2 - 0.2):
        m.box(x - 0.2, 2.5, 0, x + 0.2, 2.9, H - 0.6, "stone_main")
        m.box(x - 0.28, 2.42, 0, x + 0.28, 2.98, 0.25, "stone_main")
    m.box(-W / 2, -0.3, H - 1.0, W / 2, 3.0, H - 0.6, "paint_main")
    m.box(-W / 2, 2.5, H - 0.6, W / 2, 3.0, H, "paint_white")
    m.box(-W / 2, 0.0, 0.0, W / 2, 3.0, 0.02, "sidewalk")
    interior(m, -W / 2, W / 2, 0.5, H - 1.0, -0.6)


@mod("gf_curtain", H=4.5, cat="gf")
def _(m, W, H, rng):  # 高階高カーテンウォール(2層吹抜けロビー)
    from .lib_wall import _curtain
    _curtain(m, W, H, 0.3, 0.55, True, "alu_black")


@mod("gf_convenience", H=4.0, cat="gf")
def _(m, W, H, rng):  # コンビニ風: 全面ガラス + 色帯看板 + 軒
    m.box(-W / 2, -T, 0, W / 2, 0, H, "core")
    m.box(-W / 2, -0.12, 0, W / 2, 0.02, 0.35, "alu_main")
    glass(m, -W / 2, W / 2, 0.35, H - 1.1, -0.1, "glass_clear")
    for x in (-W / 2, -W / 6, W / 6, W / 2 - 0.06):
        m.box(x, -0.14, 0.35, x + 0.06, 0.05, H - 1.1, "alu_main")
    m.box(-W / 2, -0.2, H - 1.1, W / 2, 0.5, H - 0.9, "paint_white")
    m.box(-W / 2, -0.2, H - 0.9, W / 2, 0.55, H - 0.35, "led_white")
    m.box(-W / 2, 0.0, H - 0.5, W / 2, 0.56, H - 0.44, "sign_green")
    m.box(-W / 2, -0.2, H - 0.35, W / 2, 0.5, H, "paint_white")
    interior(m, -W / 2 + 0.06, W / 2 - 0.06, 0.35, H - 1.1, -0.5)
