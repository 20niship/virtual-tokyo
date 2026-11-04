"""田舎・郊外の住宅/農村/中規模都市の部材: 日本家屋の壁・窓・玄関・縁側、住宅メーカー風の窓、アパート、門・塀・生垣・物置・土蔵・ハウス。
壁部材の座標系: x=壁に沿う(中心0), y=外向き(壁面y=0), z=上(床0)。"""
import math

from .geom3 import beam
from .registry import T, frame, glass, hole_wall, interior, mod, reg
from .xutil import MATERIALS, arc_roof, handrail_x, ibeam_x, ladder_z, pipe, post, prism_any  # noqa: F401  (材質登録)

FOUND = 0.32     # 基礎の立ち上がり高さ


def _found(m, W, depth=0.03):
    """布基礎(立ち上がり)+通気口(床下換気口)"""
    m.box(-W / 2, -T, 0, W / 2, depth, FOUND, "rc_concrete")
    for x in (-W * 0.3, W * 0.3):
        m.box(x - 0.2, depth, 0.1, x + 0.2, depth + 0.012, 0.22, "steel_gray")
        for i in range(6):
            m.box(x - 0.2 + i * 0.07 + 0.02, depth + 0.012, 0.11, x - 0.2 + i * 0.07 + 0.05, depth + 0.02, 0.21, "alu_black")


def _hw(m, W, H, x0, x1, z0, z1, mat, found=True):
    """開口付きの壁(基礎の上から)。開口z0が基礎より下になる扉は基礎を切る"""
    if found and z0 >= FOUND:
        _found(m, W)
        m.ring((-W / 2, W / 2, FOUND, H), (x0, x1, z0, z1), -T, 0.0, mat, 0.004, 0.004)
    else:
        m.ring((-W / 2, W / 2, 0, H), (x0, x1, z0, z1), -T, 0.0, mat, 0.004, 0.004)


# -------------------------------------------------- 壁
def _wall_boards(m, W, H, mat, pitch=0.15):
    """下見板張り: 板を少しずつ張り出しながら重ねる"""
    _found(m, W)
    m.box(-W / 2, -T, FOUND, W / 2, -0.03, H, "core")
    z, i = FOUND, 0
    while z < H - 0.01:
        h = min(pitch, H - z)
        m.box(-W / 2, -0.03, z, W / 2, 0.0 + 0.004 * (i % 3 == 0), z + h * 1.05, mat)
        m.box(-W / 2, 0.0, z, W / 2, 0.012, z + 0.012, "wood_dark")        # 板の下端の影になる厚み
        z += h
        i += 1
    for x in (-W / 2 + 0.05, W / 2 - 0.05):
        m.box(x - 0.045, 0.0, FOUND, x + 0.045, 0.03, H, "wood_dark")         # 隅の見切り
    return


@mod("wall_shitamiita", cat="日本家屋")
def _(m, W, H, rng):
    _wall_boards(m, W, H, "siding_shitami")


@mod("wall_shitamiita_light", cat="日本家屋")
def _(m, W, H, rng):
    _wall_boards(m, W, H, "siding_shitami_light", 0.18)


@mod("wall_mortar_jp", cat="日本家屋")
def _(m, W, H, rng):
    """モルタル掻き落とし仕上げ+腰の板張り(木造モルタル)"""
    _found(m, W)
    m.box(-W / 2, -T, FOUND, W / 2, 0.0, H, "spray_main")
    m.box(-W / 2, 0.0, FOUND, W / 2, 0.02, FOUND + 0.9, "siding_shitami")           # 腰板
    m.box(-W / 2, 0.0, FOUND + 0.9, W / 2, 0.03, FOUND + 0.94, "wood_dark")
    m.box(-W / 2, 0.0, H - 0.04, W / 2, 0.025, H, "wood_dark")                       # 軒天の見切り
    for x in (-W / 2 + 0.03, W / 2 - 0.03):                                            # 通し柱の見え掛かり
        m.box(x - 0.04, 0.0, FOUND, x + 0.04, 0.012, H, "wood_dark")


def _siding_wall(m, W, H, mat, rows=9):
    """窯業系サイディング: パネル目地の凹+胴縁、シーリング目地"""
    _found(m, W)
    m.box(-W / 2, -T, FOUND, W / 2, 0.0, H, mat)
    z = FOUND
    ph = (H - FOUND) / rows
    for r in range(rows + 1):
        m.box(-W / 2, 0.0, z + r * ph - 0.004, W / 2, 0.004, z + r * ph + 0.004, "grout")
    m.box(-W / 2, -0.01, H - 0.05, W / 2, 0.02, H, "alu_silver")                      # 水切り
    m.box(-0.006, 0.0, FOUND, 0.006, 0.006, H, "rubber")                               # 縦目地のシーリング(中央)


for _n, _m in (("cream", "siding_ceramic_cream"), ("gray", "siding_ceramic_gray"), ("brick", "siding_ceramic_brick")):
    reg(f"wall_siding_{_n}", (lambda mm: lambda m, W, H, r: _siding_wall(m, W, H, mm))(_m), cat="日本家屋")


@mod("wall_itabei", cat="日本家屋")
def _(m, W, H, rng):
    """縦板張り+押縁(焼杉風)"""
    m.box(-W / 2, -T, 0, W / 2, -0.03, H, "core")
    n = int(W / 0.2)
    for i in range(n):
        x0 = -W / 2 + i * W / n
        m.box(x0 + 0.003, -0.03, 0, x0 + W / n - 0.003, 0.0, H, "wood_dark")
    for z in (0.5, H * 0.5, H - 0.3):
        m.box(-W / 2, 0.0, z, W / 2, 0.03, z + 0.05, "wood_dark")                     # 横の押縁
    m.box(-W / 2, -0.03, 0, W / 2, 0.02, 0.3, "garden_stone")


