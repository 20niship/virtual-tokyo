"""最終フェーズの汎用モジュール: 乗用車/タクシー/トラック/バス/二輪/自転車、歩行者(低ポリ)。色違いは材質違いのバリエーションで量産。
座標系(車両): 原点=車体中心の地面, +x=前進方向, y=幅, z=上。歩行者: 原点=足元, +y=顔の向き。"""
import math

from .registry import reg

PAINT = {"white": "car_paint_white", "black": "car_paint_black", "silver": "car_paint_silver", "gray": "car_paint_gray", "red": "car_paint_red",
         "blue": "car_paint_blue", "beige": "car_paint_beige", "green": "car_paint_green"}


def _ring(w, rw, zb, zbelt, zroof, ztop_w=None):
    """断面(y,z)のCCW輪郭: 下左→下右→ベルト右→ルーフ右→ルーフ左→ベルト左"""
    return [(-w / 2, zb), (w / 2, zb), (w / 2, zbelt), (rw / 2, zroof), (-rw / 2, zroof), (-w / 2, zbelt)]


def vehicle(m, L, W, secs, paint, wheel_r=0.32, wb=None, track=None, hood_x=None, kind="car"):
    """secs: 後→前の断面 [(x, rw, zb, zbelt, zroof, cabin)] を結んで車体を作る(cabin=Trueでガラス面)。"""
    rings = []
    for (x, rw, zb, zbelt, zroof, cabin) in secs:
        rings.append((x, _ring(W, rw, zb, zbelt, zroof), cabin))
    n = len(rings[0][1])
    # 側面/屋根/下面
    for (x0, r0, c0), (x1, r1, c1) in zip(rings, rings[1:]):
        cabin = c0 and c1
        for k in range(n):
            k2 = (k + 1) % n
            q = [(x0, r0[k][0], r0[k][1]), (x0, r0[k2][0], r0[k2][1]), (x1, r1[k2][0], r1[k2][1]), (x1, r1[k][0], r1[k][1])]
            # k: 0=下辺(底) 1=右側面下 2=右窓 3=屋根 4=左窓 5=左側面下
            if k == 0:
                mat = "car_under"
            elif k in (2, 4):
                mat = "car_glass" if cabin else paint
            else:
                mat = paint
            c = ((q[0][1] + q[2][1]) / 2, (q[0][2] + q[2][2]) / 2)
            m.oriented(q, (0, c[0] - 0.0, c[1] - 0.8) if k != 0 else (0, 0, -1), mat)
    # 前後の面(フロントノーズ/テール): 輪郭を扇で閉じる
    for (x, r, c), sgn in ((rings[0], -1), (rings[-1], 1)):
        cy = sum(p[0] for p in r) / n
        cz = sum(p[1] for p in r) / n
        for k in range(n):
            k2 = (k + 1) % n
            m.oriented([(x, cy, cz), (x, r[k][0], r[k][1]), (x, r[k2][0], r[k2][1])], (sgn, 0, 0), paint)
    # 車輪
    wb = wb or L * 0.58
    track = track or W - 0.2
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * wb / 2, sy * track / 2
            m.cyl(cx, cy - (0.12 if sy < 0 else 0.0), wheel_r, wheel_r, 0.24, "y", "car_tire", 14)
            m.cyl(cx, cy + (-0.125 if sy < 0 else 0.01), wheel_r, wheel_r * 0.6, 0.0, "y", "car_wheel", 10) if False else \
                m.cyl(cx, cy + (-0.125 if sy < 0 else 0.125), wheel_r, wheel_r * 0.62, 0.012, "y", "car_wheel", 12)
    xf, xr = rings[-1][0], rings[0][0]
    zb = secs[-1][2]
    zl = secs[-1][3] - 0.18
    for sy in (-1, 1):                                  # ヘッドライト/テールランプ
        m.box(xf - 0.02, sy * W * 0.34 - 0.18, zl - 0.06, xf + 0.012, sy * W * 0.34 + 0.18, zl + 0.08, "car_headlight")
        m.box(xr - 0.012, sy * W * 0.36 - 0.17, secs[0][3] - 0.2, xr + 0.02, sy * W * 0.36 + 0.17, secs[0][3] - 0.08, "car_taillight")
    m.box(xf - 0.01, -0.26, zb + 0.18, xf + 0.012, 0.26, zb + 0.3, "car_plate")                # ナンバー
    m.box(xr - 0.012, -0.26, zb + 0.28, xr + 0.01, 0.26, zb + 0.4, "car_plate")
    for sy in (-1, 1):                                                                           # ドアミラー
        m.box(xf - L * 0.3, sy * (W / 2 + 0.1) - 0.02, secs[1][3] + 0.02, xf - L * 0.3 + 0.12, sy * (W / 2 + 0.1) + 0.02, secs[1][3] + 0.14, paint)


