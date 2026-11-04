"""建物フットプリント → モジュールインスタンス列(形状文法ルール)。
フロア帯(1階/2〜3階の基壇/中層/最上階) × ベイ列 × レシピ(STYLES) でモジュールを敷き、付属物(extras)・特殊部材(special)・屋根・屋上設備を足す。乱数は(OSM id, seed)固定で決定論的。"""
import math
import random
from dataclasses import dataclass, field

import bpy  # noqa: F401  (mathutilsを有効化)
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.polygon import orient

from .modules import library  # noqa: F401  (モジュール登録)
from .modules.geom import Mesh
from .modules.registry import REG


def WIN(kinds, cols=("bronze", "black", "white"), walls=("spray", "alc", "tile")):
    return [f"win_{k}_{c}_{w}" for k in kinds for c in cols for w in walls]


def _x(m, p, role="any", off=(0.0, 0.0, 0.0)):
    return dict(m=m, p=p, role=role, off=off)


STYLES = {
    "office_glass": dict(gf=["gf_curtain", "gf_entrance_hall", "mall_atrium_glass"], door="door_auto", mid=["curtain_grid", "curtain_ribbon", "curtain_dpg", "curtain_stick_spandrel_stone", "curtain_unitized", "curtain_louver_band", "double_skin_panel"],
                         alt=["x_brace_ext", "curtain_louver_band"], top=["curtain_louver_band", "mech_floor_louver"], gf_h=4.8, wall="wall_alc", band=False, corner="corner_post_glass", span=3.6,
                         extras=[_x("entrance_canopy_big", 0.0, "gf")], special=["glass_elevator_shaft"],
                         roof={"ac_unit_vrf": 3, "ac_unit_vrf_big": 2, "cooling_tower": 2, "roof_duct_run": 1, "water_tank_sq": 1, "roof_helipad": 0.3, "roof_telecom_cluster": 1, "exhaust_stack_group": 1}),
    "office_tile": dict(gf=["gf_stone_base", "gf_metal_base", "gf_curtain"], door="door_main_stone", f2=["win_ribbon", "win_fix"], f2_n=2, mid=["win_ribbon", "win_sliding4", "win_fix", "win_sliding4_hood"] + WIN(["sliding4", "fix"], walls=("tile", "alc")),
                        alt=["louver_vertical", "wall_tile", "fin_ceramic_vertical"], top=["mech_floor_louver", "win_ribbon"], gf_h=4.5, wall="wall_tile", band=True, corner="corner_post", span=3.6,
                        special=["glass_elevator_shaft"], roof={"ac_unit_vrf": 3, "ac_unit_small": 2, "cooling_tower": 1, "water_tank_sq": 1, "roof_duct_run": 1, "roof_machine_room": 1, "roof_telecom_cluster": 1}),
    "tower_mansion": dict(gf=["gf_entrance_hall", "gf_stone_base"], door="door_revolving", f2=["sky_lobby_glass", "curtain_unitized"], f2_n=2, mid=["bal_glass_continuous", "bal_louver_partition", "curtain_unitized", "fin_ceramic_vertical"],
                          alt=["fin_ceramic_vertical", "bal_louver_partition"], top=["mech_floor_louver"], gf_h=5.0, wall="wall_alc", band=False, corner="corner_post_glass", span=3.6,
                          extras=[_x("entrance_canopy_big", 0.0, "gf")], special=["crown_top"],
                          roof={"ac_unit_vrf": 2, "cooling_tower": 2, "roof_helipad": 0.5, "roof_telecom_cluster": 1, "water_tank_sq": 1, "roof_machine_room": 1}),
    "apartment": dict(gf=["gf_brick_base", "gf_stone_base", "gf_garage_louver", "gf_rc_base"], door="door_residential", mid=WIN(["sliding2"], walls=("spray", "tile")) + ["win_sliding2_hood", "win_sliding2_bars", "win_floor"],
                      alt=["balcony_rc", "balcony_glass", "balcony_alu", "balcony_recess", "corridor_open", "bal_louver_partition"], gf_h=3.8, wall="wall_spray", band=True, corner="corner_post", span=3.6,
                      extras=[_x("ac_rack_wall_2", 0.06, "mid"), _x("water_heater_unit", 0.04, "mid", (1.3, 0, 0.9)), _x("duct_vertical_pipes", 0.05, "mid", (1.5, 0, 0))],
                      roof={"ac_unit_small": 4, "water_tank_sq": 1, "roof_vent_pipes": 2, "roof_hatch_ladder": 1, "exhaust_stack_group": 1}),
    "danchi_stair": dict(gf=["gf_rc_base", "gf_brick_base"], door="door_residential", mid=WIN(["sliding2", "casement"], cols=("white", "bronze"), walls=("spray",)) + ["win_sliding2_bars"], alt=["stairhall_slit", "stairhall_glass_block", "stairhall_open"],
                         gf_h=3.2, wall="wall_spray", band=True, corner="corner_post", span=3.3, k=(2, 3), variants=[dict(when="long", mid=["bal_flat_old", "bal_flat_old", "balcony_rc"], alt=["bal_partition_wall"]), dict(when="short", mid=["win_sliding2_bars"], alt=[])],
                         extras=[_x("meter_box_door", 0.5, "gf", (1.8, 0, 0)), _x("mail_box_bank", 0.35, "gf", (-1.5, 0, 1.0)), _x("duct_vertical_pipes", 0.1, "mid", (1.6, 0, 0))],
                         roof={"ac_unit_small": 2, "water_tank_sq": 1, "roof_vent_pipes": 3, "roof_hatch_ladder": 1}),
    "danchi_corridor": dict(gf=["gf_rc_base", "gf_stone_base"], door="door_residential", mid=["corridor_geo_grille", "corridor_open"], alt=["stairhall_open", "stairhall_glass_block"], gf_h=3.4, wall="wall_spray", band=True, corner="corner_post", span=3.3, k=(4, 5),
                            variants=[dict(when="long", mid=["corridor_geo_grille", "corridor_open"]), dict(when="long", mid=["bal_flat_old", "balcony_rc"], alt=[]), dict(when="short", mid=["win_sliding2_bars"], alt=[])],
                            extras=[_x("meter_box_door", 0.4, "mid", (1.7, 0, 0)), _x("gas_meter_box", 0.2, "mid", (-1.6, 0, 0.6))], roof={"water_tank_sq": 1, "roof_vent_pipes": 2, "roof_hatch_ladder": 1}),
    "zakkyo": dict(gf=["gf_storefront", "gf_storefront_nosign", "gf_convenience", "gf_metal_base"], door="door_swing_steel", f2=["win_fix", "win_sliding4_hood", "punching_metal"], f2_n=2,
                   mid=["win_sliding4_hood", "win_fix", "win_sliding2_black", "win_casement_hood"] + WIN(["sliding2", "sliding4"], cols=("black", "white"), walls=("tile", "spray")), alt=["wall_panel_emboss", "louver_horizontal", "win_awning"], gf_h=3.6, wall="wall_tile", band=True, corner="corner_post", span=3.0,
                   extras=[_x("sign_sode_4", 0.22, "f2", (1.2, 0, 0.5)), _x("sign_sode_6", 0.12, "mid", (-1.2, 0, 0.3)), _x("sign_wall_box", 0.25, "f2", (0, 0, 0.3)), _x("sign_tsukidashi_yoko", 0.12, "f2", (0.6, 0, 1.2)),
                           _x("ac_rack_wall_4", 0.12, "mid", (0, 0, 0.9)), _x("ac_rack_wall_2", 0.12, "mid", (0, 0, 1.2)), _x("duct_vertical_pipes", 0.1, "mid", (1.3, 0, 0)), _x("awning_shop_stripe", 0.25, "gf", (0, 0, 2.7)),
                           _x("tenant_plate_board", 0.25, "gf", (-1.0, 0, 0)), _x("a_frame_sign", 0.15, "gf", (0.9, 0.8, 0)), _x("vending_machine", 0.08, "gf", (1.0, 0.1, 0))],
                   special=["stair_ext_zigzag"], roof={"ac_unit_small": 4, "sign_roof_pylon": 1, "water_tank_sq": 1, "roof_vent_pipes": 1, "roof_billboard": 0.6, "antenna_mast": 0.5}),
    "commercial": dict(gf=["gf_storefront", "gf_arcade", "gf_convenience", "gf_storefront_nosign"], door="door_auto", f2=["win_fix", "win_sliding4_hood", "louver_horizontal"], f2_n=1,
                       mid=["win_sliding4_hood", "win_fix", "win_sliding2_black", "punching_metal"] + WIN(["sliding4", "fix"], walls=("tile", "alc")), alt=["louver_horizontal", "louver_diagonal", "wall_panel_emboss", "win_awning"], gf_h=4.2, wall="wall_tile", band=True, corner="corner_post", span=3.6,
                       extras=[_x("sign_wall_box", 0.18, "f2", (0, 0, 0.3)), _x("sign_sode_4", 0.08, "f2", (1.4, 0, 0.5)), _x("ac_rack_wall_2", 0.05, "mid", (0, 0, 1.0)), _x("awning_shop_stripe", 0.12, "gf", (0, 0, 2.7))],
                       roof={"ac_unit_vrf": 3, "ac_unit_small": 3, "antenna_mast": 1, "roof_duct_run": 1, "roof_vent_pipes": 1, "roof_machine_room": 0.5, "roof_billboard": 0.4}),
    "mall": dict(gf=["mall_atrium_glass", "gf_arcade", "gf_entrance_hall"], door="door_revolving", mid=["curtain_louver_band", "punching_metal", "louver_horizontal", "fin_ceramic_vertical", "wall_panel_emboss", "win_ribbon"], alt=["curtain_louver_band", "louver_diagonal"], top=["louver_horizontal", "punching_metal"],
                 gf_h=7.0, wall="wall_alc", band=True, corner="corner_post_glass", span=4.5,
                 extras=[_x("entrance_canopy_big", 0.04, "gf"), _x("deck_wood_rail", 0.12, "gf", (0, 3.0, 0)), _x("flag_poles_3", 0.04, "gf", (0, 3.5, 0))], special=["escalator_tube", "mall_sign_tower"],
                 roof={"ac_unit_vrf_big": 4, "cooling_tower": 2, "roof_machine_room": 1, "roof_duct_run": 1, "roof_telecom_cluster": 1, "water_tank_sq": 1, "exhaust_stack_group": 1}),
    "warehouse": dict(gf=["wall_metal_siding", "door_dock_overhead", "wh_dock_shelter"], door="door_dock_overhead", mid=["wall_metal_siding", "wh_high_window_band", "win_high"], top=["wh_high_window_band", "wall_metal_siding"], alt=["win_high", "wh_man_door"], gf_h=6.0, wall="wall_metal_siding", band=False, corner="corner_post", span=4.5,
                      extras=[_x("wh_canopy_dock", 0.12, "gf", (0, 0, 4.5)), _x("wh_man_door", 0.1, "gf"), _x("pallet_stack", 0.1, "gf", (1.2, 1.4, 0)), _x("ac_group_ground", 0.03, "gf", (2.0, 1.0, 0)), _x("duct_vertical_pipes", 0.04, "gf", (1.8, 0, 0))],
                      roof={"solar_row": 6, "ac_unit_vrf": 1, "roof_vent_pipes": 2, "roof_chimney": 1, "wh_roof_monitor": 1, "exhaust_stack_group": 1}),
    "parking": dict(gf=["pk_slot_open", "pk_slot_mesh"], door="pk_slot_open", mid=["pk_slot_open", "pk_slot_mesh", "pk_louver_panel"], alt=["pk_ramp_face", "stairhall_glass_block", "pk_louver_panel"], top=["pk_louver_panel", "pk_slot_open"], gf_h=3.3, wall="wall_alc", band=False, corner="corner_post", span=5.4,
                    extras=[_x("pk_entry_gate", 0.04, "gf", (0, 3.0, 0))], roof={"ac_unit_small": 1, "roof_hatch_ladder": 1, "antenna_mast": 0.3}),
    "school": dict(gf=["gf_stone_base", "gf_metal_base", "gf_rc_base"], door="door_main_stone", mid=WIN(["sliding4", "fix"], cols=("white", "bronze"), walls=("alc", "spray")) + ["win_ribbon"], alt=["stairhall_glass_block", "stairhall_open"], gf_h=3.8, wall="wall_alc", band=True, corner="corner_post", span=3.6,
                   extras=[_x("flag_poles_3", 0.02, "gf", (0, 4.0, 0))], roof={"water_tank_sq": 1, "roof_vent_pipes": 1, "antenna_mast": 0.5, "ac_unit_small": 2}),
    "hotel": dict(gf=["gf_entrance_hall", "gf_stone_base"], door="door_revolving", f2=["win_fix", "curtain_unitized"], f2_n=2, mid=["win_sliding2_hood", "bal_glass_continuous", "brise_soleil", "curtain_unitized"] + WIN(["sliding2"], walls=("alc",)), alt=["balcony_glass", "win_bay"], gf_h=5.0, wall="wall_alc", band=True, corner="corner_post_glass", span=3.6,
                  extras=[_x("entrance_canopy_big", 0.0, "gf")], special=["crown_top"], roof={"ac_unit_vrf": 3, "cooling_tower": 1, "antenna_mast": 1, "water_tank_sq": 1, "roof_machine_room": 1}),
    "public": dict(gf=["gf_stone_base", "gf_entrance_hall", "gf_arcade"], door="door_main_stone", mid=["win_casement_hood", "win_sliding2_black", "louver_window_behind", "fin_projecting"] + WIN(["casement", "fix"], cols=("bronze", "black"), walls=("alc",)), alt=["pilaster_wall", "wall_stone"],
                   gf_h=5.0, wall="wall_stone", band=True, corner="corner_post_stone", span=4.5, extras=[_x("porch_stone_columns", 0.04, "gf"), _x("flag_poles_3", 0.02, "gf", (0, 4.0, 0))],
                   roof={"ac_unit_vrf": 2, "cooling_tower": 1, "antenna_mast": 1, "water_tank_sq": 1}),
    "house": dict(gf=WIN(["sliding2", "fix"], walls=("spray", "tile")), door="house_entrance_porch", f2=WIN(["sliding2", "casement"], walls=("spray", "tile")), f2_n=1, mid=WIN(["sliding2", "casement", "sliding4"], walls=("spray", "tile")), alt=["balcony_alu", "balcony_rc"],
                  gf_h=3.0, wall="wall_spray", band=False, corner="corner_post", span=3.0, pitched=True, k=(3, 4),
                  extras=[_x("house_garage_shutter", 0.12, "gf"), _x("ac_rack_wall_2", 0.06, "mid", (0, 0, 1.0)), _x("mailbox_post", 0.2, "gf", (1.6, 1.2, 0)), _x("hedge_planter", 0.2, "gf", (-1.6, 1.4, 0)), _x("gate_slide", 0.08, "gf", (0, 2.0, 0))],
                  roof={"ac_unit_small": 1, "solar_row": 0.5}),
    "shrine": dict(gf=["wall_stone", "wall_spray"], door="door_main_stone", mid=["wall_spray"], alt=[], gf_h=3.6, wall="wall_spray", band=False, corner="corner_post_stone", span=3.6, pitched=True, extras=[_x("stone_lantern", 0.3, "gf", (1.5, 1.5, 0))],
                   special=["torii_small"], roof={}),
}
REG_FALLBACK = {"pilaster_wall": "wall_ribs_vertical", "bal_partition_wall": "bal_partition_board"}
MICRO = {  # 小物建物プレハブ: 名前 → (奥行方向に対する公称 W×D)
    "bldg_vending_corner": (4.0, 1.8), "bldg_trash_enclosure": (3.0, 1.4), "bldg_bike_shed": (5.0, 2.2), "bldg_bus_shelter": (3.6, 1.2), "bldg_kiosk": (3.0, 2.4),
    "bldg_cubicle": (2.4, 1.4), "bldg_toilet": (4.0, 3.0), "bldg_hut": (4.0, 3.0), "bldg_substation": (6.0, 4.0),
}


