"""ロードサイド(店舗ファサード・看板・GS・駐車場設備)。看板絵は shop_atlas.png(架空の店名)。座標: 壁部材は壁面y=0・外向き+y、単独物は原点=設置点の地面・+y=正面。"""
import math

from .registry import T, frame, glass, hole_wall, interior, mod, reg
from .xutil import MATERIALS, M, handrail_x, pipe, post, prism_any, shop_uv, sign_panel  # noqa: F401


def _front(m, W, H, wall, x0, x1, z0, z1, fm="alu_black", mull=3, kick=0.0, door=False, panel_mat="glass_main", spandrel=None):
    """大開口の店舗正面: 壁+開口+細い方立+腰壁+ガラス+(自動ドア)"""
    hole_wall(m, W, H, x0, x1, z0, z1, wall)
    interior(m, x0, x1, z0, z1)
    frame(m, x0, x1, z0, z1, fm, 0.05, 0.08, -0.12)
    glass(m, x0 + 0.05, x1 - 0.05, z0 + 0.05, z1 - 0.05, -0.1, panel_mat)
    for i in range(1, mull):
        x = x0 + i * (x1 - x0) / mull
        m.box(x - 0.025, -0.14, z0, x + 0.025, -0.05, z1, fm)
    if door:
        dx = (x0 + x1) / 2
        m.box(dx - 0.9, -0.17, z1 - 0.28, dx + 0.9, -0.05, z1 - 0.05, "alu_silver")                 # 自動ドアの上枠+センサー
        m.box(dx - 0.05, -0.19, z1 - 0.22, dx + 0.05, -0.17, z1 - 0.12, "sig_lens_dark")
        for sx in (-0.9, 0.0, 0.9):
            m.box(dx + sx - 0.025, -0.14, z0, dx + sx + 0.025, -0.06, z1 - 0.28, fm)
        m.box(dx - 0.95, 0.0, 0.0, dx + 0.95, 0.9, 0.02, "tile_main")                                # 玄関マット
    if kick:
        m.box(x0, -0.13, z0, x1, -0.05, z0 + kick, fm)


@mod("rs_glass_front", H=3.6, cat="ロードサイド")
def _(m, W, H, rng):
    _front(m, W, H, "siding_ceramic_gray", -W / 2 + 0.2, W / 2 - 0.2, 0.1, 2.7, mull=3, kick=0.35)


@mod("rs_glass_door_auto", H=3.6, cat="ロードサイド")
def _(m, W, H, rng):
    _front(m, W, H, "siding_ceramic_gray", -W / 2 + 0.2, W / 2 - 0.2, 0.0, 2.7, mull=4, door=True)


@mod("rs_showroom_glass", H=4.8, cat="ロードサイド")
def _(m, W, H, rng):
    """カーディーラー: 床から天井までのガラス+細い柱+ショールームの天井照明が見える"""
    _front(m, W, H, "alu_main", -W / 2 + 0.05, W / 2 - 0.05, 0.05, 4.0, mull=2, fm="alu_silver")
    m.box(-W / 2, -0.35, 4.0, W / 2, 0.02, 4.7, "alu_main")                                             # 庇
    m.box(-W / 2, -0.33, 4.65, W / 2, 0.0, 4.7, "led_white")


@mod("rs_pachi_wall", H=7.0, cat="ロードサイド")
def _(m, W, H, rng):
    """パチンコ店: 金/紫のパネル壁+縦長ネオンストリップ+小窓なしの塊感"""
    m.box(-W / 2, -0.25, 0, W / 2, 0.0, H, "paint_main")
    m.box(-W / 2, 0.0, 0.0, W / 2, 0.04, 1.0, "alu_black")
    for i in range(int(W / 0.45)):
        x = -W / 2 + 0.2 + i * 0.45
        m.box(x, 0.04, 1.1, x + 0.06, 0.08, H - 0.5, "alu_silver")
    for z, c in ((1.2, "sign_red"), (3.2, "sign_yellow"), (5.4, "sign_blue")):
        m.box(-W / 2, 0.04, z, W / 2, 0.08, z + 0.06, c)
    m.box(-W / 2 + 0.2, 0.04, 6.4, W / 2 - 0.2, 0.09, 6.9, "sign_yellow")