# 断面表: (x, ルーフ幅, 底, ベルト, ルーフ, キャビン?)  全長L=2*xmax
def sedan(m, color, taxi=False):
    L, W = 4.7, 1.8
    h = L / 2
    secs = [(-h, 1.5, 0.28, 0.72, 0.8, False), (-h * 0.6, 1.5, 0.28, 0.95, 1.0, False), (-h * 0.42, 1.38, 0.28, 0.98, 1.4, True), (-h * 0.05, 1.42, 0.28, 0.98, 1.45, True),
            (h * 0.28, 1.42, 0.28, 0.98, 1.38, True), (h * 0.42, 1.55, 0.28, 0.9, 0.95, False), (h * 0.75, 1.64, 0.3, 0.82, 0.86, False), (h, 1.55, 0.34, 0.68, 0.72, False)]
    vehicle(m, L, W, secs, "car_paint_taxi" if taxi else PAINT[color], 0.32, 2.7)
    if taxi:
        m.box(-0.15, -0.2, 1.45, 0.15, 0.2, 1.6, "car_taxi_lamp")


def hatch(m, color):
    L, W = 4.0, 1.7
    h = L / 2
    secs = [(-h, 1.5, 0.3, 0.9, 1.1, False), (-h * 0.8, 1.42, 0.3, 0.96, 1.46, True), (-h * 0.2, 1.4, 0.3, 0.95, 1.5, True), (h * 0.18, 1.4, 0.3, 0.96, 1.4, True),
            (h * 0.4, 1.5, 0.3, 0.9, 0.95, False), (h * 0.8, 1.56, 0.3, 0.8, 0.84, False), (h, 1.5, 0.34, 0.66, 0.7, False)]
    vehicle(m, L, W, secs, PAINT[color], 0.3, 2.5)


def suv(m, color):
    L, W = 4.6, 1.85
    h = L / 2
    secs = [(-h, 1.6, 0.3, 1.0, 1.35, False), (-h * 0.92, 1.5, 0.3, 1.1, 1.7, True), (-h * 0.1, 1.5, 0.3, 1.08, 1.72, True), (h * 0.22, 1.48, 0.3, 1.06, 1.6, True),
            (h * 0.44, 1.62, 0.3, 1.0, 1.04, False), (h * 0.85, 1.7, 0.32, 0.92, 0.96, False), (h, 1.6, 0.36, 0.78, 0.82, False)]
    vehicle(m, L, W, secs, PAINT[color], 0.36, 2.7)


def minivan(m, color):
    L, W = 4.7, 1.7
    h = L / 2
    secs = [(-h, 1.5, 0.3, 1.1, 1.8, False), (-h * 0.95, 1.46, 0.3, 1.1, 1.86, True), (h * 0.2, 1.46, 0.3, 1.1, 1.86, True), (h * 0.55, 1.5, 0.3, 1.0, 1.4, True),
            (h * 0.8, 1.6, 0.3, 0.9, 1.0, False), (h, 1.5, 0.34, 0.72, 0.8, False)]
    vehicle(m, L, W, secs, PAINT[color], 0.3, 2.8)


