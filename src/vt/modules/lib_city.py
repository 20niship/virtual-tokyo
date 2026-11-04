"""最終フェーズの汎用モジュール: 乗用車/タクシー/トラック/バス/二輪/自転車、歩行者(低ポリ)。色違いは材質違いのバリエーションで量産。
座標系(車両): 原点=車体中心の地面, +x=前進方向, y=幅, z=上。歩行者: 原点=足元, +y=顔の向き。"""
import math

from .registry import reg

PAINT = {"white": "car_paint_white", "black": "car_paint_black", "silver": "car_paint_silver", "gray": "car_paint_gray", "red": "car_paint_red",
         "blue": "car_paint_blue", "beige": "car_paint_beige", "green": "car_paint_green"}


def _ring(w, rw, zb, zbelt, zroof):
    """断面(y,z)の10角形輪郭(面取り+ピラー傾斜+ルーフ肩): 底→右下面取り→右側面→右窓→右肩→屋根→左肩→左窓→左側面→左下面取り"""
    dz = zroof - zbelt
    ch = min(0.12, (zbelt - zb) * 0.4)
    zg = zbelt + dz * 0.8
    return [(-w / 2 + 0.1, zb), (w / 2 - 0.1, zb), (w / 2, zb + ch), (w / 2, zbelt), (rw / 2, zg), (rw / 2 - 0.12, zroof),
            (-rw / 2 + 0.12, zroof), (-rw / 2, zg), (-w / 2, zbelt), (-w / 2, zb + ch)]


def _smooth(secs, sub=3):
    """断面列を区間ごとにsub分割し、Catmull-Romで滑らかに補間(ボンネット/ルーフの折れを丸める)。cabinは両端がTrueの区間のみTrue"""
    out = []
    n = len(secs)
    for i in range(n - 1):
        p0, p1, p2, p3 = secs[max(0, i - 1)], secs[i], secs[i + 1], secs[min(n - 1, i + 2)]
        for t in [j / sub for j in range(sub)]:
            def cr(k):
                a0, a1, a2, a3 = p0[k], p1[k], p2[k], p3[k]
                return 0.5 * (2 * a1 + (-a0 + a2) * t + (2 * a0 - 5 * a1 + 4 * a2 - a3) * t * t + (-a0 + 3 * a1 - 3 * a2 + a3) * t ** 3)
            out.append((cr(0), cr(1), cr(2), cr(3), cr(4), p1[5] and p2[5]))
    out.append(secs[-1])
    return out


