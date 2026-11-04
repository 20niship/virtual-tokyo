"""高速道路(首都高)高架の細部部材(ex_*): 非常階段・非常電話・橋脚の縦樋/ハシゴ/足場金具/番号板・桁下のケーブルトレイ/配管/鳥よけネット・支承・落橋防止・遮音壁・照明柱・標識/情報板・ETC。
壁面に付く物は面がy=0で外向き+y。橋軸に沿う物はx=橋軸。単独物の原点=設置点の地面(桁下の物は桁下面)。"""
import math

from .geom3 import beam, tube3
from .registry import mod, reg
from .xutil import MATERIALS, M, ladder_z, pipe, post, prism_any, sign_panel  # noqa: F401

MATERIALS["ex_antigraffiti"] = M("#aeaaa0", 0.8, 0.0, dirt=1, bump=0.2)


@mod("ex_emerg_stair", W=3.2, H=7.2, cat="高架")
def _(m, W, H, rng):
    """非常階段(鋼製3連・折返し): 山形鋼のささら桁+縞鋼板踏面+手すり+踊り場+足元の施錠ゲートと「非常階段」表示。1ユニット=7.2m上り"""
    nrun, rise, run = 12, 0.2, 0.28
    for k in range(3):
        x0 = -1.5 + k * 1.05
        up = (k % 2 == 0)
        for i in range(nrun):
            z = k * 2.4 + (i + 1) * rise
            y = (0.2 + i * run) if up else (0.2 + (nrun - 1 - i) * run)
            m.box(x0, y, z - 0.05, x0 + 0.9, y + run, z, "grating")
            m.box(x0, y, z - 0.07, x0 + 0.9, y + 0.03, z - 0.05, "anchor_galv")
        ya, yb = (0.2, 0.2 + nrun * run)
        for sx in (x0, x0 + 0.9):
            tube3(m, [(sx, ya if up else yb, k * 2.4 + 0.15), (sx, yb if up else ya, (k + 1) * 2.4 + 0.1)], 0.05, "girder_steel", 6)
            tube3(m, [(sx, ya if up else yb, k * 2.4 + 1.05), (sx, yb if up else ya, (k + 1) * 2.4 + 1.0)], 0.02, "steel_galv", 5)
            tube3(m, [(sx, ya if up else yb, k * 2.4 + 0.55), (sx, yb if up else ya, (k + 1) * 2.4 + 0.5)], 0.015, "steel_galv", 5)
        zl = (k + 1) * 2.4
        yl = yb if up else ya
        m.box(x0 - 0.02, yl - (0.0 if up else 1.2) - 0.0, zl - 0.06, x0 + 1.07 + 0.0, yl + (1.2 if up else 0.0), zl, "grating")
        for kk in range(3):
            m.box(x0 + 0.0 - 0.02 + kk * 0.45, yl + (1.2 if up else -1.2) - 0.02, zl, x0 + 0.02 + kk * 0.45, yl + (1.2 if up else -1.2) + 0.02, zl + 1.0, "steel_galv")
    for sx in (-1.5, 1.6):
        for sy in (0.0, 3.6):
            m.box(sx - 0.06, sy - 0.06, 0, sx + 0.06, sy + 0.06, 7.0, "girder_steel")
    for i in range(14):                                                              # 足元の施錠ゲート(縦格子)
        m.box(-1.55 + i * 0.23, -0.3, 0.0, -1.53 + i * 0.23, -0.27, 1.8, "alu_black")
    for z in (0.15, 0.9):
        m.box(-1.6, -0.31, z, 1.6, -0.26, z + 0.05, "alu_black")
    sign_panel(m, "estair", -0.5, 0.5, 1.6, 2.0, -0.24, flip=True)
    m.box(-1.6, -0.3, 1.8, 1.6, -0.25, 1.9, "girder_steel")
    m.box(-0.1, 1.0, 7.0, 0.1, 1.2, 7.8, "girder_steel")


