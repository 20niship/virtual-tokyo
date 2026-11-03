"""壁・カーテンウォール・コーナー・層間/屋上縁。"""
import math

from .registry import T, mod, reg


def _grid_wall(m, W, H, backmat, mat, pw, ph, gap, depth, bond=True, jitter=0.0, rng=None):
    m.box(-W / 2, -T, 0, W / 2, -depth, H, backmat)
    rows = int(math.ceil(H / ph))
    for r in range(rows):
        z0 = r * ph
        off = (pw / 2) if (bond and r % 2) else 0
        x = -W / 2 - off
        while x < W / 2:
            xa, xb = max(x + gap / 2, -W / 2), min(x + pw - gap / 2, W / 2)
            za, zb = z0 + gap / 2, min(z0 + ph - gap / 2, H)
            if xb > xa + 1e-3 and zb > za + 1e-3:
                d = rng.uniform(-jitter, jitter) if rng and jitter else 0
                m.box(xa, -depth, za, xb, d, zb, mat)
            x += pw


@mod("wall_tile", cat="wall")
def _(m, W, H, rng):  # 二丁掛タイル 227x60 (+目地)
    _grid_wall(m, W, H, "grout", "tile_main", 0.237, 0.07, 0.01, 0.02, True, 0.0035, rng)


@mod("wall_tile_large", cat="wall")
def _(m, W, H, rng):  # 大判タイル 300x600
    _grid_wall(m, W, H, "grout", "tile_main", 0.3, 0.6, 0.008, 0.015, False, 0.002, rng)


@mod("wall_brick", cat="wall")
def _(m, W, H, rng):  # レンガ積み(長手積み) 210x60
    _grid_wall(m, W, H, "mortar", "brick_main", 0.22, 0.075, 0.01, 0.03, True, 0.01, rng)


@mod("wall_stone", cat="wall")
def _(m, W, H, rng):  # 石積み(布積み)
    m.box(-W / 2, -T, 0, W / 2, -0.03, H, "mortar")
    z = 0
    while z < H - 0.01:
        h = min(rng.choice([0.3, 0.45, 0.6]), H - z)
        x = -W / 2
        while x < W / 2 - 0.01:
            w = min(rng.choice([0.6, 0.9, 1.2]), W / 2 - x)
            m.box(x + 0.006, -0.03, z + 0.006, x + w - 0.006, rng.uniform(-0.012, 0.012), z + h - 0.006, "stone_main")
            x += w
        z += h


@mod("wall_formwork", cat="wall")
def _(m, W, H, rng):  # 打放しRC: 型枠割り 900x1800 + セパ穴
    pw, ph = 0.9, 1.8
    m.box(-W / 2, -T, 0, W / 2, -0.01, H, "rc_concrete")
    nx, nz = int(round(W / pw)), int(math.ceil(H / ph))
    for i in range(nx):
        for j in range(nz):
            xa, xb = -W / 2 + i * W / nx, -W / 2 + (i + 1) * W / nx
            za, zb = j * ph, min((j + 1) * ph, H)
            m.box(xa + 0.006, -0.01, za + 0.006, xb - 0.006, rng.uniform(-0.003, 0.003), zb - 0.006, "rc_concrete")
            for fx in (0.25, 0.75):
                for fz in (0.25, 0.75):
                    m.cyl((xa + (xb - xa) * fx), -0.002, za + (zb - za) * fz, 0.02, 0.012, "y", "rc_hole", 10)


@mod("wall_alc", cat="wall")
def _(m, W, H, rng):  # ALC縦張り 600幅
    m.box(-W / 2, -T, 0, W / 2, -0.015, H, "grout")
    n = int(round(W / 0.6))
    for i in range(n):
        xa, xb = -W / 2 + i * W / n, -W / 2 + (i + 1) * W / n
        m.box(xa + 0.004, -0.015, 0, xb - 0.004, 0, H, "alc")


@mod("wall_metal_siding", cat="wall")
def _(m, W, H, rng):  # 金属サイディング(波形リブ)
    m.box(-W / 2, -T, 0, W / 2, -0.04, H, "metal_siding")
    n = int(W / 0.1)
    prof = [(0, 0), (0.07, 0), (0.06, 0.04), (0.01, 0.04)]
    for i in range(n):
        x = -W / 2 + i * W / n
        m.prism([(x + a, -0.04 + b) for a, b in prof], "z", 0, H, "metal_siding")


@mod("wall_spray", cat="wall")
def _(m, W, H, rng):  # 吹付け + 巾木 + 目地
    m.box(-W / 2, -T, 0, W / 2, 0, H, "spray_main")
    m.box(-W / 2, -T, 0, W / 2, 0.02, 0.35, "paint_dark")
    for z in (H * 0.5,):
        m.box(-W / 2, -0.01, z, W / 2, 0.003, z + 0.01, "grout")


