"""建物フットプリント → モジュールインスタンス列(形状文法ルール)。City Sample の「ボリューム→スタイル適用」相当。"""
import math
import random
from dataclasses import dataclass, field

import bpy  # noqa: F401  (mathutilsを有効化)
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient

from .modules.geom import Mesh
from .modules import library  # noqa: F401  (モジュール登録)
from .modules.registry import REG

# スタイル: gf=1階候補, door=入口, mid=中間階の窓型, alt=数bayごとに挟む意匠(バルコニー等),
# gf_h=1階階高, wall=無窓壁, band=層間帯, roof=屋上設備重み
STYLES = {
    "office_glass": dict(gf=["gf_curtain", "gf_entrance_hall"], door="door_auto", mid=["curtain_grid", "curtain_ribbon", "curtain_dpg", "curtain_stick_spandrel_stone"],
                         alt=[], gf_h=4.5, wall="wall_alc", band=False, corner="corner_post_glass", span=3.6,
                         roof={"ac_unit_vrf": 3, "ac_unit_vrf_big": 2, "cooling_tower": 2, "roof_duct_run": 1, "water_tank": 1}),
    "office_tile": dict(gf=["gf_stone_base", "gf_metal_base", "gf_curtain"], door="door_main_stone", mid=["win_ribbon", "win_sliding4", "win_fix", "win_sliding4_hood"],
                        alt=["louver_vertical", "wall_tile"], gf_h=4.5, wall="wall_tile", band=True, corner="corner_post", span=3.6,
                        roof={"ac_unit_vrf": 3, "ac_unit_small": 2, "cooling_tower": 1, "water_tank": 1, "roof_duct_run": 1}),
    "apartment": dict(gf=["gf_brick_base", "gf_stone_base", "gf_garage_louver", "gf_rc_base"], door="door_residential", mid=["win_sliding2_hood", "win_sliding2_bars", "win_floor"],
                      alt=["balcony_rc", "balcony_glass", "balcony_alu", "balcony_recess", "corridor_open"], gf_h=3.8, wall="wall_spray", band=True, corner="corner_post", span=3.6,
                      roof={"ac_unit_small": 4, "water_tank": 1, "roof_vent_pipes": 2, "roof_hatch_ladder": 1}),
    "commercial": dict(gf=["gf_storefront", "gf_arcade", "gf_convenience", "gf_storefront_nosign"], door="door_auto", mid=["win_sliding4_hood", "win_fix", "win_sliding2_black", "punching_metal"],
                       alt=["louver_horizontal", "louver_diagonal", "wall_panel_emboss", "win_awning"], gf_h=4.2, wall="wall_tile", band=True, corner="corner_post", span=3.6,
                       roof={"ac_unit_vrf": 3, "ac_unit_small": 3, "antenna_mast": 1, "roof_duct_run": 1, "roof_vent_pipes": 1}),
    "warehouse": dict(gf=["wall_metal_siding", "door_dock_overhead"], door="door_dock_overhead", mid=["wall_metal_siding", "win_high"],
                      alt=["win_high"], gf_h=6.0, wall="wall_metal_siding", band=False, corner="corner_post", span=4.5,
                      roof={"solar_row": 6, "ac_unit_vrf": 1, "roof_vent_pipes": 2, "roof_chimney": 1}),
    "public": dict(gf=["gf_stone_base", "gf_entrance_hall", "gf_arcade"], door="door_main_stone", mid=["win_casement_hood", "win_sliding2_black", "louver_window_behind", "fin_projecting"],
                   alt=["pilaster_wall", "wall_stone"], gf_h=5.0, wall="wall_stone", band=True, corner="corner_post_stone", span=4.5,
                   roof={"ac_unit_vrf": 2, "cooling_tower": 1, "antenna_mast": 1, "water_tank": 1}),
    "hotel": dict(gf=["gf_entrance_hall", "gf_stone_base"], door="door_revolving", mid=["win_sliding2_hood", "balcony_glass", "brise_soleil"],
                  alt=["balcony_glass", "win_bay"], gf_h=5.0, wall="wall_alc", band=True, corner="corner_post_glass", span=3.6,
                  roof={"ac_unit_vrf": 3, "cooling_tower": 1, "antenna_mast": 1, "water_tank": 1}),
}
STYLES["apartment"]["alt"] = ["balcony_rc", "balcony_glass", "balcony_alu", "balcony_recess", "corridor_open"]
REG_FALLBACK = {"pilaster_wall": "wall_ribs_vertical"}


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


