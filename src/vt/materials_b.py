"""リアリズム強化(B)で追加するマテリアル。materials.py の末尾から import され、MATERIALS に追記/上書きする。"""
from .materials import MATERIALS

M = lambda color, rough=0.7, metal=0.0, **kw: dict(color=color, rough=rough, metal=metal, **kw)


def T(png, size, rough=0.85, bump=0.0, **kw):
    return dict(color="#808080", rough=rough, metal=0.0, tex=png, size=size, bump=bump, **kw)


# ---- 車: 塗装は色ごとの画像(下端の泥跳ね+雨だれ)。粗さ・金属感はここで指定 ----
_PAINT = dict(white=(0.16, 0.2), black=(0.14, 0.3), silver=(0.2, 0.5), gray=(0.2, 0.4), red=(0.16, 0.3), blue=(0.16, 0.3), beige=(0.18, 0.3), green=(0.18, 0.3), taxi=(0.14, 0.3),
              pearl=(0.14, 0.25), navy=(0.15, 0.3), wine=(0.15, 0.3), sky=(0.18, 0.3), yellow=(0.2, 0.2), bus=(0.25, 0.2))
for _k, (_r, _m) in _PAINT.items():
    MATERIALS["car_paint_" + _k] = dict(color="#808080", rough=_r, metal=_m, tex=f"carpaint_{_k}.png", size=(5.0, 8.0), bump=0.0)
MATERIALS.update({
    "car_plate_atlas": dict(color="#ffffff", rough=0.4, metal=0.0, tex="plate_atlas.png", size=None, alpha=False),
    "car_trim": M("#202224", 0.6, 0.1), "car_chrome": M("#c8ccd0", 0.12, 1.0), "car_tread": M("#0c0c0c", 0.95, 0.0), "car_wiper": M("#101010", 0.6),
    "car_rubber_seal": M("#141414", 0.9), "car_brake_disc": M("#6a6460", 0.5, 0.9, rust=1), "car_cargo": M("#d8dad6", 0.5, 0.2, dirt=1),
    "car_dump_yellow": M("#e0a820", 0.5, 0.3, dirt=1, rust=1), "car_tarp_blue": M("#2a5a9a", 0.9),
    "bike_frame_silver": M("#b8bcc0", 0.3, 0.9), "bike_frame_black": M("#1a1a1c", 0.4, 0.8), "bike_frame_blue": M("#2a5a9a", 0.35, 0.7),
    "bike_frame_red": M("#a02a2a", 0.35, 0.7), "bike_frame_white": M("#e0e0dc", 0.35, 0.6), "bike_rust": M("#6a4a38", 0.85, 0.6, rust=1),
    "bike_seat": M("#1c1c1c", 0.6), "bike_basket": M("#9a9ea0", 0.4, 0.9, dirt=1),
})

# ---- 人: 服地テクスチャ・小物 ----
for _n in ("denim", "denim_dark", "stripe_navy", "pin_gray", "plaid_red", "plaid_green", "knit_beige", "knit_navy", "floral", "plain_pink", "plain_olive", "plain_mustard"):
    MATERIALS["ped_tex_" + _n] = T(f"cloth_{_n}.png", 0.28 if "denim" in _n or "plain" in _n else 0.36, 0.92)
MATERIALS.update({
    "ped_cloth_suit": M("#23262c", 0.8), "ped_cloth_yellow": M("#d8b838", 0.9), "ped_cloth_sky": M("#8fb0cc", 0.9), "ped_cloth_brown": M("#5a4030", 0.9),
    "ped_cloth_pink": M("#d890a8", 0.9), "ped_cloth_orange": M("#d86a28", 0.9), "ped_cloth_purple": M("#6a4a8a", 0.9),
    "ped_hair_gray": M("#a8a8a4", 0.8), "ped_hair_brown": M("#5a3a28", 0.8), "ped_hair_blonde": M("#b09050", 0.8), "ped_hair_black": M("#141010", 0.75),
    "ped_shoe_white": M("#e8e8e4", 0.6), "ped_shoe_brown": M("#4a3020", 0.6), "ped_sock": M("#e0e0dc", 0.9),
    "bag_leather": M("#3a2a20", 0.5), "bag_nylon": M("#1a1c20", 0.85), "bag_tote": M("#d8c8a8", 0.9), "bag_red": M("#a82a2a", 0.8), "bag_conv": M("#3a8a4a", 0.7),
    "bag_clear_plastic": M("#d8e0dc", 0.4), "randoseru_red": M("#a82030", 0.45), "randoseru_black": M("#17171a", 0.45), "randoseru_blue": M("#1c3a7a", 0.45),
    "umb_black": M("#16171a", 0.6), "umb_navy": M("#1c2a50", 0.6), "umb_red": M("#a82a2a", 0.6), "umb_beige": M("#c8b898", 0.6), "umb_green": M("#2f6a48", 0.6),
    "umb_clear": M("#e4ecee", 0.08, glass=1), "umb_rib": M("#3a3c3e", 0.4, 0.8), "hat_cap": M("#2a3a5a", 0.85), "hat_straw": M("#c8b078", 0.9),
    "glasses_dark": M("#101214", 0.2), "phone_screen": M("#a8d0f0", 0.1, emit=("#a8d0f0", 1.5)),
})

