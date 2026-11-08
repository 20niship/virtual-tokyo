"""山間部の道路 module(PBR 材質、1 module 1 usdc、near / "_far")。長手方向は +y、右側が +x、原点は区間の中心(底面 z=0)。
road_guardrail_4m(ガードレール) / road_retwall_4m(擁壁) / road_rocknet_8m(落石防止網) / road_curve_mirror(カーブミラー) /
tunnel_portal_{0,1,2}(坑口。開口は -y 側、+y が山の中へ) / bridge_deck_8m(橋桁+高欄、幅 8m) / bridge_chinka_8m(沈下橋) / bridge_pier_{4..45}(橋脚、高さ H)。"""
from vt.materials import MATERIALS as _MAT

from .registry import reg

_MAT["road_post_orange"] = dict(color="#d6782a", rough=0.5, metal=0.0)
_MAT["road_net"] = dict(color="#6c7072", rough=0.6, metal=0.8)
_MAT["tunnel_dark"] = dict(color="#050505", rough=1.0, metal=0.0)
_MAT["road_concrete_old"] = dict(color="#8d8b84", rough=0.92, metal=0.0, tex="concrete.png", size=3.0, bump=0.5)
CONC = "concrete_tex"


def _guardrail(lod):
    def fn(m, W, H, rng):
        L = 4.0
        n = 3 if lod == "near" else 2
        for i in range(n):
            y = -L / 2 + L * i / (n - 1)
            m.box(-0.03, y - 0.03, 0.0, 0.03, y + 0.03, 0.75, "steel_galv")                                    # 支柱
        m.box(-0.1, -L / 2, 0.55, 0.0, L / 2, 0.85, "steel_galv")                                              # ビーム
        if lod == "near":
            for k in range(3):                                                                                  # ビームの波形(山)
                m.box(-0.12, -L / 2, 0.58 + 0.1 * k, -0.1, L / 2, 0.62 + 0.1 * k, "steel_galv")
    return fn


def _retwall(lod):
    def fn(m, W, H, rng):
        L, h = 4.0, 2.4
        # 断面: 道路側(-x)が少し傾いた重力式擁壁。天端幅 0.4、底 1.1
        a = [(0.0, -0.55), (0.0, 0.55), (h, 0.2), (h, -0.2)]            # prism(axis=y) の輪郭は (z, x)
        m.prism(a, "y", -L / 2, L / 2, CONC)
        if lod == "near":
            for i in range(-1, 2):                                                                               # 水抜き孔
                m.box(-0.45 + 0.1, i * 1.2 - 0.06, 0.6, -0.1, i * 1.2 + 0.06, 0.72, "tunnel_dark")
            m.box(-0.3, -L / 2, h - 0.06, 0.3, L / 2, h + 0.1, "rc_concrete")                                  # 天端のコーピング
    return fn


def _rocknet(lod):
    def fn(m, W, H, rng):
        L, h = 8.0, 4.5
        for i in range(3 if lod == "near" else 2):
            y = -L / 2 + L * i / (2 if lod == "near" else 1)
            m.box(-0.05, y - 0.05, 0.0, 0.05, y + 0.05, h, "steel_galv")
        step = 0.5 if lod == "near" else 1.5
        k = 0
        while k * step <= L + 1e-6:                                                                              # 金網(縦横の線)
            y = -L / 2 + k * step
            m.box(-0.02, y - 0.012, 0.15, 0.02, y + 0.012, h - 0.1, "road_net")
            k += 1
        k = 0
        while k * step <= h - 0.25 + 1e-6:
            z = 0.15 + k * step
            m.box(-0.02, -L / 2, z - 0.012, 0.02, L / 2, z + 0.012, "road_net")
            k += 1
    return fn


def _mirror(lod):
    def fn(m, W, H, rng):
        m.cyl(0, 0, 0, 0.04, 2.4, "z", "road_post_orange", 10 if lod == "near" else 6)
        m.cyl(0.03, 0, 2.2, 0.35, 0.03, "y", "alu_silver", 20 if lod == "near" else 8)                        # 円形ミラー
        if lod == "near":
            m.cyl(0.0, 0.0, 2.2, 0.37, 0.025, "y", "road_post_orange", 20)                                    # 縁
    return fn


