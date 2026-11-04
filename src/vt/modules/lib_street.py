"""道路ファニチャのモジュール: 信号機(車両用/歩行者用 × 旧式/LED/薄型 × 点灯状態)、信号柱・アーム・制御機、街路灯(UsdLux付き)、標識柱と標識板(アトラス貼り)。
座標系: 原点=取付基準, +y=前(進行方向に正対), z=上。"""
import math

from ..signs import load_meta
from .registry import mod, reg

HEAD_R = 0.15   # 車両用灯器の灯火半径(φ300mm)
STATE_MAT = {"r": "sig_red", "y": "sig_yellow", "g": "sig_green", "off": "sig_lens_dark"}
STATE_COL = {"r": (1.0, 0.12, 0.08), "y": (1.0, 0.7, 0.0), "g": (0.1, 1.0, 0.6)}


def light(m, kind, pos, lumens, color=(1, 1, 1), radius=0.05, direction=(0, 0, -1), size=(0.1, 0.1), cct=None):
    m.lights.append(dict(type=kind, pos=pos, lumens=lumens, color=color, radius=radius, dir=direction, size=size, cct=cct))



def rrect(w, h, r, n=5):
    """角丸長方形の輪郭(x,z)。CCW"""
    pts = []
    cs = [(w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)]
    for cx, cz, a0 in cs:
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def loft_poly(m, A, yA, B, yB, mat):
    """同じ頂点数の2つの輪郭(x,z)を y=yA, yB で結ぶ(テーパー付き筐体)"""
    n = len(A)
    cxA = sum(p[0] for p in A) / n; czA = sum(p[1] for p in A) / n
    for i in range(n):
        j = (i + 1) % n
        q = [(A[i][0], yA, A[i][1]), (A[j][0], yA, A[j][1]), (B[j][0], yB, B[j][1]), (B[i][0], yB, B[i][1])]
        mx, mz = (A[i][0] + A[j][0]) / 2 - cxA, (A[i][1] + A[j][1]) / 2 - czA
        m.oriented(q, (mx, (yB - yA) * 0.3, mz), mat)


def cap_poly(m, pts, y, mat, front=True):
    """輪郭を平面(y)で塞ぐ(凸でない場合も扇状に。角丸長方形用)"""
    cx = sum(p[0] for p in pts) / len(pts); cz = sum(p[1] for p in pts) / len(pts)
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        m.oriented([(cx, y, cz), (pts[i][0], y, pts[i][1]), (pts[j][0], y, pts[j][1])], (0, 1 if front else -1, 0), mat)


def scale_pts(pts, s):
    return [(x * s, z * s) for x, z in pts]


def hood_sleeve(m, cx, cz, r, y0, l_max, l_min, thick, mat, n=28, keep=360):
    """筒形フード: 全周を覆う円筒で、先端は斜めに切り落とし(上が長く下が短い)。長さ=l_min+(l_max-l_min)*(0.5+0.5 sinθ)。
    keep: 残す角度(360=全周, 例えば 260=下側を開ける)"""
    a0 = 90 - keep / 2; a1 = 90 + keep / 2
    for i in range(n):
        t0 = math.radians(a0 + (a1 - a0) * i / n); t1 = math.radians(a0 + (a1 - a0) * (i + 1) / n)
        l = lambda t: l_min + (l_max - l_min) * (0.5 + 0.5 * math.sin(t))
        P = lambda rr, t, y: (cx + rr * math.cos(t), y, cz + rr * math.sin(t))
        mt = (t0 + t1) / 2
        ro, ri = r + thick, r
        m.oriented([P(ro, t0, y0), P(ro, t1, y0), P(ro, t1, y0 + l(t1)), P(ro, t0, y0 + l(t0))], (math.cos(mt), 0, math.sin(mt)), mat)
        m.oriented([P(ri, t0, y0), P(ri, t1, y0), P(ri, t1, y0 + l(t1)), P(ri, t0, y0 + l(t0))], (-math.cos(mt), 0, -math.sin(mt)), "sig_lens_dark")   # 内側は黒(つや消し)
        m.oriented([P(ri, t0, y0 + l(t0)), P(ro, t0, y0 + l(t0)), P(ro, t1, y0 + l(t1)), P(ri, t1, y0 + l(t1))], (0, 1, 0), mat)           # 先端縁
    if keep < 360:
        for t, sg in ((math.radians(a0), -1), (math.radians(a1), 1)):
            ln = l_min + (l_max - l_min) * (0.5 + 0.5 * math.sin(t))
            m.oriented([(cx + r * math.cos(t), y0, cz + r * math.sin(t)), (cx + (r + thick) * math.cos(t), y0, cz + (r + thick) * math.sin(t)),
                        (cx + (r + thick) * math.cos(t), y0 + ln, cz + (r + thick) * math.sin(t)), (cx + r * math.cos(t), y0 + ln, cz + r * math.sin(t))],
                       (-math.sin(t) * sg, 0, math.cos(t) * sg), mat)


def _arc_band(m, cx, cz, r_in, r_out, a0, a1, y0, y1, mat, n=14):
    """z-x平面上の円弧帯(庇/フード)をy方向に押し出し"""
    for i in range(n):
        t0 = math.radians(a0 + (a1 - a0) * i / n); t1 = math.radians(a0 + (a1 - a0) * (i + 1) / n)
        P = lambda r, t, y: (cx_(cx, r, t), y, cz + r * math.sin(t))
        cx_ = lambda cx, r, t: cx + r * math.cos(t)
        mt = (t0 + t1) / 2
        m.oriented([P(r_out, t0, y0), P(r_out, t1, y0), P(r_out, t1, y1), P(r_out, t0, y1)], (math.cos(mt), 0, math.sin(mt)), mat)
        m.oriented([P(r_in, t0, y0), P(r_in, t1, y0), P(r_in, t1, y1), P(r_in, t0, y1)], (-math.cos(mt), 0, -math.sin(mt)), mat)
    for t, sgn in ((math.radians(a0), -1), (math.radians(a1), 1)):
        m.oriented([(cx + r_in * math.cos(t), y0, cz + r_in * math.sin(t)), (cx + r_out * math.cos(t), y0, cz + r_out * math.sin(t)),
                    (cx + r_out * math.cos(t), y1, cz + r_out * math.sin(t)), (cx + r_in * math.cos(t), y1, cz + r_in * math.sin(t))],
                   (-math.sin(t) * sgn, 0, math.cos(t) * sgn), mat)
    m.oriented([(cx + r_in * math.cos(math.radians(a0)), y1, cz + r_in * math.sin(math.radians(a0))), (cx + r_out * math.cos(math.radians(a0)), y1, cz + r_out * math.sin(math.radians(a0))),
                (cx + r_out * math.cos(math.radians(a1)), y1, cz + r_out * math.sin(math.radians(a1))), (cx + r_in * math.cos(math.radians(a1)), y1, cz + r_in * math.sin(math.radians(a1)))], (0, 1, 0), mat)


