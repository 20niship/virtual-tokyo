"""バルコニー・外階段・廊下・屋上設備・意匠。"""
import math

from .registry import T, frame, glass, hole_wall, interior, mod, reg


def _slab(m, W, depth=1.5, th=0.2, mat="rc_concrete"):
    m.box(-W / 2, -0.1, -th, W / 2, depth, 0, mat)
    m.box(-W / 2, depth - 0.03, -th - 0.06, W / 2, depth, 0, "paint_main")  # 先端見付
    m.box(-W / 2, 0.2, -th - 0.02, W / 2, depth - 0.2, -th, "paint_dark") if False else None


def _slider(m, W, H, rng, x0=-0.9, x1=0.9):
    from .lib_win import _win
    _win(m, W, H, rng, "floor", sill=False)


def _ac_hung(m, x, z, y0):
    m.box(x - 0.4, y0, z, x + 0.4, y0 + 0.3, z + 0.55, "ac_white")
    m.cyl(x, y0 + 0.3, z + 0.28, 0.2, 0.01, "y", "rubber", 16)
    m.box(x - 0.35, y0 + 0.31, z + 0.05, x + 0.35, y0 + 0.315, z + 0.07, "plastic_gray")


def _balcony(m, W, H, rng, rail):
    _slider(m, W, H, rng)
    m.box(-W / 2, -T, 0, W / 2, 0, 0.1, "paint_main") if False else None
    m.box(-W / 2, 0.0, -0.2, W / 2, 1.5, 0.0, "rc_concrete")
    m.box(-W / 2, 1.47, -0.26, W / 2, 1.5, 0.0, "paint_white")
    if rail == "rc":
        m.box(-W / 2, 1.3, 0.0, W / 2, 1.5, 1.05, "paint_main")
        m.box(-W / 2 - 0.02, 1.28, 1.05, W / 2 + 0.02, 1.52, 1.12, "alu_silver")
        for x in (-W / 2, W / 2 - 0.1):
            m.box(x, 0.0, 0.0, x + 0.1, 1.5, 1.05, "paint_main")
    elif rail == "glass":
        glass(m, -W / 2 + 0.05, W / 2 - 0.05, 0.1, 1.05, 1.45, "glass_clear")
        m.box(-W / 2, 1.43, 1.05, W / 2, 1.5, 1.1, "alu_silver")
        for x in (-W / 2, 0, W / 2 - 0.05):
            m.box(x, 1.43, 0.0, x + 0.05, 1.5, 1.05, "alu_silver")
        for x in (-W / 2, W / 2 - 0.05):
            m.box(x, 0.0, 0.0, x + 0.05, 1.5, 0.05, "alu_silver")
    elif rail == "alu":
        n = int(W / 0.11)
        for i in range(n + 1):
            x = -W / 2 + 0.02 + i * (W - 0.04) / n
            m.box(x - 0.012, 1.44, 0.05, x + 0.012, 1.48, 1.05, "alu_main")
        for z in (0.05, 1.03):
            m.box(-W / 2, 1.42, z, W / 2, 1.5, z + 0.05, "alu_main")
        for x in (-W / 2, W / 2 - 0.05):
            m.box(x, 0.0, 0.0, x + 0.05, 1.5, 1.05, "alu_main")
    for x in (-W / 2, W / 2):  # 隔て板(側壁)
        m.box(x - 0.01, 0.0, 0, x + 0.01, 1.5, 1.05, "alc") if False else None
    _ac_hung(m, 1.1, 0.0, 1.0) if rng.random() < 0.5 else None
    m.cyl(-1.2, 1.0, 1.6, 0.02, 0.0, "x", "steel_galv", 6) if False else None
    m.box(-1.4, 0.4, 1.25, 0.4, 0.43, 1.28, "steel_galv") if rng.random() < 0.4 else None  # 物干し竿


reg("balcony_rc", lambda m, W, H, r: _balcony(m, W, H, r, "rc"), cat="balcony")
reg("balcony_glass", lambda m, W, H, r: _balcony(m, W, H, r, "glass"), cat="balcony")
reg("balcony_alu", lambda m, W, H, r: _balcony(m, W, H, r, "alu"), cat="balcony")