@mod("rs_family_wall", H=4.2, cat="ロードサイド")
def _(m, W, H, rng):
    """ファミレス: 下半分レンガ調+大きなガラス窓+上部の屋根の帯(マンサード風)"""
    _front(m, W, H, "siding_ceramic_brick", -W / 2 + 0.3, W / 2 - 0.3, 0.9, 2.8, mull=3, fm="alu_bronze")
    m.box(-W / 2, 0.0, 0.0, W / 2, 0.04, 0.9, "siding_ceramic_brick")
    prism_any(m, [(0.0, 3.25), (0.55, 3.25), (0.0, 3.95)], "x", -W / 2, W / 2, "roof_cement_red")
    m.box(-W / 2, -0.1, 3.1, W / 2, 0.45, 3.28, "alu_bronze")


@mod("rs_boxstore_wall", H=7.0, cat="ロードサイド")
def _(m, W, H, rng):
    """ホームセンター/スーパー: 大きな波板外壁(青)+コーナーのガラスエントランス風の開口+笠木"""
    m.box(-W / 2, -0.2, 0, W / 2, 0.0, H, "corrugated_blue")
    m.box(-W / 2, -0.21, 0, W / 2, 0.03, 0.4, "rc_concrete")
    m.box(-W / 2, -0.21, H - 0.25, W / 2, 0.08, H, "alu_silver")
    z = 1.6
    while z < H - 0.6:
        m.box(-W / 2, 0.0, z, W / 2, 0.012, z + 0.03, "alu_silver")
        z += 1.4


@mod("rs_ramen_wall", H=3.8, cat="ロードサイド")
def _(m, W, H, rng):
    """ラーメン屋: 木格子+暖簾+小窓、赤い庇"""
    m.box(-W / 2, -0.2, 0, W / 2, 0.0, H, "wood_dark")
    for i in range(int(W / 0.12)):
        m.box(-W / 2 + i * 0.12, 0.0, 0.2, -W / 2 + i * 0.12 + 0.03, 0.05, 2.4, "wood_dark")
    hole_wall(m, W, H, -1.0, 1.0, 0.0, 2.2, "wood_dark")
    frame(m, -1.0, 1.0, 0.0, 2.2, "wood_light", 0.08, 0.06, -0.12)
    glass(m, -0.92, 0.92, 0.08, 2.12, -0.1)
    interior(m, -1.0, 1.0, 0.0, 2.2)
    for k in range(3):                                                                                     # 暖簾
        m.box(-0.9 + k * 0.62, 0.05, 1.3, -0.35 + k * 0.62, 0.065, 2.2, "sign_red")
    m.box(-W / 2, 0.0, 2.45, W / 2, 0.75, 2.5, "sign_red")
    m.box(-W / 2, 0.75, 2.2, W / 2, 0.78, 2.5, "sign_red")


@mod("rs_drug_wall", H=4.2, cat="ロードサイド")
def _(m, W, H, rng):
    """ドラッグストア: 白壁+緑の帯+大きな入口のガラスと棚が見える"""
    _front(m, W, H, "paint_white", -W / 2 + 0.2, W / 2 - 0.2, 0.3, 2.8, mull=3, kick=0.0, door=False)
    m.box(-W / 2, -0.05, 3.2, W / 2, 0.02, 3.9, "sign_green")


# ---- 看板パネル(店舗ごと): 壁に付ける横長の看板 ----
def _fascia(m, key, w=3.4, h=0.95):
    m.box(-w / 2 - 0.04, 0.0, 0.0, w / 2 + 0.04, 0.2, h + 0.08, "alu_black")
    sign_panel(m, key, -w / 2, w / 2, 0.04, 0.04 + h, 0.205)
    for x in (-w / 2 + 0.2, w / 2 - 0.2):
        m.box(x - 0.03, -0.1, 0.05, x + 0.03, 0.0, 0.2, "steel_gray")


