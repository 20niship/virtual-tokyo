"""道路の安全施設(ガードレール/ガードパイプ/ボラード/カーブミラー…)・電柱・街具(ベンチ/バス停/ポスト/駐輪/自販機周辺)・看板類(野立て/サイネージ)。
座標系: 原点=設置点中心(柱は軸)、+y=前(道路側/利用者側)、z=上。W=スパン長/幅。"""
import json
import math
from pathlib import Path

from shapely.geometry import LineString
from shapely.geometry.polygon import orient

from .lib_street import light, plate_poly, pole, rrect, plate_poly_yz
from .registry import mod, reg

TEX = Path(__file__).resolve().parents[3] / "assets/textures"
try:
    AD = json.loads((TEX / "ad_atlas.json").read_text())["panels"]
except FileNotFoundError:
    AD = []


# ============ 安全施設 ============
def _wbeam_profile():
    """Gr-C-4E 系の波形ビーム断面(高さ0.32/奥行0.075/板厚3.2mm)をy-z平面の閉多角形に"""
    P = [(0, 0.16), (0, 0.14), (0.075, 0.1), (0.075, 0.06), (0, 0.02), (0, -0.02), (0.075, -0.06), (0.075, -0.1), (0, -0.14), (0, -0.16)]
    poly = LineString(P).buffer(0.0018, cap_style=2, join_style=2)
    poly = orient(poly, 1.0)
    return list(poly.exterior.coords)[:-1]


_WB = _wbeam_profile()


def guardrail(m, L=4.0, kind="beam"):
    n = int(round(L / 2.0))
    if kind == "beam":
        zc = 0.6
        m.prism([(y - 0.05, z + zc) for y, z in _WB], "x", -L / 2, L / 2, "steel_galv")
        for i in range(n + 1):
            x = -L / 2 + i * L / n
            m.cyl(x, -0.12, -0.35, 0.0572, 1.3, "z", "steel_galv", 14)                         # φ114.3の支柱(根入れ0.35m)
            m.cyl(x, -0.12, 0.95, 0.0572, 0.012, "z", "steel_gray", 14)                       # 笠
            m.box(x - 0.02, -0.12 + 0.0572, zc - 0.09, x + 0.02, -0.03, zc + 0.09, "steel_galv")        # 桁間ブラケット
            m.cyl(x, -0.03, zc + 0.05, 0.012, 0.006, "y", "steel_gray", 6)                    # ボルト頭
        for k in range(2):                                                                     # 反射板(オレンジ)
            m.box(L * (-0.25 + 0.5 * k) - 0.05, 0.026, 0.83, L * (-0.25 + 0.5 * k) + 0.05, 0.03, 0.89, "reflector_orange")
        m.box(-0.2, -0.055, zc - 0.17, 0.2, -0.045, zc + 0.17, "steel_galv")                  # 継手のスリーブ
    elif kind == "pipe":     # ガードパイプ(白)
        for z in (0.55, 0.9):
            m.cyl(-L / 2, -0.05, z, 0.03, L, "x", "guard_white", 14)
        for i in range(n + 1):
            x = -L / 2 + i * L / n
            m.cyl(x, -0.05, -0.2, 0.057, 1.3, "z", "guard_white", 14)
            m.lathe(x, -0.05, 1.1, [(0.058, 0), (0.05, 0.02), (0.001, 0.035)], "guard_white", 14)
            m.box(x - 0.03, -0.05 + 0.03, 0.5, x + 0.03, 0.0, 0.6, "guard_white") if False else None
    else:                    # 歩行者用転落防止柵(縦格子)
        m.cyl(-L / 2, -0.04, 1.05, 0.021, L, "x", "guard_white", 10)
        m.cyl(-L / 2, -0.04, 0.45, 0.016, L, "x", "guard_white", 10)
        for i in range(int(L / 0.12) + 1):
            m.cyl(-L / 2 + i * 0.12, -0.04, 0.05, 0.008, 1.0, "z", "guard_white", 6)
        for i in range(n + 1):
            x = -L / 2 + i * L / n
            m.cyl(x, -0.04, -0.2, 0.034, 1.3, "z", "guard_white", 10)


