"""植栽モジュール(cat="植栽"): 街路樹・公園樹・クロマツ・ヤシ・枝垂れ柳・低木・生垣・花壇/地被・壁面緑化・ツリーサークル。
原点=根元(生垣は中心、壁面緑化は壁面y=0・床z=0)。樹種×サイズ×seed×季節で多数のバリエーションを登録(生成は初回アクセス時)。"""
from .. import tree_gen as tg
from .registry import reg

SIZES = {"s": 5.0, "m": 9.0, "l": 14.0}
BIG = {"kusunoki": 1.25, "shii": 1.0, "platanus": 1.15, "keyaki": 1.1, "sakura": 0.85, "hanamizuki": 0.55, "tokaikaede": 0.7, "ichou": 1.0}
CAT = "植栽"


def _tree(name, H, seed, season):
    def fn(m, W, Ht, rng):
        mesh, _ = tg.build_tree(name, H, seed, season)
        m.add(mesh)
    return fn


def _wrap(builder, *a, **k):
    def fn(m, W, H, rng):
        mesh, _ = builder(*a, **k)
        m.add(mesh)
    return fn


for _sp, _spec in tg.SPECIES.items():
    for _sz, _h in SIZES.items():
        H = round(_h * BIG[_sp], 1)
        for _seed in (0, 1):
            seasons = _spec.seasons if _seed == 0 else (_spec.seasons[0],)
            for _se in seasons:
                reg(f"veg_{_sp}_{_sz}_{_seed}_{_se}", _tree(_sp, H, _seed, _se), W=_spec.crown_w * H * 2.1, H=H + 1.0, cat=CAT)

for _sz, _h in {"s": 5.0, "m": 8.0, "l": 12.0}.items():
    for _seed in (0, 1):
        reg(f"veg_kuromatsu_{_sz}_{_seed}_summer", _wrap(tg.build_pine, _h, _seed), W=_h * 0.9, H=_h + 1, cat=CAT)
        reg(f"veg_yanagi_{_sz}_{_seed}_summer", _wrap(tg.build_willow, _h * 1.1, _seed), W=_h * 1.2, H=_h * 1.1 + 1, cat=CAT)
for _sz, _h in {"s": 5.0, "m": 8.0, "l": 12.0}.items():
    for _seed in (0, 1):
        reg(f"veg_yashi_canary_{_sz}_{_seed}_summer", _wrap(tg.build_palm, "canary", _h, _seed), W=_h * 0.8 + 3, H=_h + 2, cat=CAT)
for _sz, _h in {"s": 7.0, "m": 11.0, "l": 15.0}.items():
    reg(f"veg_yashi_washingtonia_{_sz}_0_summer", _wrap(tg.build_palm, "washingtonia", _h, 0), W=_h * 0.5 + 3, H=_h + 2, cat=CAT)
for _sz, _h in {"s": 2.5, "m": 4.0, "l": 6.0}.items():
    reg(f"veg_shuro_{_sz}_0_summer", _wrap(tg.build_palm, "shuro", _h, 1), W=3.5, H=_h + 2, cat=CAT)

# 低木
for _i in range(3):
    for _r in (0.5, 0.8, 1.1):
        reg(f"veg_azalea_{_i}_r{int(_r * 10)}", _wrap(tg.build_dome_shrub, "azalea", _r, _i, _i, 70), W=_r * 2, H=_r * 0.8, cat=CAT)
for _r in (0.5, 0.8):
    reg(f"veg_azalea_green_r{int(_r * 10)}", _wrap(tg.build_dome_shrub, "azalea", _r, 5, -1, 60), W=_r * 2, H=_r * 0.8, cat=CAT)
    reg(f"veg_tsuge_dome_r{int(_r * 10)}", _wrap(tg.build_dome_shrub, "tsuge", _r, 2, 0, 60), W=_r * 2, H=_r * 0.7, cat=CAT)
for _i in range(2):
    for _r in (0.5, 0.75):
        reg(f"veg_hydrangea_{_i}_r{int(_r * 100)}", _wrap(tg.build_dome_shrub, "hydrangea", _r, _i, _i, 50), W=_r * 2, H=_r * 0.9, cat=CAT)
# 生垣(連結用のスパン)
for _nm, (_L, _W, _H) in {"low": (2.0, 0.5, 0.6), "mid": (2.0, 0.6, 1.2), "tall": (2.0, 0.8, 1.8), "short": (1.0, 0.6, 1.2)}.items():
    for _seed in (0, 1):
        reg(f"veg_hedge_{_nm}_{_seed}", _wrap(tg.build_hedge, _L, _W, _H, _seed), W=_L, H=_H, cat=CAT)
# 花壇・地被・草
for _i in range(3):
    reg(f"veg_flowerbed_{_i}", _wrap(tg.build_flowerbed, 2.0, 1.0, _i, "flowerbed"), W=2.0, H=0.5, cat=CAT)
reg("veg_groundcover_ivy", _wrap(tg.build_flowerbed, 2.0, 1.0, 5, "ivy_wall"), W=2.0, H=0.4, cat=CAT)
for _i in range(2):
    reg(f"veg_grass_tuft_{_i}", _wrap(tg.build_grass, "tuft", 0.6, _i), W=1.2, H=1.1, cat=CAT)
    reg(f"veg_grass_plume_{_i}", _wrap(tg.build_grass, "plume", 0.7, _i), W=1.4, H=1.6, cat=CAT)
# 壁面緑化
for _nm, (_W, _H) in {"2x2": (2.0, 2.0), "2x3": (2.0, 3.0), "1x2": (1.0, 2.0)}.items():
    reg(f"veg_ivy_wall_{_nm}", _wrap(tg.build_ivy_wall, _W, _H, 0), W=_W, H=_H, cat=CAT)


def _tree_pit(m, W, H, rng):          # ツリーグレーチング(1.2m角・中央に円形開口)+縁枠
    m.box(-0.6, -0.6, 0, 0.6, -0.22, 0.035, "tree_pit_iron")
    m.box(-0.6, 0.22, 0, 0.6, 0.6, 0.035, "tree_pit_iron")
    m.box(-0.6, -0.22, 0, -0.22, 0.22, 0.035, "tree_pit_iron")
    m.box(0.22, -0.22, 0, 0.6, 0.22, 0.035, "tree_pit_iron")
    for i in range(-5, 6):
        for sgn in (-1, 1):
            m.box(i * 0.1 - 0.008, sgn * 0.3 - 0.04, 0.034, i * 0.1 + 0.008, sgn * 0.3 + 0.04, 0.037, "sig_lens_dark")


def _tree_ring(m, W, H, rng):         # 縁石の丸い植樹桝(土入り)
    m.tube(0, 0, 0, 0.7, 0.58, 0.18, "z", "rc_concrete", 24)
    m.cyl(0, 0, 0.02, 0.58, 0.05, "z", "soil", 20)


reg("veg_tree_pit_grating", _tree_pit, W=1.2, H=0.05, cat=CAT)
reg("veg_tree_ring_curb", _tree_ring, W=1.4, H=0.2, cat=CAT)
