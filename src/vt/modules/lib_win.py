"""窓(形状別)・窓まわり意匠・ルーバー/フィン。"""
import math

from .registry import T, frame, glass, hole_wall, interior, mod, reg


def _sash(m, x0, x1, z0, z1, n, fm, y0=-0.17):
    """引違い: n枚のガラス戸を前後2レールに交互配置"""
    w = (x1 - x0) / n
    for i in range(n):
        xa, xb = x0 + i * w - (0.03 if i else 0), x0 + (i + 1) * w + (0.03 if i < n - 1 else 0)
        y = y0 + (0.05 if i % 2 else 0)
        frame(m, xa, xb, z0, z1, fm, 0.045, 0.05, y)
        glass(m, xa + 0.045, xb - 0.045, z0 + 0.045, z1 - 0.045, y + 0.02)
        if i < n - 1:  # クレセント錠
            m.box(xb - 0.07, y - 0.02, (z0 + z1) / 2 - 0.03, xb - 0.03, y, (z0 + z1) / 2 + 0.03, "steel_galv")


def _win(m, W, H, rng, kind, fm="alu_main", wall="paint_main", sill=True, hood=False, bars=False, shutterbox=False):
    G = {  # kind: (x0,x1,z0,z1)
        "sliding2": (-0.9, 0.9, 0.9, 2.4), "sliding4": (-1.5, 1.5, 0.9, 2.3), "fix": (-1.5, 1.5, 0.2, 3.0),
        "casement": (-0.8, 0.8, 0.9, 2.5), "awning": (-0.6, 0.6, 1.9, 2.5), "slit": (-0.25, 0.25, 0.5, 2.9),
        "high": (-1.2, 1.2, 2.3, 3.1), "floor": (-0.9, 0.9, 0.0, 2.3), "jalousie": (-0.45, 0.45, 1.0, 2.4),
        "bay": (-0.9, 0.9, 0.6, 2.5), "ribbon": (-W / 2 + 0.0, W / 2, 0.9, 2.6),
    }
    if kind == "slit":
        return _slit(m, W, H, wall, fm)
    x0, x1, z0, z1 = G[kind]
    if kind == "ribbon":
        m.box(-W / 2, -T, 0, W / 2, 0, z0, wall)
        m.box(-W / 2, -T, z1, W / 2, 0, H, wall)
    else:
        hole_wall(m, W, H, x0, x1, z0, z1, wall)
    interior(m, x0, x1, z0, z1)
    if kind in ("sliding2", "sliding4", "high"):
        _sash(m, x0, x1, z0, z1, 2 if kind != "sliding4" else 4, fm)
    elif kind == "ribbon":
        frame(m, x0, x1, z0, z1, fm, 0.06, 0.1)
        glass(m, x0 + 0.06, x1 - 0.06, z0 + 0.06, z1 - 0.06)
        for i in range(1, 3):
            x = x0 + i * (x1 - x0) / 3
            m.box(x - 0.03, -0.17, z0, x + 0.03, -0.05, z1, fm)
    elif kind == "fix":
        frame(m, x0, x1, z0, z1, fm, 0.05, 0.1)
        glass(m, x0 + 0.05, x1 - 0.05, z0 + 0.05, z1 - 0.05)
    elif kind == "casement":
        for a, b in ((x0, 0), (0, x1)):
            frame(m, a, b, z0, z1, fm, 0.05, 0.07, -0.17)
            glass(m, a + 0.05, b - 0.05, z0 + 0.05, z1 - 0.05)
            m.box((a + b) / 2 - 0.015 + (0.3 if a == x0 else -0.3), -0.19, (z0 + z1) / 2 - 0.06, (a + b) / 2 + 0.015 + (0.3 if a == x0 else -0.3), -0.1, (z0 + z1) / 2 + 0.06, "steel_galv")
        frame(m, x0, x1, z0, z1, fm, 0.07, 0.1, -0.2)
    elif kind == "awning":
        for k in range(2):
            xa, xb = x0 + k * (x1 - x0) / 2, x0 + (k + 1) * (x1 - x0) / 2
            frame(m, xa, xb, z0, z1, fm, 0.045, 0.07)
            glass(m, xa + 0.045, xb - 0.045, z0 + 0.045, z1 - 0.045)
    elif kind == "floor":
        _sash(m, x0, x1, z0, z1, 2, fm)
        m.box(x0 - 0.1, -0.2, -0.02, x1 + 0.1, 0.35, 0.06, "rc_concrete")  # 軒先の沓摺
        for x in (x0 - 0.08, x1 + 0.08):
            m.box(x - 0.015, 0.3, 0.06, x + 0.015, 0.34, 1.1, "steel_galv")
        m.box(x0 - 0.1, 0.3, 1.08, x1 + 0.1, 0.34, 1.12, "steel_galv")
        m.box(x0 - 0.1, 0.3, 0.55, x1 + 0.1, 0.34, 0.58, "steel_galv")
    elif kind == "jalousie":
        frame(m, x0, x1, z0, z1, fm, 0.05, 0.08)
        z = z0 + 0.06
        while z < z1 - 0.08:
            m.slat_x(x0 + 0.05, x1 - 0.05, -0.12, z, 0.14, 0.01, math.radians(-30), "glass_clear")
            z += 0.1
    elif kind == "bay":
        frame(m, x0, x1, z0, z1, fm, 0.06, 0.1)
        # 出窓: 前面ガラス+側面ガラス
        d = 0.5
        m.box(x0 - 0.08, -0.12, z0 - 0.12, x1 + 0.08, d, z0, wall)
        m.box(x0 - 0.08, -0.12, z1, x1 + 0.08, d, z1 + 0.1, wall)
        for xa, xb in ((x0 - 0.04, x0), (x1, x1 + 0.04)):
            m.box(xa, -0.12, z0, xb, d, z1, fm)
        glass(m, x0, x1, z0, z1, d - 0.05)
        m.box(x0, d - 0.08, z0, x1, d - 0.06, z0 + 0.05, fm)
        m.box(x0, d - 0.08, z1 - 0.05, x1, d - 0.06, z1, fm)
        m.box(x0, -0.1, z0, x0 + 0.02, d - 0.05, z1, "glass_main")
        m.box(x1 - 0.02, -0.1, z0, x1, d - 0.05, z1, "glass_main")
        return
    if sill and kind not in ("floor", "ribbon", "high", "fix"):
        m.box(x0 - 0.06, -0.2, z0 - 0.05, x1 + 0.06, 0.1, z0, "rc_concrete")
        m.box(x0 - 0.06, 0.06, z0 - 0.07, x1 + 0.06, 0.1, z0 - 0.05, "alu_silver")
    if hood:  # 庇(窓上)
        m.box(x0 - 0.15, 0.0, z1 + 0.08, x1 + 0.15, 0.45, z1 + 0.12, "alu_main")
        for x in (x0 - 0.15, x1 + 0.11):
            m.box(x, 0.0, z1 - 0.1, x + 0.04, 0.45, z1 + 0.12, "alu_main")
    if bars:  # 面格子
        for i in range(int((x1 - x0) / 0.11) + 1):
            x = x0 + 0.03 + i * (x1 - x0 - 0.06) / max(1, int((x1 - x0) / 0.11))
            m.box(x - 0.012, 0.04, z0 + 0.0, x + 0.012, 0.07, z1, "steel_white")
        for z in (z0 + 0.04, (z0 + z1) / 2, z1 - 0.06):
            m.box(x0, 0.03, z, x1, 0.08, z + 0.035, "steel_white")
    if shutterbox:  # 雨戸/シャッターボックス
        m.box(x0 - 0.05, -0.1, z1 + 0.02, x1 + 0.05, 0.18, z1 + 0.32, "alu_main")