def kei(m, color):
    L, W = 3.4, 1.48
    h = L / 2
    secs = [(-h, 1.3, 0.28, 1.0, 1.55, False), (-h * 0.95, 1.3, 0.28, 1.05, 1.66, True), (h * 0.3, 1.3, 0.28, 1.05, 1.66, True), (h * 0.62, 1.34, 0.28, 0.98, 1.2, True),
            (h * 0.85, 1.42, 0.28, 0.9, 0.96, False), (h, 1.36, 0.3, 0.7, 0.76, False)]
    vehicle(m, L, W, secs, PAINT[color], 0.27, 2.2)


def box_truck(m, paint="car_paint_white", L=6.2, H=3.3):
    W = 2.2
    h = L / 2
    cab = [(h * 0.55, 1.9, 0.5, 1.1, 1.6, True), (h * 0.72, 2.0, 0.5, 1.0, 1.15, False), (h, 1.9, 0.5, 0.9, 0.95, False)]
    vehicle(m, L, W, [(h * 0.5, 2.0, 0.5, 1.1, 1.6, True)] + cab[1:], paint, 0.45, 3.4, 1.9)
    m.box(-h, -W / 2 + 0.05, 0.6, h * 0.45, W / 2 - 0.05, H, paint)                                       # 荷台
    m.box(-h, -W / 2 + 0.05, 0.4, h * 0.45, W / 2 - 0.05, 0.6, "car_under")
    m.box(-h * 0.2, -W / 2 + 0.049, 1.6, h * 0.4, -W / 2 + 0.052, 2.4, "car_paint_blue")                   # 側面ロゴ帯
    m.box(-h * 0.2, W / 2 - 0.052, 1.6, h * 0.4, W / 2 - 0.049, 2.4, "car_paint_blue")
    m.box(-h - 0.02, -W / 2 + 0.2, 0.9, -h, W / 2 - 0.2, 3.0, "steel_galv")                                # 後扉


def bus(m, paint="car_paint_bus"):
    L, W, H = 10.5, 2.5, 3.1
    h = L / 2
    m.box(-h, -W / 2, 0.45, h, W / 2, H, paint)
    for sy in (-1, 1):
        for i in range(8):                                                                                  # 窓
            x = -h + 1.0 + i * 1.1
            m.box(x, sy * (W / 2) - (0.0 if sy > 0 else 0.0) - 0.0 * sy, 1.45, x + 0.95, sy * (W / 2 + 0.01) + (0.0), 2.6, "car_glass") if False else \
                m.box(x, sy * W / 2 - (0.01 if sy < 0 else -0.0), 1.45, x + 0.95, sy * W / 2 + (0.0 if sy < 0 else 0.01), 2.6, "car_glass")
    m.box(h - 0.01, -W / 2 + 0.1, 1.2, h + 0.02, W / 2 - 0.1, 2.8, "car_glass")
    m.box(h - 0.02, -0.7, 2.85, h + 0.02, 0.7, 3.0, "led_white")
    m.box(-h - 0.02, -W / 2 + 0.1, 0.8, -h + 0.0, W / 2 - 0.1, 2.6, "car_glass")
    for sx in (-3.4, 3.4):
        for sy in (-1, 1):
            m.cyl(sx, sy * (W / 2 - 0.1) - (0.14 if sy < 0 else 0.0), 0.5, 0.5, 0.28, "y", "car_tire", 16)
    m.box(-h + 1.6, -W / 2 - 0.005, 0.5, -h + 3.0, -W / 2 + 0.0, 2.6, "car_paint_white") if False else None
    m.box(h * 0.2, -W / 2 - 0.006, 0.45, h * 0.2 + 1.3, -W / 2 + 0.002, 2.9, "car_paint_white")           # 乗車ドア帯
    m.box(-0.8, -0.9, H, 0.9, 0.9, H + 0.25, "steel_gray")                                                 # 屋根上の空調