def plate_poly(m, pts_xz, y0, y1, mat):
    """(x,z)の多角形を y0..y1 に押し出す(CCWに正規化)"""
    prof = [(z, x) for x, z in pts_xz]
    area = sum(prof[i][0] * prof[(i + 1) % len(prof)][1] - prof[(i + 1) % len(prof)][0] * prof[i][1] for i in range(len(prof)))
    if area < 0:
        prof = prof[::-1]
    m.prism(prof, "y", y0, y1, mat)


def _circle_pts(cx, cz, r, n=14):
    return [(cx + r * math.cos(2 * math.pi * i / n), cz + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


# ---------------- 車両用信号灯器 ----------------
ERA = {  # era: (筐体材質, 全奥行, -, -, -)。薄型LED(フラット型)は約6cm
    "old": ("sig_housing_old", 0.34, 0.10, 0.26, 0.022),
    "led": ("sig_housing_led", 0.2, 0.03, 0.13, 0.012),
    "slim": ("sig_housing_slim", 0.065, 0.012, 0.07, 0.008),
}


LENS_R = {"old": 0.15, "led": 0.15, "slim": 0.125}     # φ300 / φ300 / φ250


def _lamp(m, era, cx, cz, state, hood=True, arrow=None, r=None):
    """灯火1つ: 凸レンズ(ドーム)+ベゼル+筒形フード(先端が斜めにカット)。旧式は深く長いフード、薄型は浅く短いフード。"""
    housing, depth, recess, hood_len, hood_t = ERA[era]
    r = r or LENS_R[era]
    face = depth * 0.62 if era != "slim" else depth * 0.7
    mat = STATE_MAT[state]
    # レンズ: 浅いドーム(円盤を段積み)
    for k, (rr, dy) in enumerate(((r * 0.97, 0.0), (r * 0.9, 0.008), (r * 0.7, 0.014))):
        m.cyl(cx, face + dy, cz, rr, 0.006, "y", mat, 28)
    # ベゼル(レンズ押え)
    m.tube(cx, face - 0.004, cz, r + 0.014, r - 0.004, 0.03, "y", housing if era != "slim" else "sig_housing_slim_black", 28)
    if era == "led" and state != "off":
        for k in range(18):     # LED素子(同心円状の点)
            ang = 2 * math.pi * k / 18
            m.cyl(cx + r * 0.62 * math.cos(ang), face + 0.02, cz + r * 0.62 * math.sin(ang), 0.006, 0.003, "y", "sig_white_icon", 6)
        for k in range(8):
            ang = 2 * math.pi * k / 8 + 0.2
            m.cyl(cx + r * 0.32 * math.cos(ang), face + 0.02, cz + r * 0.32 * math.sin(ang), 0.006, 0.003, "y", "sig_white_icon", 6)
    if arrow is not None:
        _arrow_icon(m, cx, face + 0.02, cz, r * 0.8, arrow, "sig_white_icon" if state != "off" else "sig_lens_dark")
    if hood:
        # 旧式: 長い筒形(深い)。LED: 中程度。薄型: 短い(上側のみ=ひさし)
        if era == "old":
            hood_sleeve(m, cx, cz, r + 0.016, face + 0.02, 0.27, 0.12, 0.012, housing, 28, 360)
        elif era == "led":
            hood_sleeve(m, cx, cz, r + 0.016, face + 0.02, 0.2, 0.05, 0.008, housing, 28, 360)
        else:
            hood_sleeve(m, cx, cz, r + 0.012, face + 0.01, 0.1, 0.0, 0.005, "sig_housing_slim_black", 24, 230)


def _arrow_icon(m, cx, y, cz, s, direction, mat):
    """灯火内の矢印(左/直進/右)"""
    ang = {"left": 180, "up": 90, "right": 0}[direction]
    a = math.radians(ang)
    pts = [(-.8, -.16), (.1, -.16), (.1, -.42), (.85, 0), (.1, .42), (.1, .16), (-.8, .16)]
    P = [(cx + (px * math.cos(a) - py * math.sin(a)) * s * 0.9, cz + (px * math.sin(a) + py * math.cos(a)) * s * 0.9) for px, py in pts]
    plate_poly(m, P, y, y + 0.006, mat)


def _housing(m, era, sx, sz):
    """角丸+前面面取り+背面テーパーの筐体。ヒンジ/ラッチ/水抜き/ケーブル引込口/放熱リブ付き"""
    housing, depth, recess, hood_len, hood_t = ERA[era]
    face = depth * 0.62 if era != "slim" else depth * 0.7
    r = 0.07 if era != "slim" else 0.045
    front = rrect(sx, sz, r)
    ch = scale_pts(front, 0.985)
    rear = scale_pts(front, 0.86 if era != "slim" else 0.94)
    # 前面(わずかに面取り) → 本体 → 背面にテーパー
    cap_poly(m, ch, face, housing, True)
    loft_poly(m, ch, face, front, face - 0.012, housing)
    loft_poly(m, front, face - 0.012, front, face * 0.5, housing)
    loft_poly(m, front, face * 0.5, rear, 0.0, housing)
    cap_poly(m, rear, 0.0, housing, False)
    if era != "slim":
        # 背面の放熱/補強リブ(縦3本)と上面の庇縁
        for i in (-1, 0, 1):
            m.box(i * sx * 0.25 - 0.012, -0.012, -sz * 0.35, i * sx * 0.25 + 0.012, 0.01, sz * 0.35, housing)
    # ヒンジ(右端: 上下2か所の円筒)と左端のラッチ
    for z in (sz * 0.3, -sz * 0.3):
        m.cyl(sx / 2 - 0.02, face - 0.04, z, 0.014, 0.05, "y", "steel_galv", 8)
        m.box(-sx / 2 + 0.005, face - 0.05, z - 0.02, -sx / 2 + 0.03, face - 0.01, z + 0.02, "steel_galv")
    # 下面: 水抜き孔と配線引込口
    m.cyl(0.0, face * 0.5, -sz / 2 - 0.012, 0.016, 0.02, "z", "rubber", 10)
    for dx in (-0.2, 0.2):
        m.cyl(dx * sx / 1.2, face * 0.6, -sz / 2 - 0.004, 0.004, 0.006, "z", "sig_lens_dark", 6)


def _strap_brackets(m, sx, sz, xs, z_up, z_dn, y_pipe=-0.14):
    """灯器背面から腕(パイプ)へ回す取付金具: 縦のバンドプレート+Uボルトクランプ"""
    for x in xs:
        m.box(x - 0.025, y_pipe - 0.02, z_dn, x + 0.025, -0.0, z_up, "steel_galv")           # 縦帯板
        for z in (z_up, z_dn):
            m.tube(x, y_pipe, z, 0.034, 0.024, 0.06, "x", "steel_galv", 12) if False else None
            m.cyl(x - 0.03, y_pipe, z, 0.0, 0.0, "x", "steel_galv", 4) if False else None
            m.box(x - 0.045, y_pipe - 0.035, z - 0.035, x + 0.045, y_pipe + 0.035, z + 0.035, "steel_galv")     # クランプ本体
            m.cyl(x, y_pipe - 0.04, z, 0.012, 0.03, "y", "steel_gray", 6)


def vehicle_head(m, era, layout, state, vertical=False, arrows=None, backplate=None):
    """3灯(青・黄・赤)。横型は視点左から 青・黄・赤。arrows: 下段の補助矢印灯 [(方向, 状態)]"""
    housing, depth, recess, hood_len, hood_t = ERA[era]
    face = depth * 0.62 if era != "slim" else depth * 0.7
    r = LENS_R[era]
    pitch = r * 2 + 0.05
    L = pitch * 3 + 0.07
    Wd = r * 2 + 0.1
    order = ["g", "y", "r"]
    pos = [((-(i - 1) * pitch, 0.0) if not vertical else (0.0, -(i - 1) * pitch)) for i in range(3)]
    sx, sz = (L, Wd) if not vertical else (Wd, L)
    _housing(m, era, sx, sz)
    # 取付金具: 腕(上下2本のパイプ y=-0.14 z=±0.3)へ
    if not vertical:
        _strap_brackets(m, sx, sz, (-sx * 0.3, sx * 0.3), 0.3, -0.3)
    else:
        _strap_brackets(m, sx, sz, (0.0,), sz / 2 + 0.05, -sz / 2 - 0.05)
    for (px, pz), kind in zip(pos, order):
        _lamp(m, era, px, pz, kind if kind == state else "off")
        if kind == state:
            light(m, "sphere", (px, face + 0.05, pz), 220 if era != "old" else 120, STATE_COL[kind], 0.05, (0, 1, 0))
    if backplate:   # バックプレート(黒+白反射縁)
        bw, bh = sx + 0.14, sz + 0.14
        m.box(-bw / 2, -0.016, -bh / 2, bw / 2, -0.004, bh / 2, "sig_backplate")
        for (x0, z0, x1, z1) in ((-bw / 2, -bh / 2, bw / 2, -bh / 2 + 0.018), (-bw / 2, bh / 2 - 0.018, bw / 2, bh / 2), (-bw / 2, -bh / 2, -bw / 2 + 0.018, bh / 2), (bw / 2 - 0.018, -bh / 2, bw / 2, bh / 2)):
            m.box(x0, -0.0185, z0, x1, -0.016, z1, "sig_reflect")
    if arrows:   # 補助矢印灯(下段): 小型筐体+φ250灯火
        aw = pitch * len(arrows) + 0.07
        z0 = -sz / 2 - 0.02 - 0.15
        sub = type(m)()
        _housing(sub, era, aw, 0.3)
        m.add(sub.transformed(0, 0, 0, z0))
        for i, (d, st) in enumerate(arrows):
            cx = -((i - (len(arrows) - 1) / 2) * pitch)
            _lamp(m, era, cx, z0, "g" if st == "g" else "off", hood=era != "slim", arrow=d, r=0.11)
            if st == "g":
                light(m, "sphere", (cx, face + 0.05, z0), 90, STATE_COL["g"], 0.04, (0, 1, 0))


for _era in ("old", "led", "slim"):
    for _st in ("r", "g", "y"):
        reg(f"sigv_h3_{_era}_{_st}", (lambda e, s: lambda m, W, H, r: vehicle_head(m, e, "h", s, False, None, e != "old"))(_era, _st), W=1.1, H=0.5, cat="信号(車両用)")
    reg(f"sigv_v3_{_era}_g", (lambda e: lambda m, W, H, r: vehicle_head(m, e, "v", "g", True, None, e != "old"))(_era), W=0.5, H=1.1, cat="信号(車両用)")
    reg(f"sigv_v3_{_era}_r", (lambda e: lambda m, W, H, r: vehicle_head(m, e, "v", "r", True, None, e != "old"))(_era), W=0.5, H=1.1, cat="信号(車両用)")
for _era in ("led", "slim"):
    reg(f"sigv_h3_{_era}_g_arrow", (lambda e: lambda m, W, H, r: vehicle_head(m, e, "h", "g", False, [("left", "g"), ("up", "off"), ("right", "g")], True))(_era), W=1.1, H=0.9, cat="信号(車両用)")
    reg(f"sigv_h3_{_era}_r_arrow", (lambda e: lambda m, W, H, r: vehicle_head(m, e, "h", "r", False, [("left", "g"), ("up", "off"), ("right", "off")], True))(_era), W=1.1, H=0.9, cat="信号(車両用)")


@mod("sigv_blinker_yellow", W=0.45, H=0.45, cat="信号(車両用)")
def _(m, W, H, rng):   # 点滅式(黄)1灯
    m.box(-0.2, 0, -0.2, 0.2, 0.14, 0.2, "sig_housing_led")
    m.box(-0.04, -0.07, -0.2, 0.04, 0, 0.2, "steel_galv")
    _lamp(m, "led", 0, 0, "y")
    light(m, "sphere", (0, 0.16, 0), 220, STATE_COL["y"], 0.05, (0, 1, 0))


@mod("sigv_blinker_red_yellow", W=0.45, H=0.8, cat="信号(車両用)")
def _(m, W, H, rng):   # 赤/黄交互点滅(踏切・交差点予告)
    m.box(-0.2, 0, -0.38, 0.2, 0.14, 0.38, "sig_housing_led")
    m.box(-0.04, -0.07, -0.38, 0.04, 0, 0.38, "steel_galv")
    _lamp(m, "led", 0, 0.19, "r"); _lamp(m, "led", 0, -0.19, "off")
    light(m, "sphere", (0, 0.16, 0.19), 220, STATE_COL["r"], 0.05, (0, 1, 0))


# ---------------- 歩行者用信号灯器 ----------------
def _person(m, cx, cz, s, walking, y, mat):
    plate_poly(m, _circle_pts(cx, cz + 0.36 * s, 0.07 * s, 10), y, y + 0.006, mat)
    if not walking:
        plate_poly(m, [(cx - .1 * s, cz + .26 * s), (cx + .1 * s, cz + .26 * s), (cx + .09 * s, cz - .02 * s), (cx - .09 * s, cz - .02 * s)], y, y + 0.006, mat)
        plate_poly(m, [(cx - .09 * s, cz - .02 * s), (cx - .01 * s, cz - .02 * s), (cx - .01 * s, cz - .36 * s), (cx - .09 * s, cz - .36 * s)], y, y + 0.006, mat)
        plate_poly(m, [(cx + .01 * s, cz - .02 * s), (cx + .09 * s, cz - .02 * s), (cx + .09 * s, cz - .36 * s), (cx + .01 * s, cz - .36 * s)], y, y + 0.006, mat)
    else:
        plate_poly(m, [(cx - .08 * s, cz + .26 * s), (cx + .1 * s, cz + .26 * s), (cx + .08 * s, cz - .02 * s), (cx - .1 * s, cz - .02 * s)], y, y + 0.006, mat)
        plate_poly(m, [(cx - .1 * s, cz - .02 * s), (cx - .01 * s, cz - .02 * s), (cx - .2 * s, cz - .36 * s), (cx - .28 * s, cz - .34 * s)], y, y + 0.006, mat)
        plate_poly(m, [(cx + .0 * s, cz - .02 * s), (cx + .1 * s, cz - .02 * s), (cx + .16 * s, cz - .36 * s), (cx + .08 * s, cz - .36 * s)], y, y + 0.006, mat)
        plate_poly(m, [(cx - .12 * s, cz + .22 * s), (cx - .2 * s, cz + .04 * s), (cx - .15 * s, cz + .02 * s), (cx - .07 * s, cz + .18 * s)], y, y + 0.006, mat)


def _seg_digit(m, cx, cz, h, d, y, mat):
    segs = {"1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "0": "abcdef"}[str(d)]
    w, t = h * 0.55, h * 0.1
    pos = {"a": (0, h / 2 - t / 2, w, t), "g": (0, 0, w, t), "d": (0, -h / 2 + t / 2, w, t), "f": (-w / 2 + t / 2, h / 4, t, h / 2 - t), "b": (w / 2 - t / 2, h / 4, t, h / 2 - t),
           "e": (-w / 2 + t / 2, -h / 4, t, h / 2 - t), "c": (w / 2 - t / 2, -h / 4, t, h / 2 - t)}
    for k in segs:
        px, pz, sw, sh = pos[k]
        px = -px   # +y側から見たときに正しい向き(x反転)
        m.box(cx + px - sw / 2, y, cz + pz - sh / 2, cx + px + sw / 2, y + 0.004, cz + pz + sh / 2, mat)


def ped_head(m, era, state, countdown=False):
    """歩行者用: 一辺250mmの正方形2面(上=赤立ち人形、下=青歩行人形)。角丸筐体+前傾の庇(側板付き)+柱へ抱え込むアーム金具。"""
    housing, depth, recess, hood_len, hood_t = ERA[era]
    ph = 0.25 if era != "old" else 0.27
    Wd = ph + 0.075
    gap = 0.045
    H = ph * 2 + gap + 0.07 + (0.2 if countdown else 0)
    face = (depth * 0.7 if era != "old" else depth * 0.6)
    r = 0.045
    front = rrect(Wd, H, r)
    rear = scale_pts(front, 0.9)
    cap_poly(m, scale_pts(front, 0.985), face, housing, True)
    loft_poly(m, scale_pts(front, 0.985), face, front, face - 0.01, housing)
    loft_poly(m, front, face - 0.01, front, face * 0.45, housing)
    loft_poly(m, front, face * 0.45, rear, 0.0, housing)
    cap_poly(m, rear, 0.0, housing, False)
    z_top = H / 2
    z_red = z_top - 0.035 - ph / 2
    z_grn = z_red - ph - gap
    for z, kind in ((z_red, "r"), (z_grn, "g")):
        on = (kind == state)
        # 丸隅の灯火窓(黒面)+人形
        win = rrect(ph, ph, 0.02, 3)
        plate_poly(m, [(x, zz + z) for x, zz in win], face, face + 0.01, "sig_lens_dark")
        icon = ("sig_red" if kind == "r" else "sig_green") if on else "sig_lens_dark"
        _person(m, 0, z - 0.005, 0.7 * ph / 0.25 * 0.34 / 0.34 * 0.95, kind == "g", face + 0.01, icon)
        # 窓枠
        ow = rrect(ph + 0.014, ph + 0.014, 0.026, 3)
        for i in range(len(ow)):
            j = (i + 1) % len(ow)
            a0, a1 = (ow[i][0], ow[i][1] + z), (ow[j][0], ow[j][1] + z)
            f0, f1 = (win[i][0], win[i][1] + z), (win[j][0], win[j][1] + z)
            m.oriented([(a0[0], face, a0[1]), (a1[0], face, a1[1]), (a1[0], face + 0.014, a1[1]), (a0[0], face + 0.014, a0[1])], (a0[0], 0, a0[1] - z), housing)
        if on:
            light(m, "rect", (0, face + 0.04, z), 140, STATE_COL[kind], size=(0.2, 0.2), direction=(0, 1, 0))
    if countdown:
        zc = -H / 2 + 0.11
        plate_poly(m, [(x, zz + zc) for x, zz in rrect(ph * 0.9, 0.16, 0.015, 3)], face, face + 0.01, "sig_lens_dark")
        if state == "g":
            for i, dg in enumerate((1, 2)):
                _seg_digit(m, -(i - 0.5) * 0.1, zc, 0.12, dg, face + 0.01, "sig_amber_digit")
    # 庇: 前に傾斜して下がるひさし(上板)+左右の三角側板
    vis = 0.15 if era != "slim" else 0.1
    plate_poly_yz(m, [(face - 0.02, z_top + 0.0), (face + vis, z_top - 0.02), (face + vis, z_top + 0.006), (face - 0.02, z_top + 0.02)], -Wd / 2 - 0.012, Wd / 2 + 0.012, housing)
    for sx in (-1, 1):
        x = sx * (Wd / 2 + 0.002)
        plate_poly_yz(m, [(face - 0.02, z_top + 0.0), (face + vis, z_top - 0.02), (face + vis * 0.6, z_top - 0.1), (face - 0.02, z_top - 0.16)], x - 0.004, x + 0.004, housing)
    # 柱へ抱え込む上下2本のアーム(φ34)+柱バンド。柱軸は y=-0.16
    for z in (z_top - 0.05, -z_top + 0.05):
        m.cyl(0, -0.16, z, 0.017, 0.0, "x", "steel_galv", 8) if False else None
        m.cyl(-0.03, 0.0, z, 0.017, 0.0, "y", "steel_galv", 8) if False else None
        m.box(-0.03, -0.16, z - 0.016, 0.03, 0.0, z + 0.016, "steel_galv")                  # 腕
        m.tube(0, -0.16, z - 0.03, 0.068, 0.056, 0.06, "z", "steel_galv", 14)                # 柱バンド
        m.box(-0.012, -0.095, z - 0.025, 0.012, -0.08, z + 0.025, "steel_gray")              # ボルト座


def plate_poly_yz(m, pts_yz, x0, x1, mat):
    """(y,z)の多角形を x0..x1 に押し出す"""
    prof = [(y, z) for y, z in pts_yz]
    area = sum(prof[i][0] * prof[(i + 1) % len(prof)][1] - prof[(i + 1) % len(prof)][0] * prof[i][1] for i in range(len(prof)))
    if area < 0:
        prof = prof[::-1]
    m.prism(prof, "x", x0, x1, mat)


for _era in ("old", "led", "slim"):
    for _st in ("r", "g"):
        reg(f"sigp_{_era}_{_st}", (lambda e, s: lambda m, W, H, r: ped_head(m, e, s))(_era, _st), W=0.36, H=0.8, cat="信号(歩行者用)")
for _st in ("r", "g"):
    reg(f"sigp_led_countdown_{_st}", (lambda s: lambda m, W, H, r: ped_head(m, "led", s, True))(_st), W=0.36, H=1.05, cat="信号(歩行者用)")


@mod("sigp_pushbutton", W=0.16, H=0.36, cat="信号(歩行者用)")
def _(m, W, H, rng):   # 押ボタン箱(音響付き)
    m.box(-0.07, 0, -0.17, 0.07, 0.07, 0.17, "pole_white")
    m.box(-0.05, 0.07, 0.0, 0.05, 0.085, 0.14, "sig_housing_slim_black")
    m.cyl(0, 0.085, 0.07, 0.03, 0.012, "y", "sig_red", 16)
    m.box(-0.05, 0.07, -0.14, 0.05, 0.078, -0.02, "sig_reflect")
    for k in range(4):
        m.cyl(-0.03 + k * 0.02, 0.07, 0.15, 0.004, 0.006, "y", "sig_lens_dark", 6)


# ---------------- 信号柱・制御機 ----------------
def pole(m, h, r0, r1, mat, n=16, base=True, cap=True):
    """先細りの鋼管柱(根巻き+ベースプレート+アンカーカバー+キャップ+点検口)"""
    if base:
        m.cyl(0, 0, 0, r0 + 0.07, 0.02, "z", "steel_galv", 20)
        m.lathe(0, 0, 0.02, [(r0 + 0.045, 0), (r0 + 0.03, 0.22), (r0, 0.3)], mat, n)
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            m.cyl((r0 + 0.045) * math.cos(a), (r0 + 0.045) * math.sin(a), 0.02, 0.012, 0.05, "z", "steel_galv", 6)
        m.box(-0.045, r0 - 0.002, 0.45, 0.045, r0 + 0.012, 0.75, "steel_galv")   # 点検口
    prof = [(r0, 0.3), (r1, h)] if False else [(r0 + (r1 - r0) * t / 6, 0.3 + (h - 0.3) * t / 6) for t in range(7)]
    m.lathe(0, 0, 0, prof, mat, n)
    if cap:
        m.lathe(0, 0, h, [(r1, 0), (r1 * 1.1, 0.01), (r1 * 0.6, 0.05), (0.001, 0.07)], mat, n)


for _nm, _h, _r0, _r1, _mat in (("galv", 6.6, 0.1, 0.07, "steel_galv"), ("white", 6.6, 0.1, 0.07, "pole_white"), ("dark", 6.6, 0.1, 0.07, "pole_dark")):
    reg(f"pole_signal_{_nm}", (lambda h, r0, r1, mt: lambda m, W, H, r: pole(m, h, r0, r1, mt))(_h, _r0, _r1, _mat), W=0.3, H=_h, cat="信号柱")
reg("pole_signal_ped_3m", lambda m, W, H, r: pole(m, 3.4, 0.055, 0.05, "steel_galv", 14), W=0.2, H=3.4, cat="信号柱")
reg("pole_signal_ped_white", lambda m, W, H, r: pole(m, 3.4, 0.055, 0.05, "pole_white", 14), W=0.2, H=3.4, cat="信号柱")


def mast_arm(m, L, h=6.2, mat="steel_galv", n=16):
    """片持ちアーム式信号柱: 太い主柱 + 先細りのアーム(+x方向にL) + 補剛材"""
    pole(m, h, 0.15, 0.1, mat, 18, cap=False)
    z = h - 0.35
    seg = 8
    for i in range(seg):
        r_a = 0.085 - 0.04 * i / seg; x0 = i * L / seg; x1 = (i + 1) * L / seg
        rise = 0.18 * i / seg
        m.cyl(x0, 0, z + rise, r_a, x1 - x0 + 0.01, "x", mat, 12)
    m.lathe(0, 0, h - 0.05, [(0.1, 0), (0.12, 0.12), (0.001, 0.14)], mat, 18)
    # 補剛ステー(主柱とアームを結ぶ斜材)
    steps = 6
    for i in range(steps):
        t0, t1 = i / steps, (i + 1) / steps
        x0, z0 = 0.1 + t0 * 1.4, z - 1.0 + t0 * 0.9
        x1, z1 = 0.1 + t1 * 1.4, z - 1.0 + t1 * 0.9
        m.cyl(x0, 0, z0, 0.02, 0.0, "x", mat, 6) if False else None
    m.prism([(z - 1.0 + 0.0, 0.1), (z - 0.1, 1.5), (z - 0.06, 1.5), (z - 0.96, 0.1)], "y", -0.015, 0.015, mat)


for _L in (3.0, 6.0, 9.0, 12.0):
    for _nm, _mat in (("galv", "steel_galv"), ("white", "pole_white")):
        reg(f"pole_signal_arm_{int(_L)}m_{_nm}", (lambda L, mt: lambda m, W, H, r: mast_arm(m, L, 6.2, mt))(_L, _mat), W=_L, H=6.4, cat="信号柱")


def signal_arm(m, L, kind="parallel"):
    """信号柱から出る腕(標準2.0m・最長3.5m)。原点=柱軸、+x=腕の向き、パイプ位置は y=0(灯器背面金具が掛かる)。
    kind: parallel=上下2本の平行アーム(三角補剛付き) / single=直線1本 / arc=古い円弧アーム"""
    r = 0.024
    mat = "steel_galv"
    # 柱への取付クランプ(2か所)
    def clamp(z):
        m.tube(0, 0, z - 0.04, 0.075, 0.062, 0.08, "z", mat, 16)
        m.box(0.0, -0.04, z - 0.04, 0.12, 0.04, z + 0.04, mat)
        m.cyl(0.04, 0.045, z, 0.01, 0.0, "y", "steel_gray", 6) if False else None
    if kind == "parallel":
        for z in (0.3, -0.3):
            clamp(z)
            m.cyl(0.1, 0, z, r, L - 0.1, "x", mat, 10)
            m.lathe(L, 0, z - 0.0, [(0.0, 0)], mat, 4) if False else None
            m.cyl(L, 0, z, r + 0.004, 0.012, "x", "steel_gray", 10)     # 先端キャップ
        m.box(0.08, -0.012, -0.3, 0.1, 0.012, 0.3, mat)                  # 柱側の縦つなぎ板
        # 三角補剛(柱側)
        plate_poly_xz = [(0.1, 0.0), (0.7, 0.3), (0.7, 0.285), (0.1, -0.015)]
        prof = [(z, x) for x, z in plate_poly_xz]
        m.prism(prof[::-1] if False else prof, "y", -0.006, 0.006, mat)
    elif kind == "single":
        clamp(0.0)
        m.cyl(0.1, 0, 0, 0.032, L - 0.1, "x", mat, 12)
        m.cyl(L, 0, 0, 0.036, 0.012, "x", "steel_gray", 12)
        m.prism([(-0.45, 0.1), (-0.04, L * 0.55), (-0.02, L * 0.55), (-0.43, 0.1)], "y", -0.008, 0.008, mat)      # 下から支えるステー
    else:   # 円弧アーム(古い型): 柱頭から上に反ってから水平へ
        steps = 10
        pts = [(0.1 + (L - 0.1) * (i / steps), 0.45 * math.sin(math.pi / 2 * (1 - i / steps)) ** 2 * 0 + 0.55 * (1 - math.cos(math.pi * i / steps)) / 2 * 0) for i in range(steps + 1)]
        for i in range(steps):
            t0, t1 = i / steps, (i + 1) / steps
            x0, z0 = 0.1 + (L - 0.1) * t0, 0.5 * math.sin(math.pi * t0 / 2) * (1 - t0) * 0 + 0.55 * (1 - math.cos(math.pi * t0 / 2)) - 0.55 * 0 + 0.0
            x1, z1 = 0.1 + (L - 0.1) * t1, 0.55 * (1 - math.cos(math.pi * t1 / 2))
            ang = math.atan2(z1 - z0, x1 - x0)
            ln = math.hypot(x1 - x0, z1 - z0)
            q = type(m)()
            q.cyl(0, 0, 0, 0.03, ln + 0.004, "x", mat, 10)
            m.add(q.transformed(0, x0, 0, z0 - 0.0)) if False else None
            c, sn = math.cos(ang), math.sin(ang)
            seg = [(0, -0.03), (ln, -0.03), (ln, 0.03), (0, 0.03)]
            P = [(x0 + a * c - b * sn, z0 + a * sn + b * c) for a, b in seg]
            m.prism([(zz, xx) for xx, zz in P], "y", -0.03, 0.03, mat)
        clamp(0.0)


for _L, _k in ((2.0, "parallel"), (3.0, "parallel"), (3.5, "parallel"), (2.0, "single"), (3.0, "single"), (2.0, "arc")):
    reg(f"signal_arm_{_k}_{int(_L * 10)}", (lambda L, k: lambda m, W, H, r: signal_arm(m, L, k))(_L, _k), W=_L, H=0.7, cat="信号柱")


@mod("signal_controller", W=0.85, H=1.25, cat="信号柱")
def _(m, W, H, rng):   # 信号制御機(キャビネット): 扉、換気ルーバー、錠、基礎
    m.box(-0.45, -0.28, 0, 0.45, 0.28, 0.12, "rc_concrete")
    m.box(-0.4, -0.23, 0.12, 0.4, 0.23, 1.22, "pole_white")
    m.box(-0.4, 0.23, 0.2, 0.4, 0.235, 1.15, "pole_white")
    for dx in (-0.2, 0.2):
        m.box(dx - 0.18, 0.234, 0.28, dx + 0.18, 0.244, 1.05, "pole_white")      # 扉(観音)
    m.box(-0.012, 0.234, 0.28, 0.012, 0.246, 1.05, "grout")
    for i in range(8):
        m.box(0.07, 0.244, 0.32 + i * 0.012, 0.3, 0.25, 0.328 + i * 0.012, "steel_gray")  # ルーバー
    m.box(-0.06, 0.244, 0.62, -0.03, 0.262, 0.75, "steel_galv")
    m.box(-0.42, -0.25, 1.22, 0.42, 0.25, 1.27, "pole_white")                      # 屋根


# ---------------- 街路灯(USD光源付き) ----------------
def _luminaire_cobra(m, x, z, mat="steel_galv", lumens=15000, length=0.8):
    """コブラヘッド型(上面カバー+下面レンズ)。xが先端中心。光源=DiskLight(下向き)"""
    m.lathe(x, 0, z, [(0.001, -0.1), (0.2, -0.06), (0.26, 0.0), (0.2, 0.06), (0.001, 0.1)], mat, 20) if False else None
    m.box(x - length / 2 + 0.2, -0.14, z - 0.02, x + length / 2 + 0.2, 0.14, z + 0.1, mat)
    m.box(x - length / 2 + 0.25, -0.12, z - 0.035, x + length / 2 + 0.15, 0.12, z - 0.02, "lamp_lens")
    m.box(x - length / 2 + 0.2 - 0.04, -0.1, z - 0.0, x - length / 2 + 0.2, 0.1, z + 0.08, mat)
    light(m, "disk", (x + 0.2, 0, z - 0.04), lumens, (1.0, 0.93, 0.8), 0.24, (0, 0, -1), cct=4000)


def _arm(m, L, z, mat, rise=0.6, r=0.04):
    """曲がりアーム: 柱から出て上に反って水平に出る(+x方向)"""
    pts = [(0.0, z), (0.3 * L, z + rise * 0.45), (0.7 * L, z + rise * 0.8), (L, z + rise)]
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        ln = math.hypot(x1 - x0, z1 - z0)
        ang = math.atan2(z1 - z0, x1 - x0)
        pr = [(-r, ln * 0), (r, 0)]
        c, s = math.cos(ang), math.sin(ang)
        q = [(x0 + (-r) * -s, z0 + (-r) * c), (x0 + r * -s, z0 + r * c), (x1 + r * -s, z1 + r * c), (x1 + (-r) * -s, z1 + (-r) * c)]
        m.prism([(zz, xx) for xx, zz in q][::-1] if False else [(zz, xx) for xx, zz in q], "y", -r, r, mat)


def lamp_cobra(m, H=9.0, arm=2.2, double=False, mat="steel_galv", led=False):
    pole(m, H, 0.1, 0.065, mat, 8, cap=False)
    for sgn in ((1, -1) if double else (1,)):
        mm = m
        a = type(m)()
        _arm(a, arm, H - 0.5, mat, 0.7)
        _luminaire_cobra(a, arm, H + 0.2 - 0.05, mat, 14000 if led else 12000)
        if sgn < 0:
            a = a.transformed(math.pi)
        m.add(a)


reg("light_cobra_9m", lambda m, W, H, r: lamp_cobra(m, 9.0, 2.2, False, "steel_galv"), W=2.8, H=10, cat="街路灯")
reg("light_cobra_9m_dark", lambda m, W, H, r: lamp_cobra(m, 9.0, 2.2, False, "pole_dark", True), W=2.8, H=10, cat="街路灯")
reg("light_cobra_double_10m", lambda m, W, H, r: lamp_cobra(m, 10.0, 2.0, True, "steel_galv"), W=5.0, H=11, cat="街路灯")
reg("light_cobra_12m_white", lambda m, W, H, r: lamp_cobra(m, 12.0, 2.6, False, "pole_white", True), W=3.4, H=13, cat="街路灯")


@mod("light_led_flat_8m", W=2.4, H=9, cat="街路灯")
def _(m, W, H, rng):   # 現行LED平板型(薄型・水平)
    pole(m, 8.0, 0.09, 0.06, "pole_dark", 12, cap=False)
    m.box(-0.06, -0.06, 7.9, 1.9, 0.06, 8.05, "pole_dark")
    m.box(1.2, -0.17, 7.82, 2.1, 0.17, 7.96, "alu_black")
    m.box(1.22, -0.15, 7.8, 2.08, 0.15, 7.82, "lamp_lens")
    light(m, "rect", (1.65, 0, 7.78), 16000, (1.0, 0.97, 0.9), size=(0.86, 0.3), direction=(0, 0, -1), cct=5000)


@mod("light_old_mercury_9m", W=2.2, H=10, cat="街路灯")
def _(m, W, H, rng):   # 旧式: 水銀灯(丸いドーム笠+湾曲アーム)
    pole(m, 9.0, 0.11, 0.07, "steel_galv", 12, cap=False)
    a = type(m)()
    _arm(a, 1.9, 8.4, "steel_galv", 0.9, 0.035)
    a.lathe(1.9, 0, 9.0, [(0.001, 0.0), (0.12, -0.02), (0.3, -0.12), (0.36, -0.2), (0.3, -0.26), (0.2, -0.3)], "steel_galv", 20)
    a.lathe(1.9, 0, 8.74, [(0.2, 0.0), (0.1, -0.06), (0.001, -0.1)], "lamp_globe", 16)
    light(a, "sphere", (1.9, 0, 8.7), 9000, (0.85, 0.95, 1.0), 0.1, (0, 0, -1), cct=5700)
    m.add(a)


def _globe(m, cx, cy, z, r, mat="lamp_globe", n=18):
    prof = [(r * math.sin(t), r - r * math.cos(t)) for t in [math.pi * i / 10 for i in range(11)]]
    m.lathe(cx, cy, z, [(max(0.001, p[0]), p[1]) for p in prof], mat, n)


@mod("light_postop_globe_4m", W=0.5, H=4.5, cat="街路灯")
def _(m, W, H, rng):   # ポストトップ球形(公園・遊歩道)
    pole(m, 3.8, 0.09, 0.06, "pole_dark", 12, cap=False)
    m.lathe(0, 0, 3.8, [(0.06, 0), (0.12, 0.05), (0.15, 0.1), (0.05, 0.14)], "pole_dark", 12)
    _globe(m, 0, 0, 3.92, 0.22)
    m.lathe(0, 0, 4.36, [(0.2, 0), (0.1, 0.07), (0.001, 0.12)], "pole_dark", 14)
    light(m, "sphere", (0, 0, 4.1), 6000, (1.0, 0.92, 0.8), 0.2, (0, 0, -1), cct=3500)


@mod("light_postop_lantern_3m", W=0.5, H=3.6, cat="街路灯")
def _(m, W, H, rng):   # 角型ランタン(シティ/プロムナード)
    pole(m, 3.0, 0.08, 0.055, "pole_brown", 12, cap=False)
    m.box(-0.19, -0.19, 3.0, 0.19, 0.19, 3.05, "pole_brown")
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        m.box(sx * 0.18 - 0.012, sy * 0.18 - 0.012, 3.05, sx * 0.18 + 0.012, sy * 0.18 + 0.012, 3.5, "pole_brown")
    m.box(-0.17, -0.17, 3.06, 0.17, 0.17, 3.48, "lamp_globe")
    m.lathe(0, 0, 3.5, [(0.27, 0), (0.15, 0.1), (0.001, 0.18)], "pole_brown", 4)
    light(m, "sphere", (0, 0, 3.27), 4500, (1.0, 0.9, 0.75), 0.12, (0, 0, -1), cct=3000)


@mod("light_ped_low_3m", W=0.6, H=3.4, cat="街路灯")
def _(m, W, H, rng):   # 歩道用の低い照明(円錐シェード)
    pole(m, 3.2, 0.06, 0.045, "pole_dark", 10, cap=False)
    m.lathe(0, 0, 3.15, [(0.05, 0), (0.28, 0.04), (0.3, 0.07), (0.1, 0.16), (0.001, 0.2)], "pole_dark", 18)
    m.cyl(0, 0, 3.12, 0.2, 0.02, "z", "lamp_lens", 18)
    light(m, "disk", (0, 0, 3.1), 3500, (1.0, 0.95, 0.85), 0.2, (0, 0, -1), cct=4000)


@mod("light_bollard_led_1m", W=0.25, H=1.1, cat="街路灯")
def _(m, W, H, rng):   # 足元灯ボラード
    m.cyl(0, 0, 0, 0.1, 1.0, "z", "alu_black", 16)
    m.cyl(0, 0, 1.0, 0.105, 0.025, "z", "alu_silver", 16)
    m.box(-0.07, 0.095, 0.7, 0.07, 0.108, 0.82, "lamp_lens")
    light(m, "rect", (0, 0.11, 0.76), 350, (1.0, 0.92, 0.8), size=(0.14, 0.12), direction=(0, 1, 0), cct=3000)


@mod("light_highmast_25m", W=3.0, H=26, cat="街路灯")
def _(m, W, H, rng):   # ハイマスト(広場・駐車場): 6灯の昇降式照明環
    m.cyl(0, 0, 0, 0.55, 0.3, "z", "rc_concrete", 16)
    m.lathe(0, 0, 0.3, [(0.28, 0), (0.25, 4), (0.2, 14), (0.15, 24.5)], "steel_galv", 16)
    m.cyl(0, 0, 24.5, 0.55, 0.14, "z", "steel_gray", 18)
    m.lathe(0, 0, 24.64, [(0.5, 0), (0.15, 0.4), (0.001, 0.7)], "steel_gray", 18)
    for k in range(6):
        a = k * math.pi / 3
        x, y = 0.95 * math.cos(a), 0.95 * math.sin(a)
        l = type(m)()
        l.box(-0.28, -0.18, 0, 0.28, 0.18, 0.1, "alu_black")
        l.box(-0.25, -0.15, -0.015, 0.25, 0.15, 0, "lamp_lens")
        m.add(l.transformed(a, x, y, 24.2))
        light(m, "rect", (x, y, 24.18), 25000, (1.0, 0.97, 0.92), size=(0.5, 0.3), direction=(0, 0, -1), cct=5000)


# ---------------- 標識柱・標識板 ----------------
def sign_pole(m, h, r=0.038):
    m.cyl(0, 0, 0, r, h, "z", "steel_galv", 14)
    m.cyl(0, 0, h, r * 1.15, 0.018, "z", "steel_galv", 14)
    m.cyl(0, 0, 0, r * 1.6, 0.06, "z", "rc_concrete", 14)   # 根元の補強


for _h in (2.4, 3.0, 3.6):
    reg(f"pole_sign_round_{int(_h * 10)}", (lambda h: lambda m, W, H, r: sign_pole(m, h))(_h), W=0.1, H=_h, cat="標識柱")


@mod("pole_sign_large", W=0.3, H=5.0, cat="標識柱")
def _(m, W, H, rng):   # 案内標識用の太柱
    m.lathe(0, 0, 0, [(0.13, 0), (0.1, 4.8)], "steel_galv", 16)
    m.cyl(0, 0, 0, 0.2, 0.08, "z", "rc_concrete", 16)
    m.lathe(0, 0, 4.8, [(0.1, 0), (0.11, 0.02), (0.001, 0.1)], "steel_galv", 16)


@mod("pole_sign_double_large", W=2.4, H=5.0, cat="標識柱")
def _(m, W, H, rng):   # 大型案内標識の2本柱(間隔は板幅に合わせスケール)
    for x in (-0.5, 0.5):
        m.lathe(x, 0, 0, [(0.1, 0), (0.08, 4.8)], "steel_galv", 14)
        m.cyl(x, 0, 0, 0.16, 0.08, "z", "rc_concrete", 14)
    for z in (3.2, 4.4):
        m.box(-0.55, -0.1, z, 0.55, -0.06, z + 0.06, "steel_galv")


@mod("pole_sign_cantilever", W=5.0, H=7.0, cat="標識柱")
def _(m, W, H, rng):   # 片持ち式(車道へ張り出す緑/青の案内標識用): 柱+アーム
    pole(m, 6.4, 0.16, 0.12, "steel_galv", 16, cap=False)
    for i in range(7):
        m.cyl(i * 0.7, 0, 6.1 + 0.03 * i, 0.07 - 0.005 * i, 0.72, "x", "steel_galv", 10)
    m.prism([(5.3, 0.1), (6.0, 2.6), (6.06, 2.6), (5.36, 0.1)], "y", -0.02, 0.02, "steel_galv")


def _board(m, name, info):
    w, h, shape = info["w"], info["h"], info["shape"]
    u0, v0, u1, v1 = info["uv"]
    t = 0.022
    if shape == "circle":
        sil = _circle_pts(0, 0, w / 2, 28)
    elif shape == "diamond":
        sil = [(0, h / 2), (-w / 2, 0), (0, -h / 2), (w / 2, 0)]
    elif shape == "tri_inv":
        sil = [(-w / 2, h * 0.48), (w / 2, h * 0.48), (0, -h * 0.48)]
    else:
        r = min(w, h) * 0.06
        sil = [(-w / 2 + r, h / 2), (w / 2 - r, h / 2), (w / 2, h / 2 - r), (w / 2, -h / 2 + r), (w / 2 - r, -h / 2), (-w / 2 + r, -h / 2), (-w / 2, -h / 2 + r), (-w / 2, h / 2 - r)]
    plate_poly(m, sil, -t, 0, "sign_back")
    # 表面: アトラスのアルファ(外形)で切り抜かれる貼り付け面。+y向き、左右を鏡像に(視点から見て画像が正しく読める)
    P = [(w / 2, 0.0008, -h / 2), (-w / 2, 0.0008, -h / 2), (-w / 2, 0.0008, h / 2), (w / 2, 0.0008, h / 2)]
    m.oriented(P, (0, 1, 0), "sign_atlas", [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    # 背面のバンド金具(柱抱き)
    for z in (h * 0.28, -h * 0.28) if h < 1.0 else (h * 0.3, -h * 0.3):
        m.box(-0.05, -t - 0.045, z - 0.025, 0.05, -t, z + 0.025, "steel_galv")
        m.box(-0.012, -t - 0.045, z - 0.025, 0.012, -t - 0.02, z + 0.025, "steel_gray")


try:
    _meta = load_meta()
    for _name, _info in _meta["signs"].items():
        reg(f"sign_{_name}", (lambda n, i: lambda m, W, H, r: _board(m, n, i))(_name, _info), W=_info["w"], H=_info["h"], cat="標識(" + _info["cat"] + ")", sign=_name)
except FileNotFoundError:
    pass
