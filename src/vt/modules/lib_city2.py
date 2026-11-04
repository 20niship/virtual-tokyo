"""リアリズム強化(B)の車両・人: 車種追加(ワゴン/バン/軽バン/軽トラ/ダンプ/観光・マイクロバス/スクーター/ママチャリ)と、服地・髪型・小物・ポーズ違いの歩行者(pedx_*)、自転車に乗る人。
座標系は lib_city と同じ(車両: +x=前進/y=幅、人: 原点=足元・+y=顔の向き)。"""
import math
import random
import zlib

from . import lib_city as C
from .registry import reg
from .xutil import pipe


def _i(s, n=6):
    return zlib.crc32(s.encode()) % n


# ---------------- 追加車種 ----------------
for _k, _v in dict(pearl="car_paint_pearl", navy="car_paint_navy", wine="car_paint_wine", sky="car_paint_sky", yellow="car_paint_yellow").items():
    C.PAINT[_k] = _v


def wagon(m, color):
    L, W = 4.7, 1.8
    h = L / 2
    secs = [(-h, 1.5, 0.3, 0.95, 1.2, False), (-h * 0.93, 1.48, 0.3, 0.98, 1.46, True), (-h * 0.1, 1.46, 0.3, 0.98, 1.5, True), (h * 0.28, 1.46, 0.3, 0.98, 1.44, True),
            (h * 0.45, 1.56, 0.3, 0.9, 0.95, False), (h * 0.8, 1.64, 0.3, 0.82, 0.86, False), (h, 1.55, 0.34, 0.68, 0.72, False)]
    C.vehicle(m, L, W, secs, C.PAINT[color], 0.31, 2.75, plate="white", idx=_i("wagon" + color), roof_rails=True, antenna=True)


def van(m, color, L=4.7, W=1.7, H=1.98, kei=False):
    h = L / 2
    s = H / 1.98
    secs = [(-h, W - 0.2, 0.3, 1.05 * s, H - 0.05, False), (-h * 0.97, W - 0.24, 0.3, 1.1 * s, H, False), (h * 0.12, W - 0.24, 0.3, 1.1 * s, H, False),
            (h * 0.3, W - 0.24, 0.3, 1.1 * s, H, True), (h * 0.62, W - 0.18, 0.3, 1.0 * s, H * 0.78, True), (h * 0.86, W - 0.1, 0.3, 0.9 * s, 1.1, False), (h, W - 0.2, 0.34, 0.75 * s, 0.86, False)]
    C.vehicle(m, L, W, secs, "car_paint_white" if color == "white" else C.PAINT[color], 0.27 if kei else 0.3, L * 0.6, plate="kei" if kei else "white", idx=_i("van" + color), roof_rails=True)
    z = H
    m.box(-h * 0.4, -W * 0.3, z, h * 0.1, W * 0.3, z + 0.03, "car_trim")


def kei_truck(m, color):
    L, W = 3.4, 1.48
    h = L / 2
    secs = [(-0.05, 1.3, 0.3, 1.0, 1.6, True), (0.1, 1.3, 0.3, 1.05, 1.62, True), (h * 0.62, 1.34, 0.3, 0.98, 1.3, True), (h * 0.85, 1.42, 0.3, 0.9, 0.96, False), (h, 1.36, 0.3, 0.7, 0.76, False)]
    C.vehicle(m, L, W, secs, C.PAINT[color], 0.27, 2.0, plate="keigreen" if color in ("white", "silver") else "kei", idx=_i("kt" + color), pillars=False)
    xb0, xb1 = -h, -0.1
    m.box(xb0, -W / 2 + 0.04, 0.58, xb1, W / 2 - 0.04, 0.72, "car_under")                                  # 荷台の床
    for sy in (-1, 1):
        m.box(xb0, sy * (W / 2 - 0.04) - 0.02, 0.72, xb1, sy * (W / 2 - 0.04) + 0.02, 1.0, C.PAINT[color])   # あおり(側)
    m.box(xb0, -W / 2 + 0.04, 0.72, xb0 + 0.04, W / 2 - 0.04, 1.0, C.PAINT[color])                          # あおり(後)
    m.box(xb1 - 0.04, -W / 2 + 0.04, 0.72, xb1, W / 2 - 0.04, 1.35, "car_trim")                              # キャブ後ガード
    m.box(xb0 + 0.3, -W * 0.3, 0.72, xb0 + 1.3, W * 0.3, 0.98, "car_tarp_blue")                              # 積荷のシート


