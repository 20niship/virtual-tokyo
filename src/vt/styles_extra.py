"""田舎・郊外・ロードサイド・工場の建物様式(assemble.STYLES へ追加)。区画生成(district.py)が `_style` タグで選ぶ。既存の東京中心の様式は変更しない。"""
from .assemble import STYLES, _x

ROOFS_JP = dict(kinds=["irimoya", "hip", "gable", "hip"], mats=["kawara", "kawara", "kawara_hon", "kawara_brown"])
ROOFS_MAKER = dict(kinds=["gable", "hip", "katanagare", "gable"], mats=["slate_dark", "slate_brown", "cement_blue", "tanshiki_gray", "cement_red"])
ROOFS_APT = dict(kinds=["gable", "katanagare", "hip"], mats=["tanshiki_green", "tanshiki_blue", "tanshiki_gray", "slate_dark"])
ROOFS_FACTORY = dict(kinds=["gable", "gable", "katanagare"], mats=["tanshiki_gray", "tanshiki_blue", "tanshiki_green", "tanshiki_red"])

STYLES["house_jp_kawara"] = dict(gf=["win_jp_amado", "win_jp_koshi", "wall_shitamiita", "win_jp_engawa"], door="win_jp_genkan", f2=["win_jp_koshi", "win_jp_amado"], f2_n=1,
                                 mid=["win_jp_koshi", "win_jp_amado", "wall_mortar_jp"], alt=["wall_mortar_jp"], gf_h=3.0, wall="wall_shitamiita", band=False, corner="corner_post_wood", span=3.0,
                                 pitched=True, roofs=ROOFS_JP, k=(3, 4),
                                 extras=[_x("ac_rack_wall_2", 0.05, "mid", (0, 0, 1.0)), _x("satellite_dish_wall", 0.12, "mid", (1.0, 0, 1.6)), _x("chimney_bath", 0.1, "gf", (1.3, 0.3, 0)), _x("mailbox_post", 0.12, "gf", (1.6, 1.2, 0))],
                                 roof={})
STYLES["house_jp_mortar"] = dict(gf=["win_jp_koshi", "win_jp_amado", "wall_mortar_jp", "win_jp_engawa"], door="win_jp_genkan", mid=["win_jp_amado", "win_jp_koshi", "wall_mortar_jp"], alt=["wall_mortar_jp"],
                                 gf_h=3.0, wall="wall_mortar_jp", band=False, corner="corner_post_wood", span=3.0, pitched=True, roofs=dict(kinds=["gable", "hip"], mats=["cement_red", "cement_blue", "slate_dark", "kawara_brown"]), k=(3, 4),
                                 extras=[_x("ac_rack_wall_2", 0.08, "mid", (0, 0, 1.0)), _x("satellite_dish_wall", 0.1, "mid", (1.0, 0, 1.6))], roof={})
STYLES["house_kominka"] = dict(gf=["win_jp_engawa", "win_jp_amado", "wall_shitamiita_light", "win_jp_koshi"], door="win_jp_genkan", mid=["win_jp_koshi", "wall_shitamiita_light"], alt=["wall_namako"],
                               gf_h=3.4, wall="wall_shitamiita_light", band=False, corner="corner_post_wood", span=3.6, pitched=True, roofs=dict(kinds=["irimoya", "irimoya", "hip"], mats=["kawara_hon", "kawara", "kawara_hon"]),
                               extras=[_x("stone_lantern", 0.1, "gf", (1.5, 1.5, 0)), _x("chimney_bath", 0.08, "gf", (1.3, 0.3, 0))], roof={})
STYLES["house_maker_a"] = dict(gf=["win_maker_shutter", "win_maker_pair", "win_maker_fix"], door="door_maker_entry", f2=["win_maker_shutter", "win_maker_pair"], f2_n=1, mid=["win_maker_shutter", "win_maker_pair", "win_maker_fix"],
                               alt=["balcony_alu"], gf_h=3.0, wall="wall_siding_cream", band=False, corner="corner_post_siding", span=3.2, pitched=True, roofs=ROOFS_MAKER, k=(3, 4),
                               extras=[_x("house_garage_shutter", 0.1, "gf"), _x("ac_rack_wall_2", 0.07, "mid", (0, 0, 1.0)), _x("satellite_dish_wall", 0.12, "mid", (1.0, 0, 1.6)), _x("mailbox_post", 0.1, "gf", (1.6, 1.2, 0))], roof={})
STYLES["house_maker_b"] = dict(STYLES["house_maker_a"], mid=["win_maker_pair", "win_maker_fix"], gf=["win_maker_fix", "win_maker_pair", "win_maker_shutter"], wall="wall_siding_gray", roofs=dict(kinds=["katanagare", "gable", "katanagare"], mats=["tanshiki_gray", "tanshiki_blue", "slate_dark"]))
STYLES["house_maker_brick"] = dict(STYLES["house_maker_a"], wall="wall_siding_brick", gf=["win_maker_shutter", "win_maker_fix"], roofs=dict(kinds=["hip", "gable"], mats=["cement_red", "kawara_brown", "slate_brown"]))
STYLES["apt_wood2"] = dict(gf=["win_maker_pair", "win_maker_shutter", "apt_door_row"], door="door_maker_entry", f2=["apt_door_row", "apt_balcony_laundry"], f2_n=1, mid=["apt_door_row", "apt_balcony_laundry", "win_maker_pair"], alt=["apt_balcony_laundry"],
                           gf_h=3.0, wall="wall_siding_gray", band=False, corner="corner_post_siding", span=3.0, pitched=True, roofs=ROOFS_APT, special=["apt_stair_side"], k=(2, 3),
                           extras=[_x("ac_rack_wall_2", 0.08, "mid", (0, 0, 1.0)), _x("duct_vertical_pipes", 0.08, "gf", (1.3, 0, 0))], roof={})
