"""フェーズA2の追加部材(詳細は docs/building_modules.md)。座標系: 壁面y=0, 外向き+y, 床z=0。"""
import math
from .lib_win import _win
from .registry import T, frame, glass, hole_wall, interior, mod, reg


def _prism(m, prof, axis, a0, a1, mat):
    area = sum(prof[i][0] * prof[(i + 1) % len(prof)][1] - prof[(i + 1) % len(prof)][0] * prof[i][1] for i in range(len(prof)))
    m.prism(prof if area > 0 else prof[::-1], axis, a0, a1, mat)

def ac_wall(m, x, z, w=0.82, h=0.6, d=0.3, y=0.0):
    """壁掛け室外機(正面ファン+吹出しグリル+背面の配管口)"""
    m.box(x - w / 2, y, z, x + w / 2, y + d, z + h, 'ac_white')
    cz = z + h / 2
    m.tube(x, y + d, cz, 0.22, 0.2, 0.012, 'y', 'steel_galv', 20)
    m.cyl(x, y + d, cz, 0.2, 0.004, 'y', 'rubber', 20)
    for k in range(5):
        a = k * 2 * math.pi / 5
        _prism(m, [(cz, x), (cz + 0.18 * math.sin(a), x + 0.18 * math.cos(a)), (cz + 0.18 * math.sin(a + 0.55), x + 0.18 * math.cos(a + 0.55))], 'y', y + d + 0.004, y + d + 0.01, 'steel_gray')
    for i in range(6):
        m.box(x - w / 2 + 0.06, y + d - 0.002, z + 0.05 + i * 0.012, x - w / 2 + 0.2, y + d + 0.004, z + 0.056 + i * 0.012, 'steel_galv')
    m.cyl(x + w / 2 - 0.1, y + 0.0, z + 0.08, 0.02, 0.1, 'y', 'steel_gray', 8)

def pipe_v(m, x, y, z0, z1, r=0.03, mat='steel_galv'):
    m.cyl(x, y, z0, r, z1 - z0, 'z', mat, 10)

def brace(m, x0, z0, x1, z1, y0, y1, t, mat):
    """x-z面の斜材(板状)"""
    dx, dz = (x1 - x0, z1 - z0)
    L = math.hypot(dx, dz) or 1
    nx, nz = (-dz / L * t / 2, dx / L * t / 2)
    pts = [(x0 + nx, z0 + nz), (x1 + nx, z1 + nz), (x1 - nx, z1 - nz), (x0 - nx, z0 - nz)]
    _prism(m, [(z, x) for x, z in pts], 'y', y0, y1, mat)

def _sode(m, panels, w=0.8, h=2.8, d=0.26, mats=('sign_red', 'sign_white', 'sign_blue', 'sign_yellow')):
    """袖看板(突出看板): 縦長の箱枠にテナント面を積み、壁へステーで固定。原点=取付中心・下端"""
    m.box(-w / 2, 0.0, 0.0, w / 2, d, h, 'alu_black')
    hh = h / panels
    for i in range(panels):
        c = mats[(i * 7 + panels) % len(mats)]
        for fy in (d + 0.003,):
            m.box(-w / 2 + 0.04, fy - 0.003, i * hh + 0.04, w / 2 - 0.04, fy + 0.004, (i + 1) * hh - 0.04, c)
        m.box(-w / 2 + 0.1, d + 0.004, i * hh + 0.12, w / 2 - 0.1, d + 0.008, (i + 1) * hh - 0.12, 'sign_white' if c != 'sign_white' else 'sign_blue')
    for z in (0.15, h - 0.15):
        m.box(-0.04, -0.2, z - 0.03, 0.04, 0.0, z + 0.03, 'steel_gray')
    m.box(-w / 2 - 0.01, 0.0, h, w / 2 + 0.01, d, h + 0.03, 'alu_black')
reg('sign_sode_4', lambda m, W, H, r: _sode(m, 4), W=0.8, H=2.8, cat='看板')
reg('sign_sode_6', lambda m, W, H, r: _sode(m, 6, 0.7, 3.6, 0.22), W=0.7, H=3.6, cat='看板')
reg('sign_sode_2', lambda m, W, H, r: _sode(m, 2, 0.9, 1.8, 0.3, ('sign_blue', 'sign_white')), W=0.9, H=1.8, cat='看板')

@mod('sign_tsukidashi_yoko', W=1.8, H=0.55, cat='看板')
def _(m, W, H, rng):
    m.box(-0.9, 0.0, 0.0, 0.9, 0.18, 0.55, 'alu_black')
    m.box(-0.86, 0.18, 0.04, 0.86, 0.186, 0.51, 'sign_red')
    m.box(-0.7, 0.186, 0.12, 0.7, 0.19, 0.43, 'sign_white')
    for x in (-0.6, 0.6):
        m.box(x - 0.03, -0.25, 0.25, x + 0.03, 0.0, 0.3, 'steel_gray')

@mod('sign_wall_box', W=2.4, H=0.9, cat='看板')
def _(m, W, H, rng):
    m.box(-1.2, 0.0, 0.0, 1.2, 0.2, 0.9, 'alu_silver')
    m.box(-1.14, 0.2, 0.05, 1.14, 0.206, 0.85, 'sign_white')
    for i in range(4):
        m.box(-1.0 + i * 0.5, 0.206, 0.15, -0.6 + i * 0.5, 0.209, 0.75, ('sign_red', 'sign_blue', 'sign_yellow', 'sign_red')[i])

@mod('sign_roof_pylon', W=4.0, H=2.8, cat='看板')
def _(m, W, H, rng):
    for x in (-1.7, 1.7):
        m.box(x - 0.06, -0.06, 0, x + 0.06, 0.06, 2.0, 'steel_gray')
    m.box(-2.0, -0.1, 1.0, 2.0, 0.1, 2.8, 'alu_black')
    m.box(-1.95, 0.1, 1.05, 1.95, 0.106, 2.75, 'sign_blue')
    m.box(-1.6, 0.106, 1.5, 1.6, 0.11, 2.3, 'sign_white')
    for x in (-1.9, 0, 1.9):
        brace(m, x, 1.0, x * 0.9, 0.0, -0.05, 0.05, 0.05, 'steel_gray')

def _rack(m, n, cols):
    """壁面の室外機ラック: L形鋼ブラケット+室外機n台(段数rows)"""
    rows = math.ceil(n / cols)
    w = cols * 0.95 + 0.1
    for r_ in range(rows):
        z = r_ * 0.85
        m.box(-w / 2, 0.0, z, w / 2, 0.55, z + 0.05, 'steel_galv')
        for x in (-w / 2 + 0.05, w / 2 - 0.05):
            m.box(x - 0.025, 0.0, z - 0.4, x + 0.025, 0.55, z, 'steel_galv')
    for i in range(n):
        r_, c_ = divmod(i, cols)
        ac_wall(m, (c_ - (cols - 1) / 2) * 0.95, r_ * 0.85 + 0.05, y=0.1)
    m.box(-w / 2, 0.0, rows * 0.85 - 0.05, w / 2, 0.58, rows * 0.85, 'steel_galv')
    for k in range(n):
        pipe_v(m, (k - n / 2) * 0.1, -0.05, 0.05, rows * 0.85 + 0.3, 0.015, 'ac_white')
reg('ac_rack_wall_2', lambda m, W, H, r: _rack(m, 2, 2), W=2.0, H=1.0, cat='設備')
reg('ac_rack_wall_4', lambda m, W, H, r: _rack(m, 4, 2), W=2.0, H=1.8, cat='設備')
reg('ac_rack_wall_6', lambda m, W, H, r: _rack(m, 6, 3), W=3.0, H=1.8, cat='設備')

@mod('ac_group_ground', W=3.0, H=1.0, cat='設備')
def _(m, W, H, rng):
    m.box(-1.5, 0.0, 0.0, 1.5, 1.0, 0.1, 'rc_concrete')
    for i in range(3):
        u = type(m)()
        ac_wall(u, 0, 0, 0.9, 0.9, 0.35, 0.0)
        m.add(u.transformed(0, (i - 1) * 1.0, 0.25, 0.1))
    m.cyl(-1.4, 0.9, 0.1, 0.025, 1.2, 'z', 'ac_white', 8)