@mod("wall_panel_emboss", cat="deco")
def _(m, W, H, rng):  # エンボス意匠パネル(菱形リブ)
    m.box(-W / 2, -T, 0, W / 2, -0.02, H, "alc")
    nx, nz = 6, 6
    for i in range(nx):
        for j in range(nz):
            cx, cz = -W / 2 + (i + 0.5) * W / nx, (j + 0.5) * H / nz
            a, b = W / nx / 2 * 0.8, H / nz / 2 * 0.8
            m.prism([(cx, cz - b), (cx + a, cz), (cx, cz + b), (cx - a, cz)], "y", -0.02, 0.04, "alc")


@mod("wall_ribs_vertical", cat="deco")
def _(m, W, H, rng):  # 縦リブ壁
    m.box(-W / 2, -T, 0, W / 2, -0.01, H, "paint_main")
    for i in range(int(W / 0.3)):
        x = -W / 2 + 0.15 + i * 0.3
        m.box(x - 0.04, -0.01, 0, x + 0.04, 0.12, H, "paint_main")


# ---- カーテンウォール ----
def _curtain(m, W, H, sp0, sp1, mull, mat_frame="alu_main"):
    m.box(-W / 2, -T, 0, W / 2, -0.1, H, "core")
    n = max(1, int(round(W / 1.2)))
    xs = [-W / 2 + i * W / n for i in range(n + 1)]
    m.box(-W / 2, -0.14, 0, W / 2, 0.01, sp0, mat_frame)  # 下スパンドレル
    m.box(-W / 2, -0.14, H - sp1, W / 2, 0.01, H, mat_frame)  # 上
    for i in range(n):
        m.box(xs[i] + 0.03, -0.1, sp0, xs[i + 1] - 0.03, -0.085, H - sp1, "glass_main")
    for x in xs:
        m.box(x - 0.03, -0.14, sp0, x + 0.03, 0.06 if mull else 0.01, H - sp1, mat_frame)
    m.box(-W / 2, -0.14, sp0 - 0.03, W / 2, 0.04, sp0 + 0.03, mat_frame)
    m.box(-W / 2, -0.14, H - sp1 - 0.03, W / 2, 0.04, H - sp1 + 0.03, mat_frame)
    m.box(-W / 2 + 0.05, -0.3, sp0, W / 2 - 0.05, -0.28, H - sp1, "interior")


reg("curtain_grid", lambda m, W, H, r: _curtain(m, W, H, 0.85, 0.35, True), cat="curtain")
reg("curtain_ribbon", lambda m, W, H, r: _curtain(m, W, H, 1.1, 0.6, False, "steel_white"), cat="curtain")


@mod("curtain_dpg", cat="curtain")
def _(m, W, H, rng):  # フレームレス(DPG)+ガラスフィン
    m.box(-W / 2, -T, 0, W / 2, -0.1, H, "core")
    n = max(1, int(round(W / 1.8)))
    for i in range(n):
        xa, xb = -W / 2 + i * W / n, -W / 2 + (i + 1) * W / n
        m.box(xa + 0.01, -0.1, 0.0, xb - 0.01, -0.085, H, "glass_main")
        m.box(xa - 0.01, -0.1, 0, xa + 0.01, 0.35, H, "glass_clear")  # ガラスフィン
        for z in (0.2, H / 2, H - 0.2):
            m.cyl(xa, 0.0, z, 0.03, 0.03, "y", "alu_silver", 10)
    m.box(W / 2 - 0.01, -0.1, 0, W / 2 + 0.01, 0.35, H, "glass_clear")
    m.box(-W / 2 + 0.05, -0.3, 0, W / 2 - 0.05, -0.28, H, "interior")


@mod("curtain_stick_spandrel_stone", cat="curtain")
def _(m, W, H, rng):  # 石スパンドレル+ガラス帯
    m.box(-W / 2, -T, 0, W / 2, -0.1, H, "core")
    m.box(-W / 2, -0.12, 0, W / 2, 0.02, 1.0, "stone_main")
    m.box(-W / 2, -0.12, H - 0.5, W / 2, 0.02, H, "stone_main")
    m.box(-W / 2, -0.1, 1.0, W / 2, -0.088, H - 0.5, "glass_main")
    for i in range(3):
        m.box(-W / 2 + i * W / 3 - 0.025, -0.12, 1.0, -W / 2 + i * W / 3 + 0.025, 0.05, H - 0.5, "alu_black")
    m.box(W / 2 - 0.025, -0.12, 1.0, W / 2 + 0.025, 0.05, H - 0.5, "alu_black")
    m.box(-W / 2 + 0.05, -0.3, 1.0, W / 2 - 0.05, -0.28, H - 0.5, "interior")