@mod("ex_sos_box", W=0.6, H=1.6, cat="高架")
def _(m, W, H, rng):
    """非常電話(オレンジの箱+赤色灯+表示板+支柱)"""
    m.cyl(0, 0, 0, 0.04, 1.1, "z", "pole_dark", 8)
    m.box(-0.22, -0.15, 1.0, 0.22, 0.15, 1.45, "paint_orange_sos")
    m.box(-0.2, 0.15, 1.05, 0.2, 0.17, 1.4, "alu_black")
    m.box(-0.12, 0.17, 1.1, 0.12, 0.175, 1.18, "sig_white_icon")
    m.cyl(0, 0.0, 1.45, 0.07, 0.1, "z", "beacon_red", 8)
    sign_panel(m, "sos", -0.22, 0.22, 1.2, 1.38, 0.176)
    m.box(-0.22, -0.16, 0.9, 0.22, 0.16, 1.0, "steel_gray")


@mod("ex_downpipe", W=0.3, H=10.0, cat="高架")
def _(m, W, H, rng):
    """橋脚に沿う雨水排水の縦樋(φ150塩ビ/鋼管)+固定バンド+足元の排水ます。壁面y=0, パイプはy=+0.12"""
    m.cyl(0, 0.12, 0.3, 0.075, H - 0.3, "z", "pipe_dark", 10)
    for z in [0.8 + i * 1.5 for i in range(int((H - 0.8) / 1.5))]:
        m.cyl(0, 0.12, z, 0.09, 0.06, "z", "steel_galv", 10)
        m.box(-0.04, 0.0, z - 0.02, 0.04, 0.12, z + 0.04, "steel_galv")
    m.box(-0.2, -0.05, 0.0, 0.2, 0.35, 0.3, "concrete_stained")
    m.box(-0.14, 0.02, 0.24, 0.14, 0.28, 0.3, "grating")
    for z in (H - 0.2,):
        m.cyl(0, 0.12, z, 0.1, 0.1, "z", "steel_galv", 10)


@mod("ex_downpipe_cross", W=2.4, H=0.5, cat="高架")
def _(m, W, H, rng):
    """桁側の横引き管から柱の縦樋へ折れる部分(エルボ2つ+吊り金具)"""
    pipe(m, (-1.2, 0.12, 0.0), (0.0, 0.12, 0.0), 0.075, "pipe_dark", 10)
    m.cyl(0, 0.12, -0.1, 0.075, 0.1, "z", "pipe_dark", 10)
    for x in (-1.0, -0.3):
        m.box(x - 0.03, 0.0, -0.05, x + 0.03, 0.2, 0.05, "steel_galv")
    m.cyl(-1.2, 0.12, 0.0, 0.1, 0.06, "x", "steel_galv", 10)


@mod("ex_pier_ladder", W=0.7, H=12.0, cat="高架")
def _(m, W, H, rng):
    """橋脚の点検用ハシゴ(背かご付き・壁固定ブラケット・下部は取り外し式の施錠板)。壁面y=0"""
    ladder_z(m, 0.0, 0.2, 2.2, H - 0.4, 0.5, "steel_galv", 0.3, face=1, cage=True)
    for z in [2.5 + i * 2.0 for i in range(int((H - 3) / 2.0))]:
        m.box(-0.28, 0.0, z, -0.22, 0.2, z + 0.05, "steel_galv")
        m.box(0.22, 0.0, z, 0.28, 0.2, z + 0.05, "steel_galv")
    m.box(-0.3, 0.2, 2.0, 0.3, 0.24, 2.2, "steel_gray")
    ladder_z(m, 0.0, 0.2, 0.3, 2.2, 0.5, "steel_galv", 0.3, face=1)
    m.box(-0.3, 0.15, 0.3, 0.3, 0.22, 0.8, "sign_yellow")


@mod("ex_scaffold_bracket", W=2.0, H=0.6, cat="高架")
def _(m, W, H, rng):
    """橋脚/桁の足場吊り用の金具(アイボルトと受けピース)が一定間隔で並ぶ。壁面y=0"""
    m.box(-1.0, 0.0, 0.2, 1.0, 0.04, 0.26, "anchor_galv")
    for x in (-0.8, -0.27, 0.27, 0.8):
        m.cyl(x, 0.04, 0.23, 0.045, 0.05, "y", "anchor_galv", 8)
        m.tube(x, 0.09, 0.23, 0.05, 0.03, 0.04, "y", "anchor_galv", 8)
        m.box(x - 0.04, 0.0, 0.1, x + 0.04, 0.05, 0.36, "bearing_gray")