@mod("balcony_recess", cat="balcony")
def _(m, W, H, rng):  # 内廊下型ベランダ(壁後退) + 戸境パネル + 手すり
    m.box(-W / 2, -1.6, 0, W / 2, -1.58, H, "paint_main")
    m.box(-W / 2, -1.6, -0.2, W / 2, 0.0, 0.0, "rc_concrete")
    m.box(-W / 2, -1.6, 0.0, -W / 2 + 0.15, 0.0, H, "paint_main")
    m.box(W / 2 - 0.15, -1.6, 0.0, W / 2, 0.0, H, "paint_main")
    m.box(-W / 2, 0.0, -0.2, W / 2, 0.0, 0.0, "rc_concrete")
    m.box(-W / 2 + 0.15, -0.12, 0.0, W / 2 - 0.15, 0.0, 1.05, "paint_main")
    m.box(-W / 2 + 0.1, -0.15, 1.05, W / 2 - 0.1, 0.03, 1.1, "alu_silver")
    m.box(-1.0, -1.6, 0.9, 1.0, -1.57, 2.4, "interior")
    frame(m, -1.0, 1.0, 0.9, 2.4, "alu_main", 0.05, 0.08, -1.62)
    glass(m, -0.95, 0.95, 0.95, 2.35, -1.58)
    _ac_hung(m, -1.1, 0.0, -1.5)


@mod("stair_external", H=3.5, W=3.6, cat="balcony")
def _(m, W, H, rng):  # 屋外非常階段(1フロア分: 踊り場+折返し段+手すり)
    d, w = 2.2, 1.3
    x0 = -w / 2
    m.box(x0, 0.2, H - 0.06, x0 + w, 0.2 + 1.2, H, "steel_gray")  # 踊り場
    n = 10
    for i in range(n):
        y = 0.2 + 1.2 + i * (d - 1.2) / n if False else 0.2 + i * 0.12
        m.box(x0 + 0.05, 0.2 + 1.2 + 0.0 + 0.0, 0, x0 + 0.06, 0.2 + 1.2, 0.001, "steel_gray") if False else None
    for i in range(n):  # 段板(傾斜昇降)
        y = 1.4 + i * 0.2
        m.box(x0, y, H / 2 - H / 2 + (i + 1) * H / (n + 1) - 0.04 - H, x0 + w, y + 0.22, (i + 1) * H / (n + 1) - H, "steel_gray") if False else None
    for i in range(n):
        y0 = 1.4 - i * 0.12
        z = H - (i + 1) * H / n
        m.box(x0, y0 - 0.26, z - 0.03, x0 + w, y0, z, "steel_gray")
    for x in (x0, x0 + w - 0.05):  # ササラ桁(傾斜)
        m.prism([(1.4, H), (1.4 - 0.12 * n - 0.1, 0), (1.4 - 0.12 * n - 0.1, 0.2), (1.4, H + 0.15)], "x", x, x + 0.05, "steel_gray")
    for x in (x0, x0 + w - 0.04):
        m.box(x, 0.2, H, x + 0.04, 1.4, H + 1.05, "steel_galv") if False else None
        m.box(x, 0.2, H, x + 0.04, 0.24, H + 1.05, "steel_galv")
        m.box(x, 1.36, H, x + 0.04, 1.4, H + 1.05, "steel_galv")
        m.box(x, 0.2, H + 1.0, x + 0.04, 1.4, H + 1.05, "steel_galv")
    m.box(x0 + w / 2 - 0.4, -0.01, 0.0, x0 + w / 2 + 0.4, 0.0, 2.0, "steel_green")  # 避難扉


@mod("corridor_open", cat="balcony")
def _(m, W, H, rng):  # 開放廊下(共用廊下) + 玄関扉 + 小窓 + 手すり壁
    m.box(-W / 2, 0.0, -0.2, W / 2, 1.8, 0.0, "rc_concrete")
    m.box(-W / 2, -T, 0, W / 2, 0, H, "paint_main")
    m.box(-W / 2, 1.6, 0, W / 2, 1.8, 1.1, "paint_main")
    m.box(-W / 2 - 0.02, 1.58, 1.1, W / 2 + 0.02, 1.82, 1.16, "alu_silver")
    m.box(-0.5, 0.0, 0.0, 0.5, 0.05, 2.1, "steel_gray")
    m.box(-0.55, 0.0, 2.1, 0.55, 0.06, 2.18, "steel_gray")
    m.box(0.55, 0.0, 1.2, 1.3, 0.04, 1.9, "interior")
    for i in range(6):
        m.box(0.58 + i * 0.12, 0.04, 1.2, 0.6 + i * 0.12, 0.08, 1.9, "steel_white")
    m.box(0.3, 0.05, 0.95, 0.4, 0.1, 1.05, "steel_galv")
    m.box(-1.0, 0.0, 2.3, -0.7, 0.2, 2.45, "led_white")
    m.box(1.3, 0.0, 0.0, 1.7, 0.4, 0.5, "steel_gray")  # メーターボックス