reg("guardrail_beam_4m", lambda m, W, H, r: guardrail(m, 4.0, "beam"), W=4.0, H=1.0, cat="安全施設")
reg("guardrail_beam_2m", lambda m, W, H, r: guardrail(m, 2.0, "beam"), W=2.0, H=1.0, cat="安全施設")
reg("guardpipe_4m", lambda m, W, H, r: guardrail(m, 4.0, "pipe"), W=4.0, H=1.0, cat="安全施設")
reg("ped_fence_4m", lambda m, W, H, r: guardrail(m, 4.0, "fence"), W=4.0, H=1.1, cat="安全施設")


@mod("guardrail_terminal", W=1.0, H=1.0, cat="安全施設")
def _(m, W, H, rng):       # ビーム端部: 地面へ曲げ下げた末端(ブラウンボーン)
    steps = 8
    for i in range(steps):
        t0, t1 = i / steps, (i + 1) / steps
        z0, z1 = 0.6 - 0.45 * t0 ** 2, 0.6 - 0.45 * t1 ** 2
        x0, x1 = -0.5 + t0 * 1.0, -0.5 + t1 * 1.0
        m.box(min(x0, x1) - 0.0, -0.05, min(z0, z1) - 0.16, max(x0, x1), -0.047, max(z0, z1) + 0.16, "steel_galv")
    m.cyl(0.5, -0.12, -0.35, 0.0572, 1.3, "z", "steel_galv", 14)


def bollard(m, kind):
    if kind == "fixed":
        m.cyl(0, 0, 0, 0.057, 0.8, "z", "steel_galv", 16)
        m.lathe(0, 0, 0.8, [(0.057, 0), (0.05, 0.015), (0.001, 0.035)], "steel_galv", 16)
        for z in (0.55, 0.68):
            m.cyl(0, 0, z, 0.0585, 0.04, "z", "reflector_white", 16)
    elif kind == "white":
        m.cyl(0, 0, 0, 0.057, 0.8, "z", "guard_white", 16)
        m.lathe(0, 0, 0.8, [(0.057, 0), (0.05, 0.015), (0.001, 0.035)], "guard_white", 16)
        m.cyl(0, 0, 0.5, 0.0585, 0.1, "z", "reflector_orange", 16)
    elif kind == "removable":     # 可倒式(ヒンジ+錠)
        m.cyl(0, 0, 0, 0.065, 0.12, "z", "steel_galv", 16)
        m.cyl(0, 0, 0.12, 0.05, 0.7, "z", "guard_white", 16)
        m.box(-0.07, -0.02, 0.1, 0.07, 0.02, 0.2, "steel_gray")
        m.cyl(0, 0, 0.55, 0.0515, 0.06, "z", "reflector_orange", 16)
    elif kind == "stone":
        m.box(-0.14, -0.14, 0, 0.14, 0.14, 0.7, "stone_main")
        m.lathe(0, 0, 0.7, [(0.14, 0), (0.1, 0.04), (0.001, 0.07)], "stone_main", 4)
    else:                         # ポールコーン(弾性ポスト)
        m.lathe(0, 0, 0, [(0.12, 0), (0.12, 0.03), (0.04, 0.05), (0.035, 0.75), (0.001, 0.76)], "rubber_yellow", 14)
        m.cyl(0, 0, 0.45, 0.037, 0.08, "z", "reflector_white", 14)


for _k in ("fixed", "white", "removable", "stone", "flex"):
    reg(f"bollard_{_k}", (lambda k: lambda m, W, H, r: bollard(m, k))(_k), W=0.3, H=0.9, cat="安全施設")


@mod("bollard_chain_pair", W=3.0, H=0.9, cat="安全施設")
def _(m, W, H, rng):         # 2本のポール+たるむチェーン
    for x in (-1.5, 1.5):
        m.cyl(x, 0, 0, 0.05, 0.75, "z", "steel_galv", 12)
        m.lathe(x, 0, 0.75, [(0.05, 0), (0.001, 0.03)], "steel_galv", 12)
    n = 24
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        x0, x1 = -1.5 + 3.0 * t0, -1.5 + 3.0 * t1
        z0, z1 = 0.7 - 0.28 * math.sin(math.pi * t0), 0.7 - 0.28 * math.sin(math.pi * t1)
        m.box(x0, -0.012, min(z0, z1) - 0.012, x1, 0.012, max(z0, z1) + 0.012, "steel_gray")