def dump_truck(m):
    L, W = 6.4, 2.2
    h = L / 2
    secs = [(h * 0.5, 2.0, 0.55, 1.15, 1.75, True), (h * 0.7, 2.05, 0.55, 1.05, 1.2, False), (h, 1.95, 0.55, 0.95, 1.0, False)]
    C.vehicle(m, L, W, secs, "car_paint_white", 0.5, 3.6, 1.9, plate="green", idx=2, pillars=False)
    prof = [(-W / 2 + 0.05, 0.9), (W / 2 - 0.05, 0.9), (W / 2 - 0.05, 2.2), (-W / 2 + 0.05, 2.2)]
    m.prism([(0.95, -h), (0.95, h * 0.42), (2.1, h * 0.42), (2.4, -h)], "y", -W / 2 + 0.05, W / 2 - 0.05, "car_dump_yellow")      # 荷台(側面形状)
    m.box(-h, -W / 2 + 0.2, 0.6, h * 0.4, W / 2 - 0.2, 0.95, "car_under")
    m.box(h * 0.42, -W / 2 + 0.1, 1.9, h * 0.52, W / 2 - 0.1, 2.3, "car_dump_yellow")                                                # ヘッドガード


def coach(m, L=12.0):
    W = 2.49
    h = L / 2
    secs = [(-h, 2.3, 0.45, 1.0, 3.4, False), (-h + 0.4, 2.4, 0.45, 1.0, 3.5, True), (h - 0.6, 2.4, 0.45, 1.0, 3.5, True), (h - 0.1, 2.3, 0.5, 0.95, 3.1, False), (h, 2.15, 0.52, 0.9, 2.5, False)]
    C.vehicle(m, L, W, secs, "car_paint_white", 0.5, L * 0.62, W - 0.1, plate="white", idx=3, pillars=True)
    m.box(-h + 0.4, -W / 2 - 0.005, 0.55, h - 0.5, -W / 2 + 0.005, 0.9, "car_paint_blue")
    m.box(-h + 0.4, W / 2 - 0.005, 0.55, h - 0.5, W / 2 + 0.005, 0.9, "car_paint_blue")
    m.box(-0.8, -0.9, 3.5, 0.9, 0.9, 3.7, "steel_gray")


def mini_bus(m):
    L, W = 7.0, 2.1
    h = L / 2
    secs = [(-h, 1.9, 0.4, 1.0, 2.6, False), (-h + 0.2, 1.95, 0.4, 1.0, 2.7, True), (h - 0.6, 1.95, 0.4, 1.0, 2.7, True), (h - 0.08, 1.9, 0.42, 0.9, 2.3, False), (h, 1.8, 0.45, 0.85, 1.4, False)]
    C.vehicle(m, L, W, secs, "car_paint_white", 0.38, L * 0.6, W - 0.1, plate="white", idx=4)
    m.box(-h + 0.3, -W / 2 - 0.005, 0.55, h - 0.4, -W / 2 + 0.005, 0.8, "car_paint_green")
    m.box(-h + 0.3, W / 2 - 0.005, 0.55, h - 0.4, W / 2 + 0.005, 0.8, "car_paint_green")

def _regcar(name, fn, W, H):
    reg(name, (lambda f: lambda m, w_, h_, r: f(m))(fn), W=W, H=H, cat="車両")


for _c in ("white", "silver", "black", "gray", "pearl", "navy", "wine"):
    _regcar(f"car_wagon_{_c}", (lambda c: lambda m: wagon(m, c))(_c), 4.7, 1.55)
for _c in ("white", "silver", "pearl", "gray"):
    _regcar(f"car_van_{_c}", (lambda c: lambda m: van(m, c))(_c), 4.7, 2.0)
for _c in ("white", "silver", "sky", "yellow"):
    _regcar(f"car_keivan_{_c}", (lambda c: lambda m: van(m, c, 3.4, 1.48, 1.9, True))(_c), 3.4, 1.9)
for _c in ("white", "silver", "sky"):
    _regcar(f"truck_kei_{_c}", (lambda c: lambda m: kei_truck(m, c))(_c), 3.4, 1.7)
for _c in ("pearl", "navy", "wine", "sky", "yellow"):                      # 既存5車種に追加色
    _regcar(f"car_sedan_{_c}", (lambda c: lambda m: C.sedan(m, c))(_c), 4.7, 1.5)
    _regcar(f"car_hatch_{_c}", (lambda c: lambda m: C.hatch(m, c))(_c), 4.0, 1.55)
    _regcar(f"car_suv_{_c}", (lambda c: lambda m: C.suv(m, c))(_c), 4.6, 1.75)
    _regcar(f"car_minivan_{_c}", (lambda c: lambda m: C.minivan(m, c))(_c), 4.7, 1.9)
    _regcar(f"car_kei_{_c}", (lambda c: lambda m: C.kei(m, c))(_c), 3.4, 1.7)
_regcar("truck_dump", dump_truck, 6.4, 3.0)
_regcar("bus_coach", coach, 12.0, 3.7)
_regcar("bus_mini", mini_bus, 7.0, 2.8)
for _c, _p in (("blue", "car_paint_blue"), ("white", "car_paint_white"), ("red", "car_paint_red")):
    _regcar(f"bus_city_{_c}", (lambda p: lambda m: C.bus(m, p))(_p), 10.5, 3.4)