@mod("ex_pier_plate", W=0.7, H=0.5, cat="高架")
def _(m, W, H, rng):
    """橋脚番号板(白地に紺の橋脚番号)"""
    m.box(-0.32, 0.0, 0.0, 0.32, 0.03, 0.22, "alu_black")
    sign_panel(m, "pier_no", -0.3, 0.3, 0.02, 0.2, 0.031)
    for x in (-0.3, 0.3):
        m.cyl(x, 0.03, 0.11, 0.01, 0.015, "y", "steel_galv", 5)


@mod("ex_cable_tray", W=6.0, H=0.9, cat="高架")
def _(m, W, H, rng):
    """桁下に吊るケーブルトレイ+電線管(吊りボルト・ブラケット・ケーブル)。原点=桁下面中央, x=橋軸"""
    for x in (-2.8, -0.9, 0.9, 2.8):
        m.cyl(x - 0.25, 0.0, -0.4, 0.008, 0.4, "z", "anchor_galv", 5)
        m.cyl(x + 0.25, 0.0, -0.4, 0.008, 0.4, "z", "anchor_galv", 5)
        m.box(x - 0.3, -0.15, -0.44, x + 0.3, 0.15, -0.4, "anchor_galv")
    m.box(-3.0, -0.15, -0.5, 3.0, 0.15, -0.46, "grating")
    m.box(-3.0, -0.15, -0.46, 3.0, -0.13, -0.34, "anchor_galv")
    m.box(-3.0, 0.13, -0.46, 3.0, 0.15, -0.34, "anchor_galv")
    for y, r in ((-0.07, 0.025), (0.0, 0.03), (0.06, 0.02)):
        pipe(m, (-3.0, y, -0.42), (3.0, y, -0.42), r, "rubber", 6)
    pipe(m, (-3.0, 0.32, -0.3), (3.0, 0.32, -0.3), 0.03, "pipe_dark", 6)
    for x in (-2.8, 0.0, 2.8):
        m.box(x - 0.02, 0.28, -0.34, x + 0.02, 0.36, -0.26, "anchor_galv")


@mod("ex_under_pipe_run", W=6.0, H=0.5, cat="高架")
def _(m, W, H, rng):
    """桁下の横引き排水管(吊りバンド+継手の差込部)"""
    pipe(m, (-3.0, 0.0, -0.2), (3.0, 0.0, -0.2), 0.075, "pipe_dark", 10)
    for x in (-2.5, -0.8, 0.8, 2.5):
        m.cyl(x, 0.0, -0.2, 0.09, 0.07, "x", "steel_galv", 10)
        m.box(x - 0.015, -0.015, -0.2, x + 0.015, 0.015, 0.0, "anchor_galv")
    m.cyl(0.0, 0.0, -0.2, 0.1, 0.12, "x", "pipe_dark", 10)


@mod("ex_bearing", W=1.2, H=0.55, cat="高架")
def _(m, W, H, rng):
    """鋼製支承(ベースプレート+アンカーボルト+ピボット+ゴムカバー)。原点=支承座中央, 上=桁下面"""
    m.box(-0.5, -0.5, 0.0, 0.5, 0.5, 0.06, "bearing_gray")
    for sx in (-0.4, 0.4):
        for sy in (-0.4, 0.4):
            m.cyl(sx, sy, 0.06, 0.03, 0.1, "z", "anchor_galv", 6)
    m.cyl(0, 0, 0.06, 0.28, 0.22, "z", "bearing_gray", 16)
    m.cyl(0, 0, 0.28, 0.32, 0.04, "z", "steel_gray", 16)
    m.box(-0.45, -0.45, 0.32, 0.45, 0.45, 0.5, "bearing_gray")
    m.tube(0, 0, 0.12, 0.34, 0.3, 0.16, "z", "rubber", 16)