@mod("curve_mirror_round", W=1.0, H=4.0, cat="安全施設")
def _(m, W, H, rng):          # カーブミラー(φ800・橙枠・支柱+取付アーム)。鏡面は+y
    m.cyl(0, 0, 0, 0.045, 3.4, "z", "steel_galv", 12)
    m.cyl(0, 0, 0, 0.1, 0.05, "z", "rc_concrete", 12)
    m.tube(0, 0.1, 3.05, 0.4, 0.36, 0.06, "y", "reflector_orange", 32)
    m.cyl(0, 0.115, 3.05, 0.36, 0.01, "y", "mirror", 32)
    m.lathe(0, 0.0, 0.0, [(0.0, 0.0)], "steel_gray", 4) if False else None
    for dz in (-0.2, 0.2):
        m.box(-0.015, 0.03, 3.05 + dz - 0.02, 0.015, 0.11, 3.05 + dz + 0.02, "steel_galv")
    m.cyl(0, 0.03, 3.05, 0.4, 0.04, "y", "steel_gray", 28) if False else None
    m.cyl(0, 0.04, 3.05, 0.36, 0.015, "y", "steel_gray", 28)


@mod("curve_mirror_double", W=1.6, H=4.0, cat="安全施設")
def _(m, W, H, rng):
    m.cyl(0, 0, 0, 0.05, 3.5, "z", "steel_galv", 12)
    m.cyl(0, 0, 0, 0.1, 0.05, "z", "rc_concrete", 12)
    for dx, sgn in ((-0.55, 1), (0.55, 1)):
        m.tube(dx, 0.1, 3.1, 0.38, 0.34, 0.06, "y", "reflector_orange", 28)
        m.cyl(dx, 0.115, 3.1, 0.34, 0.01, "y", "mirror", 28)
        m.cyl(dx, 0.04, 3.1, 0.34, 0.015, "y", "steel_gray", 28)
    m.box(-0.58, 0.03, 3.08, 0.58, 0.07, 3.12, "steel_galv")


@mod("wheel_stop_block", W=0.7, H=0.15, cat="安全施設")
def _(m, W, H, rng):          # 駐車場の車止めブロック(コンクリ 600x150x100 +反射)
    m.box(-0.3, -0.075, 0, 0.3, 0.075, 0.1, "rc_concrete")
    m.box(-0.26, 0.075, 0.03, 0.26, 0.078, 0.06, "rubber_yellow")


@mod("concrete_barrier_nj_4m", W=4.0, H=0.9, cat="安全施設")
def _(m, W, H, rng):          # ニュージャージー型防護柵(ジョイント付き)
    prof = [(-0.3, 0), (0.3, 0), (0.3, 0.07), (0.19, 0.32), (0.15, 0.9), (-0.15, 0.9), (-0.19, 0.32), (-0.3, 0.07)]
    m.prism([(z, y) for y, z in prof][::-1] if False else [(z, y) for y, z in prof], "x", -W / 2 + 0.01, W / 2 - 0.01, "concrete_formed")
    m.box(-0.02, -0.2, 0.12, 0.02, 0.2, 0.18, "steel_gray") if False else None


@mod("sound_barrier_panel_2m", W=4.0, H=2.6, cat="安全施設")
def _(m, W, H, rng):          # 防音壁: H形鋼支柱+透明パネル(+下部コンクリ)
    for x in (-W / 2 + 0.05, W / 2 - 0.05):
        m.box(x - 0.1, -0.075, 0, x + 0.1, 0.075, 2.6, "steel_gray")
        m.box(x - 0.1, -0.012, 0, x + 0.1, 0.012, 2.6, "steel_gray")
    m.box(-W / 2, -0.1, 0, W / 2, 0.1, 0.5, "concrete_formed")
    m.box(-W / 2 + 0.15, -0.015, 0.5, W / 2 - 0.15, 0.015, 2.5, "glass_clear")
    m.box(-W / 2 + 0.1, -0.02, 2.48, W / 2 - 0.1, 0.02, 2.58, "steel_gray")