@mod('stair_ext_zigzag', W=3.6, H=7.0, cat='階段')
def _(m, W, H, rng):
    w, y0 = 1.1, 0.35
    land = 0.9
    for lv, (z0, z1) in enumerate(((0.0, 3.5), (3.5, 7.0))):
        up = 1 if lv == 0 else -1
        xa, xb = (-W / 2 + land, W / 2 - 0.1) if up > 0 else (-W / 2 + 0.1, W / 2 - land)
        n = 12
        for i in range(n):
            f0, f1 = i / n, (i + 1) / n
            xs = (xa + (xb - xa) * f0, xa + (xb - xa) * f1) if up > 0 else (xb - (xb - xa) * f1, xb - (xb - xa) * f0)
            z = z0 + (z1 - z0) * f1
            m.box(xs[0], y0, z - 0.05, xs[1], y0 + w, z, 'steel_gray')
        for y in (y0 + 0.02, y0 + w - 0.07):
            if up > 0:
                brace(m, xa, z0, xb, z1, y, y + 0.05, 0.25, 'steel_gray')
            else:
                brace(m, xb, z0, xa, z1, y, y + 0.05, 0.25, 'steel_gray')
            for k in range(0, n + 1, 3):
                f = k / n
                x = xa + (xb - xa) * f if up > 0 else xb - (xb - xa) * f
                m.box(x - 0.02, y + 0.005, z0 + (z1 - z0) * f, x + 0.02, y + 0.045, z0 + (z1 - z0) * f + 1.0, 'steel_galv')
            if up > 0:
                brace(m, xa, z0 + 1.0, xb, z1 + 1.0, y + 0.01, y + 0.04, 0.05, 'steel_galv')
            else:
                brace(m, xb, z0 + 1.0, xa, z1 + 1.0, y + 0.01, y + 0.04, 0.05, 'steel_galv')
        lx0, lx1 = ((-W / 2 + 0.1, -W / 2 + land + 0.1) if lv == 0 else (W / 2 - land - 0.1, W / 2 - 0.1))
        lx0, lx1 = ((W / 2 - land - 0.1, W / 2 - 0.1) if up > 0 else (-W / 2 + 0.1, -W / 2 + land + 0.1))
        m.box(lx0, y0 - 0.05, z1 - 0.07, lx1, y0 + w + 0.05, z1, 'steel_gray')
        m.box(lx0, y0 + w, z1, lx1, y0 + w + 0.03, z1 + 1.0, 'steel_galv')
        m.box(lx0, y0 + w, z1 + 0.96, lx1, y0 + w + 0.05, z1 + 1.02, 'steel_galv')
    for x in (-W / 2 + 0.1, W / 2 - 0.1):
        m.box(x - 0.04, y0 - 0.05, 0, x + 0.04, y0 + 0.03, 7.0, 'steel_gray')
    m.box(-0.6, -0.01, 3.5, 0.6, 0.0, 5.6, 'steel_green')

@mod('stair_ext_spiral', W=2.4, H=3.5, cat='階段')
def _(m, W, H, rng):
    r0, r1 = (0.12, 0.95)
    cx, cy = (0.0, 1.0)
    m.cyl(cx, cy, 0, r0, 3.8, 'z', 'steel_gray', 12)
    n = 14
    for i in range(n):
        a0 = math.radians(i * 360 * 0.78 / n - 20)
        a1 = a0 + math.radians(360 * 0.78 / n - 2)
        z = (i + 1) * 3.5 / (n + 1)
        pts = [(cx + r0 * math.cos(a0), cy + r0 * math.sin(a0)), (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0)), (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1)), (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1))]
        _prism(m, pts, 'z', z - 0.04, z, 'steel_gray')
        m.cyl(cx + (r1 - 0.03) * math.cos(a0), cy + (r1 - 0.03) * math.sin(a0), z, 0.012, 1.0, 'z', 'steel_galv', 6)
    m.box(-0.7, 0.0, 3.5, 0.7, 1.9, 3.55, 'steel_gray')

@mod('stair_ext_straight_long', W=6.0, H=3.5, cat='階段')
def _(m, W, H, rng):
    n = 18
    for i in range(n):
        x = -3.0 + 0.5 + i * 5.0 / n
        m.box(x, 0.25, (i + 1) * 3.5 / (n + 1) - 0.04, x + 5.0 / n, 1.35, (i + 1) * 3.5 / (n + 1), 'steel_gray')
    m.box(2.5, 0.2, 3.44, 3.0, 1.6, 3.5, 'steel_gray')
    brace(m, -2.5, 0.0, 2.5, 3.5, 0.25, 0.3, 0.08, 'steel_gray')
    brace(m, -2.5, 0.0, 2.5, 3.5, 1.3, 1.35, 0.08, 'steel_gray')
    for y in (0.27, 1.33):
        brace(m, -2.5, 1.0, 2.5, 4.5, y - 0.01, y + 0.01, 0.04, 'steel_galv')
    m.box(2.5, 0.2, 4.5, 3.0, 0.22, 4.55, 'steel_galv')

@mod('duct_vertical_pipes', W=1.0, H=3.5, cat='設備')
def _(m, W, H, rng):
    for i, (x, r) in enumerate(((-0.25, 0.04), (-0.08, 0.03), (0.1, 0.05), (0.28, 0.025))):
        pipe_v(m, x, 0.06, 0.0, 3.5, r, 'steel_galv' if i % 2 else 'steel_white')
        for z in (0.4, 1.4, 2.4, 3.2):
            m.box(x - r - 0.01, 0.02, z - 0.015, x + r + 0.01, 0.06 + r, z + 0.015, 'steel_gray')
    m.box(-0.45, 0.0, 1.0, -0.15, 0.2, 1.3, 'steel_gray')

@mod('gas_meter_box', W=0.6, H=0.7, cat='設備')
def _(m, W, H, rng):
    m.box(-0.3, 0.0, 0.0, 0.3, 0.2, 0.7, 'steel_white')
    m.box(-0.28, 0.2, 0.05, 0.28, 0.215, 0.65, 'steel_white')
    m.box(-0.2, 0.215, 0.35, 0.2, 0.225, 0.6, 'glass_clear')
    m.box(-0.05, 0.215, 0.1, 0.05, 0.23, 0.2, 'steel_gray')

@mod('awning_shop_stripe', W=3.0, H=0.8, cat='看板')
def _(m, W, H, rng):
    n = 10
    for i in range(n):
        xa, xb = (-1.5 + i * 0.3, -1.5 + (i + 1) * 0.3)
        mat = 'fabric' if i % 2 == 0 else 'paint_white'
        _prism(m, [(0.0, 0.7), (1.0, 0.45), (1.0, 0.41), (0.0, 0.66)], 'x', xa, xb, mat)
    m.box(-1.5, 1.0, 0.4, 1.5, 1.1, 0.44, 'fabric')
    m.box(-1.5, 0.0, 0.66, 1.5, 0.08, 0.76, 'steel_gray')
    for x in (-1.5, 1.45):
        _prism(m, [(0.0, 0.7), (1.0, 0.45), (0.0, 0.45)], 'x', x, x + 0.05, 'steel_gray')

@mod('a_frame_sign', W=0.6, H=1.0, cat='小物')
def _(m, W, H, rng):
    _prism(m, [(0.3, 0.0), (0.04, 1.0), (0.01, 1.0), (0.27, 0.0)], 'x', -0.3, 0.3, 'alu_black')
    _prism(m, [(-0.3, 0.0), (-0.04, 1.0), (-0.01, 1.0), (-0.27, 0.0)], 'x', -0.3, 0.3, 'alu_black')

@mod('tenant_plate_board', W=0.9, H=1.8, cat='看板')
def _(m, W, H, rng):
    m.box(-0.45, 0.0, 0.0, 0.45, 0.08, 1.8, 'alu_black')
    for i in range(8):
        m.box(-0.38, 0.08, 0.1 + i * 0.2, 0.38, 0.084, 0.28 + i * 0.2, ('sign_white', 'sign_blue', 'sign_white', 'sign_yellow')[i % 4])

@mod('stairhall_slit', cat='団地')
def _(m, W, H, rng):
    hole_wall(m, W, H, -0.2, 0.2, 0.3, 3.2, 'paint_main')
    interior(m, -0.2, 0.2, 0.3, 3.2)
    frame(m, -0.2, 0.2, 0.3, 3.2, 'alu_main', 0.04, 0.07)
    glass(m, -0.16, 0.16, 0.34, 3.16)
    for z in (1.1, 1.8, 2.5):
        m.box(-0.2, -0.17, z - 0.01, 0.2, -0.1, z + 0.01, 'alu_main')
    m.box(-0.35, 0.0, 3.2, 0.35, 0.18, 3.26, 'rc_concrete')
    m.box(-0.35, 0.0, 0.25, 0.35, 0.08, 0.3, 'rc_concrete')

