"""地区タイプ別の街区ベース建物配置: rural(田園集落) / suburb(郊外住宅地) / town(中規模都市の幹線沿い) / roadside(ロードサイド店舗+駐車場+GS) / factory(町工場・物流) / plant(コンビナート)。
blocks.infill と同じ戻り値(features, pads, props, stats)。東京の既定(blocks.infill)は変更しない。city.build_world(district=...) から呼ばれる。"""
import math
import random

from shapely import affinity
from shapely.geometry import Point, Polygon
from shapely.ops import nearest_points, unary_union

from . import blocks
from .assemble import Inst
from .layers import Feature
from .modules.geom import Mesh
from .modules.registry import REG
from .styles_extra import RS_KEYS
from .world import fill

DISTRICTS = {
    "rural": dict(area=(300, 900), depth=34, sb=(2.5, 6.0), h=(3.4, 7.2), empty=0.14),
    "suburb": dict(area=(160, 380), depth=24, sb=(1.3, 3.2), h=(5.5, 9.0), empty=0.03),
    "town": dict(area=(260, 800), depth=36, sb=(0.6, 2.2), h=(7, 22), empty=0.0),
    "roadside": dict(area=(1100, 3200), depth=55, sb=(1.5, 3.0), h=(4.0, 8.0), empty=0.0),
    "factory": dict(area=(2800, 8500), depth=80, sb=(2.0, 4.5), h=(5.2, 12), empty=0.0),
    "plant": dict(area=(9000, 30000), depth=160, sb=(3.0, 6.0), h=(8, 15), empty=0.0),
}
HOUSE_W = {"rural": [("house_jp_kawara", .22), ("house_jp_mortar", .14), ("house_kominka", .1), ("house_maker_a", .18), ("house_maker_b", .14), ("house_maker_brick", .06), ("apt_wood2", .06), ("barn_tin", .1)],
           "suburb": [("house_maker_a", .3), ("house_maker_b", .24), ("house_maker_brick", .1), ("house_jp_mortar", .1), ("house_jp_kawara", .08), ("apt_wood2", .12), ("apartment", .06)]}
RS_W = [("conv", .2), ("drug", .1), ("family", .08), ("super", .08), ("home", .06), ("pachi", .05), ("car", .08), ("ramen", .06), ("shop100", .04), ("misc", .25)]
VEG_GARDEN = ["veg_kuromatsu_s_0", "veg_kuromatsu_m_0", "veg_tsuge_dome_r8", "veg_azalea_0_r8", "veg_sakura_s_0", "veg_kusunoki_s_0", "veg_shii_s_0", "veg_hanamizuki_s_0", "veg_tokaikaede_s_0", "veg_hydrangea_0_r75"]


def _veg(name):
    return name + "_summer" if name + "_summer" in REG else name


def rot_facing(ux, uy):
    """モジュールの+yを(ux,uy)へ向けるz回転"""
    return math.atan2(-ux, uy)


def _frame(poly):
    r = poly.minimum_rotated_rectangle
    c = list(r.exterior.coords)[:4]
    e1 = (c[1][0] - c[0][0], c[1][1] - c[0][1])
    e2 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
    l1, l2 = math.hypot(*e1), math.hypot(*e2)
    if l2 > l1:
        e1, e2, l1, l2 = e2, e1, l2, l1
    return r.centroid.x, r.centroid.y, (e1[0] / l1, e1[1] / l1), (e2[0] / l2, e2[1] / l2), l1, l2


def _front(lot, mask):
    """区画の道路側の単位ベクトルと道路までの距離"""
    c = lot.centroid
    p = nearest_points(c, mask)[1]
    d = math.hypot(p.x - c.x, p.y - c.y)
    return ((p.x - c.x) / (d or 1), (p.y - c.y) / (d or 1)), d


def _pick(items, rng):
    names, ws = zip(*items)
    return rng.choices(names, ws)[0]


def _put(props, name, x, y, z, rot, sx=1.0, sy=1.0, sz=1.0):
    if name in REG:
        props.append(Inst(name, x, y, z, rot, sx, sy, sz))


def _edge_run(props, name, p, q, zf, seg=3.6, skip=None, sz=1.0):
    """線分p→qに沿って部材(幅seg)を並べる。skip=(点, 半径)の近傍は空ける(門の位置)"""
    L = math.hypot(q[0] - p[0], q[1] - p[1])
    if L < 0.8:
        return
    n = max(1, round(L / seg))
    r = math.atan2(q[1] - p[1], q[0] - p[0])
    for i in range(n):
        t = (i + 0.5) / n
        x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        if skip and math.hypot(x - skip[0][0], y - skip[0][1]) < skip[1]:
            continue
        _put(props, name, x, y, zf(x, y), r, L / n / seg, 1.0, sz)