STYLES["barn_tin"] = dict(gf=["wall_tin_house"], door="fac_door_steel", mid=["wall_tin_house"], gf_h=3.4, wall="wall_tin_house", band=False, corner="corner_post_wood", span=3.6, pitched=True,
                          roofs=dict(kinds=["gable", "katanagare"], mats=["tanshiki_red", "tanshiki_green", "tanshiki_gray"]), roof={})


def _rs(name, key, gf, wall="wall_alc", gf_h=4.2, extra=(), roof=None, pitched=False, roofs=None):
    ex = [_x(f"rs_fascia_{key}", 0.55, "gf", (0, 0, gf_h - 0.9))] + list(extra)
    STYLES[f"rs_{name}"] = dict(gf=gf, door=gf[-1], mid=[wall], alt=[], gf_h=gf_h, wall=wall, band=False, corner="corner_post", span=3.6, extras=ex,
                                roof=roof or {"ac_unit_vrf": 2, "roof_vent_pipes": 1, "roof_billboard": 0.2, "ac_unit_small": 2}, **({"pitched": True, "roofs": roofs} if pitched else {}))


GLASS = ["rs_glass_front", "rs_glass_door_auto"]
for _k in ("conv_a", "conv_b", "conv_c"):
    _rs(_k, _k, GLASS, "wall_siding_gray", 3.8, [_x("rs_vending_pair", 0.04, "gf", (1.2, 1.4, 0))])
for _k in ("drug_a", "drug_b"):
    _rs(_k, _k, ["rs_drug_wall", "rs_glass_door_auto"], "wall_alc", 4.4)
for _k in ("family_a", "family_b"):
    _rs(_k, _k, ["rs_family_wall", "rs_glass_front"], "wall_siding_brick", 4.4)
for _k in ("super_a", "super_b", "home_a", "home_b"):
    _rs(_k, _k, ["rs_boxstore_wall", "rs_glass_door_auto"], "rs_boxstore_wall", 7.0, [_x("rs_cart_shelter", 0.04, "gf", (1.2, 1.6, 0))])
for _k in ("pachi_a", "pachi_b"):
    _rs(_k, _k, ["rs_pachi_wall"], "rs_pachi_wall", 7.0)
for _k in ("car_a", "car_b"):
    _rs(_k, _k, ["rs_showroom_glass"], "wall_alc", 4.8)
for _k in ("ramen_a", "ramen_b", "udon", "izaka", "sushi", "bake"):
    _rs(_k, _k, ["rs_ramen_wall", "rs_glass_front"], "wall_siding_gray", 3.8)
for _k in ("shop100_a", "shop100_b", "karaoke", "bank", "cl_a", "cl_b", "shoe", "bk", "rent", "hosp", "dental", "wash", "gym", "nursery", "tire", "used", "agri"):
    _rs(_k, _k, GLASS, "wall_siding_cream", 4.2)
STYLES["rs_gs"] = dict(gf=["gs_office_front"], door="gs_office_front", mid=["wall_alc"], gf_h=4.0, wall="wall_alc", band=False, corner="corner_post", span=4.0, extras=[_x("rs_fascia_gs_a", 0.0, "gf", (0, 0, 3.0))], roof={"ac_unit_small": 2})
RS_KEYS = [k[3:] for k in STYLES if k.startswith("rs_") and k != "rs_gs"]

for _c, _w in (("gray", "fac_wall_corr_gray"), ("blue", "fac_wall_corr_blue"), ("green", "fac_wall_corr_green"), ("cream", "fac_wall_corr_cream")):
    STYLES[f"factory_tin_{_c}"] = dict(gf=[_w, "fac_window_band", "fac_shutter_big"], door="fac_door_steel", mid=[_w, "fac_window_band"], gf_h=5.2, wall=_w, band=False, corner="corner_post", span=3.6,
                                       extras=[_x("fac_sign_a", 0.06, "gf", (0, 0, 3.4)), _x("fac_sign_b", 0.06, "gf", (0, 0, 3.4)), _x("fac_sign_c", 0.06, "gf", (0, 0, 3.4)), _x("duct_vertical_pipes", 0.05, "gf", (1.3, 0, 0))],
                                       special=["sp_fac_chimney_brick" if _c in ("gray", "cream") else "sp_fac_chimney_steel"], pitched=True, roofs=ROOFS_FACTORY, roof={})
STYLES["logistics"] = dict(gf=["fac_wall_panel_cream", "fac_shutter_big", "fac_wall_panel_cream"], door="fac_door_steel", mid=["fac_wall_panel_cream"], top=["fac_wall_panel_cream"], gf_h=7.0, wall="fac_wall_panel_cream", band=False, corner="corner_post", span=5.0,
                           extras=[_x("log_dock_leveler", 0.12, "gf"), _x("fac_sign_d", 0.06, "gf", (0, 0, 4.8)), _x("pallet_stack", 0.08, "gf", (1.2, 1.4, 0)), _x("ac_group_ground", 0.03, "gf", (2.0, 1.0, 0))],
                           roof={"solar_row": 6, "wh_roof_monitor": 1, "roof_vent_pipes": 2, "fac_vent_turbine": 2, "exhaust_stack_group": 1})