@mod('stairhall_glass_block', cat='団地')
def _(m, W, H, rng):
    m.ring((-W / 2, W / 2, 0, H), (-0.9, 0.9, 0.2, 3.3), -0.25, 0.0, 'rc_concrete', 0.006, 0.008)
    for i in range(int(1.8 / 0.19)):
        for j in range(int(3.1 / 0.19)):
            m.box(-0.9 + 0.01 + i * 0.19, -0.15, 0.2 + 0.01 + j * 0.19, -0.9 + 0.18 + i * 0.19, -0.04, 0.2 + 0.18 + j * 0.19, 'glass_clear')
    interior(m, -0.9, 0.9, 0.2, 3.3, -0.2)

@mod('stairhall_open', cat='団地')
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, 0, 1.1, 'paint_main')
    m.box(-W / 2 - 0.02, -T - 0.02, 1.1, W / 2 + 0.02, 0.04, 1.16, 'alu_silver')
    m.box(-W / 2, -T, 3.2, W / 2, 0, H, 'paint_main')
    interior(m, -W / 2, W / 2, 1.16, 3.2, -0.3)
    brace(m, -1.0, 0.2, 1.0, 1.9, -0.18, -0.12, 0.1, 'steel_gray')
    for i in range(8):
        m.box(-1.0 + i * 0.25, -0.25, 0.25 + i * 0.2, -0.75 + i * 0.25, -0.1, 0.29 + i * 0.2, 'rc_concrete')
    for x in (-W / 2 + 0.05, W / 2 - 0.05):
        m.box(x - 0.1, -T, 0, x + 0.1, 0.0, H, 'paint_white')

@mod('corridor_geo_grille', cat='団地')
def _(m, W, H, rng):
    m.box(-W / 2, 0.0, -0.2, W / 2, 1.5, 0.0, 'rc_concrete')
    m.box(-W / 2, -T, 0, W / 2, 0, H, 'paint_main')
    m.box(-W / 2, 1.3, 0, W / 2, 1.5, 1.1, 'paint_main')
    m.box(-0.5, 0.0, 0.0, 0.5, 0.05, 2.0, 'steel_gray')
    m.box(-0.55, 0.0, 2.0, 0.55, 0.06, 2.08, 'steel_gray')
    gx0, gx1, gz0, gz1 = (0.65, 1.55, 1.2, 1.9)
    m.box(gx0, 0.0, gz0, gx1, 0.04, gz1, 'interior')
    for i in range(9):
        for j in range(5):
            if (i + j) % 2 == 0:
                m.box(gx0 + 0.02 + i * 0.1, 0.04, gz0 + 0.02 + j * 0.14, gx0 + 0.1 + i * 0.1 - 0.02, 0.07, gz0 + 0.14 + j * 0.14 - 0.02, 'steel_white')
    m.box(-1.7, 0.0, 0.0, -1.0, 0.18, 0.9, 'steel_gray')

@mod('meter_box_door', W=1.0, H=2.2, cat='団地')
def _(m, W, H, rng):
    m.box(-0.5, -0.05, 0.0, 0.5, 0.06, 2.2, 'steel_white')
    for i in range(10):
        m.box(-0.4, 0.06, 1.4 + i * 0.05, 0.4, 0.07, 1.42 + i * 0.05, 'steel_gray')
    m.box(-0.4, 0.06, 0.15, 0.4, 0.07, 1.3, 'steel_white')
    m.box(0.3, 0.07, 1.0, 0.36, 0.1, 1.1, 'steel_galv')
    m.box(-0.1, 0.07, 0.2, 0.1, 0.075, 0.28, 'sign_yellow')

@mod('bal_partition_board', W=0.1, H=1.9, cat='団地')
def _(m, W, H, rng):
    m.box(-0.02, 0.0, 0.0, 0.02, 1.2, 1.85, 'alc')
    m.box(-0.03, 0.0, 0.0, 0.03, 1.2, 0.05, 'steel_galv')
    m.box(-0.03, 0.0, 1.8, 0.03, 1.2, 1.85, 'steel_galv')

@mod('bal_flat_old', cat='団地')
def _(m, W, H, rng):
    hole_wall(m, W, H, -0.9, 0.9, 0.0, 2.2, 'paint_main')
    interior(m, -0.9, 0.9, 0.0, 2.2)
    frame(m, -0.9, 0.9, 0.0, 2.2, 'alu_main', 0.05, 0.09)
    glass(m, -0.85, 0.85, 0.05, 2.15)
    m.box(-W / 2, 0.0, -0.18, W / 2, 1.3, 0.0, 'rc_concrete')
    m.box(-W / 2, 1.1, 0.0, W / 2, 1.3, 1.05, 'paint_main')
    m.box(-W / 2 - 0.02, 1.08, 1.05, W / 2 + 0.02, 1.32, 1.1, 'paint_white')
    m.cyl(-1.5, 0.5, 1.9, 0.015, 3.0, 'x', 'steel_galv', 6)
    ac_wall(m, 1.1, 0.0, y=0.4, w=0.7, h=0.55, d=0.26)
    if rng.random() < 0.7:
        m.box(-0.8, 0.5, 1.3, -0.3, 0.52, 1.9, 'paint_white')
        m.box(-0.2, 0.5, 1.4, 0.2, 0.52, 1.9, 'fabric')

@mod('mail_box_bank', W=1.2, H=1.4, cat='団地')
def _(m, W, H, rng):
    m.box(-0.6, 0.0, 0.0, 0.6, 0.18, 1.4, 'alu_silver')
    for i in range(3):
        for j in range(6):
            m.box(-0.58 + i * 0.4, 0.18, 0.03 + j * 0.22, -0.2 + i * 0.4 - 0.02, 0.19, 0.2 + j * 0.22, 'alu_main')
            m.box(-0.5 + i * 0.4, 0.19, 0.12 + j * 0.22, -0.3 + i * 0.4, 0.195, 0.14 + j * 0.22, 'steel_gray')

@mod('water_heater_unit', W=0.45, H=0.8, cat='設備')
def _(m, W, H, rng):
    m.box(-0.22, 0.0, 0.0, 0.22, 0.2, 0.7, 'plastic_gray')
    m.box(-0.2, 0.2, 0.05, 0.2, 0.21, 0.4, 'steel_white')
    for i in range(5):
        m.box(-0.15, 0.21, 0.5 + i * 0.03, 0.15, 0.22, 0.52 + i * 0.03, 'steel_gray')
    pipe_v(m, -0.1, 0.0, -0.3, 0.0, 0.015, 'steel_galv')
    pipe_v(m, 0.0, 0.0, -0.3, 0.0, 0.015, 'steel_gray')
    pipe_v(m, 0.1, 0.0, -0.3, 0.0, 0.015, 'ac_white')

@mod('bal_glass_continuous', cat='タワー')
def _(m, W, H, rng):
    _win(m, W, H, rng, 'floor', sill=False, fm='alu_bronze')
    m.box(-W / 2, 0.0, -0.22, W / 2, 1.7, 0.0, 'rc_concrete')
    m.box(-W / 2, 1.66, -0.3, W / 2, 1.7, 0.0, 'paint_white')
    glass(m, -W / 2 + 0.03, W / 2 - 0.03, 0.06, 1.1, 1.64, 'glass_clear')
    m.box(-W / 2, 1.6, 1.1, W / 2, 1.7, 1.15, 'alu_silver')
    for x in (-W / 2, 0, W / 2 - 0.04):
        m.box(x, 1.6, 0.0, x + 0.04, 1.68, 1.1, 'alu_silver')

@mod('bal_louver_partition', cat='タワー')
def _(m, W, H, rng):
    _win(m, W, H, rng, 'floor', sill=False, fm='alu_black')
    m.box(-W / 2, 0.0, -0.22, W / 2, 1.5, 0.0, 'rc_concrete')
    glass(m, -W / 2 + 0.05, W / 2 - 0.05, 0.06, 1.1, 1.45, 'glass_clear')
    for x in (-W / 2, W / 2 - 0.02):
        for i in range(10):
            m.box(x, 0.1 + i * 0.15, 0.0, x + 0.02, 0.2 + i * 0.15, 2.1, 'alu_main')
    m.box(-W / 2, 1.44, 1.1, W / 2, 1.5, 1.15, 'alu_black')

@mod('entrance_canopy_big', W=7.2, H=4.5, cat='タワー')
def _(m, W, H, rng):
    m.box(-3.6, -0.2, 3.7, 3.6, 4.5, 3.95, 'paint_white')
    m.box(-3.6, 4.3, 3.6, 3.6, 4.5, 4.1, 'alu_main')
    for x in (-3.2, 3.2):
        m.box(x - 0.2, 4.0, 0, x + 0.2, 4.4, 3.7, 'stone_main')
    for x in (-2, -0.7, 0.7, 2):
        m.cyl(x, 2.0, 3.65, 0.06, 0.05, 'z', 'led_white', 10)
    m.box(-3.6, -0.2, 0.0, 3.6, 4.6, 0.06, 'stone_main')

