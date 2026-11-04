"""マテリアル表。color=基本色, vary=建物ごとの色相バリエーション(bvar 0..1で補間)。"""
M = lambda color, rough=0.7, metal=0.0, **kw: dict(color=color, rough=rough, metal=metal, **kw)
MATERIALS = {
    "rc_concrete": M("#9a9a96", 0.88, bump=0.6, dirt=1),
    "rc_hole": M("#3a3a38", 0.9),
    "paint_main": M("#d8d2c4", 0.72, vary=["#e6e2d6", "#d9cfb8", "#c9ccd0", "#b8c2c8", "#d3b8a0", "#cdd6bf", "#a9a9a6"], bump=0.2, dirt=1),
    "paint_dark": M("#5b5d60", 0.7, dirt=1),
    "paint_white": M("#e4e2dc", 0.7, dirt=1),
    "spray_main": M("#cfc8b8", 0.92, vary=["#e0dccf", "#cbbfa6", "#bcb9b0", "#c8a98d", "#aab4b6"], bump=1.2, dirt=1),
    "alc": M("#dcdad4", 0.8, bump=0.3, dirt=1, joint=dict(w=0.6, h=2.0, offset=0.0, mortar=0.004, mortar_col="#aaa8a2", var=0.04, depth=0.003)),
    "tile_main": M("#8d6a52", 0.32, vary=["#8d6a52", "#a0907c", "#b8b2a5", "#6e6a66", "#c4b79c", "#7a5a48"], bump=0.1, dirt=1, joint=dict(w=0.227, h=0.06, mortar=0.005, mortar_col="#85817a", var=0.12)),
    "grout": M("#7d7a74", 0.95),
    "mortar": M("#a8a39a", 0.95),
    "brick_main": M("#9a4b38", 0.82, vary=["#a24d38", "#8a4030", "#6b3a30", "#b5654a", "#7d7468"], bump=0.5, dirt=1, joint=dict(w=0.21, h=0.065, mortar=0.010, mortar_col="#b9b3a6", var=0.2, depth=0.006)),
    "stone_main": M("#8a8985", 0.35, vary=["#8a8985", "#a8a49c", "#5e5e60", "#b9a58c", "#d8d6d0"], bump=0.15, dirt=1, joint=dict(w=0.6, h=0.3, mortar=0.012, mortar_col="#6d6b66", var=0.1, depth=0.005)),
    "quartz": M("#cfcac2", 0.2, bump=0.05),
    "marble": M("#e8e6e0", 0.12),
    "glass_main": M("#1a2a30", 0.03, 0.0, glass=1, vary=["#1d3338", "#26373f", "#2d3033", "#1a2a40", "#2a4038"]),
    "glass_clear": M("#222a2c", 0.02, 0.0, glass=1),
    "interior": M("#2a2622", 0.9, interior=1),
    "core": M("#2b2b2b", 0.95),
    "alu_main": M("#b5b8ba", 0.35, 1.0, vary=["#b5b8ba", "#3a3b3d", "#6b5a48", "#c9cacb", "#8a8c8e"], dirt=1),
    "alu_silver": M("#c0c3c5", 0.32, 1.0),
    "alu_black": M("#2a2b2d", 0.4, 0.9),
    "steel_gray": M("#7b7e80", 0.5, 0.7, dirt=1, rust=1),
    "steel_white": M("#d8d9d6", 0.45, 0.6, dirt=1, rust=1),
    "steel_green": M("#3d5e4a", 0.5, 0.6, dirt=1, rust=1),
    "steel_galv": M("#a2a6a8", 0.42, 0.9, dirt=1),
    "metal_siding": M("#aeb4b6", 0.4, 0.8, vary=["#aeb4b6", "#c9ccc8", "#8d9ba4", "#a8b8a0"], dirt=1, rust=1),
    "wood": M("#8a5e3a", 0.6, wood=1, vary=["#8a5e3a", "#a77a52", "#5e3f28"]),
    "roof_membrane": M("#8b8f90", 0.8, bump=0.4, dirt=1),
    "roof_metal": M("#9aa2a6", 0.4, 0.8, dirt=1),
    "rubber": M("#1d1d1e", 0.9),
    "plastic_gray": M("#b0b2b3", 0.5),
    "ac_white": M("#e2e3e0", 0.5, dirt=1),
    "solar": M("#10182a", 0.15, 0.4),
    "sign_green": M("#1ca860", 0.5, emit=("#2fe080", 3.0)),
    "led_white": M("#ffffff", 0.5, emit=("#fff2d8", 6.0)),
    "fabric": M("#b04a3a", 0.95, vary=["#b04a3a", "#2a4a7a", "#3a6a4a", "#d8d2c4", "#222222"]),
    "water": M("#1c3a48", 0.04, 0.0, water=1),
}