def pick_style(tags, area, floors, rng):
    b = tags.get("building", "yes")
    if b in ("industrial", "warehouse", "garage", "garages", "service", "hangar") or (area > 2500 and floors <= 4 and rng.random() < 0.6):
        return "warehouse"
    if b in ("apartments", "residential", "dormitory", "house", "terrace"):
        return "apartment"
    if b in ("retail", "commercial", "supermarket", "kiosk"):
        return "commercial"
    if b in ("hotel",):
        return "hotel"
    if b in ("public", "civic", "government", "school", "hospital", "university", "train_station", "museum"):
        return "public"
    if b == "office":
        return rng.choice(["office_glass", "office_tile"])
    if floors >= 14:
        return rng.choice(["office_glass", "office_glass", "hotel", "apartment"])
    if floors >= 7:
        return rng.choice(["office_tile", "apartment", "office_glass", "hotel"])
    return rng.choice(["commercial", "apartment", "office_tile", "commercial"])


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
    c = list(poly.exterior.coords)
    for a, b in zip(c, c[1:]):
        mesh.poly([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat)


def _edges(poly):
    c = list(poly.exterior.coords)
    return list(zip(c, c[1:]))


def _put(B, name, x, y, z, rot, sx=1.0, sy=1.0, sz=1.0):
    name = REG_FALLBACK.get(name, name)
    B.insts.append(Inst(name, x, y, z, rot, sx, sy, sz))


def _facade(B, poly, z0, floor_hs, S, rng, top_style=None):
    """1つのtier(ポリゴン×階リスト)の外周に、フロア×スパンでモジュールを敷く"""
    n_f = len(floor_hs)
    z_top = z0 + sum(floor_hs)
    edges = _edges(poly)
    longest = max(range(len(edges)), key=lambda i: math.dist(*edges[i]))
    door_done = False
    for ei, (p, q) in enumerate(edges):
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        if L < 0.6:
            continue
        rot = math.atan2(dy, dx)
        ux, uy = dx / L, dy / L
        nb = max(1, round(L / S["span"]))
        w = L / nb
        gf_mod = rng.choice(S["gf"])
        mid_mod = rng.choice(S["mid"])
        alt = rng.choice(S["alt"]) if S["alt"] else None
        k = rng.choice([2, 3, 4, 5]) if alt else 0
        blank = (L < 3.0) or (n_f > 2 and rng.random() < 0.10)  # 小さい辺/隣地側の無窓壁
        top_mod = S.get("top")
        door_bay = rng.randrange(nb) if (ei == longest and not door_done) else -1
        if door_bay >= 0:
            door_done = True
        for i in range(nb):
            cx, cy = p[0] + ux * (i + 0.5) * w, p[1] + uy * (i + 0.5) * w
            z = z0
            for fi, h in enumerate(floor_hs):
                if fi == 0 and n_f >= 1 and z0 is not None:
                    if i == door_bay and h >= 3.4:
                        m = S["door"]
                    elif blank:
                        m = S["wall"]
                    else:
                        m = gf_mod
                else:
                    if blank:
                        m = S["wall"]
                    elif alt and k and (i % k == k - 1) and fi > 0:
                        m = alt
                    else:
                        m = top_mod if (fi == n_f - 1 and top_mod) else mid_mod
                    if m.startswith("balcony") and fi == n_f - 1 and rng.random() < 0.5:
                        m = mid_mod
                Hm = REG[REG_FALLBACK.get(m, m)]["H"]
                sz = max(0.7, min(1.5, h / Hm))
                _put(B, m, cx, cy, z, rot, w / REG[REG_FALLBACK.get(m, m)]["W"], 1.0, sz)
                if S["band"] and fi > 0 and not m.startswith("curtain"):
                    _put(B, "slab_edge", cx, cy, z - 0.2, rot, w / 3.6)
                z += h
            _put(B, "parapet" if rng.random() > 0.08 else "parapet_louver", cx, cy, z_top, rot, w / 3.6)
    # 隅柱
    ring = list(poly.exterior.coords)[:-1]
    for i, v in enumerate(ring):
        a, b = ring[i - 1], ring[(i + 1) % len(ring)]
        a1 = math.atan2(v[1] - a[1], v[0] - a[0]); a2 = math.atan2(b[1] - v[1], b[0] - v[0])
        d = abs((a2 - a1 + math.pi) % (2 * math.pi) - math.pi)
        if d > math.radians(12):
            _put(B, S["corner"], v[0], v[1], z0, a2, 1.0, 1.0, (z_top - z0) / 1.0)
    return z_top


def _roof_props(B, area_geom, z, S, rng, floors, top, bigarea):
    if area_geom.is_empty:
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
    n = min(14, int(total / 110) + 1)
    if S is STYLES["warehouse"]:
        n = min(30, int(total / 90))

    def rp():
        g = rng.choices(geoms, [g.area for g in geoms])[0]
        x0, y0, x1, y1 = g.bounds
        for _ in range(30):
            from shapely.geometry import Point
            p = Point(rng.uniform(x0, x1), rng.uniform(y0, y1))
            if g.contains(p):
                return p.x, p.y
        return None
    placed = []
    if floors >= 4:
        pt = rp()
        if pt:
            _put(B, "rooftop_stairhouse", pt[0], pt[1], z, rng.choice([0, math.pi / 2]) )
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
        _put(B, nm, pt[0], pt[1], z, rng.choice([0, math.pi / 2, math.pi, -math.pi / 2]) + rng.uniform(-0.05, 0.05))


def build_building(feat, seed=0):
    g = feat.geom
    if isinstance(g, MultiPolygon):
        g = max(g.geoms, key=lambda x: x.area)
    if g.area < 25:
        return None
    poly = orient(Polygon(g.exterior).simplify(0.3, preserve_topology=True), sign=-1.0)
    if poly.is_empty or poly.geom_type != "Polygon" or poly.area < 25:
        return None
    rng = random.Random(feat.id * 7919 + seed)
    t = feat.tags
    top, mn = t["_top"], t["_min"]
    H = max(3.0, top - mn)
    n = max(1, round(H / 3.6))
    style_name = pick_style(t, poly.area, n, rng)
    S = STYLES[style_name]
    B = Built(feat.id)
    B.meta = dict(style=style_name, floors=n, height=H, bvar=rng.random())
    if n == 1:
        floors = [H]
    else:
        gf = min(S["gf_h"], H * 0.4)
        floors = [gf] + [(H - gf) / (n - 1)] * (n - 1)
    # セットバック(上下で別スタイル/ボリューム)
    upper_n, upper_poly, S_up = 0, None, S
    if n >= 10 and poly.area > 350 and rng.random() < 0.5:
        up = poly.buffer(-rng.uniform(1.5, 3.0), join_style=2)
        if up.geom_type == "Polygon" and up.area > poly.area * 0.5:
            upper_n = rng.randint(2, min(5, n // 2)); upper_poly = orient(up.simplify(0.3), sign=-1.0)
            if rng.random() < 0.5:
                S_up = STYLES[rng.choice(["office_glass", "hotel"])]
    z0 = mn
    low = floors[:-upper_n] if upper_n else floors
    zt = _facade(B, poly, z0, low, S, rng)
    _core(B.shell, poly.buffer(-0.2, join_style=2), z0, zt, "core")
    if upper_poly is not None:
        _cap(B.shell, poly.buffer(-0.2, join_style=2).difference(upper_poly.buffer(0.1)), zt, "roof_membrane")
        _roof_props(B, poly.difference(upper_poly).buffer(-0.5), zt, S, rng, n, zt, True)
        z2 = _facade(B, upper_poly, zt, floors[-upper_n:], S_up, rng)
        _core(B.shell, upper_poly.buffer(-0.2, join_style=2), zt, z2, "core")
        _cap(B.shell, upper_poly.buffer(-0.2, join_style=2), z2, "roof_membrane")
        _roof_props(B, upper_poly, z2, S_up, rng, n, z2, False)
    else:
        _cap(B.shell, poly.buffer(-0.2, join_style=2), zt, "roof_membrane")
        _roof_props(B, poly, zt, S, rng, n, zt, False)
    return B