def _front_edges(lot, mask, reach):
    c = list(lot.exterior.coords)
    out = []
    for p, q in zip(c, c[1:]):
        mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        if math.hypot(q[0] - p[0], q[1] - p[1]) > 1.5 and mask.distance(Point(mid)) < reach:
            out.append((p, q))
    return out


def dress_house_lot(lot, foot, style, zf, mask, rng, props, sb, kind):
    """住宅区画の外構: 道路側の塀/生垣+門、カーポート、物置、庭木、(農家)土蔵"""
    wts = {"rural": [("fence_itabei", .22), ("fence_ikegaki", .25), ("fence_stone_wall", .1), ("fence_blockwall_low", .23), ("fence_blockwall", .2)],
           "suburb": [("fence_blockwall", .3), ("fence_ikegaki", .18), ("fence_blockwall_low", .34), ("fence_itabei", .1), ("fence_stone_wall", .08)]}[kind if kind in ("rural", "suburb") else "suburb"]
    fence = _pick(wts, rng)
    fr = _front_edges(lot, mask, sb + 4.0)
    gate = None
    if fr:
        p, q = max(fr, key=lambda e: math.dist(*e))
        gx, gy = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        gate = "gate_mon_yakui" if style in ("house_jp_kawara", "house_kominka") and rng.random() < 0.5 else "gate_post_modern"
        _put(props, gate, gx, gy, zf(gx, gy), math.atan2(q[1] - p[1], q[0] - p[0]))
        for p, q in fr:
            if fence == "fence_ikegaki":                                              # 生垣は植栽モジュール(葉アトラス)を使う
                _edge_run(props, rng.choice(["veg_hedge_tall_0", "veg_hedge_tall_1"]), p, q, zf, 2.0, ((gx, gy), 2.4))
            else:
                _edge_run(props, fence, p, q, zf, 3.6, ((gx, gy), 2.4))
    if style.startswith("house_maker") and fr and rng.random() < 0.5:
        p, q = fr[0]
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        c = lot.centroid
        ux, uy = c.x - mx, c.y - my
        d = math.hypot(ux, uy) or 1
        cx, cy = mx + ux / d * 3.6, my + uy / d * 3.6
        r = math.atan2(q[1] - p[1], q[0] - p[0])
        car = Polygon([(cx + math.cos(r) * a - math.sin(r) * b, cy + math.sin(r) * a + math.cos(r) * b) for a, b in ((-2.6, -2.7), (2.6, -2.7), (2.6, 2.7), (-2.6, 2.7))])
        if not car.intersects(foot.buffer(0.5)) and lot.contains(car):
            _put(props, "carport_alu", cx, cy, zf(cx, cy), r + (0 if rng.random() < 0.5 else math.pi))
            if rng.random() < 0.7:
                _put(props, rng.choice(["car_hatch_white", "car_kei_white", "car_sedan_silver", "car_kei_blue", "car_minivan_silver"]), cx, cy + 0.0, zf(cx, cy) + 0.04, r + math.pi / 2 * rng.choice([1, 1, -1]))
    free = lot.difference(foot.buffer(1.5)).buffer(-1.0)
    gp = [g for g in blocks._polys(free) if g.area > 12]
    for _ in range(rng.randint(1, 3 if kind == "rural" else 2)):
        if not gp:
            break
        g = rng.choice(gp)
        x0, y0, x1, y1 = g.bounds
        for _ in range(12):
            pt = Point(rng.uniform(x0, x1), rng.uniform(y0, y1))
            if g.contains(pt):
                _put(props, _veg(rng.choice(VEG_GARDEN)), pt.x, pt.y, zf(pt.x, pt.y), rng.random() * 6.28)
                break
    if gp and rng.random() < (0.3 if kind == "rural" else 0.15):
        g = max(gp, key=lambda g: g.area)
        pt = g.representative_point()
        _put(props, "shed_inaba", pt.x, pt.y, zf(pt.x, pt.y), rng.random() * 6.28)
    if style == "house_kominka" and gp and rng.random() < 0.5:
        g = max(gp, key=lambda g: g.area)
        pt = g.representative_point()
        _put(props, "bldg_kura", pt.x, pt.y, zf(pt.x, pt.y), rng.choice([0, math.pi / 2, math.pi, -math.pi / 2]))