# ---------------- 自転車・スクーター ----------------
def bike(m, frame="bike_frame_silver", basket=True, child_seat=False, rust=False, x0=0.0):
    fm = "bike_rust" if rust else frame
    for sx in (-0.55, 0.55):                                                      # ホイール(タイヤ+リム+スポーク)
        m.tube(sx + x0, -0.02, 0.33, 0.33, 0.31, 0.04, "y", "car_tire", 22)
        m.tube(sx + x0, -0.012, 0.33, 0.31, 0.295, 0.024, "y", "bike_frame_silver", 22)
        for k in range(8):
            a = k * math.pi / 8
            pipe(m, (sx + x0 + 0.29 * math.cos(a), 0, 0.33 + 0.29 * math.sin(a)), (sx + x0 - 0.29 * math.cos(a), 0, 0.33 - 0.29 * math.sin(a)), 0.003, "bike_frame_silver", 4)
    P = lambda x, z: (x + x0, 0.0, z)
    for a, b, r in (((-0.55, 0.33), (-0.1, 0.3), 0.012), ((-0.1, 0.3), (-0.2, 0.92), 0.015), ((-0.1, 0.3), (0.42, 0.86), 0.015),
                    ((-0.2, 0.82), (0.42, 0.86), 0.013), ((-0.2, 0.92), (-0.55, 0.33), 0.01), ((0.42, 0.86), (0.55, 0.33), 0.014),
                    ((0.42, 0.86), (0.46, 1.02), 0.016)):
        pipe(m, P(*a), P(*b), r, fm, 6)
    m.box(-0.34 + x0, -0.07, 0.93, -0.06 + x0, 0.07, 0.98, "bike_seat")                # サドル
    pipe(m, (0.46 + x0, -0.3, 1.04), (0.46 + x0, 0.3, 1.04), 0.011, "bike_frame_silver", 6)  # ハンドル
    for sy in (-1, 1):
        pipe(m, (0.46 + x0, sy * 0.26, 1.04), (0.44 + x0, sy * 0.33, 1.02), 0.016, "bike_seat", 6)
    pipe(m, (-0.08 + x0, -0.12, 0.3), (-0.08 + x0, 0.12, 0.3), 0.012, "bike_frame_black", 6)   # クランク/ペダル
    for sy in (-1, 1):
        m.box(-0.14 + x0, sy * 0.13 - 0.04, 0.22, -0.02 + x0, sy * 0.13 + 0.04, 0.24, "bike_seat")
    m.box(-0.3 + x0, 0.04, 0.2, 0.0 + x0, 0.06, 0.4, "bike_frame_black")             # チェーンガード
    m.box(0.52 + x0, -0.05, 0.98, 0.56 + x0, 0.05, 1.04, "led_white")                  # ライト
    pipe(m, (-0.15 + x0, 0.0, 0.3), (-0.2 + x0, 0.0, 0.0), 0.008, "bike_frame_black", 5)  # スタンド
    m.box(-0.62 + x0, -0.14, 0.7, -0.22 + x0, 0.14, 0.73, "bike_basket")                # 荷台
    if basket:
        m.box(0.52 + x0, -0.16, 0.84, 0.82 + x0, 0.16, 0.88, "bike_basket")
        for sy in (-0.16, 0.16):
            m.box(0.52 + x0, sy - 0.006, 0.88, 0.82 + x0, sy + 0.006, 1.08, "bike_basket")
        m.box(0.8 + x0, -0.16, 0.88, 0.82 + x0, 0.16, 1.08, "bike_basket")
    if child_seat:
        m.box(-0.5 + x0, -0.14, 0.78, -0.22 + x0, 0.14, 0.86, "bike_seat")
        m.box(-0.5 + x0, -0.14, 0.86, -0.46 + x0, 0.14, 1.12, "bike_seat")


def scooter(m, color="car_paint_white", rider=None):
    for sx in (-0.52, 0.55):
        C.wheel(m, sx, 0.0, 1, 0.22, 0.1)
    m.box(-0.55, -0.16, 0.3, 0.1, 0.16, 0.62, color)                                        # 車体
    m.box(-0.15, -0.14, 0.18, 0.4, 0.14, 0.26, "car_trim")                                   # フロア
    m.prism([(0.5, -0.05), (0.5, 0.1), (0.96, 0.28), (0.96, 0.2)], "y", -0.16, 0.16, color)  # レッグシールド
    m.box(-0.6, -0.14, 0.62, -0.05, 0.14, 0.72, "bike_seat")                                  # シート
    m.box(-0.78, -0.14, 0.62, -0.58, 0.14, 0.66, "car_trim")
    m.box(0.15, -0.28, 0.98, 0.3, 0.28, 1.04, color)                                          # ハンドルカバー
    m.box(0.3, -0.1, 0.96, 0.34, 0.1, 1.04, "led_white")
    m.box(-0.78, -0.07, 0.34, -0.74, 0.07, 0.42, "car_plate")
    if rider:
        top, bottom, helm = rider
        _seated(m, -0.34, 0.74, top, bottom, helm)