_SHOP_KEYS = ["conv_a", "conv_b", "conv_c", "drug_a", "drug_b", "family_a", "family_b", "super_a", "super_b", "home_a", "home_b", "pachi_a", "pachi_b",
              "car_a", "car_b", "ramen_a", "ramen_b", "shop100_a", "shop100_b", "karaoke", "bank", "gs_a", "gs_b", "udon", "park_a", "park_b", "cl_a", "cl_b", "shoe",
              "bk", "rent", "hosp", "dental", "wash", "sushi", "bake", "izaka", "gym", "nursery", "tire", "used", "agri"]
for _k in _SHOP_KEYS:
    reg(f"rs_fascia_{_k}", (lambda k: lambda m, W, H, r: _fascia(m, k))(_k), W=3.6, H=1.1, cat="店舗看板")


def _pole_sign(m, keys, h_pole=7.0, w=2.6, hh=0.85):
    """ポール看板(単柱+箱を縦に重ねる)。keysの数だけ箱を積む"""
    m.box(-0.5, -0.5, 0, 0.5, 0.5, 0.25, "rc_concrete")
    m.box(-0.18, -0.12, 0.25, 0.18, 0.12, h_pole - 0.1, "steel_gray")
    z = h_pole - 0.1 - len(keys) * (hh + 0.12)
    for i, k in enumerate(keys):
        zz = z + i * (hh + 0.12)
        m.box(-w / 2, -0.15, zz, w / 2, 0.15, zz + hh + 0.1, "alu_black")
        sign_panel(m, k, -w / 2 + 0.04, w / 2 - 0.04, zz + 0.05, zz + 0.05 + hh, 0.155)
        sign_panel(m, k, -w / 2 + 0.04, w / 2 - 0.04, zz + 0.05, zz + 0.05 + hh, -0.155, flip=True)


for _n, _ks, _hp in (("conv", ["conv_a"], 7.0), ("drug", ["drug_a"], 7.5), ("family", ["family_a", "park_a"], 8.5), ("super", ["super_a", "park_b"], 9.0),
                     ("home", ["home_a", "home_b"], 10.0), ("pachi", ["pachi_a", "pachi_b", "pachi_a"], 12.0), ("car", ["car_a"], 7.0), ("ramen", ["ramen_a"], 6.0),
                     ("shop100", ["shop100_a", "park_a"], 8.0), ("multi", ["drug_b", "dental", "hosp", "bank"], 11.0), ("tire", ["tire", "used"], 7.5)):
    reg(f"rs_pylon_{_n}", (lambda ks, hp: lambda m, W, H, r: _pole_sign(m, ks, hp))(_ks, _hp), W=2.8, H=_hp, cat="店舗看板")


@mod("rs_nobori_flags", W=2.0, H=3.6, cat="店舗看板")
def _(m, W, H, rng):
    """幟(のぼり旗)3本: 台座+ポール+旗"""
    for i, c in enumerate(("sign_red", "sign_yellow", "sign_blue")):
        x = -0.6 + i * 0.6
        m.cyl(x, 0, 0, 0.17, 0.05, "z", "rubber", 10)
        m.cyl(x, 0, 0.05, 0.012, 3.0, "z", "alu_silver", 5)
        m.box(x + 0.0, -0.006, 1.2, x + 0.5, 0.006, 3.0, c)


@mod("rs_flag_string", W=10.0, H=4.0, cat="店舗看板")
def _(m, W, H, rng):
    """中古車店のカラーポール旗(ロープ+三角旗)"""
    for x in (-5.0, 5.0):
        m.cyl(x, 0, 0, 0.05, 4.0, "z", "steel_gray", 6)
    for i in range(24):
        x = -4.8 + i * 0.4
        c = ("sign_red", "sign_yellow", "sign_blue", "sign_white")[i % 4]
        m.poly([(x, 0, 3.9 - 0.04 * abs(12 - i) / 12), (x + 0.3, 0, 3.9 - 0.04 * abs(12 - i) / 12), (x + 0.15, 0, 3.55)], c)
    pipe(m, (-5.0, 0, 3.95), (5.0, 0, 3.95), 0.006, "steel_galv", 4)