# ---- コーナー ----
reg("corner_post", lambda m, W, H, r: (m.box(-0.3, -0.3, 0, 0.3, 0.3, H, "paint_main"),
                                       m.box(-0.34, -0.34, 0, 0.34, 0.34, 0.25, "paint_dark")), W=0.6, H=1.0, cat="corner")
reg("corner_post_stone", lambda m, W, H, r: (m.box(-0.35, -0.35, 0, 0.35, 0.35, H, "stone_main"),
                                             m.box(-0.38, -0.38, 0, 0.38, 0.38, 0.3, "stone_main")), W=0.7, H=1.0, cat="corner")
reg("corner_post_glass", lambda m, W, H, r: (m.box(-0.12, -0.12, 0, 0.12, 0.12, H, "alu_main"),
                                             m.box(-0.1, -0.1, 0, 0.1, 0.1, H, "glass_clear")), W=0.25, H=1.0, cat="corner")
reg("corner_post_round", lambda m, W, H, r: (m.cyl(0, 0, 0, 0.35, H, "z", "paint_main", 20),
                                             m.cyl(0, 0, 0, 0.4, 0.25, "z", "paint_dark", 20)), W=0.7, H=1.0, cat="corner")


# ---- 層間・屋上縁 ----
@mod("slab_edge", H=0.4, cat="edge")
def _(m, W, H, rng):  # 層間帯(腰帯) + 水切り
    m.box(-W / 2, -T, 0, W / 2, 0.06, H, "paint_main")
    m.box(-W / 2, 0.0, -0.02, W / 2, 0.08, 0.04, "paint_dark")


@mod("cornice", H=0.7, cat="edge")
def _(m, W, H, rng):  # 段付きコーニス
    m.box(-W / 2, -T, 0, W / 2, 0.08, 0.25, "paint_main")
    m.box(-W / 2, -T, 0.25, W / 2, 0.2, 0.45, "paint_main")
    m.box(-W / 2, -T, 0.45, W / 2, 0.3, 0.7, "paint_main")
    for i in range(int(W / 0.45)):
        m.box(-W / 2 + 0.1 + i * 0.45, 0.08, 0.0, -W / 2 + 0.25 + i * 0.45, 0.2, 0.25, "paint_white")


@mod("parapet", H=1.0, cat="edge")
def _(m, W, H, rng):  # パラペット + アルミ笠木
    m.box(-W / 2, -T, 0, W / 2, 0, H - 0.05, "paint_main")
    m.box(-W / 2, -T - 0.03, H - 0.05, W / 2, 0.06, H, "alu_silver")
    m.box(-W / 2, 0.0, 0.0, W / 2, 0.01, 0.25, "paint_dark")


@mod("parapet_louver", H=2.2, cat="edge")
def _(m, W, H, rng):  # 屋上設備目隠しルーバー
    m.box(-W / 2, -0.12, 0, W / 2, 0.0, 0.3, "paint_main")
    for x in (-W / 2 + 0.05, 0, W / 2 - 0.05):
        m.box(x - 0.04, -0.1, 0.3, x + 0.04, 0.02, H, "steel_gray")
    z = 0.35
    while z < H - 0.1:
        m.slat_x(-W / 2, W / 2, 0.0, z, 0.14, 0.015, math.radians(-35), "alu_silver")
        z += 0.12
    m.box(-W / 2, -0.12, H - 0.05, W / 2, 0.04, H, "steel_gray")


@mod("parapet_railing", H=1.1, cat="edge")
def _(m, W, H, rng):  # 屋上手すり
    m.box(-W / 2, -0.1, 0, W / 2, 0.0, 0.2, "paint_main")
    for i in range(int(W / 0.15) + 1):
        x = -W / 2 + i * W / int(W / 0.15)
        m.box(x - 0.01, -0.06, 0.2, x + 0.01, -0.04, H, "steel_galv")
    for z in (0.55, 1.05):
        m.box(-W / 2, -0.07, z, W / 2, -0.03, z + 0.04, "steel_galv")


@mod("canopy", H=0.35, W=3.6, cat="edge")
def _(m, W, H, rng):  # キャノピー(出庇)
    m.box(-W / 2, -0.1, 0, W / 2, 1.8, 0.15, "alu_main")
    m.box(-W / 2, 1.8, -0.1, W / 2, 1.9, 0.25, "alu_main")
    m.box(-W / 2 + 0.2, 0.0, -0.1, -W / 2 + 0.25, 0.0 + 1.7, 0.0, "steel_gray")
    m.box(W / 2 - 0.25, 0.0, -0.1, W / 2 - 0.2, 1.7, 0.0, "steel_gray")
