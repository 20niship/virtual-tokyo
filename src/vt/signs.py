"""日本の道路標識アトラス(1枚のPNG + 配置JSON)を手続き生成する。
uv run python -m vt.signs  →  assets/textures/sign_atlas.png, sign_atlas.json
各標識は実寸(m)に比例した解像度(PPM px/m)で描き、シェルフ詰めでアトラスへ。図柄は標準規格を簡略化した代表図。"""
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[2] / "assets/textures"
PPM = 380          # 1mあたりpx (600mm標識=228px)
SS = 2             # スーパーサンプル
AW, AH = 4096, 4096
RED, BLUE, WHITE, BLACK, YELLOW = (205, 8, 30), (0, 84, 166), (250, 250, 250), (20, 20, 20), (252, 200, 0)
GBLUE, GGREEN, GRAY = (0, 78, 152), (0, 116, 70), (120, 120, 120)

_font = None


def font(sz):
    global _font
    if _font is None:
        for line in subprocess.run(["fc-list", ":lang=ja", "file"], capture_output=True, text=True).stdout.splitlines():
            if "NotoSansCJK-Bold" in line or "NotoSansCJK-Medium" in line:
                _font = line.split(":")[0].strip()
                if "Bold" in _font:
                    break
    return ImageFont.truetype(_font, int(sz), index=0)