def _portal(v, lod):
    """坑口: 壁式(0)・ひさし付き(1)・ウイング壁(2)。開口は幅 7.5m・高さ 5.0m のアーチ。中は暗い面"""
    def fn(m, W, H, rng):
        t = 1.0
        # 壁(開口を抜いた正面): 開口の上の欄間と左右の袖
        wall_w = 8.5 + 2 * (2.0 if v == 2 else 0.8)
        top = 7.0 + (1.0 if v == 1 else 0.0)
        for side in (-1, 1):
            x0, x1 = (3.75, wall_w / 2) if side > 0 else (-wall_w / 2, -3.75)
            m.box(x0, -t, 0.0, x1, 0.0, top, CONC)
        m.box(-3.75, -t, 5.0, 3.75, 0.0, top, CONC)                                                              # 欄間
        m.box(-3.75, 0.0, 0.0, 3.75, 6.0 if lod == "near" else 3.0, 5.0, "tunnel_dark")                          # 坑内(暗い)
        m.box(-3.75, 0.0, 0.0, 3.75, 0.2, 0.01, "asphalt")
        if v == 1:                                                                                               # ひさし
            m.box(-wall_w / 2 - 0.3, -t - 1.5, top - 0.5, wall_w / 2 + 0.3, 0.0, top, "rc_concrete")
        if v == 2:                                                                                               # ウイング壁(斜め)
            for side in (-1, 1):
                m.box(side * (wall_w / 2) - 0.3, -t, 0.0, side * (wall_w / 2) + 0.3, 5.0, top - 1.5, CONC)
        if lod == "near":
            m.box(-3.9, -t - 0.05, 4.95, 3.9, 0.05, 5.15, "rc_concrete")                                         # 開口上端の見切り
            for side in (-1, 1):
                m.box(side * 3.85 - 0.1, -t - 0.05, 0.0, side * 3.85 + 0.1, 0.05, 5.0, "rc_concrete")
    return fn


def _deck(lod, chinka=False):
    def fn(m, W, H, rng):
        L = 8.0
        if chinka:                                                                                               # 沈下橋: 欄干の無い低い RC 床版(幅 4m)、小さな縁石
            m.box(-2.0, -L / 2, -0.4, 2.0, L / 2, 0.0, CONC)
            m.box(-2.0, -L / 2, 0.0, -1.85, L / 2, 0.15, "rc_concrete")
            m.box(1.85, -L / 2, 0.0, 2.0, L / 2, 0.15, "rc_concrete")
            m.box(-1.85, -L / 2, 0.0, 1.85, L / 2, 0.01, "asphalt")
            return
        m.box(-4.0, -L / 2, -1.6, 4.0, L / 2, -0.25, CONC)                                                       # 桁(箱桁の外形)
        m.box(-3.6, -L / 2, -0.25, 3.6, L / 2, 0.0, "rc_concrete")                                                # 床版
        m.box(-3.25, -L / 2, 0.0, 3.25, L / 2, 0.02, "asphalt")
        for sd in (-1, 1):
            x = sd * 3.75
            m.box(x - 0.15, -L / 2, 0.0, x + 0.15, L / 2, 0.45, "rc_concrete")                                    # 地覆
            nb = 4 if lod == "near" else 2
            for i in range(nb + 1):
                y = -L / 2 + L * i / nb
                m.box(x - 0.04, y - 0.04, 0.45, x + 0.04, y + 0.04, 1.1, "steel_galv")                            # 高欄の支柱
            m.box(x - 0.06, -L / 2, 1.05, x + 0.06, L / 2, 1.12, "steel_galv")
            if lod == "near":
                m.box(x - 0.04, -L / 2, 0.75, x + 0.04, L / 2, 0.8, "steel_galv")
    return fn


def _pier(Hp, lod):
    def fn(m, W, H, rng):
        # 小判形断面の柱(幅 5.0 x 奥行 1.4)+ 柱頭(幅 7.2)。上端 z=Hp が桁の下面
        wcol = 1.4 + Hp * 0.015
        m.box(-2.5 - 0.0, -wcol / 2, 0.0, 2.5, wcol / 2, Hp - 0.9, CONC)
        m.box(-3.6, -1.0, Hp - 0.9, 3.6, 1.0, Hp, "rc_concrete")                                                   # 柱頭(梁)
        m.box(-3.4, -2.2, -0.8, 3.4, 2.2, 0.0, "rc_concrete")                                                     # 基礎(地中へ)
        if lod == "near" and Hp > 12:
            m.box(-2.6, -wcol / 2 - 0.05, Hp * 0.5, 2.6, wcol / 2 + 0.05, Hp * 0.5 + 0.25, "rc_concrete")        # 中間の梁(ハンチ)
    return fn


for _lod in ("near", "far"):
    _s = "" if _lod == "near" else "_far"
    reg(f"road_guardrail_4m{_s}", _guardrail(_lod), W=4.0, H=0.9, cat="道路", lod=_lod)
    reg(f"road_retwall_4m{_s}", _retwall(_lod), W=4.0, H=2.5, cat="道路", lod=_lod)
    reg(f"road_rocknet_8m{_s}", _rocknet(_lod), W=8.0, H=4.5, cat="道路", lod=_lod)
    reg(f"road_curve_mirror{_s}", _mirror(_lod), W=0.8, H=2.6, cat="道路", lod=_lod)
    for _v in range(3):
        reg(f"tunnel_portal_{_v}{_s}", _portal(_v, _lod), W=12.0, H=8.0, cat="トンネル", lod=_lod)
    reg(f"bridge_deck_8m{_s}", _deck(_lod), W=8.0, H=2.0, cat="橋", lod=_lod)
    reg(f"bridge_chinka_8m{_s}", _deck(_lod, True), W=4.0, H=0.6, cat="橋", lod=_lod)
    for _h in (4, 8, 12, 16, 24, 32, 45):
        reg(f"bridge_pier_{_h}{_s}", _pier(_h, _lod), W=7.2, H=_h, cat="橋", lod=_lod)

PIER_HEIGHTS = (4, 8, 12, 16, 24, 32, 45)