# ---- テクスチャ付き(assets/textures)。size=1タイルのメートル寸法(None=UV 0..1)、alpha=画像のアルファを使う、wear=かすれマスクを乗せる ----
def T(png, size, rough=0.85, bump=0.0, **kw):
    return dict(color="#808080", rough=rough, metal=0.0, tex=png, size=size, bump=bump, **kw)


MATERIALS.update({
    "ground": T("plaza.png", 4.0, 0.9, 0.3),
    "sidewalk": T("sidewalk_paver.png", 2.4, 0.88, 0.4),
    "asphalt": T("asphalt.png", 5.0, 0.92, 0.8),
    "asphalt_worn": T("asphalt_worn.png", 5.0, 0.9, 0.8),
    "sidewalk_paver": T("sidewalk_paver.png", 2.4, 0.88, 0.4),
    "sidewalk_tile": T("sidewalk_tile.png", 2.4, 0.85, 0.3),
    "sidewalk_asphalt": T("sidewalk_asphalt.png", 3.0, 0.9, 0.5),
    "sidewalk_granite": T("sidewalk_granite.png", 2.4, 0.4, 0.2),
    "concrete_tex": T("concrete.png", 4.0, 0.85, 0.5),
    "concrete_formed": T("concrete_formed.png", 3.6, 0.85, 0.5),
    "riprap": T("riprap_stone.png", 4.0, 0.9, 1.0),
    "ballast": T("track_bed.png", (2.4, 3.2), 0.95, 1.0),
    "grass": T("grass.png", 3.0, 0.95, 0.8),
    "soil": T("soil.png", 3.0, 0.95, 0.6),
    "gravel": T("gravel.png", 3.0, 0.95, 1.0),
    "rail_steel": M("#6a5a4c", 0.45, 0.9, rust=1),
    # 塗料: 色+かすれマスク(paint_wear.png)をアルファに
    "paint_road_blue": dict(color="#2f6fb5", rough=0.65, metal=0.0, wear="paint_wear.png", wear_size=2.5),
    "tbs_line_tiled": T("tbs_line.png", 0.3, 0.7, 0.8),
    "tbs_dot_tiled": T("tbs_dot.png", 0.3, 0.7, 0.8),
    "paint_road_white": dict(color="#eeeee6", rough=0.6, metal=0.0, wear="paint_wear.png", wear_size=2.5),
    "paint_road_yellow": dict(color="#e2b400", rough=0.6, metal=0.0, wear="paint_wear.png", wear_size=2.5),
})
for _n in ("arrow_straight", "arrow_left", "arrow_right", "arrow_straight_left", "arrow_straight_right", "text_tomare", "text_bus", "text_jokou",
           "speed_30", "speed_40", "speed_50", "speed_60", "diamond", "triangle", "bike_symbol", "bikelane_blue", "tbs_line", "tbs_dot", "manhole"):
    MATERIALS["decal_" + _n] = dict(color="#ffffff", rough=0.6 if _n not in ("tbs_line", "tbs_dot") else 0.7, metal=0.0, tex=_n + ".png", size=None, alpha=True,
                                    wear="paint_wear.png" if not _n.startswith(("tbs", "manhole", "bikelane")) else None, wear_size=2.5)

# ---- 道路ファニチャ ----
MATERIALS.update({
    "sig_red": M("#ff2a1a", 0.3, emit=("#ff2a1a", 25.0)),
    "sig_yellow": M("#ffb200", 0.3, emit=("#ffb200", 25.0)),
    "sig_green": M("#2dffa0", 0.3, emit=("#2dffa0", 25.0)),     # 日本の「青信号」は青緑
    "sig_lens_dark": M("#12181a", 0.12, 0.0),
    "sig_white_icon": M("#ffffff", 0.4, emit=("#ffffff", 14.0)),
    "sig_amber_digit": M("#ff9a00", 0.4, emit=("#ff9a00", 14.0)),
    "sig_housing_old": M("#4c5648", 0.55, 0.2, dirt=1),        # 旧式: くすんだ緑灰の鋳物/鋼板
    "sig_housing_led": M("#2d3234", 0.5, 0.1, dirt=1),
    "sig_housing_slim": M("#e6e8e6", 0.45, 0.1, dirt=1),       # 薄型: 白/淡灰
    "sig_housing_slim_black": M("#1d1f20", 0.45, 0.1),
    "sig_backplate": M("#17191a", 0.6, 0.0),
    "sig_reflect": M("#e8e4d0", 0.4, 0.0),
    "pole_dark": M("#3a3c3d", 0.5, 0.6, dirt=1, rust=1),
    "pole_white": M("#dcdedb", 0.45, 0.6, dirt=1, rust=1),
    "pole_brown": M("#4a3a30", 0.5, 0.5, dirt=1),
    "lamp_lens": M("#e8ece8", 0.1, 0.0),
    "lamp_globe": M("#f0f0ea", 0.25, 0.0),
    "sign_atlas": dict(color="#ffffff", rough=0.28, metal=0.0, tex="sign_atlas.png", size=None, alpha=True),
    "sign_back": M("#9ea3a5", 0.45, 0.8, dirt=1),
})