# ---- ガソリンスタンド ----
@mod("gs_canopy", W=14.0, H=5.4, cat="ガソリンスタンド")
def _(m, W, H, rng):
    """GSキャノピー(14m x 9m): 4本柱(白+ブランド帯)・薄い屋根・下面の照明・縁のブランドカラー帯。原点=奥側中央、+y=手前"""
    D = 9.0
    for sx in (-5.5, 5.5):
        for sy in (1.0, 8.0):
            m.box(sx - 0.2, sy - 0.2, 0, sx + 0.2, sy + 0.2, 4.8, "steel_white")
            m.box(sx - 0.21, sy - 0.21, 1.6, sx + 0.21, sy + 0.21, 2.0, "sign_red")
    m.box(-7.0, -0.5, 4.8, 7.0, D + 0.5, 5.15, "steel_white")
    m.box(-7.0, D + 0.5, 4.85, 7.0, D + 0.55, 5.35, "sign_red")
    for x in (-7.0, 7.0):
        m.box(x - 0.02, -0.5, 4.85, x + 0.02, D + 0.5, 5.35, "sign_red")
    m.box(-7.0, -0.55, 4.85, 7.0, -0.5, 5.35, "sign_red")
    sign_panel(m, "gs_a", -3.0, 3.0, 4.95, 5.3, D + 0.56)
    for sx in (-4.5, -1.5, 1.5, 4.5):
        for sy in (2.5, 6.5):
            m.box(sx - 0.4, sy - 0.15, 4.77, sx + 0.4, sy + 0.15, 4.8, "led_white")
    m.box(-7.0, -0.5, 4.7, 7.0, D + 0.5, 4.8, "steel_gray")


@mod("gs_pump", W=1.2, H=2.3, cat="ガソリンスタンド")
def _(m, W, H, rng):
    """固定式給油機: 本体+計量表示+ノズル掛け+ホース。+y=車側"""
    m.box(-0.4, -0.25, 0.0, 0.4, 0.25, 0.1, "rc_concrete")
    m.box(-0.34, -0.2, 0.1, 0.34, 0.2, 1.9, "steel_white")
    m.box(-0.3, 0.2, 1.4, 0.3, 0.22, 1.82, "sig_lens_dark")
    for i in range(4):
        m.box(-0.22 + i * 0.12, 0.22, 1.5, -0.14 + i * 0.12, 0.225, 1.7, "sig_amber_digit")
    m.box(-0.34, -0.2, 1.9, 0.34, 0.2, 2.3, "sign_red")
    m.box(-0.34, -0.2, 2.05, 0.34, 0.2, 2.2, "sign_white")
    m.box(-0.33, 0.2, 1.0, -0.05, 0.28, 1.3, "alu_black")                                                     # ノズル掛け
    pipe(m, (-0.2, 0.28, 1.2), (-0.2, 0.34, 1.35), 0.012, "alu_silver", 5)
    pipe(m, (0.25, 0.2, 1.0), (0.38, 0.3, 0.55), 0.016, "rubber", 6)
    pipe(m, (0.38, 0.3, 0.55), (0.3, 0.35, 0.95), 0.016, "rubber", 6)


@mod("gs_island", W=6.0, H=2.4, cat="ガソリンスタンド")
def _(m, W, H, rng):
    """給油アイランド: 縁石付きコンクリート島に給油機2基+ガードポスト"""
    m.box(-3.0, -0.5, 0, 3.0, 0.5, 0.2, "rc_concrete")
    m.box(-3.0, -0.5, 0.2, 3.0, 0.5, 0.215, "paint_road_yellow")
    for x in (-1.2, 1.2):
        m.box(x - 0.4, -0.25, 0.2, x + 0.4, 0.25, 0.28, "rc_concrete")
        m.box(x - 0.34, -0.2, 0.28, x + 0.34, 0.2, 1.9, "steel_white")
        m.box(x - 0.3, 0.2, 1.4, x + 0.3, 0.22, 1.82, "sig_lens_dark")
        for i in range(4):
            m.box(x - 0.22 + i * 0.12, 0.22, 1.5, x - 0.14 + i * 0.12, 0.225, 1.7, "sig_amber_digit")
        m.box(x - 0.34, -0.2, 1.9, x + 0.34, 0.2, 2.3, "sign_red")
    for x in (-2.7, 2.7):
        m.cyl(x, 0, 0.2, 0.07, 0.6, "z", "pole_white", 8)
    pipe(m, (-0.8, 0.25, 1.2), (-0.2, 0.4, 0.8), 0.015, "rubber", 6)