def _seated(m, x, zs, top, bottom, helm=None, lean=0.15):
    """座った人(スクーター/自転車用): 腰→膝→足の脚、前傾した胴、腕でハンドルへ、ヘルメット/頭。+x向き"""
    for sy in (-0.1, 0.1):
        pipe(m, (x, sy, zs + 0.06), (x + 0.38, sy, zs + 0.05), 0.065, bottom, 8)
        pipe(m, (x + 0.38, sy, zs + 0.05), (x + 0.34, sy, 0.26), 0.05, bottom, 8)
        m.box(x + 0.26, sy - 0.05, 0.16, x + 0.46, sy + 0.05, 0.25, "ped_shoe")
    ctr = (x + 0.02, 0.0, zs + 0.1)
    top_pt = (x + 0.02 + lean * 0.5, 0.0, zs + 0.58)
    pipe(m, ctr, top_pt, 0.145, top, 10)
    for sy in (-1, 1):
        pipe(m, (top_pt[0] - 0.02, sy * 0.19, top_pt[2] - 0.05), (x + 0.6, sy * 0.26, zs + 0.3), 0.04, top, 7)
    hx, hz = top_pt[0] + 0.07, top_pt[2] + 0.2
    m.lathe(hx, 0, hz - 0.12, [(0.001, 0.0), (0.09, 0.03), (0.105, 0.12), (0.09, 0.2), (0.001, 0.24)], helm or "ped_skin", 10)
    pipe(m, (top_pt[0], 0, top_pt[2]), (hx, 0, hz - 0.1), 0.045, "ped_skin", 6)


def moto(m, color="car_paint_red", rider=None):
    """ネイキッドバイク: 前後ホイール+フォーク+フレーム+タンク+シート+エンジン+マフラー+ヘッドライト"""
    for sx in (-0.62, 0.62):
        C.wheel(m, sx, 0.0, 1, 0.31, 0.13)
    pipe(m, (0.62, 0.0, 0.31), (0.5, 0.0, 0.95), 0.025, "car_chrome", 8)                      # フォーク
    pipe(m, (-0.62, 0.0, 0.31), (-0.15, 0.0, 0.5), 0.022, "car_trim", 8)                      # スイングアーム
    m.box(-0.12, -0.13, 0.28, 0.32, 0.13, 0.62, "steel_gray")                                  # エンジン
    m.box(0.0, -0.15, 0.62, 0.42, 0.15, 0.88, color)                                           # タンク
    m.box(-0.5, -0.12, 0.74, 0.0, 0.12, 0.82, "bike_seat")                                     # シート
    m.box(-0.62, -0.1, 0.8, -0.45, 0.1, 0.9, color)                                            # テールカウル
    pipe(m, (0.5, -0.38, 1.0), (0.5, 0.38, 1.0), 0.013, "car_chrome", 6)                       # ハンドル
    m.lathe(0.6, 0, 0.78, [(0.001, 0.0), (0.1, 0.05), (0.1, 0.12), (0.001, 0.17)], "car_headlight", 10)
    pipe(m, (0.1, -0.16, 0.34), (-0.7, -0.2, 0.42), 0.04, "car_chrome", 8)                      # マフラー
    m.box(-0.64, -0.06, 0.55, -0.58, 0.06, 0.62, "car_plate")
    if rider:
        top, bottom, helm = rider
        _seated(m, -0.2, 0.8, top, bottom, helm, lean=0.3)


reg("motorbike", lambda m, W, H, r: moto(m, "car_paint_red"), W=2.0, H=1.2, cat="車両")
reg("motorbike_blue", lambda m, W, H, r: moto(m, "car_paint_blue"), W=2.0, H=1.2, cat="車両")
reg("motorbike_rider", lambda m, W, H, r: moto(m, "car_paint_black", ("ped_cloth_black", "ped_tex_denim_dark", "car_paint_white")), W=2.0, H=1.8, cat="車両")


def cyclist(m, kind):
    """kind: commuter(スーツ)/student(制服+ヘルメット)/mama(ママチャリ+前かご)。自転車の+x向き、足元基準"""
    frames = dict(commuter="bike_frame_black", student="bike_frame_silver", mama="bike_frame_blue")
    bike(m, frames[kind], basket=kind != "commuter", child_seat=kind == "mama")
    top, bottom, helm = dict(commuter=("ped_cloth_suit", "ped_cloth_suit", None), student=("ped_cloth_navy", "ped_cloth_gray", "umb_beige"), mama=("ped_tex_plaid_red", "ped_tex_denim", None))[kind]
    zs = 0.98
    x = -0.28
    for sy in (-0.1, 0.1):                                                                         # 脚(ペダル踏み)
        sw = 0.08 if sy > 0 else -0.08
        pipe(m, (x, sy, zs), (x + 0.28 + sw, sy, 0.62), 0.065, bottom, 8)
        pipe(m, (x + 0.28 + sw, sy, 0.62), (-0.08 + sw * 0.6, sy, 0.27), 0.05, bottom, 8)
        m.box(-0.14 + sw * 0.6, sy - 0.05, 0.22, 0.04 + sw * 0.6, sy + 0.05, 0.3, "ped_shoe")
    top_pt = (x + 0.2, 0.0, zs + 0.5)
    pipe(m, (x, 0, zs + 0.02), top_pt, 0.14, top, 10)
    for sy in (-1, 1):
        pipe(m, (top_pt[0], sy * 0.2, top_pt[2] - 0.05), (0.44, sy * 0.28, 1.05), 0.04, top, 7)
    hx, hz = top_pt[0] + 0.05, top_pt[2] + 0.2
    m.lathe(hx, 0, hz - 0.12, [(0.001, 0.0), (0.075, 0.03), (0.095, 0.1), (0.08, 0.18), (0.001, 0.22)], "ped_skin", 10)
    m.lathe(hx, -0.01, hz - 0.03, [(0.09, 0.0), (0.095, 0.07), (0.06, 0.15), (0.001, 0.17)], helm or "ped_hair", 10)
    pipe(m, top_pt, (hx, 0, hz - 0.1), 0.04, "ped_skin", 6)