@dataclass
class Inst:
    name: str
    x: float
    y: float
    z: float
    rot: float
    sx: float = 1.0
    sy: float = 1.0
    sz: float = 1.0


@dataclass
class Built:
    id: int
    insts: list = field(default_factory=list)
    shell: Mesh = field(default_factory=Mesh)
    meta: dict = field(default_factory=dict)


def validate_styles():
    """STYLESが参照する全モジュールがREGに在るか(テスト用)。足りない名前を返す"""
    miss = set()
    for S in STYLES.values():
        names = list(S["gf"]) + [S["door"]] + list(S["mid"]) + list(S.get("alt", [])) + list(S.get("f2", [])) + list(S.get("top", [])) + [S["wall"], S["corner"]] + list(S.get("roof", {}))
        names += [e["m"] for e in S.get("extras", [])] + [s for s in S.get("special", []) if s in REG]
        for v in S.get("variants", []):
            names += list(v.get("mid", [])) + list(v.get("alt", []))
        miss |= {n for n in names if REG_FALLBACK.get(n, n) not in REG}
    miss |= {n for n in MICRO if n not in REG}
    return miss


def pick_style(tags, area, floors, rng, rect=True, long_side=0.0):
    b = tags.get("building", "yes")
    amen = tags.get("amenity", "")
    if b in ("parking", "garage") and floors >= 2 or amen == "parking_multistorey" or b == "parking":
        return "parking"
    if b in ("industrial", "warehouse", "garage", "garages", "service", "hangar", "manufacture") or (area > 2500 and floors <= 4 and rng.random() < 0.55 and b == "yes"):
        return "warehouse"
    if b in ("shrine", "temple", "church", "chapel", "religious") or amen == "place_of_worship":
        return "shrine"
    if b in ("school", "kindergarten", "university", "college") or amen in ("school", "kindergarten"):
        return "school"
    if b in ("house", "detached", "semidetached_house", "terrace") or (b in ("residential", "yes") and area < 260 and floors <= 3 and rect and rng.random() < 0.8):
        return "house"
    if b in ("apartments", "residential", "dormitory"):
        if floors >= 14:
            return "tower_mansion"
        if long_side > 28 and 3 <= floors <= 8:
            return rng.choice(["danchi_stair", "danchi_corridor", "apartment"])
        return "apartment"
    if b in ("retail", "commercial", "supermarket", "kiosk"):
        return "mall" if area > 3000 else rng.choice(["commercial", "zakkyo", "commercial"])
    if b == "hotel":
        return rng.choice(["hotel", "tower_mansion"]) if floors >= 12 else "hotel"
    if b in ("public", "civic", "government", "hospital", "train_station", "museum"):
        return "public"
    if b == "office":
        return rng.choice(["office_glass", "office_tile"])
    if area > 4000 and floors <= 6:
        return rng.choice(["mall", "warehouse", "office_tile"])
    if floors >= 14:
        return rng.choice(["office_glass", "office_glass", "tower_mansion", "hotel"])
    if floors >= 7:
        return rng.choice(["office_tile", "apartment", "office_glass", "hotel", "tower_mansion", "danchi_stair"] if long_side > 28 else ["office_tile", "apartment", "office_glass", "hotel", "zakkyo"])
    if floors >= 4:
        return rng.choice(["zakkyo", "commercial", "apartment", "office_tile", "danchi_corridor" if long_side > 26 else "zakkyo"])
    return rng.choice(["commercial", "zakkyo", "apartment", "office_tile"])