@mod("gs_price_pole", W=1.6, H=7.5, cat="ガソリンスタンド")
def _(m, W, H, rng):
    """ガソリン価格看板: ブランド上部+LED価格板(レギュラー/ハイオク/軽油)"""
    m.box(-0.4, -0.4, 0, 0.4, 0.4, 0.2, "rc_concrete")
    m.box(-0.12, -0.1, 0.2, 0.12, 0.1, 6.0, "steel_white")
    m.box(-0.8, -0.14, 6.2, 0.8, 0.14, 7.4, "sign_red")
    sign_panel(m, "gs_a", -0.75, 0.75, 6.65, 7.35, 0.145)
    sign_panel(m, "gs_a", -0.75, 0.75, 6.65, 7.35, -0.145, flip=True)
    m.box(-0.7, -0.16, 3.6, 0.7, 0.16, 6.05, "alu_black")
    for k in range(3):
        z = 5.7 - k * 0.78
        m.box(-0.62, 0.16, z, 0.62, 0.17, z + 0.7, "sig_lens_dark")
        for d in range(3):
            m.box(-0.45 + d * 0.4, 0.17, z + 0.1, -0.15 + d * 0.4, 0.175, z + 0.6, ("sig_amber_digit" if k != 1 else "sig_amber_digit"))
        m.box(-0.62, 0.17, z, -0.5, 0.176, z + 0.7, ("sign_red", "sign_yellow", "sign_blue")[k])


@mod("gs_vent_pipe", W=0.6, H=4.2, cat="ガソリンスタンド")
def _(m, W, H, rng):
    """地下タンクの通気管(2本立ち・先端キャップ・支柱)"""
    for x in (-0.12, 0.12):
        m.cyl(x, 0, 0, 0.03, 4.0, "z", "steel_gray", 8)
        m.cyl(x, 0, 4.0, 0.045, 0.1, "z", "steel_gray", 8)
    m.box(-0.3, -0.05, 0.0, 0.3, 0.05, 0.1, "rc_concrete")
    m.box(-0.18, -0.06, 1.2, 0.18, 0.0, 1.26, "steel_galv")
    m.box(-0.18, -0.06, 2.8, 0.18, 0.0, 2.86, "steel_galv")


@mod("gs_air_station", W=0.6, H=1.2, cat="ガソリンスタンド")
def _(m, W, H, rng):
    m.box(-0.2, -0.15, 0, 0.2, 0.15, 1.0, "sign_blue")
    m.box(-0.15, 0.15, 0.6, 0.15, 0.17, 0.9, "sig_lens_dark")
    m.cyl(0.05, 0.17, 0.4, 0.015, 0.2, "y", "rubber", 5)


@mod("gs_office_front", H=4.0, cat="ガソリンスタンド")
def _(m, W, H, rng):
    """GS事務所: 白壁+大きなガラス+ブランドカラー帯"""
    _front(m, W, H, "paint_white", -W / 2 + 0.3, W / 2 - 0.3, 0.2, 2.6, mull=3, fm="alu_silver")
    m.box(-W / 2, -0.02, 2.9, W / 2, 0.04, 3.4, "sign_red")