# ---- 屋上設備 (原点=中心底) ----
def _fan_unit(m, w, d, h, nf, mat="ac_white"):
    m.box(-w / 2, -d / 2, 0, w / 2, d / 2, h, mat)
    m.box(-w / 2 - 0.02, -d / 2 - 0.02, 0, w / 2 + 0.02, d / 2 + 0.02, 0.06, "steel_gray")
    fw = w / nf
    for i in range(nf):
        cx = -w / 2 + (i + 0.5) * fw
        m.cyl(cx, 0, h, fw * 0.4, 0.02, "z", "plastic_gray", 20)
        m.tube(cx, 0, h, fw * 0.42, fw * 0.38, 0.03, "z", "steel_galv", 20)
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            m.prism([(cx, 0), (cx + fw * 0.38 * math.cos(a), fw * 0.38 * math.sin(a)),
                     (cx + fw * 0.38 * math.cos(a + 0.5), fw * 0.38 * math.sin(a + 0.5))], "z", h + 0.02, h + 0.035, "rubber")
    for i in range(int(h / 0.04)):
        m.box(-w / 2 - 0.005, -d / 2, 0.1 + i * 0.04, -w / 2, d / 2, 0.12 + i * 0.04, "steel_galv")


reg("ac_unit_small", lambda m, W, H, r: _fan_unit(m, 0.8, 0.35, 0.6, 1), W=0.8, H=0.6, cat="roof")
reg("ac_unit_vrf", lambda m, W, H, r: _fan_unit(m, 1.8, 0.8, 1.7, 2), W=1.8, H=1.7, cat="roof")
reg("ac_unit_vrf_big", lambda m, W, H, r: _fan_unit(m, 3.6, 0.9, 1.8, 4), W=3.6, H=1.8, cat="roof")


@mod("water_tank", W=3.0, H=3.6, cat="roof")
def _(m, W, H, rng):
    for x in (-1.2, 1.2):
        for y in (-1.2, 1.2):
            m.box(x - 0.08, y - 0.08, 0, x + 0.08, y + 0.08, 1.2, "steel_gray")
    for z in (0.5, 1.15):
        m.box(-1.28, -1.28, z, 1.28, -1.2, z + 0.05, "steel_gray"); m.box(-1.28, 1.2, z, 1.28, 1.28, z + 0.05, "steel_gray")
    m.cyl(0, 0, 1.2, 1.4, 2.2, "z", "steel_galv", 32)
    m.cyl(0, 0, 3.4, 1.42, 0.06, "z", "steel_gray", 32)
    m.cyl(0.6, 0.4, 3.46, 0.3, 0.1, "z", "steel_gray", 16)
    m.cyl(1.4, 0, 1.3, 0.05, 1.0, "z", "steel_gray", 8)  # 配管
    for z in (1.6, 2.4, 3.2):
        m.tube(0, 0, z, 1.42, 1.4, 0.05, "z", "steel_gray", 32)


@mod("cooling_tower", W=2.6, H=3.0, cat="roof")
def _(m, W, H, rng):
    m.box(-1.3, -1.3, 0.3, 1.3, 1.3, 2.4, "steel_white")
    m.box(-1.4, -1.4, 0, 1.4, 1.4, 0.3, "steel_gray")
    for i in range(8):
        z = 0.5 + i * 0.22
        m.box(-1.32, -1.2, z, -1.3, 1.2, z + 0.1, "steel_galv"); m.box(1.3, -1.2, z, 1.32, 1.2, z + 0.1, "steel_galv")
    m.tube(0, 0, 2.4, 0.95, 0.8, 0.5, "z", "steel_gray", 28)
    m.cyl(0, 0, 2.55, 0.2, 0.15, "z", "steel_gray", 12)
    for k in range(6):
        a = k * math.pi / 3
        m.prism([(0, 0), (0.8 * math.cos(a), 0.8 * math.sin(a)), (0.8 * math.cos(a + 0.4), 0.8 * math.sin(a + 0.4))], "z", 2.6, 2.62, "rubber")