def vehicle(m, L, W, secs, paint, wheel_r=0.32, wb=None, track=None, hood_x=None, kind="car"):
    """secs: 後→前の断面 [(x, rw, zb, zbelt, zroof, cabin)] を滑らかに補間して車体を作る(cabin=Trueでガラス面)。"""
    src = secs
    secs = _smooth(secs)
    rings = []
    for (x, rw, zb, zbelt, zroof, cabin) in secs:
        rings.append((x, _ring(W, rw, zb, zbelt, zroof), cabin))
    n = len(rings[0][1])
    for (x0, r0, c0), (x1, r1, c1) in zip(rings, rings[1:]):
        cabin = c0 and c1
        for k in range(n):
            k2 = (k + 1) % n
            q = [(x0, r0[k][0], r0[k][1]), (x0, r0[k2][0], r0[k2][1]), (x1, r1[k2][0], r1[k2][1]), (x1, r1[k][0], r1[k][1])]
            mat = "car_under" if k == 0 else ("car_glass" if (k in (3, 7) and cabin) else paint)
            c = ((q[0][1] + q[2][1]) / 2, (q[0][2] + q[2][2]) / 2)
            m.oriented(q, (0, c[0], c[1] - 0.8) if k != 0 else (0, 0, -1), mat)
    secs = src
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
    for sx in (-1, 1):                                  # ホイールアーチ(暗い円盤)
        for sy in (-1, 1):
            m.cyl(sx * wb / 2, sy * W / 2 - 0.012, wheel_r, wheel_r + 0.09, 0.024, "y", "car_under", 16)
    zbelt = secs[len(secs) // 2][3]
    for sy in (-1, 1):                                  # ドアの合わせ目とドアハンドル
        for fx in (-0.1, 0.12):
            m.box(fx * L, sy * W / 2 - 0.004, 0.36, fx * L + 0.012, sy * W / 2 + 0.004, zbelt, "car_under")
        m.box(0.02 * L, sy * W / 2 - 0.01, zbelt - 0.12, 0.02 * L + 0.14, sy * W / 2 + 0.012, zbelt - 0.09, "car_wheel")
    xf, xr = rings[-1][0], rings[0][0]
    zb = secs[-1][2]
    zl = secs[-1][3] - 0.18
    for sy in (-1, 1):                                  # ヘッドライト/テールランプ
        m.box(xf - 0.02, sy * W * 0.34 - 0.18, zl - 0.06, xf + 0.012, sy * W * 0.34 + 0.18, zl + 0.08, "car_headlight")
        m.box(xr - 0.012, sy * W * 0.36 - 0.17, secs[0][3] - 0.2, xr + 0.02, sy * W * 0.36 + 0.17, secs[0][3] - 0.08, "car_taillight")
    for xx, d in ((xf, 1), (xr, -1)):                                                            # 前後バンパー+グリル
        m.box(xx - 0.03 * (1 if d > 0 else -1) - 0.03, -W * 0.46, zb + 0.02, xx + 0.03 * d + 0.03, W * 0.46, zb + 0.16, "car_under")
    m.box(xf - 0.02, -W * 0.3, zb + 0.18, xf + 0.02, W * 0.3, zb + 0.32, "car_under")
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
    L, W = 10.5, 2.5
    h = L / 2
    secs = [(-h, 2.2, 0.4, 1.05, 3.0, False), (-h + 0.35, 2.34, 0.4, 1.05, 3.1, True), (h - 0.5, 2.34, 0.4, 1.05, 3.1, True), (h - 0.08, 2.2, 0.42, 0.95, 2.85, False), (h, 2.1, 0.45, 0.9, 2.5, False)]
    vehicle(m, L, W, secs, paint, 0.5, 6.2, W - 0.1)
    m.box(h * 0.2, -W / 2 - 0.006, 0.42, h * 0.2 + 1.3, -W / 2 + 0.002, 2.9, "car_paint_white")           # 乗車ドア帯
    m.box(h * 0.2, W / 2 - 0.002, 0.42, h * 0.2 + 1.3, W / 2 + 0.006, 2.9, "car_paint_white")
    for sy in (-1, 1):                                                                                    # 腰の白帯
        m.box(-h + 0.4, sy * W / 2 - 0.004 * (sy > 0) - 0.006 * (sy < 0), 0.5, h - 0.6, sy * W / 2 + 0.006 * (sy > 0) + 0.004 * (sy < 0), 0.75, "car_paint_white")
    m.box(h - 0.05, -0.8, 2.55, h + 0.02, 0.8, 2.75, "led_white")                                         # 行先表示
    m.box(-0.8, -0.9, 3.1, 0.9, 0.9, 3.35, "steel_gray")                                                  # 屋根上の空調


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


def _ell(cx, cy, rx, ry, n=10):
    return [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n)]


def person(m, top, bottom, walking=False, h=1.7, child=False, bag=False):
    """低ポリだが丸みのある人: 楕円断面の胴/腕/脚、卵形の頭+髪、靴、(歩行時)脚腕の前後振り"""
    s = 0.6 if child else h / 1.7
    sw = 0.2 if walking else 0.0
    for sx, ph in ((-0.09, sw), (0.09, -sw)):                                                    # 脚(大腿+下腿で膝を曲げる)
        m.prism(_ell(sx * s, ph * s * 0.5, 0.062 * s, 0.065 * s, 8), "z", 0.45 * s, 0.88 * s, bottom)
        m.prism(_ell(sx * s, ph * s * 0.8, 0.05 * s, 0.055 * s, 8), "z", 0.06 * s, 0.46 * s, bottom)
        m.prism([(sx * s - 0.05 * s, (ph * 0.8 - 0.06) * s), (sx * s + 0.05 * s, (ph * 0.8 - 0.06) * s), (sx * s + 0.045 * s, (ph * 0.8 + 0.16) * s), (sx * s - 0.045 * s, (ph * 0.8 + 0.16) * s)], "z", 0.0, 0.07 * s, "ped_shoe")
    m.prism(_ell(0, 0, 0.16 * s, 0.1 * s, 12), "z", 0.84 * s, 1.0 * s, bottom)                    # 腰
    m.prism(_ell(0, 0, 0.17 * s, 0.1 * s, 12), "z", 0.98 * s, 1.3 * s, top)                      # 胴
    m.prism(_ell(0, 0, 0.2 * s, 0.1 * s, 12), "z", 1.28 * s, 1.4 * s, top)                       # 肩
    for sx, ph in ((-0.235, -sw), (0.235, sw)):                                                  # 腕(袖+手)
        m.prism(_ell(sx * s, ph * s * 0.5, 0.04 * s, 0.045 * s, 8), "z", 0.88 * s, 1.38 * s, top)
        m.prism(_ell(sx * s, ph * s * 0.7, 0.035 * s, 0.04 * s, 8), "z", 0.76 * s, 0.9 * s, "ped_skin")
    m.cyl(0, 0, 1.38 * s, 0.045 * s, 0.07 * s, "z", "ped_skin", 8)                              # 首
    m.lathe(0, 0, 1.43 * s, [(0.001, 0.0), (0.075 * s, 0.03 * s), (0.095 * s, 0.1 * s), (0.09 * s, 0.17 * s), (0.06 * s, 0.215 * s), (0.001, 0.235 * s)], "ped_skin", 10)   # 頭
    m.lathe(0, -0.012 * s, 1.5 * s, [(0.095 * s, 0.0), (0.097 * s, 0.08 * s), (0.065 * s, 0.16 * s), (0.001, 0.185 * s)], "ped_hair", 10)                                      # 髪
    if bag:
        m.box(0.2 * s, -0.12 * s, 0.85 * s, 0.34 * s, 0.14 * s, 1.1 * s, "ped_cloth_black")