@mod('porch_stone_columns', W=5.0, H=4.0, cat='タワー')
def _(m, W, H, rng):
    m.box(-2.5, -0.1, 3.4, 2.5, 3.0, 3.8, 'stone_main')
    m.box(-2.6, -0.1, 3.8, 2.6, 3.1, 4.0, 'paint_white')
    for x in (-2.2, -0.75, 0.75, 2.2):
        m.cyl(x, 2.7, 0.15, 0.22, 3.25, 'z', 'stone_main', 18)
        m.cyl(x, 2.7, 0.0, 0.3, 0.15, 'z', 'stone_main', 18)
        m.cyl(x, 2.7, 3.35, 0.3, 0.1, 'z', 'stone_main', 18)
    m.box(-2.5, 0.0, 0.0, 2.5, 3.0, 0.15, 'stone_main')

@mod('curtain_unitized', cat='タワー')
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, -0.1, H, 'core')
    n = max(1, round(W / 1.5))
    for i in range(n):
        xa, xb = (-W / 2 + i * W / n, -W / 2 + (i + 1) * W / n)
        m.box(xa + 0.01, -0.12, 0.0, xb - 0.01, 0.0, 1.0, 'ceramic')
        glass(m, xa + 0.02, xb - 0.02, 1.0, 3.3, -0.1, 'glass_green')
        m.box(xa + 0.02, -0.11, 3.3, xb - 0.02, 0.0, H, 'alu_main')
        m.box(xa + 0.1, -0.12, 0.94, xb - 0.1, 0.01, 0.99, 'alu_black')
        m.box(xa - 0.01, -0.13, 0.0, xa + 0.03, 0.06, H, 'alu_main')
    m.box(W / 2 - 0.03, -0.13, 0.0, W / 2 + 0.01, 0.06, H, 'alu_main')
    m.box(-W / 2 + 0.05, -0.3, 1.0, W / 2 - 0.05, -0.28, 3.3, 'interior')

@mod('fin_ceramic_vertical', cat='タワー')
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, -0.1, H, 'core')
    glass(m, -W / 2, W / 2, 0.0, H, -0.1, 'glass_main')
    for i in range(int(W / 0.45) + 1):
        x = -W / 2 + i * W / int(W / 0.45)
        m.box(x - 0.05, -0.1, 0.0, x + 0.05, 0.3, H, 'ceramic')

@mod('mech_floor_louver', cat='タワー')
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, -0.08, H, 'core')
    z = 0.05
    while z < H - 0.1:
        m.slat_x(-W / 2, W / 2, 0.1, z, 0.28, 0.02, math.radians(-40), 'alu_main')
        z += 0.14
    for x in (-W / 2, W / 2 - 0.08):
        m.box(x, -0.08, 0, x + 0.08, 0.3, H, 'alu_main')
    m.box(-0.45, 0.2, 0.0, 0.45, 0.24, 2.1, 'steel_gray')

@mod('crown_louver_top', W=3.6, H=7.0, cat='タワー')
def _(m, W, H, rng):
    m.box(-W / 2, -0.2, 0, W / 2, 0.0, 0.3, 'alu_black')
    for i in range(int(W / 0.2)):
        x = -W / 2 + 0.1 + i * 0.2
        m.box(x - 0.025, 0.0, 0.3, x + 0.025, 0.25, 6.7, 'alu_main')
    m.box(-W / 2, -0.2, 6.7, W / 2, 0.3, 7.0, 'alu_black')

@mod('sky_lobby_glass', W=3.6, H=7.0, cat='タワー')
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, -0.1, H, 'core')
    glass(m, -W / 2, W / 2, 0.2, 6.7, -0.1, 'glass_clear')
    for x in (-W / 2, 0, W / 2 - 0.05):
        m.box(x, -0.12, 0.0, x + 0.05, 0.2, H, 'alu_black')
    m.box(-W / 2, -0.12, 6.7, W / 2, 0.3, 7.0, 'alu_black')
    interior(m, -W / 2 + 0.1, W / 2 - 0.1, 0.2, 6.7, -0.4)

@mod('glass_elevator_shaft', W=2.6, H=3.5, cat='オフィス')
def _(m, W, H, rng):
    m.box(-1.3, 0.0, 0.0, 1.3, 0.1, H, 'alu_black')
    for x in (-1.3, 1.25):
        m.box(x, 0.0, 0.0, x + 0.05, 1.6, H, 'alu_black')
    glass(m, -1.25, 1.25, 0.0, H, 1.58, 'glass_clear')
    for s in (-1, 1):
        m.box(s * 1.28 - 0.01, 0.05, 0.0, s * 1.28 + 0.01, 1.58, H, 'glass_clear')
    m.box(-0.5, 0.5, 0.3, 0.5, 1.3, 2.4, 'alu_silver')
    for z in (0.0, H - 0.05):
        m.box(-1.3, 0.0, z, 1.3, 1.6, z + 0.05, 'alu_black')

@mod('curtain_louver_band', cat='オフィス')
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, -0.1, H, 'core')
    glass(m, -W / 2, W / 2, 0.9, 3.2, -0.1, 'glass_main')
    m.box(-W / 2, -0.12, 0.0, W / 2, 0.0, 0.9, 'alu_main')
    z = 0.05
    while z < 0.88:
        m.slat_x(-W / 2, W / 2, 0.14, z, 0.2, 0.015, math.radians(-25), 'alu_silver')
        z += 0.1
    m.box(-W / 2, -0.12, 3.2, W / 2, 0.02, H, 'alu_main')
    for i in range(4):
        m.box(-W / 2 + i * W / 3 - 0.025, -0.12, 0.9, -W / 2 + i * W / 3 + 0.025, 0.06, 3.2, 'alu_black')
    m.box(-W / 2 + 0.05, -0.3, 0.9, W / 2 - 0.05, -0.28, 3.2, 'interior')

@mod('double_skin_panel', cat='オフィス')
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, -0.1, H, 'core')
    glass(m, -W / 2, W / 2, 0.9, 3.2, -0.1, 'glass_main')
    m.box(-W / 2, -0.12, 0.0, W / 2, 0.0, 0.9, 'alu_main')
    m.box(-W / 2, 0.0, 0.0, W / 2, 0.9, 0.05, 'steel_gray')
    glass(m, -W / 2, W / 2, 0.0, H, 0.9, 'glass_clear')
    for x in (-W / 2, W / 2 - 0.04):
        m.box(x, 0.0, 0.0, x + 0.04, 0.92, H, 'alu_black')
    for z in (0.0, H - 0.06):
        m.box(-W / 2, 0.88, z, W / 2, 0.94, z + 0.06, 'alu_black')
    m.box(-W / 2 + 0.05, -0.3, 0.9, W / 2 - 0.05, -0.28, 3.2, 'interior')

@mod('x_brace_ext', cat='オフィス')
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, -0.1, H, 'core')
    glass(m, -W / 2, W / 2, 0.1, H - 0.1, -0.1, 'glass_clear')
    brace(m, -W / 2 + 0.1, 0.0, W / 2 - 0.1, H, 0.12, 0.3, 0.14, 'steel_white')
    brace(m, W / 2 - 0.1, 0.0, -W / 2 + 0.1, H, 0.12, 0.3, 0.14, 'steel_white')
    for x in (-W / 2, W / 2 - 0.2):
        m.box(x, 0.1, 0.0, x + 0.2, 0.34, H, 'steel_white')
    m.box(-W / 2, 0.1, 0.0, W / 2, 0.34, 0.2, 'steel_white')

@mod('pk_slot_open', cat='駐車場')
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, 0.0, 0.5, 'rc_concrete')
    m.box(-W / 2, -T, 3.1, W / 2, 0.0, H, 'rc_concrete')
    m.box(-W / 2, -2.0, 0.0, W / 2, -T, 0.06, 'rc_concrete')
    m.box(-W / 2, -2.0, 3.0, W / 2, -T, 3.1, 'rc_concrete')
    m.box(-W / 2, -2.0, 0.06, W / 2, -1.95, 3.0, 'core')
    for x in (-1.2, 1.2):
        m.box(x - 0.45, -0.7, 0.06, x + 0.45, -0.58, 0.18, 'paint_white')
    for x in (-W / 2 + 0.05, W / 2 - 0.05):
        m.box(x - 0.1, -T, 0, x + 0.1, 0.0, H, 'rc_concrete')
    for z in (0.7, 0.95, 1.2):
        m.cyl(-W / 2, -0.06, z, 0.006, W, 'x', 'steel_galv', 4)
    m.box(-W / 2, -1.0, 3.0, W / 2, -0.9, 3.05, 'led_white')