def _slit(m, W, H, wall, fm):  # 縦長スリット窓x2
    z0, z1 = 0.5, 2.9
    m.box(-W / 2, -T, 0, W / 2, 0, z0, wall)
    m.box(-W / 2, -T, z1, W / 2, 0, H, wall)
    xs = [(-1.15, -0.65), (0.65, 1.15)]
    m.box(-W / 2, -T, z0, xs[0][0], 0, z1, wall)
    m.box(xs[0][1], -T, z0, xs[1][0], 0, z1, wall)
    m.box(xs[1][1], -T, z0, W / 2, 0, z1, wall)
    for a, b in xs:
        interior(m, a, b, z0, z1)
        frame(m, a, b, z0, z1, fm, 0.045, 0.07)
        glass(m, a + 0.045, b - 0.045, z0 + 0.045, z1 - 0.045)
        m.box(a - 0.04, -0.2, z0 - 0.04, b + 0.04, 0.06, z0, "rc_concrete")


for _k in ("sliding2", "sliding4", "fix", "casement", "awning", "slit", "high", "floor", "jalousie", "bay", "ribbon"):
    reg(f"win_{_k}", (lambda k: lambda m, W, H, r: _win(m, W, H, r, k))(_k), cat="window")
for _k, _o in {"sliding2_bars": dict(kind="sliding2", bars=True), "sliding2_hood": dict(kind="sliding2", hood=True),
               "sliding2_shutter": dict(kind="sliding2", shutterbox=True), "casement_hood": dict(kind="casement", hood=True),
               "sliding4_hood": dict(kind="sliding4", hood=True), "sliding2_black": dict(kind="sliding2", fm="alu_black", hood=True),
               "casement_bars": dict(kind="casement", bars=True)}.items():
    reg(f"win_{_k}", (lambda o: lambda m, W, H, r: _win(m, W, H, r, **o))(_o), cat="window")