# ---- 路面オーバーレイ(デカール) ----
for _n, _r in (("leaf_litter_1", 0.8), ("leaf_litter_2", 0.8), ("puddle", 0.03), ("oil", 0.25), ("tire_marks", 0.7), ("trench", 0.8),
               ("cover_round_sewer", 0.5), ("cover_square_water", 0.5), ("cover_round_water", 0.5), ("cover_gas", 0.5), ("cover_hand", 0.5)):
    MATERIALS["decal_overlay_" + _n] = dict(color="#ffffff", rough=_r, metal=0.0, tex=f"overlay_{_n}.png", size=None, alpha=True, wear=None)
MATERIALS.update({"curb_chip": M("#6a6a66", 0.95, bump=0.8), "curb_chip_dark": M("#2a2a28", 0.95), "crack_dark": M("#1a1a1a", 0.9), "gutter_leaf": M("#6a5030", 0.9)})

# ---- 街の生活感 ----
MATERIALS.update({
    "vending_atlas": dict(color="#ffffff", rough=0.22, metal=0.0, tex="vending_atlas.png", size=None, alpha=False),
    "vending_body_white": M("#e4e4e0", 0.35, 0.3, dirt=1), "vending_body_gray": M("#8a8e92", 0.35, 0.4, dirt=1), "vending_body_red": M("#b02a24", 0.3, 0.3, dirt=1),
    "vending_body_blue": M("#2a4a8a", 0.3, 0.3, dirt=1), "vending_body_black": M("#1c1d20", 0.3, 0.4, dirt=1),
    "vending_glow": M("#f4f4ee", 0.3, emit=("#fff4e0", 0.6)),
    "nobori_atlas": dict(color="#ffffff", rough=0.85, metal=0.0, tex="nobori_atlas.png", size=None, alpha=False),
    "lantern_atlas": dict(color="#ffffff", rough=0.7, metal=0.0, tex="lantern_atlas.png", size=None, alpha=False),
    "lantern_glow": M("#ffd890", 0.5, emit=("#ffb860", 0.8)),
    "ac_body": M("#dcddd8", 0.5, 0.1, dirt=1), "ac_grille": M("#3a3c3e", 0.5, 0.6), "ac_pipe": M("#c8c4b8", 0.7), "ac_insul": M("#d8d4c0", 0.9),
    "garbage_bag": M("#e0e4e0", 0.35), "garbage_bag_yellow": M("#d8c030", 0.35), "garbage_bag_green": M("#4a8a50", 0.35), "garbage_bag_blue": M("#3a6aa8", 0.35),
    "net_blue": M("#2a5a9a", 0.85, bump=0.4), "net_yellow": M("#d8b820", 0.85), "wire_cage": M("#8a8e90", 0.5, 0.8, dirt=1, rust=1),
    "scaffold_steel": M("#b4b8ba", 0.4, 0.9, dirt=1), "scaffold_plank": M("#a0a49c", 0.5, 0.8, dirt=1), "scaffold_clamp": M("#8a8c88", 0.5, 0.9, rust=1),
    "sheet_white": M("#e4e6e2", 0.9, dirt=1), "sheet_gray": M("#9aa0a4", 0.9, dirt=1), "sheet_blue": M("#4a78a8", 0.9, dirt=1), "sheet_green": M("#4a7a58", 0.9, dirt=1),
    "hoard_white": M("#e0e2de", 0.55, 0.3, dirt=1), "hoard_gray": M("#8a9298", 0.55, 0.3, dirt=1), "hoard_green": M("#4a7a58", 0.55, 0.3, dirt=1),
    "barricade_red": M("#d82a20", 0.5), "barricade_white": M("#f0f0ec", 0.5), "roadwork_yellow": M("#f0c820", 0.5), "roadwork_black": M("#1a1a1a", 0.6),
    "pot_terracotta": M("#a0583a", 0.85, bump=0.5), "pot_plastic": M("#e0ddd4", 0.5), "pot_dark": M("#3a3a3a", 0.6), "soil_dark": M("#3a2e22", 0.95, bump=0.4),
    "plant_green": M("#3c6a34", 0.8, vary=["#3c6a34", "#4a7a3a", "#2e5a30", "#6a8a3a"]), "flower_pink": M("#d86a90", 0.7), "flower_red": M("#c02a30", 0.7),
    "flower_yellow": M("#e8c020", 0.7), "flower_white": M("#f0f0ea", 0.7), "flower_purple": M("#7a4a9a", 0.7), "styrofoam": M("#ecece8", 0.9, bump=0.3, dirt=1),
    "mailbox_red": M("#b8281e", 0.45, 0.4, dirt=1), "mailbox_steel": M("#9a9ea0", 0.4, 0.8, dirt=1), "mailbox_brown": M("#5a4030", 0.5, 0.3, dirt=1),
    "pipe_gray": M("#868a8c", 0.45, 0.2, dirt=1), "pipe_brown": M("#5a4838", 0.45, 0.2, dirt=1), "pipe_white": M("#dcdcd6", 0.45, 0.2, dirt=1),
    "fire_red": M("#c8201c", 0.4, 0.4, dirt=1), "sign_yellow": M("#f0c820", 0.4, 0.2, dirt=1), "sign_white": M("#e8e8e4", 0.4, 0.2, dirt=1),
    "pole_band_yellow": M("#e8c020", 0.5), "pole_band_black": M("#1a1a1a", 0.6), "pole_plate": M("#e8e4d8", 0.5, 0.2),
    "stand_sign_black": M("#1c1c1e", 0.7, 0.2, dirt=1), "tarp_blue": M("#2a5a9a", 0.9, dirt=1), "rope_white": M("#d8d4c4", 0.9),
})