@mod("wall_namako", cat="日本家屋")
def _(m, W, H, rng):
    """なまこ壁: 黒い平瓦を斜めに貼り、目地を白漆喰でかまぼこ状に盛る"""
    m.box(-W / 2, -T, 0, W / 2, -0.03, H, "plaster_white")
    s = 0.22
    z = 0.0
    r = 0
    while z < H - 0.02:
        x = -W / 2 + (s / 2 if r % 2 else 0)
        while x < W / 2:
            xa, xb = max(x + 0.012, -W / 2), min(x + s - 0.012, W / 2)
            if xb > xa + 0.02:
                m.box(xa, -0.03, z + 0.012, xb, -0.005, min(z + s, H) - 0.012, "namako_tile")
            x += s
        z += s
        r += 1
    for k in range(int(H / s) + 1):                                                   # 目地の漆喰の盛り上がり
        zz = k * s
        if zz < H:
            m.box(-W / 2, -0.03, zz - 0.016, W / 2, 0.0, zz + 0.016, "plaster_white")
    m.box(-W / 2, -0.03, 0, W / 2, 0.01, 0.55, "stone_main")


@mod("wall_tin_house", cat="日本家屋")
def _(m, W, H, rng):
    """トタン張り(波板)の納屋/古い住宅: 波板の継ぎ目と胴縁"""
    m.box(-W / 2, -T, 0, W / 2, 0.0, H, "corrugated_gray")
    m.box(-W / 2, -T, 0, W / 2, 0.02, 0.35, "rc_concrete")
    for z in (0.35, H - 0.04):
        m.box(-W / 2, 0.0, z, W / 2, 0.03, z + 0.04, "steel_rusty")
    for x in (-W / 2 + 0.03, W / 2 - 0.03):
        m.box(x - 0.03, 0.0, 0.35, x + 0.03, 0.025, H, "steel_rusty")


reg("corner_post_wood", lambda m, W, H, r: (m.box(-0.07, -0.07, 0, 0.07, 0.07, H, "wood_dark"), m.box(-0.09, -0.09, 0, 0.09, 0.09, 0.32, "rc_concrete")), W=0.2, H=1.0, cat="日本家屋")
reg("corner_post_siding", lambda m, W, H, r: (m.box(-0.06, -0.06, 0, 0.06, 0.06, H, "alu_silver"), m.box(-0.09, -0.09, 0, 0.09, 0.09, 0.32, "rc_concrete")), W=0.2, H=1.0, cat="日本家屋")


# -------------------------------------------------- 窓・戸
def _sash_alu(m, x0, x1, z0, z1, n=2, y0=-0.17, fm="alu_main"):
    w = (x1 - x0) / n
    for i in range(n):
        xa, xb = x0 + i * w - (0.03 if i else 0), x0 + (i + 1) * w + (0.03 if i < n - 1 else 0)
        y = y0 + (0.05 if i % 2 else 0)
        frame(m, xa, xb, z0, z1, fm, 0.04, 0.05, y)
        glass(m, xa + 0.04, xb - 0.04, z0 + 0.04, z1 - 0.04, y + 0.02)


@mod("win_jp_koshi", H=3.0, cat="日本家屋")
def _(m, W, H, rng):
    """出格子窓(木格子+擦りガラスのサッシ)"""
    x0, x1, z0, z1 = -0.65, 0.65, 1.0, 2.0
    _hw(m, W, H, x0, x1, z0, z1, "spray_main")
    interior(m, x0, x1, z0, z1)
    frame(m, x0, x1, z0, z1, "alu_main", 0.05, 0.08)
    m.box(x0 + 0.05, -0.12, z0 + 0.05, x1 - 0.05, -0.108, z1 - 0.05, "frosted_glass")
    m.box(0 - 0.02, -0.13, z0 + 0.05, 0.02, -0.08, z1 - 0.05, "alu_main")
    for i in range(14):                                                                  # 縦の木格子
        x = x0 - 0.02 + i * (x1 - x0 + 0.04) / 13
        m.box(x - 0.012, 0.03, z0 - 0.04, x + 0.012, 0.08, z1 + 0.04, "wood_dark")
    for z in (z0 - 0.06, z1 + 0.02):
        m.box(x0 - 0.08, 0.02, z, x1 + 0.08, 0.1, z + 0.045, "wood_dark")
    m.box(x0 - 0.1, 0.0, z0 - 0.1, x1 + 0.1, 0.12, z0 - 0.06, "wood_dark")


@mod("win_jp_engawa", H=3.0, cat="日本家屋")
def _(m, W, H, rng):
    """縁側: 大きな掃出し引違い窓(ガラス戸+障子)と縁側の床・沓脱石・濡れ縁"""
    x0, x1, z0, z1 = -1.6, 1.6, 0.52, 2.1
    _hw(m, W, H, x0, x1, z0, z1, "spray_main")
    interior(m, x0, x1, z0, z1)
    _sash_alu(m, x0, x1, z0, z1, 4)
    for xs in (-0.8, 0.8):                                                                # 障子
        m.box(xs - 0.8 + 0.02, -0.26, z0 + 0.04, xs + 0.8 - 0.02, -0.245, z1 - 0.04, "paper_shoji")
        for k in range(1, 6):
            m.box(xs - 0.8 + k * 0.267 - 0.008, -0.265, z0 + 0.04, xs - 0.8 + k * 0.267 + 0.008, -0.24, z1 - 0.04, "wood_light")
        for k in range(1, 4):
            m.box(xs - 0.8, -0.265, z0 + 0.04 + k * (z1 - z0 - 0.08) / 4 - 0.008, xs + 0.8, -0.24, z0 + 0.04 + k * (z1 - z0 - 0.08) / 4 + 0.008, "wood_light")
    m.box(x0 - 0.1, -0.02, z0 - 0.08, x1 + 0.1, 1.0, z0 - 0.02, "wood_light")             # 縁側(濡れ縁)の床板
    for i in range(5):
        m.box(x0 - 0.1, i * 0.2 + 0.003, z0 - 0.08, x1 + 0.1, i * 0.2 + 0.197, z0 - 0.02, "wood_light" if i % 2 else "wood_dark")
    for x in (x0 - 0.06, 0.0, x1 + 0.06):
        m.box(x - 0.05, 0.9, 0.0, x + 0.05, 1.0, z0 - 0.08, "wood_dark")                  # 束
        m.box(x - 0.1, 0.85, 0.0, x + 0.1, 1.05, 0.08, "garden_stone")                    # 束石
    for k, (sx, sy, sz) in enumerate(((0.3, 1.7, 0.18), (-0.5, 1.5, 0.1))):               # 沓脱石・飛び石
        m.box(sx - 0.35, sy - 0.2, 0, sx + 0.35, sy + 0.2, sz, "garden_stone")