@mod("ex_fall_prevent", W=1.2, H=1.4, cat="高架")
def _(m, W, H, rng):
    """落橋防止装置(PCケーブル/チェーン式): 桁側ブラケット+橋脚側ブラケット+連結チェーン+緩衝ゴム"""
    m.box(-0.35, -0.2, 0.0, 0.35, 0.2, 0.06, "bearing_gray")
    m.box(-0.35, -0.2, 1.2, 0.35, 0.2, 1.26, "bearing_gray")
    for z0, z1 in ((0.06, 0.55), (0.45, 0.85), (0.75, 1.2)):
        tube3(m, [(0.0, 0.0, z0), (0.12, 0.0, (z0 + z1) / 2), (0.0, 0.0, z1)], 0.03, "steel_galv", 6)
    for sx in (-0.28, 0.28):
        m.box(sx - 0.04, -0.15, 0.06, sx + 0.04, 0.15, 0.4, "bearing_gray")
        m.box(sx - 0.04, -0.15, 0.85, sx + 0.04, 0.15, 1.2, "bearing_gray")
    m.box(-0.35, -0.2, 0.0, 0.35, 0.2, 0.01, "rubber")


@mod("ex_noise_barrier", W=3.0, H=3.2, cat="高架")
def _(m, W, H, rng):
    """遮音壁(先端改良型): H形鋼の支柱+下部は金属パネル+上部は透明アクリル+上端の傘状キャップ。+y=車道側"""
    for x in (-1.5, 1.5):
        m.box(x - 0.05, -0.1, 0.0, x + 0.05, 0.1, 2.9, "steel_gray")
        m.box(x - 0.1, -0.1, 0.0, x + 0.1, 0.1, 0.05, "steel_gray")
    m.box(-1.45, -0.03, 0.15, 1.45, 0.03, 1.0, "alu_main")
    m.box(-1.45, -0.02, 1.0, 1.45, 0.02, 2.8, "polycarbonate")
    m.box(-1.5, -0.06, 2.8, 1.5, 0.1, 2.88, "alu_main")
    prism_any(m, [(0.1, 2.88), (0.55, 3.05), (0.5, 3.12), (-0.04, 2.95)], "x", -1.5, 1.5, "alu_main")


@mod("ex_lightpole_hw", W=0.6, H=11.0, cat="高架")
def _(m, W, H, rng):
    """高速道路の照明柱(高欄取付・10m・アーム2.5m・ナトリウム灯器)。原点=ポール根元, +y=外側, アームは-y(車道側)"""
    m.box(-0.2, -0.16, 0.0, 0.2, 0.16, 0.08, "steel_galv")
    m.lathe(0, 0, 0.08, [(0.12, 0.0), (0.075, 10.0)], "pole_white", 10)
    beam(m, (0, 0, 9.8), (0, -2.4, 10.3), 0.07, 0.07, "pole_white")
    m.box(-0.14, -2.9, 10.2, 0.14, -2.3, 10.4, "alu_black")
    m.box(-0.12, -2.8, 10.17, 0.12, -2.35, 10.2, "lamp_lens")
    m.cyl(0, 0.0, 9.0, 0.09, 0.04, "z", "steel_galv", 10)
    m.box(-0.1, -0.08, 0.4, 0.1, 0.0, 1.0, "steel_gray")


@mod("ex_sign_gantry", W=8.0, H=7.6, cat="高架")
def _(m, W, H, rng):
    """片持ち式の案内標識(F型柱+腕+緑の方面標識+白文字帯)。柱は路側、板は車道上へ張り出す(+x方向)"""
    m.box(-0.3, -0.3, 0, 0.3, 0.3, 0.2, "steel_gray")
    m.lathe(0, 0, 0.2, [(0.24, 0.0), (0.16, 6.2)], "pole_white", 12)
    for z in (5.4, 6.2):
        beam(m, (0, 0, z), (6.6, 0, z), 0.12, 0.12, "pole_white")
    tube3(m, [(0, 0, 4.4), (3.3, 0, 5.7)], 0.04, "pole_white", 6)
    m.box(1.8, -0.06, 3.5, 6.2, 0.06, 5.7, "sign_green")
    for i, (z0, w) in enumerate(((5.2, 2.8), (4.7, 2.2), (4.2, 3.2), (3.8, 1.6))):
        m.box(2.0, 0.065, z0, 2.0 + w, 0.07, z0 + 0.28, "sign_white")
    m.box(5.0, 0.065, 4.5, 6.0, 0.07, 5.5, "sign_white")
    m.box(5.1, 0.07, 4.6, 5.9, 0.072, 5.4, "sign_blue")
    m.box(1.8, -0.1, 3.45, 6.2, 0.1, 3.5, "alu_silver")