def field_lot(lot, zf, rng, pad, props):
    """畑・空き地: 土/芝+(ビニールハウス)。"""
    fill(pad, lot, lambda x, y: zf(x, y) + 0.03, rng.choice(["soil", "grass", "soil"]), 8.0, False)
    if lot.area > 350 and rng.random() < 0.45:
        cx, cy, u, v, l1, l2 = _frame(lot)
        ang = math.atan2(u[0] * 0 + u[1], u[0])
        n = 0
        y_ = -l2 / 2 + 4
        while y_ + 6 < l2 / 2 - 1 and n < 6:
            x_ = -l1 / 2 + 3
            if l1 > 18:
                px, py = cx + v[0] * (y_ + 3) + u[0] * x_, cy + v[1] * (y_ + 3) + u[1] * x_
                foot = Polygon([(px + u[0] * a + v[0] * b, py + u[1] * a + v[1] * b) for a, b in ((0, -3), (12, -3), (12, 3), (0, 3))])
                if lot.buffer(-0.5).contains(foot):
                    _put(props, "greenhouse_vinyl", px, py, zf(px, py), ang - math.pi / 2)
                    n += 1
            y_ += 7.5


def rural_poles(w, props, rng, spacing=38.0):
    """農村の道沿いの木製電柱(片側)"""
    zf, area = w["T"], w["area"]
    for e in w["edges"]:
        if e.kind != "drive" or e.level != 0 or not e.line.intersects(area):
            continue
        L = e.line.length
        s = rng.uniform(5, spacing)
        while s < L:
            p, q = e.line.interpolate(s), e.line.interpolate(min(L, s + 1.0))
            dx, dy = q.x - p.x, q.y - p.y
            d = math.hypot(dx, dy) or 1
            off = (e.prof.half + 1.2) if e.prof is not None else 6.0
            x, y = p.x - dy / d * off, p.y + dx / d * off
            if area.contains(Point(x, y)):
                _put(props, "rural_utility_pole_wood", x, y, zf(x, y), rng.random() * 6.28)
            s += spacing * rng.uniform(0.9, 1.1)


# ------------------------------------------------------------------ ロードサイド
def gas_station(lot, u, zf, rng, pad, props):
    """ガソリンスタンド: 全面舗装+キャノピー+給油アイランド+価格看板+通気管+事務所(Featureを返す)。u=道路側の単位ベクトル"""
    cx, cy = lot.centroid.x, lot.centroid.y
    fill(pad, lot, lambda x, y: zf(x, y) + 0.03, "asphalt", 8.0, False)
    r = rot_facing(*u)
    ox, oy = -u[1], u[0]
    base = (cx - u[0] * 3.5, cy - u[1] * 3.5)
    z = zf(*base)
    _put(props, "gs_canopy", base[0], base[1], z, r)
    for side in (-1, 1):
        px, py = base[0] + ox * side * 3.5 + u[0] * 4.5, base[1] + oy * side * 3.5 + u[1] * 4.5
        _put(props, "gs_island", px, py, z + 0.02, r + math.pi / 2 * 0)
    rx, ry = cx + u[0] * 9 + ox * 9, cy + u[1] * 9 + oy * 9
    _put(props, "gs_price_pole", rx, ry, zf(rx, ry), r)
    for k in (-1, 1):
        vx, vy = cx - u[0] * 12 + ox * k * 2.0, cy - u[1] * 12 + oy * k * 2.0
        _put(props, "gs_vent_pipe", vx, vy, zf(vx, vy), r)
    ax, ay = cx + u[0] * 6 - ox * 11, cy + u[1] * 6 - oy * 11
    _put(props, "gs_air_station", ax, ay, zf(ax, ay), r)
    for n in range(rng.randint(1, 3)):
        qx, qy = cx + u[0] * 4.5 + ox * (2.0 + n * 3.2) * rng.choice([-1, 1]), cy + u[1] * 4.5 + oy * (2.0 + n * 3.2) * rng.choice([-1, 1])
        _put(props, rng.choice(["car_sedan_white", "car_kei_white", "car_suv_black", "car_hatch_silver"]), qx, qy, zf(qx, qy) + 0.04, r + math.pi / 2)
    c = (cx - u[0] * 15, cy - u[1] * 15)
    foot = Polygon([(c[0] + ox * a + u[0] * b, c[1] + oy * a + u[1] * b) for a, b in ((-6, -3.5), (6, -3.5), (6, 3.5), (-6, 3.5))])
    if lot.contains(foot):
        return Feature(0, foot, dict(building="yes", _top=4.0, _min=0.0, _hsrc="district", _style="rs_gs"))
    return None