@mod('pk_slot_mesh', cat='駐車場')
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, 0.0, 0.4, 'rc_concrete')
    m.box(-W / 2, -T, 3.2, W / 2, 0.0, H, 'rc_concrete')
    n, k = (int(W / 0.04), int(2.8 / 0.04))
    for i in range(n + 1):
        m.box(-W / 2 + i * W / n - 0.004, 0.01, 0.4, -W / 2 + i * W / n + 0.004, 0.03, 3.2, 'alu_silver')
    for j in range(k + 1):
        m.box(-W / 2, 0.03, 0.4 + j * 2.8 / k - 0.004, W / 2, 0.05, 0.4 + j * 2.8 / k + 0.004, 'alu_silver')
    m.box(-W / 2, -1.5, 0.0, W / 2, -T, 0.05, 'rc_concrete')

@mod('pk_louver_panel', cat='駐車場')
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, -0.05, H, 'core')
    z = 0.1
    while z < H - 0.1:
        m.slat_x(-W / 2, W / 2, 0.1, z, 0.22, 0.012, math.radians(-45), 'alu_silver')
        z += 0.12
    for x in (-W / 2, W / 2 - 0.05):
        m.box(x, 0.0, 0.0, x + 0.05, 0.25, H, 'alu_black')

@mod('pk_ramp_face', cat='駐車場')
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, 0.0, 0.1, 'rc_concrete')
    _prism(m, [(0.3, -1.8), (1.9, 1.8), (2.15, 1.8), (0.55, -1.8)], 'y', -2.4, -0.05, 'rc_concrete')
    _prism(m, [(1.0, -1.8), (2.6, 1.8), (2.7, 1.8), (1.1, -1.8)], 'y', -0.3, -0.05, 'rc_concrete')
    m.box(-W / 2, -T, 0, -W / 2 + 0.2, 0.0, H, 'rc_concrete')
    m.box(W / 2 - 0.2, -T, 0, W / 2, 0.0, H, 'rc_concrete')
    m.box(-W / 2, -T, 1.9, W / 2, 0.0, H, 'rc_concrete')
    m.box(-W / 2, -0.2, 2.0, W / 2, 0.0, 2.1, 'steel_galv')

@mod('pk_entry_gate', W=6.0, H=3.0, cat='駐車場')
def _(m, W, H, rng):
    m.box(-0.6, 1.0, 0.0, 0.6, 2.2, 2.3, 'ac_white')
    m.box(-0.5, 2.2, 1.0, 0.5, 2.22, 2.0, 'glass_clear')
    m.box(-0.7, 0.9, 2.3, 0.7, 2.3, 2.4, 'alu_main')
    m.box(1.8, 1.4, 0.0, 2.1, 1.7, 1.1, 'steel_gray')
    m.box(1.0, 1.55, 1.0, 2.1, 1.6, 1.08, 'paint_white')
    for i in range(5):
        m.box(1.1 + i * 0.2, 1.55, 1.0, 1.2 + i * 0.2, 1.6, 1.08, 'sign_red')
    m.box(-3.0, 0.0, 0.0, 3.0, 4.0, 0.03, 'asphalt')

@mod('wh_dock_shelter', W=4.0, H=4.2, cat='倉庫')
def _(m, W, H, rng):
    m.box(-2.0, 0.0, 0.0, -1.7, 1.2, 4.2, 'steel_gray')
    m.box(1.7, 0.0, 0.0, 2.0, 1.2, 4.2, 'steel_gray')
    m.box(-2.0, 0.0, 3.9, 2.0, 1.2, 4.2, 'steel_gray')
    for i in range(5):
        y = 0.2 + i * 0.2
        m.box(-1.7, y, 0.0, -1.5, y + 0.12, 3.9, 'rubber')
        m.box(1.5, y, 0.0, 1.7, y + 0.12, 3.9, 'rubber')
        m.box(-1.5, y, 3.7, 1.5, y + 0.12, 3.9, 'rubber')
    m.box(-1.8, 1.2, 0.0, 1.8, 1.45, 1.1, 'rc_concrete')
    m.box(-1.9, 1.3, 0.0, -1.6, 1.5, 1.2, 'rubber')
    m.box(1.6, 1.3, 0.0, 1.9, 1.5, 1.2, 'rubber')

@mod('wh_canopy_dock', W=8.0, H=0.6, cat='倉庫')
def _(m, W, H, rng):
    _prism(m, [(0.0, 0.3), (4.0, 0.1), (4.0, 0.0), (0.0, 0.2)], 'x', -4.0, 4.0, 'roof_metal')
    for x in (-3.9, 0, 3.9):
        m.box(x - 0.08, 3.8, -3.8, x + 0.08, 3.96, 0.1, 'steel_gray')
    m.box(-4.0, 3.9, 0.0, 4.0, 4.0, 0.12, 'steel_gray')

@mod('wh_man_door', H=3.0, cat='倉庫')
def _(m, W, H, rng):
    hole_wall(m, W, H, -0.5, 0.5, 0, 2.1, 'metal_siding')
    interior(m, -0.5, 0.5, 0, 2.1)
    m.box(-0.5, -0.1, 0, 0.5, -0.03, 2.1, 'steel_green')
    m.box(-0.55, -0.2, 0, 0.55, 0.05, 2.15, 'steel_gray')
    m.box(-0.7, 0.0, 2.35, 0.7, 0.6, 2.4, 'steel_gray')
    m.box(-0.8, 0.0, 0.0, 0.8, 1.0, 0.2, 'rc_concrete')
    m.box(-0.2, 0.0, 2.2, 0.2, 0.08, 2.3, 'sign_green')

@mod('wh_high_window_band', cat='倉庫')
def _(m, W, H, rng):
    hole_wall(m, W, H, -W / 2 + 0.2, W / 2 - 0.2, 2.6, 3.2, 'metal_siding')
    interior(m, -W / 2 + 0.2, W / 2 - 0.2, 2.6, 3.2)
    frame(m, -W / 2 + 0.2, W / 2 - 0.2, 2.6, 3.2, 'alu_main', 0.05, 0.08)
    glass(m, -W / 2 + 0.25, W / 2 - 0.25, 2.65, 3.15)
    for x in (-1.2, 0, 1.2):
        m.box(x - 0.025, -0.17, 2.6, x + 0.025, -0.07, 3.2, 'alu_main')

@mod('wh_roof_monitor', W=8.0, H=1.4, cat='倉庫')
def _(m, W, H, rng):
    m.box(-4.0, -1.0, 0.0, 4.0, 1.0, 0.8, 'roof_metal')
    m.box(-4.0, 0.95, 0.15, 4.0, 1.0, 0.7, 'glass_clear')
    _prism(m, [(-1.2, 0.8), (0.0, 1.4), (1.2, 0.8)], 'x', -4.1, 4.1, 'roof_metal')
    for x in (-4.0, -2.0, 0, 2.0, 4.0):
        m.box(x - 0.03, 0.9, 0.12, x + 0.03, 1.05, 0.75, 'steel_gray')

@mod('pallet_stack', W=1.4, H=1.6, cat='小物')
def _(m, W, H, rng):
    m.box(-0.6, -0.5, 0.0, 0.6, 0.5, 0.12, 'wood')
    for k in range(3):
        m.box(-0.62, -0.52, 0.12 + k * 0.45, 0.62, 0.52, 0.55 + k * 0.45, 'paint_main')
        for i in range(3):
            m.box(-0.62 + i * 0.41, -0.53, 0.14 + k * 0.45, -0.24 + i * 0.41, -0.52, 0.53 + k * 0.45, 'paint_white')

@mod('mall_atrium_glass', W=3.6, H=7.0, cat='商業施設')
def _(m, W, H, rng):
    m.box(-W / 2, -T, 0, W / 2, -0.1, H, 'core')
    glass(m, -W / 2, W / 2, 0.2, 6.6, -0.1, 'glass_clear')
    for x in (-W / 2, 0, W / 2 - 0.06):
        m.box(x, -0.12, 0.0, x + 0.06, 0.3, H, 'steel_white')
    for z in (3.5, 6.6):
        m.box(-W / 2, -0.12, z, W / 2, 0.3, z + 0.08, 'steel_white')
    for i in range(7):
        z = 0.6 + i * 0.9
        m.box(-W / 2, -0.1, z, W / 2, 0.02, z + 0.02, 'alu_silver')
    m.box(-W / 2, -0.2, 6.9, W / 2, 1.2, 7.0, 'alu_main')
    interior(m, -W / 2 + 0.1, W / 2 - 0.1, 0.2, 6.6, -0.5)