reg("scooter_white", lambda m, W, H, r: scooter(m, "car_paint_white"), W=1.9, H=1.1, cat="車両")
reg("scooter_black", lambda m, W, H, r: scooter(m, "car_paint_black"), W=1.9, H=1.1, cat="車両")
reg("scooter_rider_0", lambda m, W, H, r: scooter(m, "car_paint_silver", ("ped_cloth_navy", "ped_tex_denim_dark", "car_paint_black")), W=1.9, H=1.7, cat="車両")
reg("scooter_rider_1", lambda m, W, H, r: scooter(m, "car_paint_red", ("ped_cloth_green", "ped_cloth_beige", "car_paint_white")), W=1.9, H=1.7, cat="車両")
reg("bicycle_mama", lambda m, W, H, r: bike(m, "bike_frame_blue", True, True), W=1.9, H=1.15, cat="車両")
reg("bicycle_silver", lambda m, W, H, r: bike(m, "bike_frame_silver", False), W=1.9, H=1.1, cat="車両")
reg("bicycle_black_basket", lambda m, W, H, r: bike(m, "bike_frame_black", True), W=1.9, H=1.1, cat="車両")
reg("bicycle_red", lambda m, W, H, r: bike(m, "bike_frame_red", True), W=1.9, H=1.1, cat="車両")
reg("bicycle_abandoned", lambda m, W, H, r: bike(m, "bike_frame_silver", True, False, True), W=1.9, H=1.1, cat="車両")
for _k in ("commuter", "student", "mama"):
    reg(f"cyclist_{_k}", (lambda k: lambda m, W, H, r: cyclist(m, k))(_k), W=1.9, H=1.9, cat="人")


# ---------------- 歩行者(pedx_*) ----------------
SKIRT_TOPS = ["ped_tex_floral", "ped_tex_knit_beige", "ped_cloth_white", "ped_cloth_pink", "ped_tex_stripe_navy", "ped_cloth_sky", "ped_cloth_beige"]
CASUAL_TOPS = ["ped_cloth_navy", "ped_cloth_gray", "ped_cloth_red", "ped_cloth_white", "ped_cloth_green", "ped_tex_plaid_red", "ped_tex_plaid_green", "ped_tex_stripe_navy",
               "ped_tex_knit_navy", "ped_cloth_yellow", "ped_cloth_orange", "ped_tex_plain_olive", "ped_tex_plain_mustard", "ped_cloth_sky"]
BOTTOMS = ["ped_tex_denim", "ped_tex_denim_dark", "ped_cloth_black", "ped_cloth_gray", "ped_cloth_navy", "ped_cloth_beige", "ped_cloth_brown", "ped_tex_plain_olive"]
HAIRS = ["ped_hair_black"] * 10 + ["ped_hair_brown"] * 3 + ["ped_hair"] * 3 + ["ped_hair_gray"] * 2 + ["ped_hair_blonde"]      # 日本の街: 黒髪が大半