def roadside_lot(lot, mask, zf, rng, pad, props, feats, uid):
    """ロードサイド区画: 奥に店舗、道路側に駐車場、角にポール看板。GSは全面舗装の専用レイアウト。"""
    u, d = _front(lot, mask)
    if lot.area > 1000 and rng.random() < 0.18:
        f = gas_station(lot.buffer(-0.5, join_style=2), u, zf, rng, pad, props)
        if f:
            f.id = uid
            feats.append(f)
            return "gs"
    fill(pad, lot, lambda x, y: zf(x, y) + 0.025, "asphalt", 8.0, False)                  # 敷地全面を舗装(空きを作らない)
    cx, cy, ax, ay, l1, l2 = _frame(lot)
    ext = max(abs((p[0] - cx) * u[0] + (p[1] - cy) * u[1]) for p in lot.exterior.coords)
    q = rng.uniform(0.0, 0.25) * ext
    ox, oy = -u[1], u[0]
    far = 500.0
    # 道路側の半平面(法線u, 位置 = 中心 + u*q)
    hp = Polygon([(cx + u[0] * q + ox * far, cy + u[1] * q + oy * far), (cx + u[0] * q - ox * far, cy + u[1] * q - oy * far),
                  (cx + u[0] * (q + far) - ox * far, cy + u[1] * (q + far) - oy * far), (cx + u[0] * (q + far) + ox * far, cy + u[1] * (q + far) + oy * far)])
    park, rear = lot.intersection(hp), lot.difference(hp)
    rear_p = [g for g in blocks._polys(rear) if g.area > 250]
    key = _pick(RS_W, rng)
    key = rng.choice([k for k in RS_KEYS if k not in ("conv_a", "conv_b", "conv_c", "drug_a", "drug_b")] + ["conv_a"]) if key == "misc" else {"conv": rng.choice(["conv_a", "conv_b", "conv_c"]), "drug": rng.choice(["drug_a", "drug_b"]), "family": rng.choice(["family_a", "family_b"]),
                                                                                                                                       "super": rng.choice(["super_a", "super_b"]), "home": rng.choice(["home_a", "home_b"]), "pachi": rng.choice(["pachi_a", "pachi_b"]),
                                                                                                                                       "car": rng.choice(["car_a", "car_b"]), "ramen": rng.choice(["ramen_a", "ramen_b"]), "shop100": rng.choice(["shop100_a", "shop100_b"])}[key]
    if rear_p:
        b = max(rear_p, key=lambda g: g.area)
        foot = b.buffer(-2.2, join_style=2)
        fp = [g for g in blocks._polys(foot) if g.area > 60]
        if fp:
            foot = max(fp, key=lambda g: g.area)
            cap = {"super": 3000, "home": 3500, "pachi": 2000}
            if foot.area > cap.get(key.split("_")[0], 700):
                foot = affinity.scale(foot, math.sqrt(cap.get(key.split("_")[0], 700) / foot.area), math.sqrt(cap.get(key.split("_")[0], 700) / foot.area))
            h = {"super": 7.0, "home": 7.0, "pachi": 8.0}.get(key.split("_")[0], 4.4 if key.startswith("family") else 4.2)
            feats.append(Feature(uid, foot, dict(building="yes", _top=h, _min=0.0, _hsrc="district", _style=f"rs_{key}")))
            fill(pad, b.difference(foot.buffer(0.5)), lambda x, y: zf(x, y) + 0.03, "asphalt", 8.0, False)
    if park.area > 150:
        m, ins = blocks.parking_lot(park.buffer(-0.4, join_style=2), zf, rng, uid)
        pad.add(m)
        props += ins
    # ポール看板/のぼり/自販機/EV充電器は道路側の角付近
    if not park.is_empty and park.area > 100:
        pk = REG_PYLON.get(key.split("_")[0], "rs_pylon_multi")
        pts = sorted(lot.exterior.coords, key=lambda p: -(p[0] - cx) * u[0] - (p[1] - cy) * u[1])[:2]
        px, py = (pts[0][0] * 0.85 + cx * 0.15, pts[0][1] * 0.85 + cy * 0.15)
        if lot.contains(Point(px, py)):
            _put(props, pk, px, py, zf(px, py), rot_facing(*u))
        for k in range(rng.randint(0, 2)):
            nx_, ny_ = px + ox * (3 + k * 2), py + oy * (3 + k * 2)
            if lot.contains(Point(nx_, ny_)):
                _put(props, "rs_nobori_flags", nx_, ny_, zf(nx_, ny_), rot_facing(*u))
        if rng.random() < 0.3:
            _put(props, "pk_sign_coin", px - ox * 3, py - oy * 3, zf(px, py), rot_facing(*u))
        if rng.random() < 0.2:
            _put(props, "rs_ev_charger", px + u[0] * -4, py + u[1] * -4, zf(px, py), rot_facing(*u))
    return key