def motorbike(m):
    for sx in (-0.6, 0.6):
        m.cyl(sx, -0.05, 0.3, 0.3, 0.1, "y", "car_tire", 12)
    m.box(-0.5, -0.12, 0.35, 0.5, 0.12, 0.65, "car_paint_black")
    m.box(-0.1, -0.2, 0.65, 0.5, 0.2, 0.75, "car_under")
    m.box(0.5, -0.3, 0.95, 0.56, 0.3, 1.0, "steel_gray")


def bicycle(m, basket=True):
    for sx in (-0.55, 0.55):
        m.tube(sx, -0.02, 0.33, 0.33, 0.3, 0.04, "y", "car_tire", 20)
    m.box(-0.55, -0.02, 0.32, 0.55, 0.02, 0.35, "steel_gray")
    m.box(-0.1, -0.02, 0.35, 0.05, 0.02, 0.95, "steel_gray")
    m.box(-0.2, -0.05, 0.93, 0.0, 0.05, 0.97, "car_under")
    m.box(0.5, -0.25, 1.0, 0.54, 0.25, 1.04, "steel_gray")
    if basket:
        m.box(0.55, -0.15, 0.85, 0.85, 0.15, 1.1, "steel_galv")


for _c in ("white", "black", "silver", "gray", "red", "blue", "beige"):
    reg(f"car_sedan_{_c}", (lambda c: lambda m, W, H, r: sedan(m, c))(_c), W=4.7, H=1.5, cat="車両")
    reg(f"car_hatch_{_c}", (lambda c: lambda m, W, H, r: hatch(m, c))(_c), W=4.0, H=1.55, cat="車両")
    reg(f"car_suv_{_c}", (lambda c: lambda m, W, H, r: suv(m, c))(_c), W=4.6, H=1.75, cat="車両")
    reg(f"car_minivan_{_c}", (lambda c: lambda m, W, H, r: minivan(m, c))(_c), W=4.7, H=1.9, cat="車両")
    reg(f"car_kei_{_c}", (lambda c: lambda m, W, H, r: kei(m, c))(_c), W=3.4, H=1.7, cat="車両")
reg("car_taxi", lambda m, W, H, r: sedan(m, "black", True), W=4.7, H=1.65, cat="車両")
reg("truck_box_white", lambda m, W, H, r: box_truck(m, "car_paint_white"), W=6.2, H=3.4, cat="車両")
reg("truck_box_silver", lambda m, W, H, r: box_truck(m, "car_paint_silver", 7.5, 3.5), W=7.5, H=3.6, cat="車両")
reg("bus_city", lambda m, W, H, r: bus(m), W=10.5, H=3.4, cat="車両")
reg("motorbike", lambda m, W, H, r: motorbike(m), W=1.9, H=1.1, cat="車両")
reg("bicycle_parked", lambda m, W, H, r: bicycle(m, True), W=1.9, H=1.1, cat="車両")
reg("bicycle_plain", lambda m, W, H, r: bicycle(m, False), W=1.8, H=1.05, cat="車両")


# ---------------- 歩行者(低ポリ) ----------------
CLOTH = ["ped_cloth_navy", "ped_cloth_gray", "ped_cloth_red", "ped_cloth_white", "ped_cloth_green", "ped_cloth_beige", "ped_cloth_black"]