# ============ 電柱 ============
def utility_pole(m, h=12.0, trans=False, comm=False):
    m.cyl(0, 0, 0, 0.21, 0.4, "z", "rc_concrete", 18)
    m.lathe(0, 0, 0, [(0.19, 0), (0.15, h * 0.5), (0.1, h)], "pole_concrete", 18)                # 先細りコンクリ柱(φ0.38→0.2)
    m.lathe(0, 0, h, [(0.1, 0), (0.06, 0.04), (0.001, 0.07)], "pole_concrete", 18)
    z = h - 0.6
    m.box(-0.9, -0.05, z, 0.9, 0.05, z + 0.1, "steel_gray")                                        # 腕金
    for x in (-0.7, 0.0, 0.7):
        m.cyl(x, 0, z + 0.1, 0.035, 0.1, "z", "insulator", 10)
        for k in range(3):
            m.cyl(x, 0, z + 0.2 + k * 0.05, 0.05 - 0.005 * k, 0.03, "z", "insulator", 10)           # がいし(碍子)の笠
    for k in range(5):                                                                              # 昇柱用の足場ボルト
        a = math.radians(70)
        m.cyl(0.14 * math.cos(a), 0.14 * math.sin(a), 3.0 + k * 0.45, 0.01, 0.12, "y", "steel_galv", 6)
    m.box(-0.1, 0.15, 2.2, 0.1, 0.16, 2.5, "reflector_white")                                       # 電柱番号札
    if trans:                                                                                       # 柱上変圧器(3台)
        for x in (-0.45, 0.0, 0.45):
            m.cyl(x, 0.45, z - 1.0, 0.18, 0.6, "z", "steel_gray", 14)
            m.cyl(x, 0.45, z - 0.4, 0.2, 0.05, "z", "steel_gray", 14)
        m.box(-0.6, 0.06, z - 1.1, 0.6, 0.16, z - 0.95, "steel_gray")
    if comm:                                                                                        # 通信線添架: ハンガー+ケーブル接続箱
        z2 = h - 2.4
        m.box(-0.25, 0.1, z2, 0.25, 0.22, z2 + 0.5, "steel_gray")
        m.cyl(0.0, 0.0, z2 + 0.6, 0.12, 0.0, "z", "wire", 8) if False else None
        m.box(-0.5, 0.12, z2 + 0.45, 0.5, 0.15, z2 + 0.5, "steel_gray")


for _h, _t, _c, _n in ((12.0, False, False, "utility_pole_12m"), (12.0, True, False, "utility_pole_12m_trans"), (10.0, False, True, "utility_pole_10m_comm")):
    reg(_n, (lambda h, t, c: lambda m, W, H, r: utility_pole(m, h, t, c))(_h, _t, _c), W=1.8, H=_h + 0.3, cat="電柱")


@mod("street_cabinet_pillar", W=0.9, H=1.4, cat="電柱")
def _(m, W, H, rng):           # 地上機器(トランス/通信キャビネット)
    m.box(-0.5, -0.3, 0, 0.5, 0.3, 0.1, "rc_concrete")
    m.box(-0.45, -0.25, 0.1, 0.45, 0.25, 1.3, "cabinet_green")
    for dx in (-0.2, 0.2):
        m.box(dx - 0.19, 0.25, 0.2, dx + 0.19, 0.262, 1.2, "cabinet_green")
    m.box(-0.012, 0.25, 0.2, 0.012, 0.265, 1.2, "grout")
    for i in range(6):
        m.box(0.0, 0.262, 0.3 + i * 0.015, 0.4, 0.268, 0.31 + i * 0.015, "steel_gray")
    m.box(-0.5, -0.3, 1.3, 0.5, 0.3, 1.34, "cabinet_green")