@mod("ex_vms", W=4.4, H=6.0, cat="高架")
def _(m, W, H, rng):
    """可変情報板(F型柱+黒い箱+琥珀色のLED文字行)"""
    m.lathe(0, 0, 0.0, [(0.22, 0.0), (0.15, 5.6)], "pole_dark", 12)
    beam(m, (0, 0, 5.2), (2.0, 0, 5.2), 0.15, 0.15, "pole_dark")
    m.box(0.6, -0.15, 3.4, 4.2, 0.15, 5.2, "alu_black")
    for r in range(3):
        for c in range(12):
            if (r * 7 + c * 3) % 5 != 0:
                m.box(0.75 + c * 0.28, 0.151, 4.55 - r * 0.55, 0.95 + c * 0.28, 0.155, 4.95 - r * 0.55, "led_amber")
    m.box(0.55, -0.16, 3.35, 4.25, 0.16, 3.4, "steel_gray")


@mod("ex_etc_gate", W=3.6, H=5.6, cat="高架")
def _(m, W, H, rng):
    """ETCレーン(1レーン): 料金所アイランド+路上アンテナ付き門+遮断バー+「ETC」の青/紫の標示。原点=レーン中心の地面, y=進行方向"""
    for sx in (-1.9, 1.9):
        m.box(sx - 0.45, -3.0, 0.0, sx + 0.45, 3.0, 0.2, "rc_concrete")
        m.box(sx - 0.45, -3.0, 0.2, sx + 0.45, -2.9, 0.22, "paint_road_yellow")
    for sx in (-1.9, 1.9):
        m.box(sx - 0.2, -0.3, 0.2, sx + 0.2, 0.3, 4.9, "paint_white")
    m.box(-2.4, -0.45, 4.9, 2.4, 0.45, 5.2, "alu_silver")
    sign_panel(m, "etc", -1.1, 1.1, 4.95, 5.15, -0.455, flip=True)
    m.box(-0.2, -0.15, 4.65, 0.2, 0.15, 4.9, "alu_black")
    m.box(-0.1, 0.15, 4.7, 0.1, 0.17, 4.85, "sig_lens_dark")
    m.box(-1.7, -0.1, 0.2, -1.5, 0.1, 1.2, "paint_white")
    for i in range(6):
        m.box(-1.5 + i * 0.5, -0.025, 1.05, -1.5 + i * 0.5 + 0.25, 0.025, 1.12, "sign_red" if i % 2 else "sign_white")


@mod("ex_toll_booth", W=3.6, H=4.2, cat="高架")
def _(m, W, H, rng):
    """料金所ブース(有人): ガラス窓付き箱+庇+表示灯+アイランド"""
    m.box(-1.5, -2.0, 0.0, 1.5, 2.0, 0.25, "rc_concrete")
    m.box(-1.2, -1.5, 0.25, 1.2, 1.5, 2.6, "paint_white")
    m.box(-1.22, -1.0, 1.0, -1.18, 1.0, 2.3, "glass_main")
    m.box(1.18, -1.0, 1.0, 1.22, 1.0, 2.3, "glass_main")
    m.box(-1.5, -2.2, 2.6, 1.5, 2.2, 2.75, "alu_silver")
    for y in (-2.0, 2.0):
        m.box(-1.5, y - 0.04, 2.75, 1.5, y + 0.04, 3.2, "sign_blue")
    m.box(-0.2, -1.55, 2.0, 0.2, -1.5, 2.3, "led_amber")