REG_PYLON = {"conv": "rs_pylon_conv", "drug": "rs_pylon_drug", "family": "rs_pylon_family", "super": "rs_pylon_super", "home": "rs_pylon_home", "pachi": "rs_pylon_pachi", "car": "rs_pylon_car",
             "ramen": "rs_pylon_ramen", "shop100": "rs_pylon_shop100", "tire": "rs_pylon_tire", "bank": "rs_pylon_multi", "hosp": "rs_pylon_multi", "dental": "rs_pylon_multi"}


# ------------------------------------------------------------------ 工場・物流
def factory_lot(lot, mask, zf, rng, pad, props, feats, uid, big=False):
    """町工場/物流センター: 建物+ヤード(コンテナ/トレーラー/設備)+周囲フェンス。"""
    u, d = _front(lot, mask)
    foot = lot.buffer(-rng.uniform(3, 6), join_style=2)
    fp = [g for g in blocks._polys(foot) if g.area > 400]
    if not fp:
        return
    foot = max(fp, key=lambda g: g.area)
    kind = "logistics" if rng.random() < 0.4 else f"factory_tin_{rng.choice(['gray', 'blue', 'green', 'cream'])}"
    cx, cy = foot.centroid.x, foot.centroid.y
    k = rng.uniform(0.45, 0.65)
    bfoot = affinity.scale(foot, k, k + 0.1)
    bfoot = bfoot.intersection(foot)
    if bfoot.geom_type != "Polygon" or bfoot.area < 300:
        return
    # 建物を道路と反対(奥)に寄せる
    shift = (min(foot.bounds[2] - foot.bounds[0], foot.bounds[3] - foot.bounds[1]) * 0.18)
    bfoot = affinity.translate(bfoot, -u[0] * shift, -u[1] * shift).intersection(foot)
    if bfoot.geom_type != "Polygon" or bfoot.area < 300:
        return
    h = rng.uniform(9, 14) if kind == "logistics" else rng.uniform(4.6, 5.2)
    feats.append(Feature(uid, bfoot, dict(building="yes", _top=h, _min=0.0, _hsrc="district", _style=kind)))
    yard = lot.difference(bfoot.buffer(1.0)).buffer(-0.8)
    yp = [g for g in blocks._polys(yard) if g.area > 250]
    for g in yp:
        m, ins = blocks.yard_lot(g, zf, rng) if rng.random() < 0.6 else blocks.parking_lot(g, zf, rng, uid)
        pad.add(m)
        props += ins
    # 設備と車両
    c = list(bfoot.exterior.coords)
    longest = max(zip(c, c[1:]), key=lambda e: math.dist(*e))
    (p, q) = longest
    ang = math.atan2(q[1] - p[1], q[0] - p[0])
    nx_, ny_ = -(q[1] - p[1]), (q[0] - p[0])
    nl = math.hypot(nx_, ny_) or 1
    nx_, ny_ = nx_ / nl, ny_ / nl
    if bfoot.contains(Point((p[0] + q[0]) / 2 - nx_, (p[1] + q[1]) / 2 - ny_)):
        nx_, ny_ = -nx_, -ny_
    L = math.hypot(q[0] - p[0], q[1] - p[1])
    for i in range(rng.randint(1, 3)):
        t = rng.uniform(0.15, 0.85)
        x, y = p[0] + (q[0] - p[0]) * t + nx_ * 8, p[1] + (q[1] - p[1]) * t + ny_ * 8
        if lot.contains(Point(x, y)):
            _put(props, rng.choice(["log_trailer", "truck_box_white", "truck_box_silver"]), x, y, zf(x, y) + 0.05, ang + (0 if rng.random() < 0.5 else math.pi))
    if kind != "logistics":
        for name, pr in (("fac_silo", .35), ("fac_dust_collector", .35), ("fac_conveyor_gallery", .2), ("fac_gantry_crane", .3), ("pl_tank_fixed_s", .2), ("pl_pipe_ground", .3)):
            if rng.random() < pr:
                t = rng.uniform(0.1, 0.9)
                x, y = p[0] + (q[0] - p[0]) * t + nx_ * 14, p[1] + (q[1] - p[1]) * t + ny_ * 14
                if lot.buffer(-6).contains(Point(x, y)):
                    _put(props, name, x, y, zf(x, y), ang)
    ring = lot.buffer(-0.5, join_style=2)
    if ring.geom_type == "Polygon":
        cs = list(ring.exterior.coords)
        for a, b in zip(cs, cs[1:]):
            _edge_run(props, "fence_mesh_2m", a, b, zf, 2.0)