@mod('mall_sign_tower', W=3.0, H=14.0, cat='商業施設')
def _(m, W, H, rng):
    m.box(-0.6, -0.6, 0.0, 0.6, 0.6, 0.5, 'rc_concrete')
    m.box(-0.5, -0.3, 0.5, 0.5, 0.3, 13.5, 'alu_black')
    for z in (2.0, 6.0, 10.0):
        m.box(-0.45, 0.3, z, 0.45, 0.34, z + 3.5, 'sign_blue')
        m.box(-0.3, 0.34, z + 0.4, 0.3, 0.345, z + 3.1, 'sign_white')
        m.box(-0.45, -0.34, z, 0.45, -0.3, z + 3.5, 'sign_red')
    m.box(-0.55, -0.35, 13.5, 0.55, 0.35, 14.0, 'alu_black')

@mod('escalator_tube', W=3.6, H=9.0, cat='商業施設')
def _(m, W, H, rng):
    L = 14.0
    ang = math.atan2(8.0, L)
    for x in (-0.55, 0.55):
        _prism(m, [(1.0, 0.0), (13.0, 8.0), (13.0, 8.5), (1.0, 0.5)], 'x', x - 0.03, x + 0.03, 'steel_gray')
    for x in (-0.65, 0.65):
        _prism(m, [(1.0, 0.5), (13.0, 8.5), (13.0, 9.5), (1.0, 1.5)], 'x', x - 0.01, x + 0.01, 'glass_clear')
    _prism(m, [(1.0, 0.5), (13.0, 8.5), (13.0, 8.6), (1.0, 0.6)], 'x', -0.6, 0.6, 'alu_silver')
    for k in range(6):
        t = k / 5
    for y in (1.0, 13.0):
        m.box(-0.8, y - 0.1, 0.0 if y < 5 else 8.0, 0.8, y + 0.1, 0.1 if y < 5 else 8.1, 'steel_gray')

@mod('deck_wood_rail', cat='商業施設')
def _(m, W, H, rng):
    for i in range(int(W / 0.14)):
        m.box(-W / 2 + i * 0.14 + 0.005, 0.0, 0.0, -W / 2 + (i + 1) * 0.14 - 0.005, 3.0, 0.1, 'wood')
    for x in (-W / 2 + 0.05, 0, W / 2 - 0.05):
        m.box(x - 0.05, 2.95, 0.1, x + 0.05, 3.05, 1.1, 'wood')
    for z in (0.55, 1.05):
        m.box(-W / 2, 2.97, z, W / 2, 3.03, z + 0.05, 'wood')
    m.box(-W / 2, 2.93, 1.1, W / 2, 3.07, 1.16, 'wood')

@mod('flag_poles_3', W=4.0, H=8.0, cat='商業施設')
def _(m, W, H, rng):
    for i, x in enumerate((-1.5, 0.0, 1.5)):
        m.cyl(x, 0, 0, 0.05, 8.0, 'z', 'steel_white', 10)
        m.cyl(x, 0, 8.0, 0.07, 0.07, 'z', 'alu_silver', 10)
        m.box(x + 0.03, -0.01, 6.2, x + 1.2, 0.01, 7.8, ('fabric', 'sign_white', 'sign_blue')[i])

@mod('roof_helipad', W=12.0, H=0.5, cat='屋上')
def _(m, W, H, rng):
    m.cyl(0, 0, 0, 6.0, 0.2, 'z', 'paint_dark', 40)
    m.tube(0, 0, 0.2, 5.0, 4.8, 0.01, 'z', 'paint_white', 40)
    for x0, y0, x1, y1 in ((-1.5, -2.2, -1.0, 2.2), (1.0, -2.2, 1.5, 2.2), (-1.0, -0.25, 1.0, 0.25)):
        m.box(x0, y0, 0.2, x1, y1, 0.215, 'paint_white')
    for i in range(16):
        a = i * math.pi / 8
        m.cyl(5.8 * math.cos(a), 5.8 * math.sin(a), 0.2, 0.08, 0.15, 'z', 'sign_yellow', 8)

@mod('roof_machine_room', W=6.0, H=3.4, cat='屋上')
def _(m, W, H, rng):
    m.box(-3.0, -2.0, 0.0, 3.0, 2.0, 3.0, 'paint_main')
    for i in range(14):
        m.box(-2.6, 2.0, 0.6 + i * 0.12, 0.8, 2.04, 0.64 + i * 0.12, 'alu_silver')
    m.box(1.2, 2.0, 0.0, 2.2, 2.05, 2.1, 'steel_gray')
    m.box(-3.1, -2.1, 3.0, 3.1, 2.1, 3.12, 'alu_silver')
    for x in (-1.5, 0.0, 1.5):
        m.cyl(x, 0, 3.12, 0.25, 0.3, 'z', 'steel_galv', 14)

@mod('water_tank_sq', W=2.6, H=3.0, cat='屋上')
def _(m, W, H, rng):
    for x in (-1.1, 1.1):
        for y in (-0.8, 0.8):
            m.box(x - 0.08, y - 0.08, 0, x + 0.08, y + 0.08, 0.9, 'steel_gray')
    m.box(-1.3, -1.0, 0.9, 1.3, 1.0, 0.98, 'steel_gray')
    m.box(-1.2, -0.9, 0.98, 1.2, 0.9, 2.8, 'paint_white')
    for i in range(1, 4):
        m.box(-1.2 + i * 0.6 - 0.01, -0.91, 0.98, -1.2 + i * 0.6 + 0.01, -0.9, 2.8, 'steel_white')
    for x in (1.25, 1.55):
        m.box(x, 0.2, 0.0, x + 0.03, 0.24, 2.8, 'steel_galv')
    for z in range(1, 12):
        m.box(1.25, 0.2, z * 0.23, 1.58, 0.24, z * 0.23 + 0.025, 'steel_galv')

@mod('roof_billboard', W=6.0, H=4.0, cat='屋上')
def _(m, W, H, rng):
    for x in (-2.2, 2.2):
        m.box(x - 0.1, -0.2, 0, x + 0.1, 0.2, 3.0, 'steel_gray')
    m.box(-3.0, -0.15, 1.8, 3.0, 0.15, 4.0, 'alu_black')
    m.box(-2.9, 0.15, 1.9, 2.9, 0.16, 3.9, 'sign_blue')
    m.box(-2.2, 0.16, 2.4, 2.2, 0.165, 3.4, 'sign_white')
    for x in (-2.8, 0, 2.8):
        m.box(x - 0.05, 0.16, 3.9, x + 0.05, 0.5, 4.1, 'steel_gray')
        m.box(x - 0.15, 0.4, 4.05, x + 0.15, 0.6, 4.1, 'led_white')

@mod('roof_telecom_cluster', W=3.0, H=6.0, cat='屋上')
def _(m, W, H, rng):
    m.cyl(0, 0, 0, 0.06, 6.0, 'z', 'steel_galv', 10)
    for k in range(3):
        a = k * 2 * math.pi / 3
        for z in (4.8, 5.5):
            q = type(m)()
            q.box(-0.12, 0.08, 0, 0.12, 0.2, 1.3, 'ac_white')
            m.add(q.transformed(a, 0, 0, z - 0.65))
    d = type(m)()
    d.cyl(0, 0.15, 3.0, 0.4, 0.06, 'y', 'ac_white', 18)
    d.cyl(0, 0.05, 3.0, 0.03, 0.15, 'y', 'steel_gray', 6)
    m.add(d.transformed(0.7, 0, 0, 0))
    m.box(-0.8, -1.2, 0.0, -0.2, -0.7, 0.9, 'steel_white')

@mod('exhaust_stack_group', W=2.0, H=4.0, cat='屋上')
def _(m, W, H, rng):
    for i, (x, y, h, r) in enumerate(((-0.6, 0.0, 4.0, 0.22), (0.1, 0.3, 3.2, 0.18), (0.7, -0.2, 3.6, 0.2))):
        m.cyl(x, y, 0, r, h, 'z', 'steel_galv', 16)
        m.cyl(x, y, h, r * 1.7, 0.05, 'z', 'steel_galv', 16)
        m.cyl(x, y, h - 0.4, r * 0.3, 0.4, 'z', 'steel_gray', 6)
        m.tube(x, y, 1.0, r + 0.02, r, 0.06, 'z', 'steel_gray', 16)