@mod("win_jp_genkan", H=3.0, cat="日本家屋")
def _(m, W, H, rng):
    """玄関引戸: 木枠+格子入りガラスの2枚引戸、框、敷居の石"""
    x0, x1, z0, z1 = -0.95, 0.95, 0.06, 2.1
    _hw(m, W, H, x0, x1, z0, z1, "spray_main", found=False)
    m.box(-W / 2, -T, 0, W / 2, 0.03, 0.06, "rc_concrete")
    interior(m, x0, x1, z0, z1)
    for k, xa in enumerate((x0, 0.0)):
        y = -0.14 + 0.04 * k
        xb = xa + 0.95
        frame(m, xa, xb, z0, z1, "wood_dark", 0.07, 0.05, y)
        m.box(xa + 0.07, y + 0.02, z0 + 0.1, xb - 0.07, y + 0.026, z1 - 0.1, "frosted_glass")
        for i in range(1, 4):                                                              # 組子
            m.box(xa + 0.07 + i * (0.81 / 4) - 0.006, y + 0.026, z0 + 0.1, xa + 0.07 + i * (0.81 / 4) + 0.006, y + 0.04, z1 - 0.1, "wood_dark")
        for i in range(1, 6):
            m.box(xa + 0.07, y + 0.026, z0 + 0.1 + i * (z1 - z0 - 0.2) / 6 - 0.006, xb - 0.07, y + 0.04, z0 + 0.1 + i * (z1 - z0 - 0.2) / 6 + 0.006, "wood_dark")
        m.box(xa + 0.07, y + 0.0, z0 + 0.04, xb - 0.07, y + 0.05, z0 + 0.7, "wood_dark")     # 腰板
    m.box(x0 - 0.1, 0.0, 0.0, x1 + 0.1, 0.7, 0.14, "garden_stone")                          # たたき(石張り)
    m.box(x1 + 0.12, 0.0, 1.35, x1 + 0.4, 0.04, 1.65, "wood_dark")                          # 表札板
    m.box(x1 + 0.14, 0.04, 1.4, x1 + 0.38, 0.044, 1.6, "sign_white")
    m.box(x0 - 0.3, 0.02, 2.2, x1 + 0.3, 0.3, 2.24, "wood_dark")                            # 小庇


@mod("win_jp_amado", H=3.0, cat="日本家屋")
def _(m, W, H, rng):
    """雨戸(戸袋)付き引違い窓"""
    x0, x1, z0, z1 = -0.9, 0.5, 0.8, 2.2
    _hw(m, W, H, x0, x1, z0, z1, "spray_main")
    interior(m, x0, x1, z0, z1)
    _sash_alu(m, x0, x1, z0, z1, 2)
    m.box(0.55, -0.02, 0.65, 1.05, 0.2, 2.35, "wood_dark")                                   # 戸袋
    for i in range(8):
        m.box(0.58, 0.2, 0.7 + i * 0.2, 1.02, 0.206, 0.88 + i * 0.2, "wood_light")
    m.box(x0 - 0.06, 0.0, z0 - 0.07, x1 + 0.06, 0.12, z0 - 0.02, "alu_silver")


@mod("win_maker_shutter", H=3.0, cat="戸建")
def _(m, W, H, rng):
    """住宅メーカー風: 引違い窓+シャッターボックス(雨戸)+アルミ面格子"""
    x0, x1, z0, z1 = -0.9, 0.9, 0.9, 2.2
    _hw(m, W, H, x0, x1, z0, z1, "siding_ceramic_cream")
    interior(m, x0, x1, z0, z1)
    _sash_alu(m, x0, x1, z0, z1, 2, fm="alu_bronze")
    m.box(x0 - 0.04, -0.01, z1 + 0.04, x1 + 0.04, 0.2, z1 + 0.34, "steel_white")              # シャッターボックス
    m.box(x0 - 0.04, 0.19, z1 + 0.04, x1 + 0.04, 0.215, z1 + 0.06, "alu_black")
    m.box(x0 - 0.1, 0.0, z0 - 0.06, x1 + 0.1, 0.1, z0 - 0.015, "alu_silver")                  # 水切り
    for i in range(9):
        m.box(x0 + i * (x1 - x0) / 8 - 0.012, 0.09, z0 + 0.03, x0 + i * (x1 - x0) / 8 + 0.012, 0.11, z1 - 0.03, "alu_bronze")


@mod("win_maker_pair", H=3.0, cat="戸建")
def _(m, W, H, rng):
    """縦長の2連窓(外開き)+出窓カウンター"""
    _hw(m, W, H, -1.2, 1.2, 0.95, 2.2, "siding_ceramic_gray")
    interior(m, -1.2, 1.2, 0.95, 2.2)
    for xa, xb in ((-1.2, 0.0), (0.0, 1.2)):
        frame(m, xa, xb, 0.95, 2.2, "alu_black", 0.05, 0.07, -0.17)
        glass(m, xa + 0.05, xb - 0.05, 1.0, 2.15, -0.15)
        m.box((xa + xb) / 2 - 0.2, -0.2, 1.5, (xa + xb) / 2 - 0.17, -0.1, 1.65, "steel_galv")
    m.box(-1.3, 0.0, 0.9, 1.3, 0.12, 0.96, "alu_silver")