def ped(m, o):
    """o: dict(top,bottom,pose=stand|walk|phone, kind=pants|skirt|suit|coat, h, build, hair=short|long|bun|cap|none, hairc, hat, acc=[...], lean, child, shoe)"""
    s = o.get("h", 1.7) / 1.7
    b = o.get("build", 1.0)
    pose = o.get("pose", "stand")
    kind = o.get("kind", "pants")
    top, bottom = o["top"], o["bottom"]
    lean = o.get("lean", 0.0)
    sw = 0.2 if pose == "walk" else 0.0
    sh = o.get("shoe", "ped_shoe")
    hipz = 0.9 * s
    for sx, ph in ((-0.09 * b, sw), (0.09 * b, -sw)):                                # 脚: 股関節→膝→足首(歩行で前後)
        knee = (sx * s, ph * 0.55 * s, 0.5 * s)
        ank = (sx * s, ph * s * 1.0 - (0.04 * s if ph < 0 else 0.0), 0.08 * s)
        pipe(m, (sx * s, 0.0, hipz), knee, 0.082 * s * b, bottom, 10)
        pipe(m, knee, ank, 0.062 * s * b, bottom if kind != "skirt" else "ped_skin", 10)
        m.box(sx * s - 0.05 * s, ank[1] - 0.07 * s, 0.0, sx * s + 0.05 * s, ank[1] + 0.17 * s, 0.075 * s, sh)
    if kind == "skirt":
        m.lathe(0, 0, 0.56 * s, [(0.25 * s * b, 0.0), (0.22 * s * b, 0.2 * s), (0.17 * s * b, 0.38 * s), (0.001, 0.38 * s)], bottom, 14)
    elif kind == "coat":
        m.lathe(0, 0, 0.58 * s, [(0.24 * s * b, 0.0), (0.22 * s * b, 0.3 * s), (0.18 * s * b, 0.5 * s), (0.17 * s * b, 0.78 * s)], top, 14)
    def E(cx, cy, rx, ry, n=16):
        return [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n)]
    sy = lean * 0.2 * s
    m.prism(E(0, 0, 0.165 * s * b, 0.11 * s), "z", 0.84 * s, 1.0 * s, bottom if kind not in ("coat", "suit") else top)    # 腰
    m.prism(E(0, sy * 0.4, 0.18 * s * b, 0.118 * s), "z", 0.98 * s, 1.3 * s, top)                                          # 胴
    m.prism(E(0, sy * 0.8, 0.21 * s * b, 0.112 * s), "z", 1.28 * s, 1.4 * s, top)                                             # 肩
    if kind in ("pants", "suit"):
        m.prism(E(0, 0, 0.168 * s * b, 0.114 * s), "z", 0.97 * s, 1.0 * s, "ped_shoe")                                                   # ベルト
    if kind == "suit":
        m.box(-0.04 * s, 0.103 * s + sy * 0.6, 1.16 * s, 0.04 * s, 0.108 * s + sy * 0.6, 1.36 * s, "ped_cloth_white")          # シャツの胸元
        m.box(-0.012 * s, 0.108 * s + sy * 0.6, 0.98 * s, 0.012 * s, 0.112 * s + sy * 0.6, 1.34 * s, o.get("tie", "ped_cloth_red"))  # ネクタイ
    # 腕: 肩→肘→手首
    sh_y = sy * 0.8
    for side in (-1, 1):
        sx = 0.235 * s * b * side
        if side == 1 and pose == "phone":
            el, ha = (sx + 0.02 * s, sh_y + 0.13 * s, 1.08 * s), (0.1 * s, sh_y + 0.2 * s, 1.42 * s)
        elif side == -1 and "umb_open" in o.get("acc", []):
            el, ha = (sx - 0.03 * s, sh_y + 0.14 * s, 1.1 * s), (sx - 0.03 * s, sh_y + 0.24 * s, 1.3 * s)
        else:
            ph = (-sw if side == 1 else sw) * s * 0.9
            el = (sx + 0.01 * s * side, sh_y + ph * 0.5, 1.08 * s)
            ha = (sx + 0.02 * s * side, sh_y + ph * 0.9, 0.82 * s)
        pipe(m, (sx, sh_y, 1.36 * s), el, 0.05 * s, top, 9)
        pipe(m, el, ha, 0.042 * s, top if kind in ("coat", "suit") or o.get("longsleeve", True) else "ped_skin", 9)
        m.lathe(ha[0], ha[1], ha[2] - 0.05 * s, [(0.001, 0.0), (0.035 * s, 0.025 * s), (0.04 * s, 0.07 * s), (0.001, 0.1 * s)], "ped_skin", 6)
        if side == 1 and pose == "phone":
            m.box(ha[0] - 0.03 * s, ha[1] - 0.005, ha[2] - 0.02 * s, ha[0] + 0.03 * s, ha[1] + 0.01, ha[2] + 0.1 * s, "ped_cloth_black")
        o.setdefault("_hands", {})[side] = ha
    m.cyl(0, sh_y, 1.38 * s, 0.045 * s, 0.07 * s, "z", "ped_skin", 8)                                                           # 首
    hy = sy * 1.4
    head = 1.43 * s
    m.lathe(0, hy, head, [(0.001, 0.0), (0.075 * s, 0.03 * s), (0.095 * s, 0.1 * s), (0.09 * s, 0.17 * s), (0.06 * s, 0.215 * s), (0.001, 0.235 * s)], "ped_skin", 14)
    for ex in (-0.034, 0.034):                                                                                                      # 目
        m.box(ex * s - 0.008 * s, hy + 0.083 * s, head + 0.135 * s, ex * s + 0.008 * s, hy + 0.092 * s, head + 0.147 * s, "glasses_dark")
    m.box(-0.01 * s, hy + 0.088 * s, head + 0.085 * s, 0.01 * s, hy + 0.108 * s, head + 0.125 * s, "ped_skin")                      # 鼻
    hair = o.get("hair", "short")
    hc = o.get("hairc", "ped_hair")
    if hair != "none":
        m.lathe(0, hy - 0.005 * s, head + 0.13 * s, [(0.094 * s, 0.0), (0.092 * s, 0.05 * s), (0.062 * s, 0.1 * s), (0.001, 0.12 * s)], hc, 10)            # 頭頂
        m.box(-0.092 * s, hy - 0.1 * s, head + 0.06 * s, 0.092 * s, hy - 0.02 * s, head + 0.2 * s, hc)                                                  # 後頭部
        if hair == "long":
            m.box(-0.09 * s, hy - 0.1 * s, head - 0.17 * s, 0.09 * s, hy - 0.045 * s, head + 0.17 * s, hc)
        elif hair == "bun":
            m.lathe(0, hy - 0.09 * s, head + 0.22 * s, [(0.001, 0.0), (0.04 * s, 0.02 * s), (0.045 * s, 0.06 * s), (0.001, 0.09 * s)], hc, 8)
    hat = o.get("hat")
    if hat == "cap":
        m.lathe(0, hy, head + 0.12 * s, [(0.1 * s, 0.0), (0.102 * s, 0.07 * s), (0.07 * s, 0.13 * s), (0.001, 0.14 * s)], "hat_cap", 10)
        m.box(-0.07 * s, hy + 0.08 * s, head + 0.14 * s, 0.07 * s, hy + 0.17 * s, head + 0.155 * s, "hat_cap")
    elif hat == "straw":
        m.lathe(0, hy, head + 0.14 * s, [(0.26 * s, -0.01 * s), (0.2 * s, 0.0), (0.1 * s, 0.02 * s), (0.09 * s, 0.1 * s), (0.001, 0.105 * s)], "hat_straw", 14)
    if "glasses" in o.get("acc", []):
        m.box(-0.07 * s, hy + 0.088 * s, head + 0.125 * s, 0.07 * s, hy + 0.095 * s, head + 0.14 * s, "glasses_dark")
    for a in o.get("acc", []):
        _accessory(m, a, o, s, sy)