def person(m, top, bottom, walking=False, h=1.7, child=False, bag=False):
    s = 0.6 if child else h / 1.7
    hy = 0.0
    sw = 0.18 if walking else 0.0
    # 脚
    for sx, ph in ((-0.09, sw), (0.09, -sw)):
        m.prism([(0, 0), (0.0, 0.0)], "z", 0, 0, "ped_skin") if False else None
        m.box(sx * s - 0.055 * s, (-0.05 + ph) * s, 0.0, sx * s + 0.055 * s, (0.05 + ph) * s, 0.85 * s, bottom)
        m.box(sx * s - 0.06 * s, (-0.04 + ph) * s, 0.0, sx * s + 0.06 * s, (0.13 + ph) * s, 0.06 * s, "ped_shoe")
    m.box(-0.17 * s, -0.09 * s, 0.82 * s, 0.17 * s, 0.09 * s, 1.35 * s, top)                    # 胴
    m.box(-0.2 * s, -0.1 * s, 1.25 * s, 0.2 * s, 0.1 * s, 1.42 * s, top)                         # 肩
    for sx, ph in ((-0.22, -sw), (0.22, sw)):                                                    # 腕
        m.box(sx * s - 0.04 * s, (-0.05 + ph) * s, 0.8 * s, sx * s + 0.04 * s, (0.05 + ph) * s, 1.38 * s, top)
        m.box(sx * s - 0.035 * s, (-0.04 + ph) * s, 0.72 * s, sx * s + 0.035 * s, (0.04 + ph) * s, 0.82 * s, "ped_skin")
    m.cyl(0, 0, 1.4 * s, 0.045 * s, 0.07 * s, "z", "ped_skin", 8)
    m.cyl(0, 0, 1.46 * s, 0.1 * s, 0.21 * s, "z", "ped_skin", 10)                                # 頭
    m.cyl(0, -0.005 * s, 1.58 * s, 0.105 * s, 0.1 * s, "z", "ped_hair", 10)
    if bag:
        m.box(0.2 * s, -0.12 * s, 0.85 * s, 0.34 * s, 0.14 * s, 1.1 * s, "ped_cloth_black")


for _i, _t in enumerate(CLOTH):
    _b = CLOTH[(_i * 3 + 2) % len(CLOTH)]
    for _w in (False, True):
        reg(f"person_{'walk' if _w else 'stand'}_{_i}", (lambda t, b, w: lambda m, W, H, r: person(m, t, b, w, 1.55 + 0.35 * ((hash(t) % 7) / 7.0), False, w))(_t, _b, _w), W=0.6, H=1.8, cat="人")
def container(m, L, color):
    W, H = 2.44, 2.59
    m.box(-L / 2, -W / 2, 0.0, L / 2, W / 2, H, color)
    n = int(L / 0.12)
    for i in range(n):                                   # 側面の波板リブ
        x = -L / 2 + 0.06 + i * L / n
        m.box(x - 0.02, -W / 2 - 0.02, 0.1, x + 0.02, -W / 2, H - 0.1, color)
        m.box(x - 0.02, W / 2, 0.1, x + 0.02, W / 2 + 0.02, H - 0.1, color)
    m.box(-L / 2, -W / 2, 0, L / 2, W / 2, 0.14, "steel_gray")
    for sy in (-1, 1):
        m.box(L / 2, sy * 0.45 - 0.03, 0.15, L / 2 + 0.03, sy * 0.45 + 0.03, H - 0.15, "steel_galv")   # 扉の施錠棒


for _n, _c in (("blue", "ctn_blue"), ("red", "ctn_red"), ("gray", "ctn_gray"), ("green", "ctn_green"), ("orange", "ctn_orange")):
    reg(f"container_20_{_n}", (lambda c: lambda m, W, H, r: container(m, 6.06, c))(_c), W=6.06, H=2.6, cat="資材")
    reg(f"container_40_{_n}", (lambda c: lambda m, W, H, r: container(m, 12.19, c))(_c), W=12.19, H=2.6, cat="資材")