# ---- 建物ディテール追加(フェーズA2) ----
MATERIALS.update({
    "alu_bronze": M("#5a4636", 0.38, 0.95),
    "roof_tile": M("#4a4f55", 0.6, vary=["#4a4f55", "#6b4a3a", "#3c3f44", "#55504a", "#7a5a44"], bump=0.8, dirt=1),
    "glass_green": M("#1d3a34", 0.03, 0.0, glass=1),
    "ceramic": M("#c9c3b6", 0.25, 0.0, vary=["#c9c3b6", "#b0a89a", "#8a8d90", "#a56a50", "#d8d4c8"], dirt=1),
    "plant": M("#3f6b2e", 0.9, 0.0, vary=["#3f6b2e", "#4d7a35", "#2f5a28", "#6b8a3a"], bump=1.0),
    "sign_red": M("#d8231f", 0.4, emit=("#d8231f", 1.5)),
    "sign_blue": M("#1b4fa8", 0.4, emit=("#1b4fa8", 1.5)),
    "sign_white": M("#f2f0ea", 0.4, emit=("#f2f0ea", 2.5)),
    "sign_yellow": M("#f3c200", 0.4, emit=("#f3c200", 1.8)),
    "vend_red": M("#c8201c", 0.35, 0.2),
    "vend_blue": M("#1d4d9b", 0.35, 0.2),
    "vend_white": M("#e6e6e2", 0.35, 0.2),
    "vend_window": M("#f0f2ee", 0.3, emit=("#f0f2ee", 3.0)),
    "ground_slab": M("#8f8d88", 0.9, bump=0.6, dirt=1),
})

# ---- 植栽: 葉アトラス(alpha cutout・両面)・樹皮(手続きテクスチャ) ----
MATERIALS.update({
    "leaf_atlas": dict(color="#ffffff", rough=0.55, metal=0.0, tex="leaves_atlas.png", size=None, alpha=True, cutout=0.45, double_sided=True, foliage=True),
    "foliage_core": M("#1f3418", 0.95),
    "bark_furrow": T("bark_furrow.png", 1.0, 0.92, 1.0),
    "bark_furrow_dark": T("bark_furrow_dark.png", 1.0, 0.92, 1.0),
    "bark_smooth": T("bark_smooth.png", 0.8, 0.7, 0.4),
    "bark_plane": T("bark_plane.png", 1.2, 0.8, 0.6),
    "bark_pine": T("bark_pine.png", 0.9, 0.95, 1.0),
    "bark_palm": T("bark_palm.png", 0.7, 0.9, 0.7),
    "bark_shuro": T("bark_shuro.png", 0.6, 0.95, 0.5),
    "tree_pit_iron": M("#2d2f31", 0.6, 0.8, rust=1),
})

# ---- 路面の追加要素(右折レーン/バスレーン/道路鋲/劣化デカール/排水) ----
MATERIALS.update({
    "paint_road_bus": dict(color="#b0452e", rough=0.65, metal=0.0, wear="paint_wear.png", wear_size=2.5),
    "cats_eye_white": M("#e8e8e0", 0.25, 0.4, emit=("#ffffff", 0.6)),
    "cats_eye_yellow": M("#e2b400", 0.25, 0.4, emit=("#ffcc00", 0.6)),
    "asphalt_rut": T("asphalt_rut.png", (4.0, 0.7), 0.7, 0.0, alpha=True),
    "gutter": T("gutter.png", (1.0, 0.3), 0.85, 0.5),
})
for _n in ("asphalt_crack_1", "asphalt_crack_2", "asphalt_crack_3", "asphalt_patch_1", "asphalt_patch_2", "grating", "drain_inlet"):
    MATERIALS["decal_" + _n] = dict(color="#ffffff", rough=0.85 if "asphalt" in _n else 0.5, metal=0.0, tex=_n + ".png", size=None, alpha=True, wear=None)