for _i, _t in enumerate(CLOTH):
    _b = CLOTH[(_i * 3 + 2) % len(CLOTH)]
    for _w in (False, True):
        reg(f"person_{'walk' if _w else 'stand'}_{_i}", (lambda t, b, w, hh: lambda m, W, H, r: person(m, t, b, w, hh, False, w))(_t, _b, _w, 1.55 + 0.05 * ((_i * 5) % 7)), W=0.6, H=1.8, cat="人")
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


def fence_mesh(m, h=1.8):
    """線路沿い・敷地境界の緑色メッシュフェンス(2m): 支柱+上下の横桟+細い格子"""
    for x in (-1.0, 1.0):
        m.cyl(x, 0, 0, 0.03, h + 0.1, "z", "steel_green", 8)
    for z in (0.12, h):
        m.cyl(-1.0, 0, z, 0.015, 2.0, "x", "steel_green", 6)
    n = 40
    for i in range(n + 1):
        x = -1.0 + i * 2.0 / n
        m.box(x - 0.004, -0.004, 0.12, x + 0.004, 0.004, h, "steel_green")
    for k in range(1, 9):
        m.box(-1.0, -0.004, 0.12 + k * (h - 0.12) / 9, 1.0, 0.004, 0.125 + k * (h - 0.12) / 9, "steel_green")


reg("fence_mesh_2m", lambda m, W, H, r: fence_mesh(m), W=2.0, H=1.9, cat="資材")


def playground(m, kind):
    if kind == "slide":
        for sx in (-0.4, 0.4):
            m.box(sx - 0.03, -0.3, 0, sx + 0.03, -0.2, 2.2, "steel_galv")
        m.box(-0.45, -0.35, 1.6, 0.45, -0.1, 1.68, "car_paint_red")
        m.prism([(1.9, 0.3), (1.9, 0.36), (-0.1, 1.66), (-0.1, 1.6)], "x", -0.3, 0.3, "car_paint_blue")      # 滑り面
        for sx in (-0.3, 0.3):                                                                                 # 側壁
            m.prism([(1.9, 0.3), (1.9, 0.55), (-0.1, 1.9), (-0.1, 1.6)], "x", sx - 0.015, sx + 0.015, "car_paint_blue")
    elif kind == "swing":
        for sx in (-1.4, 1.4):
            m.cyl(sx, -0.6, 0, 0.04, 2.4, "z", "steel_galv", 8)
            m.cyl(sx, 0.6, 0, 0.04, 2.4, "z", "steel_galv", 8)
        m.cyl(-1.45, 0, 2.4, 0.04, 2.9, "x", "steel_galv", 8)
        for sx in (-0.5, 0.5):
            m.cyl(sx, 0, 0.45, 0.01, 1.95, "z", "steel_gray", 6)
            m.box(sx - 0.2, -0.08, 0.4, sx + 0.2, 0.08, 0.45, "car_paint_red")
    else:                                   # 砂場
        m.box(-1.2, -1.2, 0, 1.2, 1.2, 0.3, "wood")
        m.box(-1.1, -1.1, 0.05, 1.1, 1.1, 0.28, "sidewalk_granite")


for _k in ("slide", "swing", "sandpit"):
    reg(f"playground_{_k}", (lambda k: lambda m, W, H, r: playground(m, k))(_k), W=3.0, H=2.5, cat="遊具")


def pergola(m):
    for sx in (-1.5, 1.5):
        for sy in (-1.5, 1.5):
            m.box(sx - 0.1, sy - 0.1, 0, sx + 0.1, sy + 0.1, 2.6, "wood")
    for i in range(7):
        y = -1.6 + i * 0.53
        m.box(-1.8, y - 0.05, 2.6, 1.8, y + 0.05, 2.75, "wood")
    for sy in (-1.5, 1.5):
        m.box(-1.8, sy - 0.08, 2.45, 1.8, sy + 0.08, 2.6, "wood")


reg("pergola_wood", lambda m, W, H, r: pergola(m), W=3.6, H=2.8, cat="遊具")


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