def construction_fence(m):
    for i in range(2):
        x = -0.95 + i * 1.9
        m.box(x - 0.03, -0.3, 0.0, x + 0.03, 0.3, 0.06, "steel_gray")
        m.cyl(x, 0, 0, 0.025, 1.9, "z", "steel_galv", 8)
    m.box(-0.95, -0.01, 0.1, 0.95, 0.01, 1.8, "fence_sheet")
    for z in (0.1, 1.8):
        m.cyl(-1.0, 0, z, 0.02, 2.0, "x", "steel_galv", 8)


reg("construction_fence_2m", lambda m, W, H, r: construction_fence(m), W=2.0, H=1.9, cat="資材")


def traffic_cone(m):
    m.box(-0.18, -0.18, 0, 0.18, 0.18, 0.03, "rubber")
    m.lathe(0, 0, 0.03, [(0.12, 0), (0.05, 0.62), (0.03, 0.66)], "cone_orange", 12)
    m.cyl(0, 0, 0.3, 0.085, 0.1, "z", "reflector_white", 12)


reg("traffic_cone", lambda m, W, H, r: traffic_cone(m), W=0.4, H=0.7, cat="資材")


def boat(m, L, W, kind):
    prof = [(-L / 2, -W / 2), (L * 0.22, -W / 2), (L / 2, 0), (L * 0.22, W / 2), (-L / 2, W / 2)]
    m.prism(prof, "z", -0.4, 0.9 if kind != "ferry" else 1.2, "boat_hull")
    m.prism([(x * 0.98, y * 0.98) for x, y in prof], "z", 0.9 if kind != "ferry" else 1.2, 0.93 if kind != "ferry" else 1.23, "steel_white")
    if kind == "yacht":
        m.box(-L * 0.3, -W * 0.3, 0.93, L * 0.1, W * 0.3, 2.2, "steel_white")
        m.box(-L * 0.3, -W * 0.3 - 0.005, 1.3, L * 0.1, -W * 0.3 + 0.0, 2.0, "car_glass")
        m.box(-L * 0.3, W * 0.3, 1.3, L * 0.1, W * 0.3 + 0.005, 2.0, "car_glass")
        m.cyl(-L * 0.1, 0, 2.2, 0.05, 6.0, "z", "alu_silver", 8)
    elif kind == "ferry":
        m.box(-L * 0.4, -W * 0.45, 1.23, L * 0.3, W * 0.45, 3.2, "steel_white")
        for sy in (-1, 1):
            m.box(-L * 0.38, sy * W * 0.45 - (0.01 if sy < 0 else 0), 1.7, L * 0.28, sy * W * 0.45 + (0 if sy < 0 else 0.01), 2.9, "car_glass")
        m.box(-L * 0.38, -W * 0.45, 3.2, L * 0.28, W * 0.45, 3.35, "alu_main")
        m.box(-L * 0.1, -W * 0.3, 3.35, L * 0.05, W * 0.3, 4.2, "steel_white")
    else:
        m.box(-L * 0.2, -W * 0.28, 0.93, L * 0.2, W * 0.28, 1.8, "steel_white")
        m.box(-L * 0.2, -W * 0.28 - 0.005, 1.25, L * 0.2, -W * 0.28, 1.7, "car_glass")


reg("boat_yacht", lambda m, W, H, r: boat(m, 11.0, 3.4, "yacht"), W=11.0, H=8.0, cat="船")
reg("boat_ferry", lambda m, W, H, r: boat(m, 28.0, 7.0, "ferry"), W=28.0, H=4.5, cat="船")
reg("boat_small", lambda m, W, H, r: boat(m, 6.5, 2.2, "small"), W=6.5, H=2.0, cat="船")
reg("person_child_0", lambda m, W, H, r: person(m, "ped_cloth_red", "ped_cloth_navy", False, 1.1, True), W=0.4, H=1.1, cat="人")
reg("person_child_1", lambda m, W, H, r: person(m, "ped_cloth_green", "ped_cloth_gray", True, 1.1, True), W=0.4, H=1.1, cat="人")