@mod("antenna_mast", W=1.2, H=18.0, cat="roof")
def _(m, W, H, rng):  # 格子鉄塔(3脚 + 斜材) + 航空障害灯
    legs = [(0.5 * math.cos(a), 0.5 * math.sin(a)) for a in (math.pi / 2, math.pi * 7 / 6, math.pi * 11 / 6)]
    n = 12
    hs = H - 1.2
    for i in range(n):
        z0, z1 = i * hs / n, (i + 1) * hs / n
        k0, k1 = 1.0 - 0.6 * i / n, 1.0 - 0.6 * (i + 1) / n
        for j in range(3):
            ax, ay = legs[j][0] * k0, legs[j][1] * k0
            bx, by = legs[(j + 1) % 3][0] * k1, legs[(j + 1) % 3][1] * k1
            m.box(ax - 0.025, ay - 0.025, z0, ax + 0.025, ay + 0.025, z1, "steel_white")
            # 斜材(細い平板で近似)
            m.prism([(ax, ay), (bx, by), (bx + 0.02, by + 0.02), (ax + 0.02, ay + 0.02)], "z", z0, z0 + 0.02, "steel_white")
    m.cyl(0, 0, hs, 0.04, 1.2, "z", "steel_white", 8)
    m.cyl(0, 0, H - 0.1, 0.07, 0.1, "z", "sign_green" if False else "led_white", 8)


@mod("lightning_rod", W=0.3, H=3.0, cat="roof")
def _(m, W, H, rng):
    m.cyl(0, 0, 0, 0.05, 0.3, "z", "steel_gray", 8); m.cyl(0, 0, 0.3, 0.015, H - 0.3, "z", "steel_galv", 6)


@mod("solar_row", W=4.0, H=1.0, cat="roof")
def _(m, W, H, rng):  # 傾斜太陽光パネル(架台 + セル)
    for x in (-1.8, 0, 1.8):
        m.prism([(-0.3, 0), (0.3, 0), (0.3, 0.25), (-0.3, 0.9)], "x", x - 0.02, x + 0.02, "steel_galv")
    for i in range(4):
        xa, xb = -2.0 + i * 1.0 + 0.02, -2.0 + (i + 1) * 1.0 - 0.02
        m.prism([(-0.32, 0.3), (0.32, 0.3 + 0.0), (0.32, 0.37), (-0.32, 0.97)], "x", xa, xb, "alu_silver") if False else None
        m.prism([(-0.32, 0.05), (0.32, 0.05 + 0.0), (0.32, 0.3), (-0.32, 0.9)], "x", xa, xb, "alu_silver") if False else None
        m.slat_x(xa, xb, 0.0, 0.55, 1.65, 0.035, math.radians(32), "alu_silver")
        m.slat_x(xa + 0.02, xb - 0.02, -0.001, 0.55, 1.6, 0.04, math.radians(32), "solar") if False else None


@mod("rooftop_stairhouse", W=4.0, H=3.0, cat="roof")
def _(m, W, H, rng):  # 塔屋(ペントハウス) + ドア + 外壁 + 庇
    m.box(-2.0, -1.5, 0, 2.0, 1.5, 2.8, "paint_main")
    m.box(-2.05, -1.55, 2.8, 2.05, 1.55, 3.0, "alu_silver")
    m.box(-0.5, 1.5, 0.0, 0.5, 1.56, 2.1, "steel_gray")
    m.box(-0.6, 1.5, 2.1, 0.6, 1.8, 2.15, "alu_main")
    m.box(-0.55, 1.5, 0.0, 0.55, 2.0, 0.05, "rc_concrete")
    m.box(-1.8, 1.5, 0.0, -1.2, 1.56, 0.0 + 0.4, "steel_galv")
    m.cyl(1.4, -1.5, 1.5, 0.14, 0.4, "y", "steel_galv", 12)  # ガラリ丸
    m.box(0.9, -1.55, 0.8, 1.9, -1.5, 1.9, "steel_gray")