# ------------------------------------------------------------------ コンビナート
TANKS = [("pl_tank_fixed_s", 12.0), ("pl_tank_fixed_m", 20.0), ("pl_tank_fixed_l", 32.0), ("pl_tank_floating_m", 38.0), ("pl_tank_floating_l", 60.0), ("pl_sphere_tank", 16.0)]


def _tank_farm(poly, c, u, v, l1, l2, rng, props, zf):
    inner = poly.buffer(-9, join_style=2)
    if inner.is_empty:
        return
    cand = [t for t in TANKS if t[1] * 2.4 < min(l1, l2)]
    if not cand:
        return
    name, D = rng.choice(cand)
    sp = D * 1.25 + 10
    ru, rv = (l1 * 0.5 - D * 0.6), (l2 * 0.5 - D * 0.6)
    nu, nv = max(1, int(2 * ru // sp) + 1), max(1, int(2 * rv // sp) + 1)
    placed = []
    ang = math.atan2(u[1], u[0])
    for i in range(nu):
        for j in range(nv):
            a = -ru + (i * sp if nu > 1 else ru)
            b = -rv + (j * sp if nv > 1 else rv)
            x, y = c[0] + u[0] * a + v[0] * b, c[1] + u[1] * a + v[1] * b
            if inner.buffer(-D * 0.5).contains(Point(x, y)):
                nm = name if rng.random() < 0.8 else rng.choice(cand)[0]
                _put(props, nm, x, y, zf(x, y), rng.random() * 6.28)
                placed.append((x, y))
    if len(placed) < 2:
        return
    xs, ys = [p[0] for p in placed], [p[1] for p in placed]
    # 防液堤: 配置したタンクの外接矩形(u,v軸)
    us = [(p[0] - c[0]) * u[0] + (p[1] - c[1]) * u[1] for p in placed]
    vs = [(p[0] - c[0]) * v[0] + (p[1] - c[1]) * v[1] for p in placed]
    pad_ = D * 0.5 + 6
    u0, u1, v0, v1 = min(us) - pad_, max(us) + pad_, min(vs) - pad_, max(vs) + pad_
    P = lambda a, b: (c[0] + u[0] * a + v[0] * b, c[1] + u[1] * a + v[1] * b)
    for (a, b), (a2, b2) in (((u0, v0), (u1, v0)), ((u1, v0), (u1, v1)), ((u1, v1), (u0, v1)), ((u0, v1), (u0, v0))):
        _edge_run(props, "pl_bund_wall", P(a, b), P(a2, b2), zf, 6.0)
    for (a, b) in ((u0, (v0 + v1) / 2), (u1, (v0 + v1) / 2)):
        x, y = P(a, b)
        _put(props, "pl_bund_stairs", x, y, zf(x, y), ang + math.pi / 2)
    for k in range(len(placed) - 1):
        (x0, y0), (x1, y1) = placed[k], placed[k + 1]
        if math.hypot(x1 - x0, y1 - y0) < sp * 1.2:
            _edge_run(props, "pl_pipe_ground", (x0, y0 + 3), (x1, y1 + 3), zf, 6.0)
    for a, b in ((u0 - 4, v0 - 4), (u1 + 4, v1 + 4)):
        x, y = P(a, b)
        _put(props, "pl_light_tower", x, y, zf(x, y), 0.0)
        _put(props, "pl_fire_monitor", *P(a * 0.9, b * 0.9), zf(*P(a * 0.9, b * 0.9)), 0.0)


def _process_area(poly, c, u, v, l1, l2, rng, props, zf):
    ang = math.atan2(u[1], u[0])
    P = lambda a, b: (c[0] + u[0] * a + v[0] * b, c[1] + u[1] * a + v[1] * b)
    n = int((l1 - 20) // 6)
    for i in range(n):
        a = -(n * 6) / 2 + 3 + i * 6
        x, y = P(a, 0)
        nm = rng.choices(["pl_pipe_rack_a", "pl_pipe_rack_b", "pl_pipe_rack_riser", "pl_pipe_loop"], [.65, .15, .06, .14])[0]
        _put(props, nm, x, y, zf(x, y), ang)
    side_d = min(l2 / 2 - 8, 16)
    for side in (-1, 1):
        a = -(n * 6) / 2 + 6
        while a < (n * 6) / 2 - 6:
            kind = rng.choices(["col", "drum", "hx", "pump", "tank"], [.26, .16, .2, .24, .14])[0]
            off = side * (side_d if kind in ("col", "tank") else side_d * 0.55)
            x, y = P(a, off)
            if poly.buffer(-3).contains(Point(x, y)):
                if kind == "col":
                    nm = rng.choice(["pl_column_a", "pl_column_b", "pl_column_c"])
                    _put(props, nm, x, y, zf(x, y), rng.random() * 6.28)
                    a += 12
                elif kind == "drum":
                    _put(props, "pl_drum_horizontal", x, y, zf(x, y), ang)
                    _put(props, "pl_stairs_tower", *P(a + 6, off + side * 3), zf(*P(a + 6, off + side * 3)), ang)
                    a += 11
                elif kind == "hx":
                    _put(props, "pl_heat_exchanger", x, y, zf(x, y), ang)
                    a += 11
                elif kind == "pump":
                    _put(props, "pl_pump_skid", x, y, zf(x, y), ang)
                    _put(props, "pl_valve_group", *P(a + 4, off * 0.5), zf(*P(a + 4, off * 0.5)), ang)
                    _put(props, "pl_pipe_ground", *P(a + 2, off * 0.5 + side * 4), zf(*P(a + 2, off * 0.5 + side * 4)), ang)
                    a += 5
                else:
                    _put(props, "pl_tank_fixed_s", x, y, zf(x, y), 0.0)
                    a += 16
            else:
                a += 6
    # 目立つ構造物
    for nm, a, b in (("pl_stack_rw" if rng.random() < 0.5 else "pl_tank_fixed_m", -l1 / 2 + 10, l2 / 2 - 9), ("pl_flare_stack" if rng.random() < 0.5 else "pl_column_b", l1 / 2 - 10, -l2 / 2 + 10), ("pl_cooling_tower", l1 / 2 - 20, l2 / 2 - 8), ("pl_control_room", -l1 / 2 + 12, -l2 / 2 + 8),
                     ("pl_transformer", -l1 / 2 + 24, -l2 / 2 + 8), ("pl_loading_rack", 0, -l2 / 2 + 8), ("pl_stairs_tower", 10, side_d * 0.0 + 0)):
        x, y = P(a, b)
        if poly.buffer(-2).contains(Point(x, y)):
            _put(props, nm, x, y, zf(x, y), ang if nm not in ("pl_stack_rw", "pl_flare_stack") else 0.0)
    for a in range(int(-l1 / 2 + 15), int(l1 / 2 - 5), 40):
        for b in (-l2 / 2 + 4, l2 / 2 - 4):
            x, y = P(a, b)
            if poly.buffer(-2).contains(Point(x, y)):
                _put(props, "pl_light_tower", x, y, zf(x, y), 0.0)
        if rng.random() < 0.5:
            _put(props, "pl_pipeline_marker", *P(a + 3, l2 / 2 - 3), zf(*P(a + 3, l2 / 2 - 3)), 0.0)


def plant_lot(lot, zf, rng, pad, props):
    """コンビナート区画: 砂利敷き+タンクヤード(防液堤)またはプロセスエリア(配管ラック+塔槽類)+煙突/フレア+周囲フェンス。"""
    fill(pad, lot, lambda x, y: zf(x, y) + 0.03, "gravel", 8.0, False)
    cx, cy, u, v, l1, l2 = _frame(lot)
    layout = rng.choice(["tank", "process", "process", "mixed"]) if l1 > 70 and l2 > 45 else "tank"
    if layout == "tank" or l2 < 45:
        _tank_farm(lot, (cx, cy), u, v, l1, l2, rng, props, zf)
    elif layout == "process":
        _process_area(lot, (cx, cy), u, v, l1, l2, rng, props, zf)
    else:
        h = l1 * 0.45
        c1 = (cx - u[0] * (l1 / 2 - h / 2), cy - u[1] * (l1 / 2 - h / 2))
        c2 = (cx + u[0] * (h / 2 + 0), cy + u[1] * (h / 2 + 0))
        _tank_farm(lot, c1, u, v, h, l2, rng, props, zf)
        _process_area(lot, (cx + u[0] * l1 * 0.22, cy + u[1] * l1 * 0.22), u, v, l1 * 0.55, l2, rng, props, zf)
    ring = lot.buffer(-1.0, join_style=2)
    if ring.geom_type == "Polygon":
        cs = list(ring.exterior.coords)
        for a, b in zip(cs, cs[1:]):
            _edge_run(props, "fence_mesh_2m", a, b, zf, 2.0)


# ------------------------------------------------------------------ メイン
def infill(w, district, mode="infill", seed=7, log=print):
    """district別の建物/外構。戻り値はblocks.infillと同じ(features, pads, props, stats)"""
    rng = random.Random(seed)
    Z = DISTRICTS[district]
    zf = w["T"]
    free = blocks.free_area(w, mode)
    bks = [p for p in blocks._polys(free) if p.area > 150]
    info = w["info"]
    mask = unary_union([info["cw"].buffer(0.6), info["sw"].buffer(0.3)])
    feats, pad, props = [], Mesh(), []
    stats = dict(blocks=len(bks), lots=0)
    uid = 8_000_000_000
    for bk in bks:
        lots = blocks.split_lot(bk, rng, rng.uniform(*Z["area"]), Z["depth"])
        for lot in lots:
            stats["lots"] += 1
            uid += 1
            if district in ("rural", "suburb"):
                if rng.random() < Z["empty"] or lot.area < 120:
                    if lot.area > 120:
                        field_lot(lot, zf, rng, pad, props)
                        stats["field"] = stats.get("field", 0) + 1
                    continue
                style = _pick(HOUSE_W[district], rng)
                fill(pad, lot, lambda x, y: zf(x, y) + 0.03, rng.choice(["grass", "grass", "gravel", "soil"]), 8.0, False)   # 庭/敷地の地面
                sb = rng.uniform(*Z["sb"])
                foot = lot.buffer(-sb, join_style=2)
                fp = [g for g in blocks._polys(foot) if g.area > 50]
                if not fp:
                    continue
                foot = max(fp, key=lambda g: g.area)
                if style not in ("apartment",) and foot.area > 70:
                    k = rng.uniform(0.52, 0.8) if district == "rural" else rng.uniform(0.62, 0.85)
                    foot = affinity.scale(foot.minimum_rotated_rectangle, k, rng.uniform(0.55, 0.8)).intersection(foot)
                    if foot.geom_type != "Polygon" or foot.area < 45:
                        continue
                if style == "barn_tin":
                    foot = affinity.scale(foot, 0.7, 0.7)
                h = {"apartment": rng.uniform(10, 17), "apt_wood2": rng.uniform(5.6, 7.0), "barn_tin": rng.uniform(3.6, 5.0), "house_kominka": rng.uniform(3.4, 4.6)}.get(style, rng.uniform(*Z["h"]))
                feats.append(Feature(uid, foot, dict(building="house" if style.startswith("house") else "yes", _top=h, _min=0.0, _hsrc="district", _style=style)))
                dress_house_lot(lot, foot, style, zf, mask, rng, props, sb, district)
            elif district == "town":
                tag = rng.choices(["house_maker_a", "apartment", "zakkyo", "commercial", "house_jp_mortar", "office_tile", "apt_wood2"] + [f"rs_{rng.choice(RS_KEYS)}"], [.14, .2, .2, .15, .08, .08, .05, .1])[0]
                sb = rng.uniform(*Z["sb"])
                foot = lot.buffer(-sb, join_style=2)
                fp = [g for g in blocks._polys(foot) if g.area > 60]
                if not fp:
                    continue
                foot = max(fp, key=lambda g: g.area)
                h = rng.uniform(*Z["h"]) if tag in ("apartment", "zakkyo", "commercial", "office_tile") else rng.uniform(5.6, 8.5)
                if tag.startswith("rs_"):
                    h = 4.4
                feats.append(Feature(uid, foot, dict(building="yes", _top=h, _min=0.0, _hsrc="district", _style=tag)))
                if tag.startswith("house") or tag == "apt_wood2":
                    dress_house_lot(lot, foot, tag if tag.startswith("house") else "house_maker_a", zf, mask, rng, props, sb, "suburb")
            elif district == "roadside":
                k = roadside_lot(lot, mask, zf, rng, pad, props, feats, uid)
                stats[k.split("_")[0]] = stats.get(k.split("_")[0], 0) + 1
            elif district == "factory":
                factory_lot(lot, mask, zf, rng, pad, props, feats, uid)
            elif district == "plant":
                plant_lot(lot, zf, rng, pad, props)
    if district == "rural":
        rural_poles(w, props, rng)
    log(f"district {district}: blocks={stats['blocks']} lots={stats['lots']} buildings={len(feats)} props={len(props)} extra={ {k: v for k, v in stats.items() if k not in ('blocks', 'lots')} }")
    return dict(features=feats, pads=pad, props=props, stats=stats)