@mod("win_maker_fix", H=3.0, cat="戸建")
def _(m, W, H, rng):
    """FIX窓+小窓(すべり出し)の組合せ"""
    _hw(m, W, H, -1.4, 1.4, 0.7, 2.3, "siding_ceramic_cream")
    interior(m, -1.4, 1.4, 0.7, 2.3)
    frame(m, -1.4, 0.4, 0.7, 2.3, "alu_bronze", 0.05, 0.1)
    glass(m, -1.35, 0.35, 0.75, 2.25)
    frame(m, 0.4, 1.4, 1.3, 2.3, "alu_bronze", 0.05, 0.08, -0.17)
    glass(m, 0.45, 1.35, 1.35, 2.25, -0.15)
    m.box(0.4, -0.18, 0.7, 1.4, -0.05, 1.3, "alu_bronze")
    m.box(-1.5, 0.0, 0.64, 1.5, 0.1, 0.7, "alu_silver")


@mod("door_maker_entry", H=3.0, cat="戸建")
def _(m, W, H, rng):
    """玄関ドア(縦スリット窓付き断熱ドア)+ポーチ庇+ポーチライト+タイルの土間"""
    x0, x1, z0, z1 = -0.55, 0.55, 0.12, 2.15
    _hw(m, W, H, x0, x1, z0, z1, "siding_ceramic_cream", found=False)
    m.box(-W / 2, -T, 0, W / 2, 0.03, 0.12, "rc_concrete")
    interior(m, x0, x1, z0, z1)
    frame(m, x0, x1, z0, z1, "alu_bronze", 0.06, 0.09)
    m.box(x0 + 0.06, -0.12, z0 + 0.06, x1 - 0.06, -0.07, z1 - 0.06, "wood_light")
    m.box(x1 - 0.32, -0.065, z0 + 0.3, x1 - 0.2, -0.06, z1 - 0.3, "frosted_glass")
    m.box(x0 + 0.1, -0.06, 1.0, x0 + 0.13, 0.02, 1.35, "alu_silver")                         # 引手
    m.box(-0.8, 0.0, 2.3, 0.8, 1.4, 2.38, "alu_bronze")                                        # 袖壁付きポーチ庇
    m.box(-0.8, 1.35, 2.15, -0.75, 1.4, 2.38, "alu_bronze")
    m.box(-0.8, 0.0, 0.0, 0.8, 1.4, 0.12, "tile_main")
    m.cyl(-0.7, 0.05, 1.9, 0.07, 0.06, "y", "led_white", 10)


@mod("apt_door_row", H=3.0, cat="アパート")
def _(m, W, H, rng):
    """木造アパート2階の開放廊下側: 玄関ドア+小窓+メーターBOX+手すり付き廊下床(鋼製)"""
    _hw(m, W, H, -0.45, 0.45, 0.05, 2.05, "spray_main", found=False)
    interior(m, -0.45, 0.45, 0.05, 2.05)
    frame(m, -0.45, 0.45, 0.05, 2.05, "steel_gray", 0.05, 0.07)
    m.box(-0.4, -0.12, 0.1, 0.4, -0.08, 2.0, "steel_green")
    m.box(-0.1, -0.08, 1.0, 0.1, 0.0, 1.1, "alu_silver")
    m.box(0.55, -0.02, 1.2, 0.95, 0.12, 2.0, "steel_white")                                    # メーターBOX
    m.box(-0.9, -0.02, 1.4, -0.55, 0.01, 1.9, "frosted_glass")                                 # 台所小窓の格子
    m.box(-W / 2, 0.0, -0.1, W / 2, 1.2, 0.0, "rc_concrete")                                   # 廊下床スラブ
    handrail_x(m, -W / 2, W / 2, 1.15, 0.0, 1.0, "steel_galv", 1.2)
    for i in range(int(W / 0.12)):
        m.box(-W / 2 + i * 0.12, 1.14, 0.1, -W / 2 + i * 0.12 + 0.012, 1.16, 0.95, "steel_galv")


@mod("apt_balcony_laundry", H=3.0, cat="アパート")
def _(m, W, H, rng):
    """アパートのベランダ: 掃出し窓+洗濯物干し+バルコニー手すり+室外機"""
    _hw(m, W, H, -1.0, 1.0, 0.1, 2.15, "siding_ceramic_gray", found=False)
    interior(m, -1.0, 1.0, 0.1, 2.15)
    _sash_alu(m, -1.0, 1.0, 0.1, 2.15, 2)
    m.box(-W / 2, 0.0, -0.12, W / 2, 1.0, 0.0, "rc_concrete")
    for x in (-W / 2 + 0.03, W / 2 - 0.03):
        m.box(x - 0.025, 0.95, 0.0, x + 0.025, 1.0, 1.05, "alu_silver")
    m.box(-W / 2, 0.95, 1.0, W / 2, 1.0, 1.05, "alu_silver")
    for i in range(int(W / 0.1)):
        m.box(-W / 2 + i * 0.1, 0.96, 0.05, -W / 2 + i * 0.1 + 0.01, 0.99, 1.0, "alu_silver")
    m.cyl(-0.9, 0.5, 2.1, 0.012, 1.8, "x", "steel_galv", 6)
    for sx in (-0.9, 0.9):
        m.cyl(sx, 0.5, 1.9, 0.012, 0.2, "z", "steel_galv", 6)
    m.box(0.9, 0.55, 0.0, 1.4, 0.85, 0.65, "ac_white")