@mod("win_round", cat="window")
def _(m, W, H, rng):  # 丸窓
    m.box(-W / 2, -T, 0, W / 2, 0, H, "paint_main")
    m.box(-0.6, -0.34, 1.0, 0.6, -0.24, 2.2, "interior")
    m.tube(0, -0.17, 1.6, 0.62, 0.55, 0.2, "y", "alu_main", 28)
    m.cyl(0, -0.1, 1.6, 0.55, 0.012, "y", "glass_main", 28)
    m.tube(0, 0.0, 1.6, 0.68, 0.62, 0.06, "y", "paint_white", 28)


@mod("win_porthole_pair", cat="window")
def _(m, W, H, rng):  # 小丸窓2つ
    m.box(-W / 2, -T, 0, W / 2, 0, H, "paint_main")
    for x in (-0.9, 0.9):
        m.box(x - 0.3, -0.34, 1.4, x + 0.3, -0.24, 2.0, "interior")
        m.tube(x, -0.17, 1.7, 0.32, 0.27, 0.2, "y", "steel_galv", 20)
        m.cyl(x, -0.1, 1.7, 0.27, 0.012, "y", "glass_main", 20)


# ---- ルーバー / フィン ----
def _screen(m, W, H, wall="alc"):
    m.box(-W / 2, -T, 0, W / 2, 0, H, wall)


def _rails(m, W, H, y1=0.18):
    for z in (0.0, H / 2, H - 0.06):
        m.box(-W / 2, 0.0, z, W / 2, y1, z + 0.06, "steel_gray")
    for x in (-W / 2 + 0.02, 0, W / 2 - 0.08):
        m.box(x, 0.0, 0.0, x + 0.06, y1, H, "steel_gray")


@mod("louver_vertical", cat="louver")
def _(m, W, H, rng):
    _screen(m, W, H); _rails(m, W, H)
    n = int(W / 0.12)
    for i in range(n):
        x = -W / 2 + (i + 0.5) * W / n
        m.box(x - 0.02, 0.12, 0.02, x + 0.02, 0.24, H - 0.02, "alu_main")


@mod("louver_horizontal", cat="louver")
def _(m, W, H, rng):
    _screen(m, W, H); _rails(m, W, H)
    z = 0.1
    while z < H - 0.1:
        m.slat_x(-W / 2 + 0.02, W / 2 - 0.02, 0.17, z, 0.2, 0.02, math.radians(-20), "alu_main")
        z += 0.13


@mod("louver_diagonal", cat="louver")
def _(m, W, H, rng):
    _screen(m, W, H); _rails(m, W, H)
    z = 0.1
    while z < H - 0.1:
        m.slat_x(-W / 2 + 0.02, W / 2 - 0.02, 0.17, z, 0.2, 0.02, math.radians(-50), "alu_main")
        z += 0.1


@mod("louver_wood", cat="louver")
def _(m, W, H, rng):
    _screen(m, W, H, "paint_dark"); _rails(m, W, H, 0.2)
    n = int(W / 0.08)
    for i in range(n):
        x = -W / 2 + (i + 0.5) * W / n
        m.box(x - 0.02, 0.1, 0.02, x + 0.02, 0.2, H - 0.02, "wood")