@mod("roof_vent_pipes", W=1.2, H=1.5, cat="roof")
def _(m, W, H, rng):  # ベントキャップ群
    for i, (x, y, h, r) in enumerate([(-0.3, 0, 1.2, 0.07), (0.1, 0.2, 0.8, 0.05), (0.4, -0.1, 1.5, 0.09)]):
        m.cyl(x, y, 0, r, h, "z", "steel_galv", 12)
        m.cyl(x, y, h, r * 1.8, 0.02, "z", "steel_galv", 12)


@mod("roof_chimney", W=1.0, H=8.0, cat="roof")
def _(m, W, H, rng):
    m.cyl(0, 0, 0, 0.4, 0.4, "z", "steel_gray", 24); m.cyl(0, 0, 0.4, 0.28, H - 0.4, "z", "steel_white", 24)
    for z in range(1, int(H), 2):
        m.tube(0, 0, z, 0.3, 0.28, 0.08, "z", "steel_gray", 24)


@mod("roof_duct_run", W=4.0, H=0.8, cat="roof")
def _(m, W, H, rng):  # 屋上ダクト+配管ラック
    for x in (-1.8, 0, 1.8):
        m.box(x - 0.04, -0.3, 0, x + 0.04, -0.2, 0.5, "steel_gray"); m.box(x - 0.04, 0.3, 0, x + 0.04, 0.4, 0.5, "steel_gray")
        m.box(x - 0.04, -0.3, 0.5, x + 0.04, 0.4, 0.55, "steel_gray")
    m.box(-2, -0.15, 0.55, 2, 0.35, 1.0, "steel_galv")
    m.cyl(-2, 0.0, 0.2 + 0.4, 0.08, 4.0, "x", "steel_white", 12)


@mod("roof_hatch_ladder", W=1.0, H=1.2, cat="roof")
def _(m, W, H, rng):
    m.box(-0.5, -0.5, 0, 0.5, 0.5, 0.35, "paint_main"); m.box(-0.52, -0.52, 0.35, 0.52, 0.52, 0.4, "alu_silver")
    for x in (-0.55, 0.55):
        m.box(x - 0.02, 0.7, 0, x + 0.02, 0.74, 1.2, "steel_galv")


# ---- 意匠 ----
@mod("pilaster", W=0.6, H=3.5, cat="deco")
def _(m, W, H, rng):
    m.box(-0.3, -0.1, 0, 0.3, 0.25, H, "paint_main")
    m.box(-0.36, -0.1, 0, 0.36, 0.32, 0.25, "paint_main"); m.box(-0.36, -0.1, H - 0.25, 0.36, 0.32, H, "paint_main")


@mod("stripe_light", H=0.12, cat="deco")
def _(m, W, H, rng):  # ラインライト
    m.box(-W / 2, 0.0, 0.0, W / 2, 0.08, H, "alu_black"); m.box(-W / 2 + 0.02, 0.08, 0.02, W / 2 - 0.02, 0.1, H - 0.02, "led_white")


@mod("sign_band_blank", H=1.0, cat="deco")
def _(m, W, H, rng):  # 看板帯(袖/壁面看板 プレースホルダ)
    m.box(-W / 2, 0.0, 0, W / 2, 0.25, H, "paint_white"); m.box(-W / 2 + 0.1, 0.25, 0.1, W / 2 - 0.1, 0.27, H - 0.1, "led_white")


@mod("led_vision", W=3.6, H=2.0, cat="deco")
def _(m, W, H, rng):
    m.box(-W / 2, 0.0, 0, W / 2, 0.3, H, "alu_black")
    n, k = 36, 20
    for i in range(0, n, 2):
        for j in range(0, k, 2):
            c = rng.choice(["led_white", "sign_green", "led_white"]) if rng.random() < 0.3 else "alu_black"
            m.box(-W / 2 + 0.05 + i * (W - 0.1) / n, 0.3, 0.05 + j * (H - 0.1) / k, -W / 2 + 0.05 + (i + 2) * (W - 0.1) / n, 0.32, 0.05 + (j + 2) * (H - 0.1) / k, c)