@mod('roof_planter_row', W=3.6, H=1.2, cat='屋上')
def _(m, W, H, rng):
    m.box(-1.8, -0.4, 0.0, 1.8, 0.4, 0.45, 'ceramic')
    for i in range(9):
        x = -1.6 + i * 0.4
        m.box(x - 0.17, -0.3, 0.45, x + 0.17, 0.3, 0.45 + 0.4 + i * 37 % 5 * 0.05, 'plant')

@mod('roof_dish_pair', W=2.0, H=1.5, cat='屋上')
def _(m, W, H, rng):
    for x, r in ((-0.6, 0.5), (0.7, 0.35)):
        m.cyl(x, 0, 0, 0.05, 1.0, 'z', 'steel_galv', 8)
        d = type(m)()
        d.cyl(0, 0, 0, r, 0.05, 'y', 'ac_white', 20)
        d.box(-0.03, -0.3, -0.03, 0.03, 0.0, 0.03, 'steel_gray')
        m.add(d.transformed(0.3 if x < 0 else -0.4, x, 0, 1.2))

@mod('vending_machine', W=1.0, H=1.8, cat='小物')
def _(m, W, H, rng):
    body = rng.choice(['vend_red', 'vend_blue', 'vend_white'])
    m.box(-0.5, 0.0, 0.0, 0.5, 0.75, 1.8, body)
    m.box(-0.45, 0.75, 0.55, 0.15, 0.78, 1.7, 'vend_window')
    for i in range(6):
        for j in range(3):
            m.box(-0.42 + j * 0.19, 0.78, 0.6 + i * 0.17, -0.3 + j * 0.19, 0.795, 0.7 + i * 0.17, ('sign_red', 'sign_blue', 'sign_yellow', 'paint_white')[(i + j) % 4])
    m.box(0.2, 0.75, 0.6, 0.45, 0.78, 1.55, 'alu_black')
    m.box(-0.4, 0.75, 0.1, 0.2, 0.78, 0.4, 'alu_black')
    m.box(0.25, 0.78, 0.9, 0.4, 0.8, 1.0, 'steel_galv')

@mod('vending_double', W=2.0, H=1.8, cat='小物')
def _(m, W, H, rng):
    for k, body in enumerate(('vend_red', 'vend_white')):
        u = type(m)()
        u.box(-0.5, 0.0, 0.0, 0.5, 0.75, 1.8, body)
        u.box(-0.45, 0.75, 0.55, 0.15, 0.78, 1.7, 'vend_window')
        u.box(0.2, 0.75, 0.6, 0.45, 0.78, 1.55, 'alu_black')
        m.add(u, -0.5 + k * 1.0, 0, 0)

@mod('bldg_vending_corner', W=4.0, H=2.8, cat='小物建物')
def _(m, W, H, rng):
    for i, k in enumerate(('vend_red', 'vend_blue', 'vend_white')):
        u = type(m)()
        u.box(-0.5, 0.0, 0.0, 0.5, 0.75, 1.8, k)
        u.box(-0.45, 0.75, 0.55, 0.15, 0.78, 1.7, 'vend_window')
        u.box(0.2, 0.75, 0.6, 0.45, 0.78, 1.55, 'alu_black')
        m.add(u, -1.1 + i * 1.1, 0.4, 0.0)
    m.box(-2.0, 0.0, 2.6, 2.0, 1.8, 2.7, 'alu_main')
    for x in (-1.95, 1.95):
        m.box(x - 0.05, 1.7, 0.0, x + 0.05, 1.8, 2.6, 'steel_gray')
    m.box(-2.0, 0.0, 0.0, 2.0, 1.8, 0.03, 'ground_slab')
    m.box(-1.2, 1.2, 2.55, 1.2, 1.35, 2.6, 'led_white')

@mod('bldg_trash_enclosure', W=3.0, H=1.8, cat='小物建物')
def _(m, W, H, rng):
    m.box(-1.5, -0.1, 0.0, 1.5, 0.1, 1.6, 'rc_concrete')
    for s in (-1, 1):
        m.box(s * 1.45 - 0.07, 0.1, 0.0, s * 1.45 + 0.07, 1.4, 1.6, 'rc_concrete')
    for i in range(12):
        m.box(-1.3 + i * 0.22, 1.35, 0.0, -1.3 + i * 0.22 + 0.02, 1.4, 1.6, 'steel_galv')
    m.box(-1.4, 1.35, 1.5, 1.4, 1.42, 1.58, 'steel_galv')
    for i, (x, y) in enumerate(((-0.8, 0.5), (-0.3, 0.8), (0.4, 0.4), (0.8, 0.9))):
        m.box(x - 0.2, y - 0.2, 0.0, x + 0.2, y + 0.2, 0.5, 'plastic_gray' if i % 2 else 'paint_white')
    m.box(-1.5, 0.1, 0.0, 1.5, 1.4, 0.02, 'ground_slab')

@mod('bldg_bike_shed', W=5.0, H=2.6, cat='小物建物')
def _(m, W, H, rng):
    for x in (-2.4, 2.4):
        for y in (0.0, 2.0):
            m.box(x - 0.05, y - 0.05, 0.0, x + 0.05, y + 0.05, 2.5, 'steel_gray')
    _prism(m, [(0.0, 2.5), (2.2, 2.8), (2.2, 2.75), (0.0, 2.45)], 'x', -2.6, 2.6, 'roof_metal')
    for i in range(8):
        x = -2.1 + i * 0.6
        m.box(x - 0.01, 0.2, 0.0, x + 0.01, 1.8, 0.35, 'steel_galv')
        if rng.random() < 0.8:
            for yy in (0.45, 1.4):
                m.tube(x, yy, 0.35, 0.34, 0.31, 0.03, 'x', 'rubber', 14)
            m.box(x - 0.015, 0.45, 0.35, x + 0.015, 1.4, 0.38, rng.choice(['steel_gray', 'alu_main', 'paint_dark']))
            m.box(x - 0.015, 0.95, 0.38, x + 0.015, 1.0, 0.95, 'steel_gray')
            m.box(x - 0.09, 0.9, 0.95, x + 0.09, 1.1, 0.99, 'rubber')
    m.box(-2.6, 0.0, 0.0, 2.6, 2.2, 0.03, 'ground_slab')

@mod('bldg_bus_shelter', W=3.6, H=2.8, cat='小物建物')
def _(m, W, H, rng):
    m.box(-1.8, -0.5, 2.5, 1.8, 0.7, 2.6, 'alu_main')
    for x in (-1.75, 1.75):
        m.box(x - 0.04, -0.5, 0.0, x + 0.04, -0.42, 2.5, 'alu_black')
    glass(m, -1.7, 1.7, 0.4, 2.45, -0.46, 'glass_clear')
    m.box(-1.3, -0.4, 0.45, 1.3, 0.0, 0.5, 'wood')
    m.box(1.4, 0.8, 0.0, 1.5, 0.9, 2.5, 'steel_galv')
    m.box(1.3, 0.78, 1.9, 1.6, 0.8, 2.3, 'sign_blue')
    m.box(-1.8, -0.5, 0.0, 1.8, 0.7, 0.03, 'ground_slab')

@mod('bldg_kiosk', W=3.0, H=3.0, cat='小物建物')
def _(m, W, H, rng):
    m.box(-1.5, -1.2, 0.0, 1.5, 1.2, 2.6, 'paint_main')
    m.box(-1.6, -1.3, 2.6, 1.6, 1.3, 2.7, 'alu_main')
    m.box(-1.1, 1.2, 1.0, 1.1, 1.23, 2.0, 'glass_clear')
    m.box(-1.15, 1.2, 0.95, 1.15, 1.45, 1.05, 'alu_silver')
    _prism(m, [(1.2, 2.0), (2.0, 1.7), (2.0, 1.65), (1.2, 1.95)], 'x', -1.3, 1.3, 'fabric')
    m.box(-1.2, 1.22, 2.3, 1.2, 1.25, 2.55, 'sign_red')
    m.box(-0.3, -1.25, 0.0, 0.3, -1.2, 2.0, 'steel_gray')