def _accessory(m, a, o, s, sy):
    bag = o.get("bagc", "bag_leather")
    H = o.get("_hands", {})
    if a == "backpack":
        m.box(-0.14 * s, -0.25 * s, 0.98 * s, 0.14 * s, -0.1 * s, 1.34 * s, o.get("bagc", "bag_nylon"))
    elif a == "randoseru":
        m.box(-0.14 * s, -0.27 * s, 0.9 * s, 0.14 * s, -0.1 * s, 1.26 * s, o.get("bagc", "randoseru_red"))
    elif a == "shoulder":
        h = H.get(1, (0.24 * s, 0, 0.8 * s))
        m.box(0.27 * s, -0.1 * s, 0.78 * s, 0.37 * s, 0.14 * s, 1.0 * s, bag)
        pipe(m, (0.14 * s, 0.0, 1.38 * s), (0.3 * s, 0.0, 1.0 * s), 0.01 * s, bag, 4)
    elif a == "briefcase":
        h = H.get(1, (0.25 * s, 0.0, 0.8 * s))
        m.box(h[0] - 0.03 * s, h[1] - 0.2 * s, h[2] - 0.34 * s, h[0] + 0.04 * s, h[1] + 0.2 * s, h[2] - 0.04 * s, "bag_leather")
    elif a == "shopbag":
        h = H.get(-1, (-0.25 * s, 0.0, 0.8 * s))
        m.box(h[0] - 0.05 * s, h[1] - 0.14 * s, h[2] - 0.38 * s, h[0] + 0.05 * s, h[1] + 0.14 * s, h[2] - 0.04 * s, o.get("bagc2", "bag_clear_plastic"))
    elif a == "umb_closed":
        h = H.get(-1, (-0.25 * s, 0.0, 0.8 * s))
        pipe(m, (h[0], h[1] - 0.05, h[2] - 0.02), (h[0], h[1] + 0.1, h[2] - 0.62 * s), 0.016, o.get("umbc", "umb_navy"), 6)
    elif a == "umb_open":
        h = H.get(-1, (-0.27 * s, 0.24 * s, 1.3 * s))
        z0 = 1.84 * s
        pipe(m, (h[0], h[1], h[2]), (h[0], h[1], z0 + 0.02), 0.012, "umb_rib", 6)
        m.lathe(h[0], h[1], z0 - 0.02 * s, [(0.001, 0.25 * s), (0.2 * s, 0.23 * s), (0.42 * s, 0.15 * s), (0.56 * s, 0.0)], o.get("umbc", "umb_clear"), 14)
    elif a == "cane":
        h = H.get(1, (0.25 * s, 0.0, 0.8 * s))
        pipe(m, (h[0], h[1], h[2] + 0.02), (h[0] + 0.02, h[1] + 0.1, 0.0), 0.014, "umb_rib", 5)