# ---- 道路ファニチャ2(安全施設・電柱・街具・看板) ----
MATERIALS.update({
    "ad_atlas": dict(color="#ffffff", rough=0.35, metal=0.0, tex="ad_atlas.png", size=None, alpha=False),
    "mirror": M("#8aa4b8", 0.03, 1.0),
    "reflector_orange": M("#ff7a00", 0.3, emit=("#ff7a00", 0.6)),
    "reflector_white": M("#f4f4f0", 0.3, emit=("#ffffff", 0.4)),
    "guard_white": M("#e8eae6", 0.5, 0.5, dirt=1),
    "post_red": M("#c8201c", 0.35, 0.3, dirt=1),
    "cabinet_green": M("#4a6a55", 0.55, 0.3, dirt=1),
    "pole_concrete": M("#a9a9a4", 0.9, bump=0.5, dirt=1),
    "insulator": M("#d9d9d2", 0.2, 0.0),
    "wire": M("#17181a", 0.6, 0.2),
    "bench_wood": M("#8a6a44", 0.7, wood=1, vary=["#8a6a44", "#6b4f33", "#a98b62"]),
    "rubber_yellow": M("#f2c500", 0.8),
})

# ---- 最終フェーズ: 車両・人・汎用小物 ----
MATERIALS.update({
    "car_paint_white": M("#e8e8e4", 0.16, 0.55), "car_paint_black": M("#16171a", 0.14, 0.6), "car_paint_silver": M("#aeb2b6", 0.2, 0.8),
    "car_paint_gray": M("#5a5f64", 0.2, 0.7), "car_paint_red": M("#a3161c", 0.16, 0.6), "car_paint_blue": M("#1c3f7a", 0.16, 0.6),
    "car_paint_beige": M("#bba98a", 0.18, 0.6), "car_paint_green": M("#2f5a40", 0.18, 0.6), "car_paint_taxi": M("#1a1a1c", 0.14, 0.6),
    "car_paint_bus": M("#2f7d4a", 0.25, 0.4),
    "car_glass": M("#26394a", 0.03, 0.55),
    "car_under": M("#1c1d1f", 0.9, 0.0), "car_tire": M("#1a1a1a", 0.9, 0.0), "car_wheel": M("#b5b8ba", 0.3, 0.9),
    "car_headlight": M("#f4f4ee", 0.1, emit=("#fff8e0", 1.2)), "car_taillight": M("#a01010", 0.2, emit=("#ff2a1a", 0.8)),
    "car_plate": M("#eef0ee", 0.4, 0.0), "car_taxi_lamp": M("#f4d46a", 0.3, emit=("#ffe59a", 2.0)),
    "ped_skin": M("#c89a7a", 0.7, vary=["#e0b392", "#c89a7a", "#a87858", "#f0c8a8"]), "ped_hair": M("#1e1a18", 0.8, vary=["#1e1a18", "#3a2a20", "#7a6a58", "#c8c0b0"]),
    "ped_shoe": M("#222222", 0.8),
    "ped_cloth_navy": M("#1f2a44", 0.9), "ped_cloth_gray": M("#6a6d70", 0.9), "ped_cloth_red": M("#a8332f", 0.9), "ped_cloth_white": M("#d8d8d4", 0.9),
    "ped_cloth_green": M("#3f6a48", 0.9), "ped_cloth_beige": M("#b5a58a", 0.9), "ped_cloth_black": M("#1a1a1c", 0.9),
    "ctn_blue": M("#2a4f8a", 0.55, 0.4, dirt=1, rust=1), "ctn_red": M("#8a2a24", 0.55, 0.4, dirt=1, rust=1), "ctn_gray": M("#8a8e90", 0.55, 0.4, dirt=1, rust=1),
    "ctn_green": M("#3a6a48", 0.55, 0.4, dirt=1, rust=1), "ctn_orange": M("#c8661c", 0.55, 0.4, dirt=1, rust=1),
    "fence_sheet": M("#d9dcd8", 0.6, 0.2, dirt=1), "cone_orange": M("#ff5a00", 0.6), "boat_hull": M("#e6e8e8", 0.3, 0.2, dirt=1),
})
from . import materials_b  # noqa: E402,F401  (リアリズム強化B: 追記マテリアル)
from . import materials_h  # noqa: E402,F401  (Anny 人物: 肌・服・髪)
