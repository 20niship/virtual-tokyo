"""橋・駅の繰り返し部品(フェーズC): ハンガーロープ金具、ホームドア、駅屋根ベイ、駅名標。"""
import math

from ..materials import MATERIALS
from ..station_signs import load_meta
from .geom3 import beam, tube3
from .registry import mod, reg

MATERIALS.update({
    "station_sign_atlas": dict(color="#ffffff", rough=0.4, metal=0.0, tex="station_signs.png", size=None),
    "beacon_red": dict(color="#ff2a1a", rough=0.3, metal=0.0, emit=("#ff2a1a", 20.0)),
    "truss_white": dict(color="#e9ecec", rough=0.5, metal=0.6, dirt=1, rust=1),
})


@mod("hanger_clamp", W=0.8, H=1.2, cat="橋")
def _(m, W, H, rng):   # 主ケーブルのケーブルバンド + ハンガーロープのソケット(原点=バンド中心, 下へロープが垂れる)
    m.tube(-0.3, 0, 0, 0.36, 0.29, 0.6, "x", "truss_white", 20)
    m.tube(-0.34, 0, 0, 0.4, 0.36, 0.05, "x", "steel_gray", 20)
    m.tube(0.29, 0, 0, 0.4, 0.36, 0.05, "x", "steel_gray", 20)
    m.box(-0.12, -0.2, -0.62, 0.12, 0.2, -0.3, "truss_white")                 # 下がり金具
    m.cyl(0, 0, -1.0, 0.07, 0.4, "z", "steel_gray", 10)                       # ソケット
    m.cyl(0, 0, -0.62, 0.11, 0.1, "z", "steel_galv", 12)


@mod("platform_door_unit", W=3.0, H=2.2, cat="駅")
def _(m, W, H, rng):   # 全高ホームドア1基(固定2+引戸2)。+yが乗客側
    hw = W / 2
    m.box(-hw, -0.1, 0, hw, 0.1, 0.12, "steel_gray")
    m.box(-hw, -0.12, H - 0.28, hw, 0.14, H, "alu_main")                       # 戸袋/上部ボックス
    m.box(-0.12, 0.14, H - 0.2, 0.12, 0.16, H - 0.12, "led_white")             # 開閉表示灯
    for x in (-hw, -hw * 0.42, hw * 0.42, hw - 0.05):
        m.box(x, -0.1, 0.12, x + 0.05, 0.1, H - 0.28, "alu_black")             # 縦枠
    for x0, x1, y in ((-hw + 0.05, -hw * 0.42, 0.0), (hw * 0.42 + 0.05, hw - 0.05, 0.0)):
        m.box(x0, y - 0.01, 0.17, x1, y + 0.01, H - 0.3, "glass_clear")        # 固定窓
    for x0, x1, y in ((-hw * 0.42 + 0.05, 0.0, 0.05), (0.0, hw * 0.42, -0.05)):
        m.box(x0, y - 0.012, 0.17, x1, y + 0.012, H - 0.3, "glass_clear")      # 引戸(前後にずらして召し合わせ)
        m.box(x0, y - 0.02, 0.17, x0 + 0.04, y + 0.02, H - 0.3, "alu_black")
        m.box(x1 - 0.04, y - 0.02, 0.17, x1, y + 0.02, H - 0.3, "alu_black")
    m.box(-0.45, 0.02, 1.35, 0.45, 0.025, 1.65, "paint_white")                  # ガラス中段の注意帯


@mod("station_roof_bay", W=9.0, H=5.0, cat="駅")
def _(m, W, H, rng):   # 片持ち曲面屋根の1ベイ(x方向9m, 原点=柱脚, +yへ6m張り出す)
    span, rise, z0, t = 6.4, 0.9, 3.9, 0.12
    n = 14
    pts = [(span * i / n, z0 + rise * math.sin(math.pi * 0.5 * i / n) - 0.25 * (i / n) ** 2) for i in range(n + 1)]
    outer = [(y, z + t / 2) for y, z in pts]
    inner = [(y, z - t / 2) for y, z in pts][::-1]
    m.prism(outer + inner, "x", -W / 2 + 0.2, W / 2 - 0.2, "glass_main")        # 屋根面(半透明パネル)
    for x in (-W / 2, W / 2):
        o = [(y, z + 0.17) for y, z in pts]; i_ = [(y, z - 0.17) for y, z in pts][::-1]
        m.prism(o + i_, "x", x - 0.1, x + 0.1, "truss_white")                  # 大梁(曲面リブ)
    for k in range(1, 3):
        x = -W / 2 + k * W / 3
        o = [(y, z + 0.06) for y, z in pts]; i_ = [(y, z - 0.06) for y, z in pts][::-1]
        m.prism(o + i_, "x", x - 0.04, x + 0.04, "steel_white")                # 中間リブ
    m.box(-0.18, -0.18, 0, 0.18, 0.18, z0 - 0.1, "truss_white")                # 柱
    m.box(-W / 2, -0.12, z0 - 0.12, W / 2, 0.12, z0 + 0.1, "truss_white")      # 柱頭の桁
    m.box(-W / 2, span - 0.05, z0 + rise - 0.3, W / 2, span + 0.08, z0 + rise - 0.1, "alu_silver")  # 先端の雨樋


def _sign(m, name, info):
    u0, v0, u1, v1 = info["uv"]
    w, h, t = 3.2, 1.0, 0.07
    m.box(-w / 2, -t, -h / 2, w / 2, 0, h / 2, "alu_black")
    P = [(w / 2, 0.001, -h / 2), (-w / 2, 0.001, -h / 2), (-w / 2, 0.001, h / 2), (w / 2, 0.001, h / 2)]
    m.oriented(P, (0, 1, 0), "station_sign_atlas", [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    for x in (-1.1, 1.1):
        m.box(x - 0.02, -t - 0.02, h / 2, x + 0.02, -t, h / 2 + 0.6, "steel_gray")   # 吊り棒


try:
    for _n, _i in load_meta()["stations"].items():
        reg(f"station_sign_{_i['code'].replace('-', '_')}", (lambda n, i: lambda m, W, H, r: _sign(m, n, i))(_n, _i), W=3.2, H=1.0, cat="駅")
except FileNotFoundError:
    pass