# ---- 駐車場設備 ----
@mod("pk_pay_machine", W=0.6, H=1.7, cat="駐車場")
def _(m, W, H, rng):
    """コインパーキング精算機(スタンド型): 本体+表示+硬貨口+紙幣口+台座+看板"""
    m.box(-0.35, -0.25, 0, 0.35, 0.25, 0.1, "rc_concrete")
    m.box(-0.28, -0.2, 0.1, 0.28, 0.2, 1.45, "steel_white")
    m.box(-0.22, 0.2, 1.05, 0.22, 0.22, 1.35, "sig_lens_dark")
    for z in (0.85, 0.7, 0.55):
        m.box(-0.1, 0.2, z, 0.1, 0.225, z + 0.06, "alu_black")
    m.box(-0.28, -0.2, 1.45, 0.28, 0.2, 1.7, "sign_blue")


@mod("pk_lock_plate", W=1.0, H=0.4, cat="駐車場")
def _(m, W, H, rng):
    """フラップ式ロック板(起立状態)+固定ボルト"""
    m.box(-0.5, -0.03, 0, 0.5, 0.03, 0.02, "steel_gray")
    m.box(-0.45, -0.02, 0.02, 0.45, 0.02, 0.3, "steel_gray")
    m.box(-0.45, 0.02, 0.1, 0.45, 0.03, 0.18, "paint_road_yellow")
    m.box(-0.1, -0.05, 0.3, 0.1, 0.05, 0.4, "alu_black")


@mod("pk_wheel_stop", W=1.8, H=0.12, cat="駐車場")
def _(m, W, H, rng):
    """コンクリート輪止め"""
    m.box(-0.9, -0.1, 0, 0.9, 0.1, 0.1, "rc_concrete")
    m.box(-0.9, -0.1, 0.1, 0.9, 0.1, 0.12, "paint_road_yellow")


@mod("pk_gate_bar", W=3.2, H=1.4, cat="駐車場")
def _(m, W, H, rng):
    """出入口の遮断機(支柱+アーム+センサー)と発券機"""
    m.box(-0.2, -0.2, 0, 0.2, 0.2, 1.3, "steel_white")
    m.box(-0.2, 0.2, 0.8, 0.2, 0.22, 1.1, "sig_lens_dark")
    for i in range(6):
        m.box(0.2 + i * 0.45, -0.025, 1.05, 0.2 + i * 0.45 + 0.22, 0.025, 1.12, "sign_red" if i % 2 else "sign_white")
    m.box(0.2, -0.02, 1.0, 3.1, 0.02, 1.05, "sign_white")


@mod("pk_mech_tower", W=5.6, H=5.2, cat="駐車場")
def _(m, W, H, rng):
    """2段式機械式駐車場(ピット式): 鉄骨フレーム+パレット2枚+上段の車止め+支柱ごとの注意帯。+y=車の進入側"""
    D = 5.4
    for sx in (-2.6, 2.6):
        for sy in (0.0, D):
            m.box(sx - 0.07, sy - 0.07, 0, sx + 0.07, sy + 0.07, 3.9, "steel_gray")
    for z in (0.12, 2.0):
        m.box(-2.7, -0.1, z, 2.7, D + 0.1, z + 0.1, "grating")
        m.box(-2.7, -0.1, z + 0.1, -2.5, D + 0.1, z + 0.2, "steel_gray")
        m.box(2.5, -0.1, z + 0.1, 2.7, D + 0.1, z + 0.2, "steel_gray")
    m.box(-2.2, 0.0, 2.1, 2.2, 0.2, 2.2, "rc_concrete")
    m.box(-2.7, -0.1, 3.9, 2.7, D + 0.1, 3.95, "polycarbonate")
    for sx in (-2.6, 2.6):
        m.box(sx - 0.075, -0.075, 0.0, sx + 0.075, 0.075, 0.3, "paint_road_yellow")
    m.box(2.8, 2.5, 0.0, 3.2, 3.0, 1.2, "sign_blue")