def _tess(poly):
    """shapely Polygon(穴付き) → 三角形リスト(3D座標z=0)"""
    rings = [list(poly.exterior.coords)[:-1]] + [list(i.coords)[:-1] for i in poly.interiors]
    rings = [[Vector((x, y, 0)) for x, y in r] for r in rings]
    flat = [v for r in rings for v in r]
    return [[flat[i] for i in t] for t in tessellate_polygon(rings)]


def _cap(mesh, geom, z, mat, up=True):
    gs = [geom] if geom.geom_type == "Polygon" else list(getattr(geom, "geoms", []))
    for g in gs:
        if g.geom_type != "Polygon" or g.area < 0.5:
            continue
        for tri in _tess(g):
            pts = [(v.x, v.y, z) for v in tri]
            a, b, c = pts
            n = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            mesh.poly(pts if (n > 0) == up else pts[::-1], mat)


def _core(mesh, poly, z0, z1, mat="core"):
    for g in ([poly] if poly.geom_type == "Polygon" else list(getattr(poly, "geoms", []))):   # 細い建物はbufferで分裂することがある
        if g.geom_type != "Polygon":
            continue
        c = list(g.exterior.coords)
        for a, b in zip(c, c[1:]):
            mesh.poly([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat)


def _edges(poly):
    c = list(poly.exterior.coords)
    return list(zip(c, c[1:]))


def _put(B, name, x, y, z, rot, sx=1.0, sy=1.0, sz=1.0):
    name = REG_FALLBACK.get(name, name)
    B.insts.append(Inst(name, x, y, z, rot, sx, sy, sz))


def _band(fi, n_f, S, z_is_base):
    if fi == 0 and z_is_base:
        return "gf"
    if 1 <= fi <= S.get("f2_n", 0) and n_f > S.get("f2_n", 0) + 1:
        return "f2"
    if fi == n_f - 1 and n_f > 3 and S.get("top"):
        return "top"
    return "mid"


def _pick_variant(S, L, rng):
    vs = S.get("variants")
    if not vs:
        return {}
    kind = "long" if L >= 12 else "short"
    cand = [v for v in vs if v.get("when", "any") in (kind, "any")]
    return rng.choice(cand) if cand else {}


def _facade(B, poly, z0, floor_hs, S, rng, base=True, door_wanted=True):
    """1つのtier(ポリゴン×階リスト)の外周に、フロア帯×ベイ列でモジュールと付加部材を敷く"""
    n_f = len(floor_hs)
    z_top = z0 + sum(floor_hs)
    edges = _edges(poly)
    longest = max(range(len(edges)), key=lambda i: math.dist(*edges[i]))
    door_done = not door_wanted
    pitched = S.get("pitched", False)
    for ei, (p, q) in enumerate(edges):
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        if L < 0.6:
            continue
        rot = math.atan2(dy, dx)
        ux, uy = dx / L, dy / L
        ox, oy = -uy, ux
        nb = max(1, round(L / S["span"]))
        w = L / nb
        v = _pick_variant(S, L, rng)
        mids = v.get("mid", S["mid"]); alts = v.get("alt", S.get("alt", []))
        gf_mod = rng.choice(S["gf"])
        f2_mod = rng.choice(S.get("f2", mids)) if S.get("f2") else None
        mid_mod = rng.choice(mids)
        top_mod = rng.choice(S["top"]) if S.get("top") else None
        alt = rng.choice(alts) if alts else None
        kr = S.get("k", (2, 5))
        k = rng.randint(kr[0], kr[1]) if alt else 0
        blank = (L < 3.0) or (2 < n_f <= 8 and rng.random() < 0.10)   # 高層で一面が無窓になるのを避ける
        door_bay = rng.randrange(nb) if (ei == longest and not door_done and base) else -1
        if door_bay >= 0:
            door_done = True
        for i in range(nb):
            cx, cy = p[0] + ux * (i + 0.5) * w, p[1] + uy * (i + 0.5) * w
            z = z0
            fi = 0
            while fi < n_f:
                h = floor_hs[fi]
                role = _band(fi, n_f, S, base)
                if role == "gf":
                    m = S["door"] if (i == door_bay and h >= 3.0) else (S["wall"] if blank else gf_mod)
                elif blank:
                    m = S["wall"]
                elif alt and k and (i % k == k - 1) and fi > 0:
                    m = alt
                elif role == "f2":
                    m = f2_mod
                elif role == "top":
                    m = top_mod
                else:
                    m = mid_mod
                if m.startswith("balcony") and fi == n_f - 1 and rng.random() < 0.5:
                    m = mid_mod
                mm = REG_FALLBACK.get(m, m)
                Hm = REG[mm]["H"]
                nfl = 1
                if Hm >= 1.7 * h and fi + 1 < n_f:
                    nfl = min(n_f - fi, max(1, round(Hm / h)))
                hh = sum(floor_hs[fi:fi + nfl])
                sz = max(0.7, min(1.5, hh / Hm))
                _put(B, mm, cx, cy, z, rot, w / REG[mm]["W"], 1.0, sz)
                if m == S["door"] and role == "gf":
                    for ex in S.get("extras", []):
                        if ex["role"] == "gf" and ex["p"] > 0 and rng.random() < ex["p"] * 4 and ex["m"] in ("entrance_canopy_big", "porch_stone_columns"):
                            _put(B, ex["m"], cx, cy, z, rot)
                            break
                elif role != "gf" or not blank:
                    for ex in S.get("extras", []):
                        if (ex["role"] in (role, "any")) and ex["p"] > 0 and ex["m"] not in ("entrance_canopy_big", "porch_stone_columns") and rng.random() < ex["p"] and w > 1.6:
                            ox_, oy_, oz_ = ex["off"]
                            if ex["m"] in ("flag_poles_3", "deck_wood_rail", "pk_entry_gate") and i != nb // 2:
                                continue
                            _put(B, ex["m"], cx + ux * ox_ + ox * 0.0, cy + uy * ox_, z + oz_, rot) if oy_ == 0 else _put(B, ex["m"], cx + ux * ox_ + ox * oy_, cy + uy * ox_ + oy * oy_, z + oz_, rot)
                if S["band"] and fi > 0 and not m.startswith(("curtain", "mall", "double", "sky", "bal_glass", "pk_")):
                    _put(B, "slab_edge", cx, cy, z - 0.2, rot, w / 3.6)
                z += hh
                fi += nfl
            if not pitched:
                _put(B, "parapet" if rng.random() > 0.08 else "parapet_louver", cx, cy, z_top, rot, w / 3.6)
    ring = list(poly.exterior.coords)[:-1]
    for i, v in enumerate(ring):
        a, b = ring[i - 1], ring[(i + 1) % len(ring)]
        a1 = math.atan2(v[1] - a[1], v[0] - a[0]); a2 = math.atan2(b[1] - v[1], b[0] - v[0])
        d = abs((a2 - a1 + math.pi) % (2 * math.pi) - math.pi)
        if d > math.radians(12):
            _put(B, S["corner"], v[0], v[1], z0, a2, 1.0, 1.0, (z_top - z0) / 1.0)
    return z_top


def _specials(B, poly, z0, z_top, S, rng, n_f):
    """建物に1つずつ付く特殊部材(非常階段/EVシャフト/エスカレーター/サイン塔/頂部ルーバー/鳥居)"""
    edges = _edges(poly)
    if not edges or not S.get("special"):
        return
    order = sorted(range(len(edges)), key=lambda i: math.dist(*edges[i]))
    short, long_ = edges[order[0]], edges[order[-1]]

    def at(e, t, out=0.0):
        (px, py), (qx, qy) = e
        L = math.hypot(qx - px, qy - py) or 1
        ux, uy = (qx - px) / L, (qy - py) / L
        return px + (qx - px) * t - uy * out, py + (qy - py) * t + ux * out, math.atan2(uy, ux)
    for sp in S["special"]:
        if sp == "stair_ext_zigzag" and n_f >= 3 and math.dist(*short) > 3.0:
            x, y, r = at(short, 0.5)
            for z in range(0, max(1, int((z_top - z0) // 7.0))):
                _put(B, "stair_ext_zigzag", x, y, z0 + z * 7.0, r)
        elif sp == "glass_elevator_shaft" and math.dist(*long_) > 6 and rng.random() < 0.6:
            x, y, r = at(long_, rng.choice([0.2, 0.8]))
            hs = (z_top - z0) / max(1, n_f)
            for f in range(n_f):
                _put(B, "glass_elevator_shaft", x, y, z0 + f * hs, r, 1.0, 1.0, hs / 3.5)
        elif sp == "crown_top" and n_f >= 10 and rng.random() < 0.8:
            for (px, py), (qx, qy) in edges:
                L = math.hypot(qx - px, qy - py)
                if L < 3:
                    continue
                nb = max(1, round(L / 3.6)); r = math.atan2(qy - py, qx - px)
                for i in range(nb):
                    t = (i + 0.5) / nb
                    _put(B, "crown_louver_top", px + (qx - px) * t, py + (qy - py) * t, z_top, r, L / nb / 3.6)
        elif sp == "escalator_tube" and math.dist(*long_) > 15 and rng.random() < 0.7:
            x, y, r = at(long_, rng.choice([0.25, 0.75]), 0.0)
            _put(B, "escalator_tube", x, y, z0, r)
        elif sp == "mall_sign_tower" and rng.random() < 0.7:
            x, y, r = at(long_, rng.choice([0.1, 0.9]), 6.0)
            _put(B, "mall_sign_tower", x, y, z0, r)
        elif sp == "torii_small":
            x, y, r = at(long_, 0.5, 8.0)
            _put(B, "torii_small", x, y, z0, r)
        elif sp == "apt_stair_side" and n_f >= 2 and math.dist(*short) > 2.0:
            x, y, r = at(short, 0.5)
            _put(B, "apt_stair_side", x, y, z0, r, 1.0, 1.0, (z_top - z0) / 6.2)
        elif sp.startswith("sp_") and sp in REG and rng.random() < 0.8:
            x, y, r = at(long_, rng.uniform(0.15, 0.85), 3.5)
            _put(B, sp, x, y, z0, r)


def _pitched_roof(B, poly, z, rng, kind=None, mat="roof_tile", wall_mat="spray_main"):
    """ほぼ長方形の平面に切妻/寄棟屋根(軒の出0.45m, 勾配23〜30°)。長方形でなければFalse"""
    try:
        r = poly.minimum_rotated_rectangle
    except Exception:
        return False
    if r.geom_type != "Polygon" or poly.area / r.area < 0.85:
        return False
    c = list(r.exterior.coords)[:4]
    e1 = (c[1][0] - c[0][0], c[1][1] - c[0][1]); e2 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
    l1, l2 = math.hypot(*e1), math.hypot(*e2)
    if l2 > l1:
        e1, e2, l1, l2 = e2, e1, l2, l1
    cx, cy = r.centroid.x, r.centroid.y
    u = (e1[0] / l1, e1[1] / l1); v = (e2[0] / l2, e2[1] / l2)
    a, b = l1 / 2 + 0.45, l2 / 2 + 0.45
    h = b * math.tan(math.radians(rng.uniform(23, 30)))
    kind = kind or rng.choice(["gable", "hip", "gable"])
    P = lambda s, t, zz: (cx + u[0] * s + v[0] * t, cy + u[1] * s + v[1] * t, zz)
    sh = B.shell
    if kind == "gable":
        for sgn in (-1, 1):
            sh.oriented([P(-a, sgn * b, z), P(a, sgn * b, z), P(a, 0, z + h), P(-a, 0, z + h)], (v[0] * sgn * h, v[1] * sgn * h, b), mat)
        for sgn in (-1, 1):
            sh.oriented([P(sgn * (a - 0.45), -b + 0.45, z), P(sgn * (a - 0.45), b - 0.45, z), P(sgn * (a - 0.45), 0, z + h * 0.88)], (u[0] * sgn, u[1] * sgn, 0), wall_mat)
        _cap(sh, poly.buffer(-0.2, join_style=2), z - 0.02, "core", False)
    else:
        rl = max(0.2, a - b)
        ridge = [P(-rl, 0, z + h), P(rl, 0, z + h)]
        sh.oriented([P(-a, -b, z), P(a, -b, z), P(rl, 0, z + h), P(-rl, 0, z + h)], (-v[0] * h, -v[1] * h, b), mat)
        sh.oriented([P(a, b, z), P(-a, b, z), P(-rl, 0, z + h), P(rl, 0, z + h)], (v[0] * h, v[1] * h, b), mat)
        sh.oriented([P(a, -b, z), P(a, b, z), P(rl, 0, z + h)], (u[0] * h, u[1] * h, a - rl), mat)
        sh.oriented([P(-a, b, z), P(-a, -b, z), P(-rl, 0, z + h)], (-u[0] * h, -u[1] * h, a - rl), mat)
    return True


def _roof_props(B, area_geom, z, S, rng, floors, top, bigarea):
    if area_geom.is_empty or not S.get("roof"):
        return
    reg = area_geom.buffer(-1.6)
    if reg.is_empty:
        return
    geoms = [reg] if reg.geom_type == "Polygon" else list(reg.geoms)
    geoms = [g for g in geoms if g.area > 4]
    if not geoms:
        return
    total = sum(g.area for g in geoms)
    names, wts = zip(*S["roof"].items())
    n = min(26, int(total / 65) + 2)       # 屋上設備を密に(空中視点で平らに見えない)
    if S is STYLES["warehouse"]:
        n = min(30, int(total / 90))

    def rp():
        g = rng.choices(geoms, [g.area for g in geoms])[0]
        x0, y0, x1, y1 = g.bounds
        for _ in range(30):
            p = Point(rng.uniform(x0, x1), rng.uniform(y0, y1))
            if g.contains(p):
                return p.x, p.y
        return None
    placed = []
    if floors >= 4:
        pt = rp()
        if pt:
            _put(B, "rooftop_stairhouse", pt[0], pt[1], z, rng.choice([0, math.pi / 2]))
            placed.append(pt)
    if top > 45:
        pt = rp()
        if pt:
            _put(B, "antenna_mast", pt[0], pt[1], z, rng.random() * 6.28)
    for _ in range(n):
        pt = rp()
        if not pt or any(math.dist(pt, q) < 3.5 for q in placed):
            continue
        placed.append(pt)
        nm = rng.choices(names, wts)[0]
        if nm == "roof_helipad" and (top < 60 or any(i.name == "roof_helipad" for i in B.insts)):
            continue
        _put(B, nm, pt[0], pt[1], z, rng.choice([0, math.pi / 2, math.pi, -math.pi / 2]) + rng.uniform(-0.05, 0.05))


def _micro(feat, poly, rng):
    """小面積の建物/設備(自販機コーナー・駐輪場・バス停・売店・ゴミ置場・変電室など)を1プレハブで置く"""
    t = feat.tags
    amen, shop, power = t.get("amenity", ""), t.get("shop", ""), t.get("power", "")
    if amen == "bicycle_parking":
        name = "bldg_bike_shed"
    elif amen in ("bus_station", "shelter") or t.get("highway") == "bus_stop" or t.get("public_transport"):
        name = "bldg_bus_shelter"
    elif amen == "toilets":
        name = "bldg_toilet"
    elif amen == "vending_machine":
        name = "bldg_vending_corner"
    elif amen == "waste_disposal" or amen == "waste_basket":
        name = "bldg_trash_enclosure"
    elif shop in ("kiosk", "convenience") or amen == "fast_food":
        name = "bldg_kiosk"
    elif power in ("substation", "transformer", "generator"):
        name = rng.choice(["bldg_substation", "bldg_cubicle"])
    else:
        name = rng.choice(["bldg_hut", "bldg_cubicle", "bldg_vending_corner", "bldg_trash_enclosure", "bldg_bike_shed", "bldg_kiosk", "bldg_hut"])
    nw, nd = MICRO[name]
    r = poly.minimum_rotated_rectangle
    if r.geom_type != "Polygon":
        return None
    c = list(r.exterior.coords)[:4]
    e1 = (c[1][0] - c[0][0], c[1][1] - c[0][1]); e2 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
    l1, l2 = math.hypot(*e1), math.hypot(*e2)
    if l2 > l1:
        e1, l1, l2 = e2, l2, l1
    ang = math.atan2(e1[1], e1[0]) + rng.choice([0.0, math.pi])
    return name, r.centroid.x, r.centroid.y, ang, max(0.7, min(1.6, l1 / nw)), max(0.7, min(1.6, l2 / nd))


def build_building(feat, seed=0, style=None):
    g = feat.geom
    if isinstance(g, MultiPolygon):
        g = max(g.geoms, key=lambda x: x.area)
    t = feat.tags
    poly = orient(Polygon(g.exterior).simplify(0.3, preserve_topology=True), sign=-1.0) if g.geom_type == "Polygon" else None
    if poly is None or poly.is_empty or poly.geom_type != "Polygon":
        return None
    rng = random.Random(feat.id * 7919 + seed)
    micro_tag = t.get("amenity") in ("bicycle_parking", "bus_station", "shelter", "toilets", "vending_machine", "waste_disposal") or t.get("power") in ("substation", "transformer") or t.get("shop") == "kiosk"
    if poly.area < 45 and (micro_tag or poly.area >= 6):
        mi = _micro(feat, poly, rng)
        if mi is None:
            return None
        B = Built(feat.id)
        B.meta = dict(style="micro", floors=1, height=3.0, bvar=rng.random(), variant=mi[0])
        _put(B, mi[0], mi[1], mi[2], 0.0, mi[3], mi[4], mi[5], 1.0)
        return B
    if poly.area < 25:
        return None
    top, mn = t["_top"], t["_min"]
    H = max(3.0, top - mn)
    n = max(1, round(H / 3.6))
    r = poly.minimum_rotated_rectangle
    rect = r.geom_type == "Polygon" and poly.area / r.area > 0.85
    rc = list(r.exterior.coords)[:4] if r.geom_type == "Polygon" else []
    long_side = max((math.dist(rc[i], rc[i + 1]) for i in range(3)), default=0.0) if rc else 0.0
    style_name = style or t.get("_style") or pick_style(t, poly.area, n, rng, rect, long_side)
    if style_name == "house" and not rect:
        style_name = "zakkyo"
    S = STYLES[style_name]
    B = Built(feat.id)
    B.meta = dict(style=style_name, floors=n, height=H, bvar=rng.random())
    if n == 1:
        floors = [H]
    else:
        gf = min(S["gf_h"], H * 0.4)
        floors = [gf] + [(H - gf) / (n - 1)] * (n - 1)
    upper_n, upper_poly, S_up = 0, None, S
    if n >= 10 and poly.area > 350 and rng.random() < 0.5:
        up = poly.buffer(-rng.uniform(1.5, 3.0), join_style=2)
        if up.geom_type == "Polygon" and up.area > poly.area * 0.5:
            upper_n = rng.randint(2, min(5, n // 2)); upper_poly = orient(up.simplify(0.3), sign=-1.0)
            if rng.random() < 0.5:
                S_up = STYLES[rng.choice(["office_glass", "hotel", "tower_mansion"])]
    z0 = mn
    low = floors[:-upper_n] if upper_n else floors
    zt = _facade(B, poly, z0, low, S, rng)
    _core(B.shell, poly.buffer(-0.2, join_style=2), z0, zt, "core")
    if upper_poly is not None:
        _cap(B.shell, poly.buffer(-0.2, join_style=2).difference(upper_poly.buffer(0.1)), zt, "roof_membrane")
        _roof_props(B, poly.difference(upper_poly).buffer(-0.5), zt, S, rng, n, zt, True)
        z2 = _facade(B, upper_poly, zt, floors[-upper_n:], S_up, rng, base=False, door_wanted=False)
        _core(B.shell, upper_poly.buffer(-0.2, join_style=2), zt, z2, "core")
        _cap(B.shell, upper_poly.buffer(-0.2, join_style=2), z2, "roof_membrane")
        _roof_props(B, upper_poly, z2, S_up, rng, n, z2, False)
        _specials(B, upper_poly, zt, z2, S_up, rng, upper_n)
        _specials(B, poly, z0, zt, {k: v for k, v in S.items() if k != "special"} | {"special": [s for s in S.get("special", []) if s in ("glass_elevator_shaft", "escalator_tube", "mall_sign_tower", "stair_ext_zigzag", "torii_small")]}, rng, len(low))
    else:
        if S.get("pitched") and S.get("roofs"):
            from . import roofs
            R = S["roofs"]
            done = roofs.build(B, poly, zt, rng, rng.choice(R["kinds"]), rng.choice(R["mats"]), S.get("wall_mat", "spray_main"))
        else:
            done = S.get("pitched") and _pitched_roof(B, poly, zt, rng, "gable" if style_name == "shrine" else None, "roof_tile" if rng.random() < 0.75 else "roof_metal")
        if not done:
            _cap(B.shell, poly.buffer(-0.2, join_style=2), zt, "roof_membrane")
            _roof_props(B, poly, zt, S, rng, n, zt, False)
        _specials(B, poly, z0, zt, S, rng, n)
    return B


from . import styles_extra  # noqa: E402,F401  (田舎/ロードサイド/工場の様式を登録)