@mod("apt_stair_side", W=1.3, H=6.2, cat="アパート")
def _(m, W, H, rng):
    """アパートの屋外鉄骨階段(2層分): 蹴込みなしの踏み板(縞鋼板)+手すり+踊り場"""
    n, rise = 18, 6.0 / 18
    for i in range(n):
        z = (i + 1) * rise
        yy0 = 0.35 + (i if i < 9 else 17 - i) * 0.26
        m.box(-0.5, yy0, z - 0.04, 0.5, yy0 + 0.26, z, "grating")
    for sx in (-0.52, 0.52):
        pipe(m, (sx, 0.35, 0.0), (sx, 0.35 + 9 * 0.26, 3.0), 0.04, "steel_gray", 6)
        pipe(m, (sx, 0.35 + 9 * 0.26, 3.0), (sx, 0.35, 6.0), 0.04, "steel_gray", 6)
    m.box(-0.55, 0.35 + 9 * 0.26, 2.93, 0.55, 0.35 + 9 * 0.26 + 1.0, 3.0, "grating")           # 中間踊り場
    for sx in (-0.55, 0.55):
        pipe(m, (sx, 0.35, 1.0), (sx, 0.35 + 9 * 0.26, 4.0), 0.018, "steel_galv", 6)
        pipe(m, (sx, 0.35 + 9 * 0.26, 4.0), (sx, 0.35, 7.0), 0.018, "steel_galv", 6)
    for sx in (-0.5, 0.5):
        post(m, sx, 0.4, 0.0, 3.0, 0.08, "steel_gray")
        post(m, sx, 0.4 + 9 * 0.26 + 0.9, 0.0, 3.0, 0.08, "steel_gray")


# -------------------------------------------------- 外構: 門・塀・生垣・物置
@mod("gate_mon_yakui", W=4.0, H=3.4, cat="外構")
def _(m, W, H, rng):
    """薬医門風の門: 太い柱2本+腕木+切妻の瓦屋根(本瓦)+両脇の土塀と扉"""
    for x in (-1.3, 1.3):
        m.box(x - 0.17, -0.17, 0, x + 0.17, 0.17, 2.7, "wood_dark")
        m.box(x - 0.25, -0.25, 0, x + 0.25, 0.25, 0.25, "garden_stone")
    for x in (-1.9, 1.9):
        m.box(x - 0.1, -0.1, 0, x + 0.1, 0.1, 2.2, "wood_dark")
    m.box(-2.0, -0.2, 2.7, 2.0, 0.2, 2.9, "wood_dark")                                         # 冠木
    for xx in (-1.3, 1.3):
        m.box(xx - 0.1, -0.35, 2.5, xx + 0.1, 0.35, 2.7, "wood_dark")                          # 腕木
    prism_any(m, [(-0.7, 2.85), (0.0, 3.35), (0.7, 2.85)], "x", -2.4, 2.4, "roof_kawara_hon")
    m.box(-2.4, -0.02, 3.33, 2.4, 0.02, 3.4, "roof_ridge")
    for sx in (-1, 1):
        m.box(sx * 2.4 - 0.1, -0.1, 3.3, sx * 2.4 + 0.1, 0.1, 3.5, "onigawara")
    for sx in (-1, 1):                                                                          # 両開きの板扉
        m.box(min(sx * 0.05, sx * 1.15), -0.05, 0.25, max(sx * 0.05, sx * 1.15), 0.05, 2.4, "wood_dark")
        for k in range(5):
            m.box(sx * (0.15 + k * 0.2) - 0.008, 0.05, 0.3, sx * (0.15 + k * 0.2) + 0.008, 0.06, 2.35, "steel_gray")


@mod("gate_post_modern", W=3.6, H=2.0, cat="外構")
def _(m, W, H, rng):
    """門柱(タイル貼り)+表札+インターホン+ポスト+アルミ門扉"""
    m.box(-1.8, -0.2, 0, -1.2, 0.2, 1.7, "tile_main")
    m.box(-1.8, -0.2, 1.7, -1.2, 0.2, 1.78, "alu_silver")
    m.box(-1.6, 0.2, 1.2, -1.4, 0.22, 1.4, "sign_white")
    m.box(-1.55, 0.2, 1.45, -1.45, 0.23, 1.58, "alu_black")
    m.box(-1.65, 0.2, 0.85, -1.35, 0.23, 1.0, "alu_silver")
    m.box(1.2, -0.12, 0, 1.4, 0.12, 1.5, "alu_black")
    for i in range(14):
        m.box(-1.0 + i * 0.16, -0.015, 0.1, -0.985 + i * 0.16, 0.015, 1.2, "alu_black")
    for z in (0.12, 1.2):
        m.box(-1.2, -0.02, z, 1.2, 0.02, z + 0.05, "alu_black")
    m.box(-1.2, -0.12, 0, 1.2, 0.12, 0.04, "rc_concrete")


@mod("fence_blockwall", W=3.6, H=1.8, cat="外構")
def _(m, W, H, rng):
    """ブロック塀(3段)+笠木+その上のメッシュフェンス(高さ制限の目安1.2m+フェンス)"""
    m.box(-1.8, -0.1, 0, 1.8, 0.1, 0.6, "cmu_block")
    m.box(-1.8, -0.11, 0.6, 1.8, 0.11, 0.66, "rc_concrete")
    for x in (-1.78, 0.0, 1.78):
        m.box(x - 0.07, -0.13, 0, x + 0.07, 0.13, 1.7, "rc_concrete")
    for i in range(24):
        m.box(-1.7 + i * 0.145, -0.012, 0.66, -1.69 + i * 0.145, 0.012, 1.6, "alu_black")
    for z in (0.7, 1.6):
        m.box(-1.8, -0.02, z, 1.8, 0.02, z + 0.04, "alu_black")


@mod("fence_blockwall_low", W=3.6, H=1.0, cat="外構")
def _(m, W, H, rng):
    """低いブロック塀(花ブロック入り)+植込み"""
    m.box(-1.8, -0.1, 0, 1.8, 0.1, 0.8, "cmu_block")
    for i in range(6):
        m.box(-1.6 + i * 0.55, -0.11, 0.4, -1.3 + i * 0.55, 0.11, 0.7, "interior")
        for k in range(3):
            m.box(-1.58 + i * 0.55 + k * 0.1, -0.1, 0.4, -1.55 + i * 0.55 + k * 0.1, 0.1, 0.7, "rc_concrete")
    m.box(-1.8, -0.11, 0.8, 1.8, 0.11, 0.86, "rc_concrete")