def _spec(i, group):
    r = random.Random(f"{group}{i}")
    ch = lambda L: L[r.randrange(len(L))]
    o = dict(hairc=ch(HAIRS), build=r.uniform(0.88, 1.2))
    o["h"] = r.uniform(1.52, 1.82)
    o["shoe"] = ch(["ped_shoe", "ped_shoe", "ped_shoe_white", "ped_shoe_brown"])
    if group == "office":
        o.update(top="ped_cloth_suit", bottom="ped_cloth_suit" if r.random() < 0.7 else "ped_cloth_navy", kind="suit", tie=ch(["ped_cloth_red", "ped_cloth_navy", "ped_cloth_yellow", "ped_cloth_green"]),
                 hair="short", acc=[ch(["briefcase", "briefcase", "backpack", "shoulder"])], pose=ch(["walk", "walk", "stand"]), shoe="ped_shoe_brown" if r.random() < 0.3 else "ped_shoe")
        if r.random() < 0.35:
            o["acc"].append("glasses")
        if r.random() < 0.4:
            o["hairc"] = "ped_hair_black"
    elif group == "woman":
        o.update(top=ch(SKIRT_TOPS), bottom=ch(["ped_cloth_navy", "ped_cloth_beige", "ped_cloth_black", "ped_tex_plaid_green", "ped_cloth_brown"]), kind=ch(["skirt", "skirt", "pants"]),
                 hair=ch(["long", "long", "bun", "short"]), acc=[ch(["shoulder", "shoulder", "shopbag"])], pose=ch(["walk", "stand"]), build=r.uniform(0.82, 1.0), h=r.uniform(1.5, 1.7))
        o["bagc"] = ch(["bag_leather", "bag_tote", "bag_red", "bag_nylon"])
    elif group == "casual":
        o.update(top=ch(CASUAL_TOPS), bottom=ch(BOTTOMS), kind="pants", hair=ch(["short", "short", "long", "cap"]), acc=[ch(["backpack", "shoulder", "shopbag", "backpack"])] if r.random() < 0.7 else [],
                 pose=ch(["walk", "walk", "stand"]))
        o["bagc"] = ch(["bag_nylon", "bag_conv", "bag_tote"])
        if r.random() < 0.3:
            o["hat"] = "cap"
    elif group == "phone":
        o.update(top=ch(CASUAL_TOPS), bottom=ch(BOTTOMS), kind=ch(["pants", "skirt"]), hair=ch(["short", "long"]), pose="phone", lean=0.5, acc=["glasses"] if r.random() < 0.3 else [])
    elif group == "elder":
        o.update(top=ch(["ped_tex_knit_beige", "ped_cloth_gray", "ped_tex_plain_olive", "ped_cloth_brown", "ped_tex_plaid_green"]), bottom=ch(["ped_cloth_gray", "ped_cloth_brown", "ped_cloth_black"]), kind="pants",
                 hair="short", hairc="ped_hair_gray", hat=ch([None, "cap", "straw"]), lean=1.0, acc=ch([["cane"], ["shopbag"], []]), pose="walk", h=r.uniform(1.45, 1.62), build=r.uniform(0.9, 1.1))
    elif group == "parasol":
        o.update(top=ch(SKIRT_TOPS), bottom=ch(["ped_cloth_white", "ped_cloth_beige", "ped_cloth_navy"]), kind="skirt", hair="long", acc=["umb_open"], umbc=ch(["umb_beige", "umb_black", "umb_navy", "umb_red"]),
                 pose="stand", build=0.88, h=r.uniform(1.52, 1.68))
    elif group == "student":
        o.update(top="ped_cloth_navy", bottom=ch(["ped_tex_plaid_green", "ped_cloth_gray", "ped_cloth_navy"]), kind=ch(["skirt", "pants"]), hair=ch(["short", "long", "bun"]), acc=["backpack"], pose=ch(["walk", "stand"]),
                 h=r.uniform(1.5, 1.72), build=0.9, shoe="ped_shoe_white")
        o["bagc"] = ch(["bag_nylon", "randoseru_black", "bag_red"])
    elif group == "kid":
        o.update(top=ch(["ped_cloth_yellow", "ped_cloth_red", "ped_cloth_sky", "ped_cloth_orange", "ped_cloth_green"]), bottom=ch(["ped_cloth_navy", "ped_tex_denim", "ped_cloth_gray"]), kind="pants",
                 hair=ch(["short", "long"]), acc=["randoseru"] if r.random() < 0.6 else [], pose=ch(["walk", "stand"]), h=r.uniform(1.05, 1.35), build=0.8, hat="cap" if r.random() < 0.4 else None, shoe="ped_shoe_white")
        o["bagc"] = ch(["randoseru_red", "randoseru_black", "randoseru_blue"])
    return o


_GROUPS = [("office", 6), ("woman", 6), ("casual", 10), ("phone", 4), ("elder", 4), ("parasol", 3), ("student", 4), ("kid", 3)]
PEDX = {g: [f"pedx_{g}_{k}" for k in range(n)] for g, n in _GROUPS}
for _g, _n in _GROUPS:
    for _k in range(_n):
        reg(f"pedx_{_g}_{_k}", (lambda g, k: lambda m, W, H, r: ped(m, _spec(k, g)))(_g, _k), W=0.6 if _g != "parasol" else 1.2, H=1.85 if _g != "parasol" else 2.1, cat="人")