@mod("louver_window_behind", cat="louver")
def _(m, W, H, rng):  # 窓の前に縦ルーバー(日射遮蔽)
    from .lib_win import _win
    _win(m, W, H, rng, "sliding4")
    for z in (0.0, H - 0.06):
        m.box(-W / 2, 0.2, z, W / 2, 0.26, z + 0.06, "alu_black")
    n = int(W / 0.2)
    for i in range(n):
        x = -W / 2 + (i + 0.5) * W / n
        m.box(x - 0.015, 0.1, 0.06, x + 0.015, 0.3, H - 0.06, "alu_black")


@mod("punching_metal", cat="louver")
def _(m, W, H, rng):  # パンチングメタル/エキスパンドメタル(格子で表現)
    _screen(m, W, H, "paint_dark")
    n, k = int(W / 0.045), int(H / 0.045)
    for i in range(n + 1):
        x = -W / 2 + i * W / n
        m.box(x - 0.006, 0.12, 0, x + 0.006, 0.14, H, "alu_silver")
    for j in range(k + 1):
        z = min(j * 0.045, H - 0.012)
        m.box(-W / 2, 0.14, z, W / 2, 0.16, z + 0.012, "alu_silver")
    for x in (-W / 2, W / 2 - 0.05):
        m.box(x, 0.0, 0, x + 0.05, 0.17, H, "alu_black")


@mod("lattice_wood", cat="louver")
def _(m, W, H, rng):  # 木調格子
    _screen(m, W, H, "paint_dark")
    for i in range(int(W / 0.15) + 1):
        x = -W / 2 + i * W / int(W / 0.15)
        m.box(x - 0.015, 0.05, 0, x + 0.015, 0.2, H, "wood")
    for j in range(int(H / 0.15) + 1):
        z = min(j * H / int(H / 0.15), H - 0.03)
        m.box(-W / 2, 0.05, z, W / 2, 0.1, z + 0.03, "wood")


@mod("fin_projecting", cat="louver")
def _(m, W, H, rng):  # 突出縦フィン(深さ0.5)
    _screen(m, W, H, "glass_main")
    m.box(-W / 2, -T, 0, W / 2, -0.1, H, "core")
    n = int(W / 0.6)
    for i in range(n + 1):
        x = -W / 2 + i * W / n
        m.box(x - 0.025, -0.1, 0, x + 0.025, 0.5, H, "alu_main")


@mod("brise_soleil", cat="louver")
def _(m, W, H, rng):  # 水平ブリーズソレイユ
    m.box(-W / 2, -T, 0, W / 2, -0.1, H, "core")
    glass(m, -W / 2, W / 2, 0.9, 3.0, -0.12)
    m.box(-W / 2, -0.12, 0, W / 2, 0.0, 0.9, "alu_main")
    for z in (1.0, 1.8, 2.6, 3.3):
        m.slat_x(-W / 2, W / 2, 0.35, z, 0.8, 0.03, math.radians(-8), "alu_main")
    for x in (-W / 2, W / 2 - 0.03):
        m.box(x, 0.0, 0.9, x + 0.03, 0.75, 3.5, "alu_main")


@mod("awning_fabric", cat="louver")
def _(m, W, H, rng):  # 日除けオーニング
    from .lib_win import _win
    _win(m, W, H, rng, "sliding4")
    m.prism([(0.0, 2.7), (0.9, 2.1), (0.9, 1.95), (0.0, 2.55)], "x", -1.6, 1.6, "fabric")
    for x in (-1.6, 1.58):
        m.box(x, 0.0, 2.55, x + 0.02, 0.9, 2.7, "steel_gray")


@mod("sunshade_glass_fin", cat="louver")
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, -0.1, H, "core")
    glass(m, -W / 2, W / 2, 0.0, H, -0.1)
    for z in (H - 0.15,):
        m.box(-W / 2, -0.1, z, W / 2, 0.8, z + 0.015, "glass_clear")
        m.box(-W / 2, 0.8, z - 0.03, W / 2, 0.83, z + 0.045, "alu_silver")
    m.box(-W / 2 + 0.05, -0.3, 0, W / 2 - 0.05, -0.28, H, "interior")