@mod("fence_itabei", W=3.6, H=1.9, cat="外構")
def _(m, W, H, rng):
    """板塀(縦板+胴縁+笠木+柱)"""
    for x in (-1.8, 0.0, 1.8):
        m.box(x - 0.06, -0.06, 0, x + 0.06, 0.06, 1.85, "wood_dark")
    for i in range(18):
        m.box(-1.75 + i * 0.195, -0.01, 0.1, -1.56 + i * 0.195, 0.02, 1.8 - (i % 2) * 0.02, "wood_dark")
    for z in (0.35, 1.0, 1.6):
        m.box(-1.8, -0.045, z, 1.8, -0.015, z + 0.06, "wood_dark")
    m.box(-1.8, -0.1, 1.8, 1.8, 0.1, 1.87, "wood_dark")


@mod("fence_ikegaki", W=3.6, H=1.9, cat="外構")
def _(m, W, H, rng):
    """生垣(刈り込み)+根元の縁石。上面は微妙に波打つ"""
    m.box(-1.8, -0.35, 0, 1.8, 0.35, 0.18, "stone_main")
    n = 12
    for i in range(n):
        x0 = -1.8 + i * 3.6 / n
        h = 1.55 + 0.1 * math.sin(i * 1.7) + 0.05 * (i % 3)
        m.box(x0, -0.28, 0.18, x0 + 3.6 / n + 0.01, 0.28, h, "plant")


@mod("fence_stone_wall", W=3.6, H=1.2, cat="外構")
def _(m, W, H, rng):
    """大谷石/野面積みの石垣(農家の屋敷構え)"""
    z = 0.0
    while z < 1.1:
        h = rng.choice([0.28, 0.35, 0.42])
        x = -1.8
        while x < 1.8:
            w = min(rng.choice([0.5, 0.7, 0.9]), 1.8 - x)
            m.box(x + 0.006, -0.18, z + 0.006, x + w - 0.006, 0.06 + rng.uniform(-0.03, 0.03), z + h - 0.006, "stone_main")
            x += w
        z += h
    m.box(-1.8, -0.2, 1.1, 1.8, 0.08, 1.18, "stone_main")


@mod("carport_alu", W=5.2, H=2.6, cat="外構")
def _(m, W, H, rng):
    """アルミカーポート(波板ポリカ屋根・柱4本・樋)。原点=間口中央の手前"""
    for sx in (-2.5, 2.5):
        for sy in (0.0, 5.2):
            m.box(sx - 0.05, sy - 0.05, 0, sx + 0.05, sy + 0.05, 2.4, "alu_main")
    m.box(-2.7, 0.0, 2.4, 2.7, 5.2, 2.46, "polycarbonate")
    for sx in (-2.7, 2.7):
        m.box(sx - 0.03, 0.0, 2.38, sx + 0.03, 5.2, 2.5, "alu_main")
    m.box(-2.7, -0.03, 2.38, 2.7, 0.03, 2.5, "alu_main")
    m.box(-2.7, 5.17, 2.38, 2.7, 5.23, 2.5, "alu_main")
    m.box(-2.4, 0.2, 0.0, 2.4, 5.0, 0.02, "ground_slab")


@mod("shed_inaba", W=2.6, H=2.2, cat="外構")
def _(m, W, H, rng):
    """イナバ風の物置(スチール製、引戸+屋根の勾配+ダイヤルロック)"""
    m.box(-1.3, -0.5, 0, 1.3, 0.5, 0.1, "rc_concrete")
    m.box(-1.25, -0.45, 0.1, 1.25, 0.45, 1.9, "steel_white")
    prism_any(m, [(-0.47, 1.9), (0.0, 2.15), (0.47, 1.9)], "x", -1.3, 1.3, "steel_white")
    for x0, x1 in ((-1.2, 0.0), (0.0, 1.2)):
        m.box(x0 + 0.03, 0.45, 0.25, x1 - 0.03, 0.47, 1.75, "steel_gray")
        for k in range(8):
            m.box(x0 + 0.05, 0.47, 0.4 + k * 0.16, x1 - 0.05, 0.48, 0.45 + k * 0.16, "steel_white")
    m.box(-0.05, 0.47, 0.9, 0.05, 0.5, 1.05, "alu_black")


@mod("bldg_kura", W=5.4, H=7.0, cat="日本家屋")
def _(m, W, H, rng):
    """土蔵(漆喰壁+なまこ腰壁+観音開きの二重扉+瓦屋根)。原点=平面中心、+y=正面"""
    w, d = 2.7, 2.2
    m.box(-w, -d, 0, w, d, 3.6, "plaster_white")
    m.box(-w - 0.05, -d - 0.05, 0, w + 0.05, d + 0.05, 1.1, "namako_tile")
    for k in range(int(w * 2 / 0.22)):
        m.box(-w - 0.05 + k * 0.22, d + 0.04, 0.0, -w - 0.05 + k * 0.22 + 0.016, d + 0.055, 1.1, "plaster_white")
    for k in range(5):
        m.box(-w - 0.05, d + 0.04, 0.22 + k * 0.22, w + 0.05, d + 0.055, 0.236 + k * 0.22, "plaster_white")
    m.box(-0.85, d, 1.1, 0.85, d + 0.18, 3.0, "plaster_white")                                   # 扉の枠(厚い)
    m.box(-0.7, d + 0.18, 1.2, 0.0, d + 0.24, 2.9, "wood_dark")
    m.box(0.0, d + 0.18, 1.2, 0.7, d + 0.24, 2.9, "wood_dark")
    m.box(-0.8, d + 0.04, 3.05, 0.8, d + 0.24, 3.3, "plaster_white")                              # 扉の庇
    for sx in (-1.7, 1.7):
        m.box(sx - 0.35, d, 2.0, sx + 0.35, d + 0.14, 2.8, "plaster_white")
        m.box(sx - 0.25, d + 0.14, 2.1, sx + 0.25, d + 0.17, 2.7, "steel_gray")
    prism_any(m, [(-d - 0.7, 3.6), (0.0, 5.6), (d + 0.7, 3.6)], "x", -w - 0.8, w + 0.8, "roof_kawara")
    m.box(-w - 0.8, -0.05, 5.55, w + 0.8, 0.05, 5.7, "roof_ridge")
    for sx in (-1, 1):
        m.box(sx * (w + 0.8) - 0.12, -0.12, 5.5, sx * (w + 0.8) + 0.12, 0.12, 5.85, "onigawara")