@mod("pk_sign_coin", W=0.8, H=3.0, cat="駐車場")
def _(m, W, H, rng):
    """コインパーキング看板(A型+ポール): 最大料金表付き"""
    m.cyl(0, 0, 0, 0.04, 3.0, "z", "pole_dark", 8)
    m.box(-0.4, -0.04, 1.9, 0.4, 0.04, 2.9, "sign_blue")
    sign_panel(m, "park_a", -0.38, 0.38, 2.4, 2.88, 0.045)
    m.box(-0.38, 0.045, 1.95, 0.38, 0.05, 2.35, "sign_white")
    for z in (2.2, 2.05):
        m.box(-0.3, 0.05, z, 0.3, 0.052, z + 0.05, "alu_black")


@mod("pk_carport_row", W=5.0, H=2.7, cat="駐車場")
def _(m, W, H, rng):
    """月極駐車場の連棟カーポート(片流れ・折板屋根)"""
    for sx in (-2.5, 2.5):
        for sy in (0.0, 5.0):
            m.box(sx - 0.06, sy - 0.06, 0, sx + 0.06, sy + 0.06, 2.4, "steel_galv")
    m.box(-2.7, -0.2, 2.45, 2.7, 5.2, 2.55, "steel_galv")
    for i in range(9):
        m.box(-2.7 + i * 0.6, -0.2, 2.55, -2.7 + i * 0.6 + 0.04, 5.2, 2.63, "steel_galv")
    m.box(-2.7, -0.2, 2.45, -2.7 + 0.04, 5.2, 2.2, "steel_galv")


# ---- 自販機・看板類(ロードサイドの小物) ----
@mod("rs_vending_pair", W=2.0, H=1.9, cat="ロードサイド")
def _(m, W, H, rng):
    for i, (c, w) in enumerate((("vend_red", 0.8), ("vend_blue", 0.8))):
        x0 = -0.95 + i * 1.0
        m.box(x0, -0.35, 0.0, x0 + w, 0.35, 1.85, c)
        m.box(x0 + 0.05, 0.35, 0.7, x0 + w - 0.05, 0.36, 1.65, "vend_window")
        m.box(x0 + w - 0.2, 0.35, 0.35, x0 + w - 0.05, 0.36, 0.6, "alu_silver")
        m.box(x0 + 0.1, 0.35, 0.05, x0 + w - 0.1, 0.355, 0.25, "alu_black")


@mod("rs_ev_charger", W=0.6, H=1.7, cat="ロードサイド")
def _(m, W, H, rng):
    m.box(-0.2, -0.15, 0, 0.2, 0.15, 1.5, "paint_white")
    m.box(-0.15, 0.15, 1.0, 0.15, 0.17, 1.35, "sig_lens_dark")
    m.box(-0.2, -0.15, 1.5, 0.2, 0.15, 1.6, "sig_green")
    pipe(m, (0.2, 0.0, 0.9), (0.28, 0.15, 0.5), 0.02, "rubber", 6)


@mod("rs_cart_shelter", W=3.0, H=1.8, cat="ロードサイド")
def _(m, W, H, rng):
    """カートシェルター(屋根+カート収納の柵)"""
    for x in (-1.4, 1.4):
        m.box(x - 0.04, -0.4, 0, x + 0.04, -0.34, 1.9, "steel_galv")
        m.box(x - 0.04, 0.34, 0, x + 0.04, 0.4, 1.9, "steel_galv")
    m.box(-1.6, -0.5, 1.9, 1.6, 0.5, 1.96, "polycarbonate")
    for i in range(6):
        m.box(-1.3 + i * 0.5, -0.3, 0.2, -1.3 + i * 0.5 + 0.4, 0.3, 0.9, "steel_galv")


@mod("rs_billboard_field", W=6.0, H=5.2, cat="ロードサイド")
def _(m, W, H, rng):
    """野立て看板(店舗アトラス)+単柱"""
    m.box(-0.2, -0.2, 0, 0.2, 0.2, 3.6, "steel_gray")
    m.box(-3.0, -0.12, 2.3, 3.0, 0.12, 5.2, "alu_black")
    sign_panel(m, "home_a", -2.9, 2.9, 2.4, 5.1, 0.125)
    sign_panel(m, "super_b", -2.9, 2.9, 2.4, 5.1, -0.125, flip=True)