class C:
    """正規化座標(0..1, 左上原点)で描く小さなキャンバス"""

    def __init__(self, w, h):
        self.w, self.h = w * SS, h * SS
        self.im = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def p(self, x, y):
        return (x * self.w, y * self.h)

    def poly(self, pts, fill, outline=None, width=0):
        self.d.polygon([self.p(*q) for q in pts], fill=fill, outline=outline, width=width)

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, width=0):
        a, b = self.p(cx - rx, cy - ry), self.p(cx + rx, cy + ry)
        self.d.ellipse([a, b], fill=fill, outline=outline, width=width)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=0, r=0):
        a, b = self.p(x0, y0), self.p(x1, y1)
        if r:
            self.d.rounded_rectangle([a, b], r * self.w, fill=fill, outline=outline, width=width)
        else:
            self.d.rectangle([a, b], fill=fill, outline=outline, width=width)

    def line(self, pts, fill, width):
        self.d.line([self.p(*q) for q in pts], fill=fill, width=int(width * self.w), joint="curve")

    def text(self, s, x, y, size, fill=BLACK, anchor="mm", stretch=1.0):
        f = font(size * self.h)
        if stretch == 1.0:
            self.d.text(self.p(x, y), s, font=f, fill=fill, anchor=anchor)
        else:
            t = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0)); ImageDraw.Draw(t).text(self.p(x, y), s, font=f, fill=fill, anchor=anchor)
            bb = t.getbbox()
            if bb:
                c = t.crop(bb); c = c.resize((int(c.width * stretch), c.height), Image.LANCZOS)
                cx, cy = self.p(x, y)
                self.im.alpha_composite(c, (int(cx - c.width / 2), int(cy - c.height / 2)))

    def done(self):
        return self.im.resize((self.w // SS, self.h // SS), Image.LANCZOS)


# ---- 図柄(0..1の正方形内に描く) ----
def car(c, cx, cy, s, col=BLACK):
    c.poly([(cx - .36 * s, cy + .08 * s), (cx - .34 * s, cy - .02 * s), (cx - .2 * s, cy - .04 * s), (cx - .1 * s, cy - .2 * s), (cx + .14 * s, cy - .2 * s),
            (cx + .26 * s, cy - .04 * s), (cx + .38 * s, cy), (cx + .38 * s, cy + .12 * s), (cx - .36 * s, cy + .12 * s)], col)
    for dx in (-.2, .22):
        c.ellipse(cx + dx * s, cy + .14 * s, .07 * s, .07 * s, col, WHITE, 2)


def truck(c, cx, cy, s, col=BLACK):
    c.rect(cx - .4 * s, cy - .2 * s, cx + .08 * s, cy + .12 * s, col)
    c.poly([(cx + .1 * s, cy - .1 * s), (cx + .26 * s, cy - .1 * s), (cx + .38 * s, cy + .02 * s), (cx + .38 * s, cy + .12 * s), (cx + .1 * s, cy + .12 * s)], col)
    for dx in (-.26, .0, .28):
        c.ellipse(cx + dx * s, cy + .14 * s, .06 * s, .06 * s, col, WHITE, 2)


def moto(c, cx, cy, s, col=BLACK):
    for dx in (-.24, .24):
        c.ellipse(cx + dx * s, cy + .1 * s, .13 * s, .13 * s, None, col, int(.03 * c.w))
    c.line([(cx - .24 * s, cy + .1 * s), (cx - .05 * s, cy - .05 * s), (cx + .12 * s, cy - .05 * s), (cx + .24 * s, cy + .1 * s)], col, .035)
    c.line([(cx + .08 * s, cy - .05 * s), (cx + .14 * s, cy - .18 * s), (cx + .24 * s, cy - .2 * s)], col, .03)
    c.poly([(cx - .12 * s, cy - .12 * s), (cx + .04 * s, cy - .12 * s), (cx, cy - .04 * s), (cx - .12 * s, cy - .04 * s)], col)


def bike(c, cx, cy, s, col=BLACK):
    for dx in (-.22, .22):
        c.ellipse(cx + dx * s, cy + .12 * s, .13 * s, .13 * s, None, col, max(2, int(.022 * c.w)))
    c.line([(cx - .22 * s, cy + .12 * s), (cx - .02 * s, cy - .08 * s), (cx + .22 * s, cy + .12 * s)], col, .022 * s)
    c.line([(cx - .02 * s, cy - .08 * s), (cx + .12 * s, cy - .08 * s), (cx + .22 * s, cy + .12 * s)], col, .022 * s)
    c.line([(cx - .06 * s, cy - .14 * s), (cx - .02 * s, cy - .08 * s)], col, .022 * s)
    c.line([(cx + .1 * s, cy - .08 * s), (cx + .13 * s, cy - .18 * s)], col, .022 * s)


def ped(c, cx, cy, s, col=BLACK, flip=1):
    c.ellipse(cx, cy - .3 * s, .06 * s, .06 * s, col)
    c.poly([(cx - .07 * s, cy - .22 * s), (cx + .07 * s, cy - .22 * s), (cx + .1 * s * flip, cy + .02 * s), (cx + .06 * s, cy + .02 * s), (cx, cy - .04 * s), (cx - .06 * s, cy + .02 * s), (cx - .1 * s * flip, cy + .02 * s)], col)
    c.line([(cx - .02 * s, cy), (cx - .1 * s * flip, cy + .28 * s)], col, .035 * s); c.line([(cx + .02 * s, cy), (cx + .1 * s * flip, cy + .28 * s)], col, .035 * s)
    c.line([(cx - .05 * s, cy - .18 * s), (cx - .14 * s, cy - .04 * s)], col, .03 * s); c.line([(cx + .05 * s, cy - .18 * s), (cx + .14 * s, cy - .06 * s)], col, .03 * s)


def child(c, cx, cy, s, col=BLACK):
    ped(c, cx - .12 * s, cy, s * .9, col); ped(c, cx + .14 * s, cy + .08 * s, s * .6, col)


def arrow(c, cx, cy, s, ang, col=WHITE, head=1.0):
    """ang度: 0=右, 90=上"""
    a = math.radians(ang); ca, sa = math.cos(a), -math.sin(a)

    def T(x, y):
        return (cx + (x * ca - y * sa) * s, cy + (x * sa + y * ca) * s)
    pts = [(-.4, -.07), (.1, -.07), (.1, -.2 * head), (.4, 0), (.1, .2 * head), (.1, .07), (-.4, .07)]
    c.poly([T(*q) for q in pts], col)


def stripes(c, y0, y1, col=WHITE):
    for i in range(6):
        c.rect(.1 + i * .14, y0, .1 + i * .14 + .07, y1, col)


# ---- 地(外形)の描画 ----
def disc(c, fill, border=None, bw=.1):
    c.ellipse(.5, .5, .5, .5, border or fill)
    if border:
        c.ellipse(.5, .5, .5 - bw, .5 - bw, fill)


def reg(c, inner=WHITE, bw=.11):          # 赤縁の円(規制)
    disc(c, inner, RED, bw)


def slash(c, w=.09):
    c.line([(.2, .8), (.8, .2)], RED, w)


def diamond(c, bg=YELLOW):                # 警戒標識(菱形)
    c.poly([(.5, .0), (1, .5), (.5, 1), (0, .5)], bg)
    c.poly([(.5, .06), (.94, .5), (.5, .94), (.06, .5)], None, BLACK, 4 * SS)
    c.poly([(.5, .075), (.925, .5), (.5, .925), (.075, .5)], bg)


def rectsign(c, bg, border=WHITE, r=.04, bw=.025):
    c.rect(0, 0, 1, 1, bg, r=r)
    c.rect(bw, bw, 1 - bw, 1 - bw, None, border, 3 * SS, r=r)


def tri_inv(c, fill=WHITE, border=RED):
    c.poly([(.0, .04), (1, .04), (.5, .95)], border)
    c.poly([(.12, .13), (.88, .13), (.5, .8)], fill)


# 名前 → (カテゴリ, 形状, 幅m, 高さm, 描画関数)
SIGNS = {}


def sg(name, cat, shape, w, h):
    def deco(fn):
        SIGNS[name] = (cat, shape, w, h, fn)
        return fn
    return deco


def add(name, cat, shape, w, h, fn):
    SIGNS[name] = (cat, shape, w, h, fn)


R6 = 0.6
# ===== 規制標識 =====
def f_noent(c):
    disc(c, RED); c.rect(.14, .42, .86, .58, WHITE)
add("reg_no_entry", "規制", "circle", R6, R6, f_noent)
add("reg_road_closed", "規制", "circle", R6, R6, lambda c: (reg(c), None)[1])
add("reg_no_vehicles", "規制", "circle", R6, R6, lambda c: (reg(c), car(c, .5, .52, 1.0, BLACK), car(c, .5, .52, 0, BLACK))[0])
add("reg_no_motor", "規制", "circle", R6, R6, lambda c: (reg(c), car(c, .5, .52, 1.0, BLACK))[0])
add("reg_no_bicycle", "規制", "circle", R6, R6, lambda c: (reg(c), bike(c, .5, .5, 1.5, BLACK))[0])
add("reg_no_moto", "規制", "circle", R6, R6, lambda c: (reg(c), moto(c, .5, .5, 1.5, BLACK))[0])
add("reg_no_truck", "規制", "circle", R6, R6, lambda c: (reg(c), truck(c, .5, .5, 1.2, BLACK))[0])
add("reg_no_pedestrian", "規制", "circle", R6, R6, lambda c: (reg(c), ped(c, .5, .5, 1.1, BLACK))[0])
add("reg_no_bike_ped", "規制", "circle", R6, R6, lambda c: (reg(c), ped(c, .33, .5, .9, BLACK), bike(c, .66, .55, 1.0, BLACK))[0])
add("reg_no_overtake", "規制", "circle", R6, R6, lambda c: (reg(c), car(c, .32, .5, .9, BLACK), car(c, .68, .5, .9, RED))[0])
add("reg_no_parking", "規制", "circle", R6, R6, lambda c: (disc(c, BLUE, RED, .09), c.ellipse(.5, .5, .39, .39, BLUE), slash(c))[0])
def f_nostop(c):
    disc(c, BLUE, RED, .09); slash(c); c.line([(.2, .2), (.8, .8)], RED, .09)
add("reg_no_stopping", "規制", "circle", R6, R6, f_nostop)
add("reg_no_uturn", "規制", "circle", R6, R6, lambda c: (reg(c), c.line([(.62, .75), (.62, .38), (.38, .38), (.38, .55)], BLACK, .07), c.poly([(.3, .52), (.46, .52), (.38, .66)], BLACK))[0])
add("reg_no_right", "規制", "circle", R6, R6, lambda c: (reg(c), c.line([(.4, .8), (.4, .45), (.65, .45)], BLACK, .07), c.poly([(.62, .34), (.78, .45), (.62, .56)], BLACK), slash(c, .08))[0])
add("reg_no_left", "規制", "circle", R6, R6, lambda c: (reg(c), c.line([(.6, .8), (.6, .45), (.35, .45)], BLACK, .07), c.poly([(.38, .34), (.22, .45), (.38, .56)], BLACK), slash(c, .08))[0])
add("reg_no_cross", "規制", "circle", R6, R6, lambda c: (reg(c), ped(c, .5, .5, 1.0, BLACK), c.line([(.35, .8), (.65, .2)], RED, .06))[0])
add("reg_stop", "規制", "tri_inv", 0.8, 0.8, lambda c: (c.poly([(0, .04), (1, .04), (.5, .96)], RED), c.poly([(.1, .11), (.9, .11), (.5, .84)], WHITE), c.poly([(.17, .15), (.83, .15), (.5, .78)], None, RED, 2), c.text("止まれ", .5, .36, .2, RED), c.text("STOP", .5, .55, .13, RED))[0] if False else None)
SIGNS.pop("reg_stop", None)


def f_stop(c):
    c.poly([(0, .04), (1, .04), (.5, .96)], RED)
    c.poly([(.1, .11), (.9, .11), (.5, .85)], WHITE)
    c.text("止まれ", .5, .31, .15, RED, stretch=0.95)
    c.text("STOP", .5, .52, .085, RED)
add("reg_stop", "規制", "tri_inv", 0.8, 0.8, f_stop)
def f_slow(c):
    c.poly([(0, .04), (1, .04), (.5, .96)], RED); c.poly([(.1, .11), (.9, .11), (.5, .85)], WHITE)
    c.text("徐行", .5, .36, .17, RED); c.text("SLOW", .5, .56, .1, RED)
add("reg_slow", "規制", "tri_inv", 0.6, 0.6, f_slow)
for v in (20, 30, 40, 50, 60, 80, 100):
    add(f"reg_speed_{v}", "規制", "circle", R6, R6, (lambda v: lambda c: (reg(c, WHITE, .12), c.text(str(v), .5, .52, .42 if v < 100 else .34, BLACK, stretch=1.0)))(v))
for v in (50, 60):
    add(f"reg_minspeed_{v}", "規制", "circle", R6, R6, (lambda v: lambda c: (disc(c, BLUE), c.text(str(v), .5, .45, .36, WHITE), c.line([(.25, .75), (.75, .75)], WHITE, .045)))(v))
for t in ("3.0", "5.5", "8", "10", "20"):
    add(f"reg_weight_{t.replace('.', 'p')}", "規制", "circle", R6, R6, (lambda t: lambda c: (reg(c), c.text(t + "t", .5, .52, .3, BLACK)))(t))
for t in ("2.5", "3.0", "3.5", "4.0"):
    add(f"reg_height_{t.replace('.', 'p')}", "規制", "circle", R6, R6, (lambda t: lambda c: (reg(c), c.text(t + "m", .5, .52, .28, BLACK), c.line([(.3, .22), (.7, .22)], BLACK, .035)))(t))
for t in ("1.9", "2.0", "2.5"):
    add(f"reg_width_{t.replace('.', 'p')}", "規制", "circle", R6, R6, (lambda t: lambda c: (reg(c), c.text(t + "m", .5, .52, .28, BLACK), arrow(c, .5, .22, .3, 0, BLACK, .5), arrow(c, .5, .22, .3, 180, BLACK, .5)))(t))
def f_oneway(c):
    c.rect(0, 0, 1, 1, BLUE, r=.08); c.rect(.03, .03, .97, .97, None, WHITE, 3 * SS, r=.06); arrow(c, .5, .5, .8, 0, WHITE, 1.3)
add("reg_oneway_right", "規制", "rect", 0.6, 0.6, f_oneway)
add("reg_oneway_left", "規制", "rect", 0.6, 0.6, lambda c: (c.rect(0, 0, 1, 1, BLUE, r=.08), c.rect(.03, .03, .97, .97, None, WHITE, 3 * SS, r=.06), arrow(c, .5, .5, .8, 180, WHITE, 1.3))[0])
for nm, ang in (("straight", 90), ("right", 0), ("left", 180)):
    add(f"reg_only_{nm}", "規制", "circle", R6, R6, (lambda ang: lambda c: (disc(c, BLUE), arrow(c, .5, .5, .7, ang, WHITE, 1.3)))(ang))
add("reg_only_straight_right", "規制", "circle", R6, R6, lambda c: (disc(c, BLUE), arrow(c, .5, .55, .6, 90, WHITE, 1.2), c.line([(.5, .5), (.78, .5)], WHITE, .07), c.poly([(.74, .38), (.9, .5), (.74, .62)], WHITE))[0])
add("reg_only_straight_left", "規制", "circle", R6, R6, lambda c: (disc(c, BLUE), arrow(c, .5, .55, .6, 90, WHITE, 1.2), c.line([(.5, .5), (.22, .5)], WHITE, .07), c.poly([(.26, .38), (.1, .5), (.26, .62)], WHITE))[0])
add("reg_ped_only", "規制", "circle", R6, R6, lambda c: (disc(c, BLUE), ped(c, .5, .5, 1.05, WHITE))[0])
add("reg_bike_only", "規制", "circle", R6, R6, lambda c: (disc(c, BLUE), bike(c, .5, .5, 1.5, WHITE))[0])
add("reg_bike_ped", "規制", "circle", R6, R6, lambda c: (disc(c, BLUE), ped(c, .33, .5, .85, WHITE), bike(c, .68, .55, 1.0, WHITE))[0])
add("reg_bus_lane", "規制", "rect", 0.6, 0.6, lambda c: (c.rect(0, 0, 1, 1, BLUE, r=.08), c.text("バス", .5, .5, .34, WHITE))[0])
add("reg_priority_road", "指示", "diamond", 0.6, 0.6, lambda c: (c.poly([(.5, 0), (1, .5), (.5, 1), (0, .5)], WHITE, BLACK, 3 * SS), c.poly([(.5, .12), (.88, .5), (.5, .88), (.12, .5)], YELLOW)))
add("reg_park_time", "規制", "circle", R6, R6, lambda c: (disc(c, BLUE), c.text("P", .5, .42, .4, WHITE), c.text("60分", .5, .73, .16, WHITE)))
# ===== 指示標識 =====
def f_crosswalk(c):
    c.rect(0, 0, 1, 1, BLUE, r=.06); c.poly([(.5, .06), (.94, .86), (.06, .86)], WHITE); stripes(c, .7, .84, BLUE); ped(c, .5, .45, .5, BLUE)
add("ins_crosswalk", "指示", "rect", 0.6, 0.6, f_crosswalk)
add("ins_bike_crossing", "指示", "rect", 0.6, 0.6, lambda c: (c.rect(0, 0, 1, 1, BLUE, r=.06), c.poly([(.5, .06), (.94, .86), (.06, .86)], WHITE), bike(c, .5, .55, 1.0, BLUE)))
add("ins_parking", "指示", "rect", 0.6, 0.6, lambda c: (c.rect(0, 0, 1, 1, BLUE, r=.06), c.text("P", .5, .5, .62, WHITE)))
add("ins_stopping_ok", "指示", "rect", 0.6, 0.6, lambda c: (c.rect(0, 0, 1, 1, BLUE, r=.06), car(c, .5, .5, 1.2, WHITE)))
add("ins_one_lane", "指示", "rect", 0.6, 0.6, lambda c: (c.rect(0, 0, 1, 1, BLUE, r=.06), arrow(c, .5, .5, .6, 90, WHITE)))
# ===== 警戒標識(菱形) =====
def warn(name, fn, w=0.6):
    add(name, "警戒", "diamond", w, w, lambda c: (diamond(c), fn(c)))
warn("warn_cross", lambda c: (c.rect(.44, .2, .56, .8, BLACK), c.rect(.2, .44, .8, .56, BLACK)))
warn("warn_t", lambda c: (c.rect(.2, .44, .8, .56, BLACK), c.rect(.44, .44, .56, .8, BLACK)))
warn("warn_y", lambda c: (c.rect(.44, .5, .56, .8, BLACK), c.line([(.5, .55), (.28, .25)], BLACK, .1), c.line([(.5, .55), (.72, .25)], BLACK, .1)))
warn("warn_roundabout", lambda c: (c.ellipse(.5, .5, .2, .2, None, BLACK, 6 * SS), arrow(c, .5, .22, .2, 0, BLACK), arrow(c, .78, .5, .2, 270, BLACK), arrow(c, .22, .5, .2, 90, BLACK)))
warn("warn_signal", lambda c: (c.rect(.36, .2, .64, .8, BLACK, r=.05), c.ellipse(.5, .32, .07, .07, RED), c.ellipse(.5, .5, .07, .07, YELLOW), c.ellipse(.5, .68, .07, .07, (0, 190, 90))))
def f_railway(c):
    c.line([(.2, .2), (.8, .8)], BLACK, .09); c.line([(.8, .2), (.2, .8)], BLACK, .09); c.line([(.5, .5), (.5, .88)], BLACK, .06)
warn("warn_railway", f_railway)
warn("warn_school", lambda c: (child(c, .5, .5, .8)))
warn("warn_pedestrian", lambda c: ped(c, .5, .5, .9))
warn("warn_roadwork", lambda c: (ped(c, .42, .56, .6), c.poly([(.55, .75), (.8, .75), (.675, .5)], BLACK), c.line([(.55, .4), (.78, .6)], BLACK, .04)))
warn("warn_slippery", lambda c: (car(c, .5, .42, .8), c.line([(.25, .72), (.35, .62), (.45, .72), (.55, .62), (.65, .72), (.75, .62)], BLACK, .04)))
warn("warn_rockfall", lambda c: (c.poly([(.2, .8), (.5, .3), (.8, .8)], BLACK), c.ellipse(.42, .3, .06, .06, BLACK), c.ellipse(.6, .22, .05, .05, BLACK)))
warn("warn_animal", lambda c: (c.poly([(.2, .7), (.3, .45), (.55, .42), (.7, .3), (.8, .38), (.7, .5), (.78, .7), (.68, .7), (.62, .56), (.38, .56), (.3, .7)], BLACK)))
warn("warn_merge_left", lambda c: (c.line([(.5, .85), (.5, .2)], BLACK, .09), c.line([(.3, .85), (.3, .6), (.46, .4)], BLACK, .07)))
warn("warn_merge_right", lambda c: (c.line([(.5, .85), (.5, .2)], BLACK, .09), c.line([(.7, .85), (.7, .6), (.54, .4)], BLACK, .07)))
warn("warn_lane_reduce", lambda c: (c.line([(.35, .85), (.35, .2)], BLACK, .08), c.line([(.65, .85), (.65, .55), (.5, .25)], BLACK, .08)))
warn("warn_width_reduce", lambda c: (c.line([(.3, .2), (.4, .5), (.4, .85)], BLACK, .08), c.line([(.7, .2), (.6, .5), (.6, .85)], BLACK, .08)))
warn("warn_up_steep", lambda c: (c.poly([(.2, .75), (.8, .75), (.8, .4)], BLACK), c.text("10%", .45, .62, .16, WHITE)))
warn("warn_down_steep", lambda c: (c.poly([(.2, .75), (.8, .75), (.2, .4)], BLACK), c.text("10%", .55, .62, .16, WHITE)))
warn("warn_winding", lambda c: c.line([(.4, .85), (.6, .65), (.4, .5), (.6, .35), (.5, .18)], BLACK, .08))
warn("warn_curve_right", lambda c: (c.line([(.35, .85), (.35, .55), (.55, .3), (.7, .3)], BLACK, .09), c.poly([(.66, .18), (.84, .3), (.66, .42)], BLACK)))
warn("warn_curve_left", lambda c: (c.line([(.65, .85), (.65, .55), (.45, .3), (.3, .3)], BLACK, .09), c.poly([(.34, .18), (.16, .3), (.34, .42)], BLACK)))
warn("warn_two_way", lambda c: (arrow(c, .5, .32, .35, 90, BLACK), arrow(c, .5, .68, .35, 270, BLACK)))
warn("warn_bike_crossing", lambda c: bike(c, .5, .5, 1.1))
warn("warn_crosswind", lambda c: (c.line([(.2, .35), (.7, .35)], BLACK, .05), c.line([(.2, .5), (.8, .5)], BLACK, .05), c.line([(.2, .65), (.7, .65)], BLACK, .05), c.poly([(.62, .26), (.82, .5), (.62, .74)], None, BLACK, 3 * SS)))
warn("warn_bump", lambda c: (c.poly([(.2, .7), (.4, .7), (.5, .52), (.6, .7), (.8, .7), (.8, .78), (.2, .78)], BLACK)))
warn("warn_other", lambda c: c.text("!", .5, .52, .5, BLACK))
warn("warn_pedestrian_crossing_ahead", lambda c: (c.poly([(.5, .12), (.82, .82), (.18, .82)], None, BLACK, 4 * SS), ped(c, .5, .55, .42)))
# ===== 補助標識 =====
def aux(name, text, w=0.45, h=0.25, sub=None):
    def f(c):
        c.rect(0, 0, 1, 1, WHITE, r=.06); c.rect(.03, .05, .97, .95, None, BLACK, 3 * SS, r=.05)
        lines = text.split("\n")
        for i, t in enumerate(lines):
            c.text(t, .5, (i + 1) / (len(lines) + 1), min(.34 if len(lines) == 1 else .27, 1.5 / max(len(t), 3)), BLACK)
    add(name, "補助", "rect", w, h, f)
aux("aux_time_8_20", "8-20")
aux("aux_time_24h", "24時間")
aux("aux_except_sun", "日曜・休日を除く", 0.45, 0.25)
aux("aux_zone", "この先\n区域内", 0.45, 0.3)
aux("aux_weight_3", "重量 3t以上")
aux("aux_large_truck", "大型貨物\n等・特定中型")
aux("aux_school", "通学路")
aux("aux_except_local", "沿道を除く")
aux("aux_start", "始点", 0.45, 0.3)
aux("aux_end", "終点", 0.45, 0.3)
aux("aux_100m", "100m先")
aux("aux_speed_check", "速度取締中")
aux("aux_bike_except", "自転車を除く")
aux("aux_pedestrian_priority", "歩行者\n優先")
# ===== 案内標識 =====
def guide(name, bg, text, sub=None, w=1.6, h=0.8, arrow_dir=None, kind="road"):
    def f(c):
        rectsign(c, bg, WHITE, .035, .022)
        n = len(text.split("\n"))
        for i, t in enumerate(text.split("\n")):
            c.text(t, .46 if arrow_dir else .5, .28 + i * .3 if n > 1 else .42, .26 if n == 1 else .22, WHITE)
        if sub:
            c.text(sub, .5, .78, .13, WHITE)
        if arrow_dir is not None:
            arrow(c, .86, .5, .26, arrow_dir, WHITE, 1.2)
    add(name, "案内", "rect", w, h, f)
guide("gd_odaiba_left", GBLUE, "お台場\nOdaiba", None, 1.6, 0.8, 180)
guide("gd_odaiba_right", GBLUE, "お台場\nOdaiba", None, 1.6, 0.8, 0)
guide("gd_straight_toyosu", GBLUE, "豊洲\nToyosu", "357", 1.8, 0.9, 90)
guide("gd_tokyo_left", GBLUE, "東京駅\nTokyo Sta.", None, 1.8, 0.9, 180)
guide("gd_shinagawa_right", GBLUE, "品川\nShinagawa", None, 1.8, 0.9, 0)
guide("gd_aomi", GBLUE, "青海\nAomi", None, 1.6, 0.8, 90)
guide("gd_ariake", GBLUE, "有明\nAriake", None, 1.6, 0.8, 0)
guide("gd_big_sight", GBLUE, "東京ビッグサイト", None, 2.0, 0.6, 0)
guide("gd_fuji", GBLUE, "フジテレビ", None, 1.6, 0.6, 180)
guide("gd_station_yurikamome", GBLUE, "ゆりかもめ\n台場駅", None, 1.6, 0.8, 90)
guide("gd_parking", GBLUE, "駐車場\nParking", None, 1.2, 0.6, 0)
# 高速道路(緑)
guide("ex_odaiba_exit", GGREEN, "お台場\n出口 800m", "11", 2.2, 1.1, 90)
guide("ex_wangan", GGREEN, "湾岸線\n葛西・羽田", "B", 2.2, 1.1, 90)
guide("ex_toshin", GGREEN, "都心環状線\n銀座・汐留", "C1", 2.2, 1.1, 90)
guide("ex_rainbow", GGREEN, "レインボー\nブリッジ", "11", 2.2, 1.1, 90)
guide("ex_exit_only", GGREEN, "出口\nEXIT", None, 1.6, 0.8, 315)
guide("ex_entrance", GGREEN, "入口\nENTRANCE", None, 1.6, 0.8, 45)
guide("ex_distance", GGREEN, "お台場まで\n2km", None, 1.6, 0.8, 90)
guide("ex_speed_limit_50", GGREEN, "50", None, 0.6, 0.6, None)
# 路線番号マーク
def route_kokudo(num):
    def f(c):
        c.poly([(.5, .0), (1, .18), (.86, 1), (.14, 1), (0, .18)], BLUE)
        c.poly([(.5, .05), (.94, .2), (.82, .94), (.18, .94), (.06, .2)], None, WHITE, 3 * SS)
        c.text(str(num), .5, .55, .34, WHITE)
    return f
for n in (15, 357, 1, 131):
    add(f"route_kokudo_{n}", "案内", "shield", 0.45, 0.45, route_kokudo(n))
def route_kendo(num):
    def f(c):
        c.poly([(.2, .06), (.8, .06), (1, .5), (.8, .94), (.2, .94), (0, .5)], WHITE, BLUE, 3 * SS)
        c.poly([(.24, .12), (.76, .12), (.93, .5), (.76, .88), (.24, .88), (.07, .5)], None, BLUE, 4 * SS)
        c.text(str(num), .5, .52, .3, BLUE)
    return f
for n in (316, 482, 304):
    add(f"route_kendo_{n}", "案内", "shield", 0.45, 0.45, route_kendo(n))
def route_shuto(code):
    def f(c):
        c.ellipse(.5, .5, .5, .5, GGREEN); c.ellipse(.5, .5, .43, .43, None, WHITE, 3 * SS)
        c.text(code, .5, .5, .36, WHITE)
    return f
for code in ("C1", "B", "11", "9", "K1"):
    add(f"route_shuto_{code}", "案内", "circle", 0.45, 0.45, route_shuto(code))
# その他案内(ピクト)
def pict(name, bg, fn, w=0.45, h=0.45):
    add(name, "案内", "rect", w, h, lambda c: (c.rect(0, 0, 1, 1, bg, r=.08), c.rect(.04, .04, .96, .96, None, WHITE, 3 * SS, r=.06), fn(c)))
pict("gd_p_toilet", GBLUE, lambda c: (ped(c, .33, .5, .6, WHITE), ped(c, .67, .5, .6, WHITE, -1)))
pict("gd_p_shelter", GGREEN, lambda c: (c.poly([(.5, .18), (.84, .45), (.16, .45)], WHITE), c.rect(.28, .45, .72, .78, WHITE), ped(c, .5, .62, .3, GGREEN)))
pict("gd_p_emergency_phone", GBLUE, lambda c: (c.text("非常\n電話", .5, .5, .24, WHITE)))
pict("gd_p_info", GBLUE, lambda c: (c.text("i", .5, .5, .6, WHITE)))
pict("gd_p_bus", GBLUE, lambda c: (c.rect(.2, .28, .8, .66, WHITE, r=.06), c.ellipse(.34, .72, .07, .07, WHITE), c.ellipse(.66, .72, .07, .07, WHITE)))
pict("gd_p_taxi", GBLUE, lambda c: (car(c, .5, .55, 1.0, WHITE)))
pict("gd_p_station", GBLUE, lambda c: (c.text("駅", .5, .5, .5, WHITE)))
pict("gd_p_hospital", GBLUE, lambda c: (c.rect(.4, .2, .6, .8, WHITE), c.rect(.2, .4, .8, .6, WHITE)))
pict("gd_p_park", GGREEN, lambda c: (c.ellipse(.5, .38, .22, .22, WHITE), c.rect(.46, .55, .54, .82, WHITE)))
pict("gd_p_bike_parking", GBLUE, lambda c: bike(c, .5, .52, 1.1, WHITE))
pict("gd_p_charging", GBLUE, lambda c: (c.text("EV", .5, .5, .38, WHITE)))


def pack():
    items = sorted(SIGNS.items(), key=lambda kv: -int(kv[1][3] * PPM))
    x = y = rowh = 0
    pos = {}
    for name, (cat, shape, w, h, fn) in items:
        pw, ph = max(32, int(w * PPM)), max(32, int(h * PPM))
        if x + pw + 4 > AW:
            x, y, rowh = 0, y + rowh + 4, 0
        pos[name] = (x, y, pw, ph)
        x += pw + 4
        rowh = max(rowh, ph)
    return pos, y + rowh


def main():
    pos, used_h = pack()
    assert used_h <= AH, used_h
    atlas = Image.new("RGBA", (AW, AH), (0, 0, 0, 0))
    meta = {"size": [AW, AH], "ppm": PPM, "signs": {}}
    for name, (cat, shape, w, h, fn) in SIGNS.items():
        x, y, pw, ph = pos[name]
        c = C(pw, ph)
        fn(c)
        atlas.alpha_composite(c.done(), (x, y))
        meta["signs"][name] = dict(cat=cat, shape=shape, w=w, h=h, rect=[x, y, pw, ph],
                                   uv=[x / AW, 1 - (y + ph) / AH, (x + pw) / AW, 1 - y / AH])
    OUT.mkdir(parents=True, exist_ok=True)
    atlas.save(OUT / "sign_atlas.png", optimize=True)
    (OUT / "sign_atlas.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(len(SIGNS), "signs, atlas used height", used_h)


def load_meta():
    return json.loads((OUT / "sign_atlas.json").read_text())


if __name__ == "__main__":
    main()