@mod("greenhouse_vinyl", W=6.0, H=3.2, cat="農業")
def _(m, W, H, rng):
    """ビニールハウス(パイプ骨組み+ポリ被覆)。原点=端部中央、奥行き12m"""
    n = 9
    for i in range(n):
        y = i * 12.0 / (n - 1)
        pts = [(3.0 * math.cos(math.pi * k / 12), 0.0 + 3.0 * math.sin(math.pi * k / 12) * 0.95) for k in range(13)]
        for k in range(12):
            a, b = pts[k], pts[k + 1]
            pipe(m, (a[0], y, a[1]), (b[0], y, b[1]), 0.02, "steel_galv", 5)
    prof = [(3.02 * math.cos(math.pi * k / 12), 3.02 * 0.95 * math.sin(math.pi * k / 12)) for k in range(13)]
    for k in range(12):
        a, b = prof[k], prof[k + 1]
        m.poly([(a[0], 0, a[1]), (b[0], 0, b[1]), (b[0], 12.0, b[1]), (a[0], 12.0, a[1])], "plastic_film")
    for y in (0, 12.0):
        m.poly([(x, y, z) for x, z in prof] if y == 12.0 else [(x, y, z) for x, z in prof[::-1]], "plastic_film")
    for k in range(3):
        pipe(m, (-2.9 + k * 2.9, 0, 0.9), (-2.9 + k * 2.9, 12, 0.9), 0.015, "steel_galv", 5)
    m.box(-0.8, -0.01, 0.0, 0.8, 0.0, 2.0, "steel_galv")


@mod("field_water_tank_house", W=1.4, H=2.8, cat="農業")
def _(m, W, H, rng):
    """軽トラ置場兼 農機具小屋(トタン)"""
    m.box(-2.0, -1.5, 0, 2.0, 1.5, 2.2, "corrugated_green")
    prism_any(m, [(-1.6, 2.2), (0.0, 2.9), (1.6, 2.2)], "x", -2.1, 2.1, "roof_tanshiki_red")
    m.box(-1.6, 1.5, 0.0, 1.6, 1.52, 2.0, "steel_gray")


# -------------------------------------------------- 屋根の付属物(棟・鬼瓦・樋・アンテナ)
@mod("ridge_cap_tile", W=0.5, H=0.35, cat="屋根部材")
def _(m, W, H, rng):
    """棟瓦(熨斗瓦を積んだ上に丸瓦): 0.5m当たり。x=棟方向"""
    for k, (hh, ww) in enumerate(((0.05, 0.36), (0.05, 0.32), (0.05, 0.28))):
        m.box(-0.25, -ww / 2, k * 0.05, 0.25, ww / 2, k * 0.05 + hh, "roof_ridge")
    m.cyl(-0.25, 0, 0.18, 0.1, 0.5, "x", "roof_ridge", 12)


@mod("onigawara", W=0.5, H=0.8, cat="屋根部材")
def _(m, W, H, rng):
    """鬼瓦(棟端の飾り): 台座+渦巻き型の簡易形"""
    m.box(-0.25, -0.1, 0, 0.25, 0.1, 0.12, "roof_ridge")
    m.box(-0.2, -0.08, 0.12, 0.2, 0.08, 0.5, "roof_ridge")
    prism_any(m, [(-0.2, 0.5), (0.0, 0.78), (0.2, 0.5)], "y", -0.07, 0.07, "roof_ridge")
    m.cyl(0, 0.08, 0.3, 0.09, 0.03, "y", "plaster_white", 12)


@mod("eave_gutter", W=3.6, H=0.5, cat="屋根部材")
def _(m, W, H, rng):
    """軒樋(半円樋)+吊り金具+竪樋への落とし口。原点=軒先、+y=外"""
    for k in range(10):
        a0, a1 = math.pi * k / 10, math.pi * (k + 1) / 10
        m.poly([(-W / 2, 0.06 * math.cos(a0), -0.06 * math.sin(a0)), (W / 2, 0.06 * math.cos(a0), -0.06 * math.sin(a0)),
                (W / 2, 0.06 * math.cos(a1), -0.06 * math.sin(a1)), (-W / 2, 0.06 * math.cos(a1), -0.06 * math.sin(a1))][::-1], "alu_silver")
    for x in (-W / 2 + 0.05, 0.0, W / 2 - 0.05):
        m.box(x - 0.01, -0.07, -0.07, x + 0.01, 0.07, -0.05, "steel_galv")


@mod("house_downpipe", W=0.1, H=3.0, cat="屋根部材")
def _(m, W, H, rng):
    """竪樋(塩ビ)+ブラケット。壁面y=0、上端が軒樋に接続、下端はエルボで外に曲がる"""
    m.cyl(0, 0.05, 0.1, 0.03, H - 0.1, "z", "plastic_gray", 8)
    for z in (0.5, 1.5, 2.5):
        m.box(-0.035, 0.0, z, 0.035, 0.09, z + 0.03, "steel_galv")
    m.cyl(0, 0.05, 0.0, 0.03, 0.1, "z", "plastic_gray", 8)
    m.box(-0.05, 0.0, 0.0, 0.05, 0.14, 0.04, "rc_concrete")