@mod("ex_bird_net", W=6.0, H=2.6, cat="高架")
def _(m, W, H, rng):
    """鳥よけネット(桁下フランジ下に張る): 傾斜したメッシュ+吊りワイヤ+固定アングル。原点=桁下面, 奥(-y)に桁、手前(+y)へ下がる"""
    m.box(-3.0, -0.05, -0.05, 3.0, 0.05, 0.0, "anchor_galv")
    m.box(-3.0, 2.0, -1.55, 3.0, 2.05, -1.5, "anchor_galv")
    for i in range(25):
        x = -3.0 + i * 0.25
        pipe(m, (x, 0.0, -0.05), (x, 2.0, -1.5), 0.006, "net_nylon", 4)
    for j in range(10):
        t = j / 9
        pipe(m, (-3.0, 2.0 * t, -0.05 - 1.45 * t), (3.0, 2.0 * t, -0.05 - 1.45 * t), 0.006, "net_nylon", 4)
    for x in (-2.9, 0.0, 2.9):
        pipe(m, (x, 0.0, 0.2), (x, 2.0, -1.5), 0.01, "steel_galv", 4)


@mod("ex_cctv_pole", W=0.6, H=8.0, cat="高架")
def _(m, W, H, rng):
    """路側のCCTV/気象観測ポール(8m): ポール+ドームカメラ+配線ボックス+避雷針"""
    m.cyl(0, 0, 0, 0.15, 0.4, "z", "rc_concrete", 10)
    m.lathe(0, 0, 0.4, [(0.1, 0.0), (0.06, 7.2)], "pole_white", 10)
    m.box(-0.2, -0.12, 1.0, 0.2, -0.02, 1.8, "steel_white")
    m.lathe(0, 0.22, 7.4, [(0.09, 0.0), (0.12, 0.22), (0.08, 0.4)], "alu_black", 12)
    m.cyl(0, 0, 7.6, 0.01, 0.4, "z", "steel_galv", 4)


@mod("ex_guard_wall", W=3.0, H=0.9, cat="高架")
def _(m, W, H, rng):
    """剛性防護柵(F型コンクリート防護壁)+反射板"""
    prism_any(m, [(-0.3, 0.0), (0.3, 0.0), (0.2, 0.32), (0.13, 0.9), (-0.13, 0.9), (-0.2, 0.32)], "x", -1.5, 1.5, "concrete_stained")
    m.box(-1.5, -0.02, 0.0, 1.5, 0.02, 0.02, "rubber")
    m.box(-0.12, 0.2, 0.7, 0.12, 0.215, 0.8, "sign_yellow")


@mod("ex_joint_cover", W=4.0, H=0.5, cat="高架")
def _(m, W, H, rng):
    """桁端の伸縮装置の下の遮水ゴムトラフ+排水管+吊り金具(桁の端部直下)"""
    m.box(-1.9, -0.25, -0.35, 1.9, 0.25, -0.3, "rubber")
    m.box(-1.9, -0.28, -0.3, 1.9, -0.25, -0.1, "rubber")
    m.box(-1.9, 0.25, -0.3, 1.9, 0.28, -0.1, "rubber")
    pipe(m, (1.9, 0.0, -0.32), (2.5, 0.0, -0.6), 0.04, "pipe_dark", 6)
    for x in (-1.5, 0.0, 1.5):
        m.box(x - 0.02, -0.3, -0.3, x + 0.02, 0.3, 0.0, "anchor_galv")


@mod("ex_underdeck_lamp", W=0.6, H=0.4, cat="高架")
def _(m, W, H, rng):
    """桁下照明(防水型LED灯器): 取付板+箱+拡散パネル。上=桁下面に付ける"""
    m.box(-0.18, -0.08, -0.04, 0.18, 0.08, 0.0, "steel_gray")
    m.box(-0.15, -0.07, -0.16, 0.15, 0.07, -0.04, "alu_main")
    m.box(-0.13, -0.05, -0.19, 0.13, 0.05, -0.16, "led_white")