@mod("street_cabinet_small", W=0.6, H=1.2, cat="電柱")
def _(m, W, H, rng):
    m.box(-0.3, -0.2, 0, 0.3, 0.2, 0.08, "rc_concrete")
    m.box(-0.27, -0.17, 0.08, 0.27, 0.17, 1.0, "cabinet_green")
    m.box(-0.25, 0.17, 0.15, 0.25, 0.18, 0.95, "cabinet_green")
    m.box(-0.2, 0.18, 0.5, -0.12, 0.2, 0.62, "steel_galv")


# ============ 街具 ============
def bench(m, kind):
    if kind == "wood_back":      # 背もたれ付き木製(両肘掛け)
        for k in range(6):
            m.box(-0.9, -0.2 + k * 0.065, 0.42, 0.9, -0.2 + k * 0.065 + 0.055, 0.45, "bench_wood")
        for k in range(3):
            m.box(-0.9, -0.22, 0.55 + k * 0.1, 0.9, -0.2, 0.62 + k * 0.1, "bench_wood")
        for x in (-0.85, 0.85):
            m.box(x - 0.025, -0.2, 0.0, x + 0.025, 0.2, 0.42, "alu_black")
            m.box(x - 0.025, -0.24, 0.42, x + 0.025, -0.2, 0.95, "alu_black")
            m.box(x - 0.03, -0.15, 0.62, x + 0.03, 0.15, 0.66, "alu_black")
    elif kind == "metal":        # パンチングメタル
        m.box(-0.9, -0.2, 0.42, 0.9, 0.2, 0.45, "steel_gray")
        m.box(-0.9, -0.22, 0.45, 0.9, -0.2, 0.85, "steel_gray")
        for x in (-0.8, 0.8):
            m.box(x - 0.03, -0.2, 0, x + 0.03, 0.2, 0.42, "alu_black")
        for i in range(10):
            m.cyl(-0.8 + i * 0.18, 0, 0.45, 0.02, 0.003, "z", "sig_lens_dark", 8)
    elif kind == "backless":     # 背なし(石/木のブロック)
        m.box(-0.9, -0.22, 0.0, 0.9, 0.22, 0.4, "stone_main")
        m.box(-0.9, -0.22, 0.4, 0.9, 0.22, 0.44, "bench_wood")
    else:                        # 円弧(曲げ木)ベンチ
        for k in range(8):
            m.box(-1.0, -0.2 + k * 0.05, 0.42, 1.0, -0.2 + k * 0.05 + 0.04, 0.45, "bench_wood")
        for x in (-0.8, 0.0, 0.8):
            m.box(x - 0.03, -0.2, 0, x + 0.03, 0.2, 0.42, "alu_silver")


for _k in ("wood_back", "metal", "backless", "arc"):
    reg(f"bench_{_k}", (lambda k: lambda m, W, H, r: bench(m, k))(_k), W=1.9, H=1.0, cat="街具")