@mod("tv_antenna_yagi", W=1.2, H=3.0, cat="屋根部材")
def _(m, W, H, rng):
    """八木式アンテナ(UHF)+マスト+支線"""
    m.cyl(0, 0, 0, 0.022, 2.6, "z", "steel_galv", 6)
    for i in range(8):
        y = -0.5 + i * 0.16
        L = 0.5 - 0.03 * i if i > 0 else 0.6
        m.cyl(-L / 2, y, 2.3 - 0.0, 0.006, L, "x", "alu_silver", 4)
    m.cyl(0, -0.5, 2.3, 0.008, 1.2, "y", "alu_silver", 5)
    m.cyl(0, 0, 0, 0.1, 0.05, "z", "steel_gray", 8)


@mod("satellite_dish_wall", W=0.8, H=0.8, cat="屋根部材")
def _(m, W, H, rng):
    """BS/CSアンテナ(パラボラ+アーム)。壁面y=0に取付"""
    m.cyl(0, 0.0, 0.0, 0.03, 0.4, "z", "steel_galv", 6)
    for k in range(10):
        a0, a1 = 2 * math.pi * k / 10, 2 * math.pi * (k + 1) / 10
        for r0, r1, z0, z1 in ((0.0, 0.2, 0.0, 0.03), (0.2, 0.38, 0.03, 0.12)):
            m.poly([(r0 * math.cos(a0), 0.35 + r0 * math.sin(a0) * 0.2 + z0, 0.5 + r0 * math.sin(a0)), (r1 * math.cos(a0), 0.35 + z1, 0.5 + r1 * math.sin(a0)),
                    (r1 * math.cos(a1), 0.35 + z1, 0.5 + r1 * math.sin(a1)), (r0 * math.cos(a1), 0.35 + r0 * math.sin(a0) * 0.2 + z0, 0.5 + r0 * math.sin(a1))], "ac_white")
    m.box(-0.03, 0.0, 0.45, 0.03, 0.4, 0.5, "steel_galv")


@mod("roof_solar_house", W=3.6, H=0.2, cat="屋根部材")
def _(m, W, H, rng):
    """住宅用太陽光パネル1枚分(架台+パネル+枠)。x=棟方向、屋根面に沿う向きで置く前提のフラット部材"""
    m.box(-W / 2, -0.8, 0, W / 2, 0.8, 0.05, "solar")
    for sx in (-W / 2, W / 2):
        m.box(sx - 0.015, -0.8, 0, sx + 0.015, 0.8, 0.07, "alu_silver")


@mod("chimney_bath", W=0.5, H=1.6, cat="屋根部材")
def _(m, W, H, rng):
    """給湯器/風呂釜の排気筒+雨除けキャップ(住宅の外壁沿いに立つ)"""
    m.cyl(0, 0.1, 0, 0.06, 1.3, "z", "alu_silver", 10)
    m.cyl(0, 0.1, 1.3, 0.1, 0.03, "z", "alu_silver", 10)
    m.box(-0.05, 0.0, 0.6, 0.05, 0.1, 0.65, "steel_galv")


# -------------------------------------------------- 農村の小さな土木・設備
@mod("rural_utility_pole_wood", W=0.4, H=9.0, cat="農村")
def _(m, W, H, rng):
    """木製電柱(古い)+腕金+碍子+変圧器(柱上トランス)"""
    m.cyl(0, 0, 0, 0.12, 9.0, "z", "wood_dark", 10)
    m.box(-0.7, -0.05, 8.3, 0.7, 0.05, 8.38, "steel_gray")
    for x in (-0.6, -0.2, 0.2, 0.6):
        m.cyl(x, 0, 8.38, 0.04, 0.12, "z", "ceramic", 8)
    m.cyl(0.35, 0.3, 6.6, 0.22, 0.75, "z", "steel_gray", 12)
    m.box(-0.08, -0.12, 5.4, 0.08, 0.12, 5.9, "steel_gray")


@mod("rural_bus_stop_sign", W=0.5, H=2.6, cat="農村")
def _(m, W, H, rng):
    """田舎の路線バス停(丸い標識+時刻表の箱+ベンチ)"""
    m.cyl(0, 0, 0, 0.03, 2.6, "z", "pole_dark", 8)
    m.cyl(0, 0.04, 2.1, 0.22, 0.03, "y", "sign_white", 16)
    m.cyl(0, 0.07, 2.1, 0.17, 0.005, "y", "sign_red", 16)
    m.box(-0.2, 0.04, 1.2, 0.2, 0.08, 1.8, "alu_silver")
    m.box(-0.18, 0.08, 1.25, 0.18, 0.082, 1.75, "sign_white")


@mod("rural_farm_road_mirror", W=0.6, H=3.4, cat="農村")
def _(m, W, H, rng):
    """農道の交差点のカーブミラー(支柱+円形ミラー)"""
    m.cyl(0, 0, 0, 0.04, 3.4, "z", "pole_white", 8)
    m.cyl(0, 0.05, 2.8, 0.3, 0.03, "y", "alu_main", 20)
    m.cyl(0, 0.08, 2.8, 0.26, 0.005, "y", "glass_clear", 20)


@mod("rural_rice_hasa", W=4.0, H=2.6, cat="農村")
def _(m, W, H, rng):
    """稲架(はさ掛け): 木の支柱+横竿+掛けられた稲束"""
    for x in (-1.9, 0.0, 1.9):
        m.cyl(x, 0, 0, 0.04, 2.5, "z", "wood_dark", 6)
    for z in (1.0, 1.4, 1.8, 2.2):
        m.cyl(-1.9, 0, z, 0.02, 3.8, "x", "wood_light", 5)
    for z in (1.0, 1.4, 1.8):
        for i in range(25):
            m.box(-1.85 + i * 0.15, -0.06, z - 0.5, -1.77 + i * 0.15, 0.06, z, "wood_light")