@mod('bldg_cubicle', W=3.0, H=2.6, cat='小物建物')
def _(m, W, H, rng):
    m.box(-1.2, -0.7, 0.0, 1.2, 0.7, 2.2, 'steel_white')
    for i in range(10):
        m.box(-1.0, 0.7, 1.0 + i * 0.1, -0.2, 0.72, 1.04 + i * 0.1, 'steel_gray')
    m.box(0.2, 0.7, 0.3, 1.1, 0.72, 1.8, 'steel_white')
    m.box(0.8, 0.72, 1.0, 1.0, 0.74, 1.1, 'sign_yellow')
    for x in (-1.5, 1.5):
        m.box(x - 0.03, -1.0, 0, x + 0.03, 1.0, 1.4, 'steel_galv')
    m.box(-1.5, 0.95, 0.0, 1.5, 1.0, 1.4, 'steel_galv')

@mod('bldg_toilet', W=4.0, H=3.2, cat='小物建物')
def _(m, W, H, rng):
    m.box(-2.0, -1.5, 0.0, 2.0, 1.5, 2.6, 'rc_concrete')
    m.box(-2.2, -1.7, 2.6, 2.2, 1.7, 2.75, 'roof_metal')
    for x, c in ((-0.9, 'sign_blue'), (0.9, 'sign_red')):
        m.box(x - 0.45, 1.5, 0.0, x + 0.45, 1.55, 2.1, 'steel_gray')
        m.box(x - 0.2, 1.55, 1.5, x + 0.2, 1.57, 1.9, c)
    for i in range(8):
        m.box(-1.9, 1.5, 2.15 + i * 0.05, -1.3, 1.52, 2.17 + i * 0.05, 'steel_gray')

@mod('bldg_hut', W=4.0, H=3.2, cat='小物建物')
def _(m, W, H, rng):
    m.box(-2.0, -1.5, 0.0, 2.0, 1.5, 2.2, 'metal_siding')
    _prism(m, [(-1.7, 2.2), (0.0, 3.0), (1.7, 2.2)], 'x', -2.15, 2.15, 'roof_metal')
    m.box(-0.5, 1.5, 0.0, 0.5, 1.55, 1.9, 'steel_gray')

@mod('bldg_substation', W=6.0, H=4.0, cat='小物建物')
def _(m, W, H, rng):
    m.box(-3.0, -2.0, 0.0, 3.0, 2.0, 3.6, 'rc_concrete')
    m.box(-1.0, 2.0, 0.0, 1.0, 2.04, 2.8, 'steel_galv')
    for i in range(14):
        m.box(1.6, 2.0, 0.6 + i * 0.12, 2.8, 2.03, 0.65 + i * 0.12, 'steel_gray')
    m.box(-3.1, -2.1, 3.6, 3.1, 2.1, 3.7, 'paint_white')

@mod('torii_small', W=3.2, H=3.6, cat='小物')
def _(m, W, H, rng):
    for x in (-1.1, 1.1):
        m.cyl(x, 0, 0, 0.17, 3.0, 'z', 'sign_red', 14)
        m.box(x - 0.24, -0.24, 0.0, x + 0.24, 0.24, 0.25, 'stone_main')
    m.box(-1.5, -0.14, 3.0, 1.5, 0.14, 3.18, 'paint_dark')
    m.box(-1.7, -0.2, 3.18, 1.7, 0.2, 3.3, 'paint_dark')
    m.box(-1.3, -0.1, 2.5, 1.3, 0.1, 2.65, 'sign_red')
    m.box(-0.2, -0.12, 2.65, 0.2, 0.12, 3.0, 'paint_dark')

@mod('stone_lantern', W=0.6, H=2.0, cat='小物')
def _(m, W, H, rng):
    m.box(-0.3, -0.3, 0.0, 0.3, 0.3, 0.15, 'stone_main')
    m.cyl(0, 0, 0.15, 0.1, 0.7, 'z', 'stone_main', 8)
    m.box(-0.25, -0.25, 0.85, 0.25, 0.25, 0.95, 'stone_main')
    m.box(-0.14, -0.14, 0.95, 0.14, 0.14, 1.3, 'stone_main')
    m.box(-0.35, -0.35, 1.3, 0.35, 0.35, 1.45, 'stone_main')
    m.cyl(0, 0, 1.45, 0.12, 0.2, 'z', 'stone_main', 8)

@mod('gate_slide', W=3.6, H=1.3, cat='小物')
def _(m, W, H, rng):
    for x in (-1.8, 1.8):
        m.box(x - 0.15, -0.15, 0.0, x + 0.15, 0.15, 1.4, 'ceramic')
    for i in range(int(3.3 / 0.08)):
        m.box(-1.65 + i * 0.08, -0.02, 0.1, -1.63 + i * 0.08, 0.02, 1.2, 'alu_main')
    for z in (0.12, 0.6, 1.2):
        m.box(-1.65, -0.03, z, 1.65, 0.03, z + 0.05, 'alu_main')

@mod('fence_block_span', W=3.6, H=1.8, cat='小物')
def _(m, W, H, rng):
    m.box(-1.8, -0.1, 0.0, 1.8, 0.1, 0.6, 'rc_concrete')
    for i in range(18):
        m.box(-1.8 + i * 0.2 + 0.004, -0.1, 0.0, -1.8 + (i + 1) * 0.2 - 0.004, 0.1, 0.6, 'rc_concrete')
    for x in (-1.75, 1.75):
        m.box(x - 0.1, -0.12, 0.0, x + 0.1, 0.12, 1.8, 'rc_concrete')
    for i in range(30):
        m.box(-1.65 + i * 0.11, -0.01, 0.6, -1.63 + i * 0.11, 0.01, 1.7, 'steel_galv')
    m.box(-1.8, -0.02, 1.7, 1.8, 0.02, 1.75, 'steel_galv')

@mod('hedge_planter', W=3.6, H=1.2, cat='小物')
def _(m, W, H, rng):
    m.box(-1.8, -0.4, 0.0, 1.8, 0.4, 0.25, 'stone_main')
    for i in range(12):
        m.box(-1.7 + i * 0.3, -0.3, 0.25, -1.4 + i * 0.3, 0.3, 0.9 + i * 53 % 7 * 0.03, 'plant')

@mod('mailbox_post', W=0.5, H=1.3, cat='小物')
def _(m, W, H, rng):
    m.box(-0.25, -0.2, 0.0, 0.25, 0.2, 1.3, 'ceramic')
    m.box(-0.2, 0.2, 0.8, 0.2, 0.22, 1.1, 'alu_black')
    m.box(-0.18, 0.2, 0.55, 0.18, 0.22, 0.7, 'sign_white')
    m.box(-0.06, 0.2, 0.35, 0.06, 0.23, 0.48, 'steel_white')

@mod('house_entrance_porch', H=3.0, cat='住宅')
def _(m, W, H, rng):
    hole_wall(m, W, H, -0.8, 0.8, 0.0, 2.1, 'spray_main')
    interior(m, -0.8, 0.8, 0.0, 2.1)
    frame(m, -0.8, 0.8, 0.0, 2.1, 'alu_bronze', 0.06, 0.09)
    m.box(-0.75, -0.1, 0.05, 0.0, -0.06, 2.05, 'wood')
    m.box(0.0, -0.13, 0.05, 0.75, -0.09, 2.05, 'wood')
    m.box(-1.0, 0.0, 2.3, 1.0, 0.9, 2.38, 'alu_bronze')
    m.cyl(-1.0, 0.1, 1.8, 0.07, 0.12, 'y', 'sign_white', 10)
    m.box(-1.1, 0.0, 0.0, 1.1, 1.0, 0.15, 'stone_main')

@mod('house_garage_shutter', cat='住宅')
def _(m, W, H, rng):
    hole_wall(m, W, H, -1.5, 1.5, 0.0, 2.4, 'spray_main')
    interior(m, -1.5, 1.5, 0.0, 2.4)
    z = 0.0
    while z < 2.35:
        m.box(-1.5, -0.12, z, 1.5, -0.09, z + 0.07, 'steel_white')
        z += 0.08
    m.box(-1.6, -0.22, 2.4, 1.6, 0.15, 2.75, 'steel_white')
    m.box(-1.5, 0.0, 0.0, 1.5, 3.0, 0.02, 'ground_slab')
for _k in ('sliding2', 'sliding4', 'fix', 'casement', 'high'):
    for _c in ('bronze', 'black', 'white'):
        _fm = {'bronze': 'alu_bronze', 'black': 'alu_black', 'white': 'steel_white'}[_c]
        for _w in ('spray', 'alc', 'tile'):
            _wm = {'spray': 'spray_main', 'alc': 'alc', 'tile': 'tile_main'}[_w]
            reg(f'win_{_k}_{_c}_{_w}', (lambda k, f, w_: lambda m, W, H, r: _win(m, W, H, r, k, fm=f, wall=w_, hood=k in ('sliding2', 'sliding4') and w_ != 'alc'))(_k, _fm, _wm), cat='窓バリエーション')