@mod("bus_stop_post", W=0.6, H=3.0, cat="街具")
def _(m, W, H, rng):           # バス停標柱: 円盤基礎+標識+時刻表ケース+広告面(アトラス)
    m.cyl(0, 0, 0, 0.12, 0.05, "z", "rc_concrete", 16)
    m.cyl(0, 0, 0.0, 0.035, 2.7, "z", "steel_galv", 12)
    m.cyl(0, 0, 2.7, 0.04, 0.02, "z", "steel_gray", 12)
    m.tube(0, 0.04, 2.45, 0.22, 0.2, 0.025, "y", "sign_blue", 24)
    m.cyl(0, 0.04, 2.45, 0.2, 0.012, "y", "sign_blue", 24)
    m.box(-0.15, 0.04, 2.35, 0.15, 0.054, 2.55, "sign_white")                                      # 白帯(系統名の欄)
    m.box(-0.22, 0.045, 1.45, 0.22, 0.095, 2.05, "steel_gray")                                     # 時刻表ケース
    m.box(-0.2, 0.095, 1.5, 0.2, 0.1, 2.0, "sign_white")
    if AD:
        u0, v0, u1, v1 = AD[11]["uv"]
        m.oriented([(0.2, 0.101, 1.5), (-0.2, 0.101, 1.5), (-0.2, 0.101, 1.7), (0.2, 0.101, 1.7)], (0, 1, 0), "ad_atlas", [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


@mod("post_box_red", W=0.5, H=1.6, cat="街具")
def _(m, W, H, rng):           # 郵便ポスト(丸ポスト・赤): 円筒+投函口2+取集時刻板
    m.lathe(0, 0, 0, [(0.2, 0), (0.2, 0.15), (0.17, 0.16), (0.17, 1.2), (0.2, 1.22), (0.18, 1.3), (0.1, 1.42), (0.001, 1.45)], "post_red", 20)
    m.box(-0.1, 0.165, 0.9, 0.1, 0.19, 0.98, "steel_gray")
    m.box(-0.1, 0.165, 0.75, 0.1, 0.19, 0.83, "steel_gray")
    m.box(-0.08, 0.166, 0.3, 0.08, 0.172, 0.55, "sign_white")
    m.cyl(0, 0, 0, 0.23, 0.05, "z", "rc_concrete", 20)


def trash_can(m, kind):
    if kind == "sorted":      # 分別2連(燃える/PET・缶)
        for x, mat in ((-0.27, "sign_blue"), (0.27, "post_red")):
            m.box(x - 0.24, -0.25, 0.0, x + 0.24, 0.25, 0.85, "steel_gray")
            m.box(x - 0.2, 0.25, 0.55, x + 0.2, 0.27, 0.62, "sig_lens_dark")
            m.box(x - 0.2, 0.25, 0.7, x + 0.2, 0.26, 0.8, mat)
        m.box(-0.5, -0.27, 0.85, 0.5, 0.27, 0.9, "steel_gray")
    else:                      # 丸型メッシュ
        m.lathe(0, 0, 0, [(0.2, 0), (0.22, 0.0), (0.22, 0.75), (0.2, 0.78)], "steel_gray", 18)
        m.cyl(0, 0, 0.78, 0.22, 0.03, "z", "alu_black", 18)
        m.tube(0, 0, 0.8, 0.12, 0.09, 0.02, "z", "alu_silver", 18)


for _k in ("sorted", "round"):
    reg(f"trash_can_{_k}", (lambda k: lambda m, W, H, r: trash_can(m, k))(_k), W=1.1 if _k == "sorted" else 0.5, H=0.95, cat="街具")


@mod("bicycle_rack_u", W=2.4, H=0.9, cat="街具")
def _(m, W, H, rng):           # U字ラック×4(間隔0.6m)
    for i in range(4):
        x = -0.9 + i * 0.6
        m.cyl(x, 0, 0, 0.02, 0.7, "z", "steel_galv", 8)
        m.cyl(x, 0.35, 0, 0.02, 0.7, "z", "steel_galv", 8)
        m.cyl(x, 0.0, 0.7, 0.02, 0.35, "y", "steel_galv", 8)


@mod("bike_share_dock", W=3.0, H=1.5, cat="街具")
def _(m, W, H, rng):           # シェアサイクルのポート: 精算機+ドック3基
    m.box(-0.18, -0.15, 0, 0.18, 0.15, 1.25, "sign_blue")
    m.box(-0.14, 0.15, 0.85, 0.14, 0.16, 1.15, "sig_lens_dark")
    for i in range(3):
        x = 0.6 + i * 0.7
        m.box(x - 0.06, -0.1, 0, x + 0.06, 0.1, 0.9, "alu_silver")
        m.box(x - 0.05, 0.1, 0.5, x + 0.05, 0.12, 0.6, "sign_blue")


@mod("phone_booth_green", W=0.9, H=2.4, cat="街具")
def _(m, W, H, rng):           # 公衆電話ボックス
    m.box(-0.45, -0.45, 0, 0.45, 0.45, 0.1, "rc_concrete")
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        m.box(sx * 0.42 - 0.02, sy * 0.42 - 0.02, 0.1, sx * 0.42 + 0.02, sy * 0.42 + 0.02, 2.3, "steel_green")
    m.box(-0.45, -0.45, 2.3, 0.45, 0.45, 2.4, "steel_green")
    for (x0, y0, x1, y1) in ((-0.42, -0.42, 0.42, -0.41), (-0.42, 0.41, 0.42, 0.42), (-0.42, -0.42, -0.41, 0.42), (0.41, -0.42, 0.42, 0.42)):
        m.box(x0, y0, 0.9, x1, y1, 2.28, "glass_clear")
    m.box(-0.2, -0.3, 0.9, 0.2, -0.2, 1.4, "steel_green")


@mod("drinking_fountain", W=0.5, H=1.0, cat="街具")
def _(m, W, H, rng):
    m.box(-0.18, -0.18, 0, 0.18, 0.18, 0.8, "stone_main")
    m.box(-0.22, -0.22, 0.8, 0.22, 0.22, 0.86, "steel_galv")
    m.cyl(0, 0.1, 0.86, 0.015, 0.14, "z", "steel_galv", 8)


@mod("hydrant_marker", W=0.3, H=2.0, cat="街具")
def _(m, W, H, rng):           # 消火栓標識(赤白の柱)
    m.cyl(0, 0, 0, 0.04, 1.9, "z", "post_red", 10)
    m.box(-0.18, 0.035, 1.45, 0.18, 0.05, 1.85, "sign_red")
    m.box(-0.16, 0.05, 1.6, 0.16, 0.054, 1.78, "sign_white")


@mod("clock_post", W=0.8, H=3.6, cat="街具")
def _(m, W, H, rng):
    m.cyl(0, 0, 0, 0.07, 3.0, "z", "alu_black", 12)
    m.cyl(0, 0, 3.0, 0.4, 0.14, "y", "alu_black", 24) if False else m.cyl(0, -0.07, 3.35, 0.4, 0.14, "y", "alu_black", 28)
    m.cyl(0, 0.08, 3.35, 0.36, 0.012, "y", "sign_white", 28)
    m.cyl(0, 0.093, 3.35, 0.012, 0.01, "y", "steel_gray", 8)
    m.box(-0.01, 0.093, 3.35, 0.01, 0.1, 3.65, "alu_black") if False else m.box(-0.008, 0.093, 3.35, 0.008, 0.1, 3.62, "alu_black")
    m.box(-0.008, 0.093, 3.34, 0.22, 0.1, 3.36, "alu_black")


@mod("flagpole_8m", W=0.6, H=8.5, cat="街具")
def _(m, W, H, rng):
    m.cyl(0, 0, 0, 0.18, 0.15, "z", "rc_concrete", 14)
    m.lathe(0, 0, 0.15, [(0.07, 0), (0.035, 8.0)], "alu_silver", 12)
    m.cyl(0, 0, 8.15, 0.05, 0.0, "z", "alu_silver", 8) if False else m.lathe(0, 0, 8.15, [(0.04, 0), (0.001, 0.06)], "alu_silver", 12)
    m.box(-0.005, 0.0, 6.0, 0.005, 1.5, 7.8, "sign_white")
    m.cyl(0, 0.75, 6.9, 0.2, 0.012, "y", "sign_red", 20)


@mod("info_map_board", W=1.4, H=2.2, cat="街具")
def _(m, W, H, rng):           # 案内図板(2本脚+傾斜しない直立板)
    for x in (-0.55, 0.55):
        m.box(x - 0.04, -0.05, 0, x + 0.04, 0.05, 1.9, "steel_gray")
    m.box(-0.7, -0.05, 1.0, 0.7, 0.05, 1.9, "steel_gray")
    if AD:
        u0, v0, u1, v1 = AD[15]["uv"]
        m.oriented([(0.64, 0.052, 1.06), (-0.64, 0.052, 1.06), (-0.64, 0.052, 1.84), (0.64, 0.052, 1.84)], (0, 1, 0), "ad_atlas", [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


@mod("planter_box_long", W=2.4, H=0.8, cat="街具")
def _(m, W, H, rng):           # 花壇ボックス(植栽は別途。土のみ)
    m.box(-1.2, -0.3, 0, 1.2, 0.3, 0.55, "concrete_formed")
    m.box(-1.15, -0.25, 0.5, 1.15, 0.25, 0.56, "soil")


# ============ 看板(道路沿い) ============
def _ad(m, pts_x, y, zs, idx, w=None):
    if not AD:
        return
    u0, v0, u1, v1 = AD[idx % len(AD)]["uv"]
    x0, x1 = pts_x
    z0, z1 = zs
    m.oriented([(x1, y, z0), (x0, y, z0), (x0, y, z1), (x1, y, z1)], (0, 1, 0 if True else 0), "ad_atlas", [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


for _i in range(0, 16, 3):
    @mod(f"billboard_roadside_{_i}", W=3.2, H=3.4, cat="看板")
    def _(m, W, H, rng, i=_i):     # 野立て看板(2本柱・3.0x1.5m)
        for x in (-1.2, 1.2):
            m.cyl(x, -0.06, 0, 0.06, 2.9, "z", "steel_galv", 10)
        m.box(-1.6, -0.1, 1.6, 1.6, -0.02, 3.3, "steel_gray")
        _ad(m, (-1.5, 1.5), 0.0, (1.7, 3.2), i)
        m.box(-1.6, 0.0, 3.3, 1.6, 0.06, 3.34, "steel_galv") if False else m.box(-1.6, -0.02, 3.3, 1.6, 0.02, 3.34, "steel_galv")


@mod("billboard_pole_6m", W=6.4, H=9.0, cat="看板")
def _(m, W, H, rng):           # 単柱広告看板(6x3m)
    m.lathe(0, 0, 0, [(0.35, 0), (0.28, 0.6), (0.22, 6.0)], "steel_galv", 14)
    m.cyl(0, 0, 0, 0.5, 0.3, "z", "rc_concrete", 14)
    m.box(-3.2, 0.12, 5.4, 3.2, 0.3, 8.4, "steel_gray")
    _ad(m, (-3.1, 3.1), 0.31, (5.5, 8.3), 13)
    for x in (-2.8, 0, 2.8):
        m.box(x - 0.05, 0.3, 8.4, x + 0.05, 0.9, 8.46, "steel_galv")
        light(m, "rect", (x, 0.9, 8.4), 3000, (1, 1, 1), size=(0.3, 0.1), direction=(0, 0.3, -1))


@mod("digital_signage_vertical", W=1.2, H=2.3, cat="看板")
def _(m, W, H, rng):           # 縦型デジタルサイネージ(発光面)
    m.box(-0.5, -0.12, 0, 0.5, 0.12, 0.1, "steel_gray")
    m.box(-0.45, -0.1, 0.1, 0.45, 0.1, 2.1, "alu_black")
    m.box(-0.4, 0.1, 0.25, 0.4, 0.105, 2.0, "sig_lens_dark")
    if AD:
        u0, v0, u1, v1 = AD[3]["uv"]
        m.oriented([(0.38, 0.106, 0.3), (-0.38, 0.106, 0.3), (-0.38, 0.106, 1.95), (0.38, 0.106, 1.95)], (0, 1, 0), "ad_atlas", [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    light(m, "rect", (0, 0.12, 1.1), 1500, (1, 0.98, 0.95), size=(0.8, 1.7), direction=(0, 1, 0))


@mod("nobori_flag_pole", W=0.9, H=3.0, cat="看板")
def _(m, W, H, rng):           # のぼり旗(ポール+旗)
    m.cyl(0, 0, 0, 0.012, 3.0, "z", "alu_silver", 8)
    m.box(-0.2, 0, 0, 0.2, 0.18, 0.02, "rubber") if False else None
    m.box(-0.025, -0.3, 0, 0.025, 0.3, 0.03, "steel_gray")
    m.cyl(0, 0, 2.97, 0.012, 0.0, "x", "alu_silver", 6) if False else m.cyl(0, 0, 2.95, 0.012, 0.35, "x", "alu_silver", 6)
    _ad(m, (0.0, 0.35), 0.002, (0.9, 2.9), 4)


@mod("street_nameplate", W=0.5, H=2.8, cat="看板")
def _(m, W, H, rng):           # 町名表示板(電柱/標柱取付)
    m.cyl(0, 0, 0, 0.035, 2.5, "z", "steel_galv", 10)
    m.box(-0.22, 0.04, 2.1, 0.22, 0.056, 2.38, "sign_blue")
    m.box(-0.2, 0.056, 2.12, 0.2, 0.058, 2.36, "sign_white")
