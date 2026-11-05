"""街の生活感(走行車両/路駐/バス/タクシー/歩行者/自転車)を道路網と歩道から手続き配置する。決定論的(seed固定)。"""
import math
import random

import numpy as np
from shapely.geometry import Point

from .assemble import Inst

COLORS = ["white"] * 28 + ["black"] * 20 + ["silver"] * 18 + ["gray"] * 12 + ["blue"] * 6 + ["red"] * 5 + ["beige"] * 4 + ["pearl"] * 10 + ["navy"] * 5 + ["wine"] * 3
KINDS = ["sedan"] * 30 + ["hatch"] * 20 + ["suv"] * 16 + ["minivan"] * 14 + ["kei"] * 20
CAR_KINDS = (["sedan"] * 22 + ["hatch"] * 16 + ["suv"] * 14 + ["minivan"] * 13 + ["kei"] * 16 + ["wagon"] * 6 + ["van"] * 5 + ["keivan"] * 4 + ["truck_kei"] * 3)
POOL = {"wagon": ["white", "silver", "black", "gray", "pearl", "navy", "wine"], "van": ["white", "white", "silver", "pearl", "gray"], "keivan": ["white", "white", "silver", "sky", "yellow"],
        "truck_kei": ["white", "white", "silver", "sky"], "kei": COLORS + ["sky"] * 6 + ["yellow"] * 3}
PED_W = {3: dict(office=20, woman=14, casual=28, phone=8, elder=6, parasol=4, student=10, kid=4), 2: dict(office=10, woman=14, casual=32, phone=7, elder=10, parasol=4, student=12, kid=6),
         1: dict(office=3, woman=14, casual=30, phone=5, elder=18, parasol=3, student=12, kid=14), 0: dict(office=4, woman=14, casual=34, phone=6, elder=12, parasol=6, student=10, kid=10)}


def car_name(rng):
    k = rng.choice(CAR_KINDS)
    return f"{'' if k == 'truck_kei' else 'car_'}{k}_{rng.choice(POOL.get(k, COLORS))}"


HUMANS = "pedx"     # "anny": Anny 由来の人物(modules/lib_anny.py)を使う
ANNY_G = dict(office="office", woman="casual", casual="casual", phone="casual", elder="elder", parasol="casual", student="student", kid="kid")


def _ped(rng, rank=2, role=None):
    """歩行者モジュール名: 道路の格に応じて属性(会社員/女性/私服/スマホ/高齢者/日傘/学生/子供)の比率を変える"""
    wt = PED_W[3 if rank >= 3 else rank]
    g = rng.choices(list(wt), weights=list(wt.values()))[0]
    if HUMANS == "anny":
        from .modules import lib_anny as A
        ag = ANNY_G[g]
        if ag == "casual":
            r = rng.random()
            ag = "heavy" if r < 0.06 else "worker" if r < 0.14 else "casual"
        want = dict(walk=A.WALK, wait=A.WAIT, park=A.PARK).get(role)
        c = [n for n in A.NAMES[ag] if want is None or A.clip_of(n) in want]
        return rng.choice(c or A.NAMES[ag])
    from .modules.lib_city2 import PEDX
    return rng.choice(PEDX[g])


RANK = {"motorway": 6, "trunk": 5, "primary": 4, "secondary": 3, "tertiary": 2, "unclassified": 1, "residential": 1, "living_street": 0, "service": 0}


def _vehicle(rng, rank):
    r = rng.random()
    if rank >= 3 and r < 0.06:
        return "car_taxi"
    if rank >= 4 and r < 0.09:
        return rng.choice(["bus_city"] * 3 + ["bus_city_blue", "bus_city_white", "bus_city_red", "bus_coach", "bus_mini"])
    if rank >= 2 and r < 0.14:
        return rng.choice(["truck_box_white", "truck_box_silver", "truck_box_white", "truck_dump"])
    return car_name(rng)


def _frame(line, s):
    p, q = line.interpolate(s), line.interpolate(min(line.length, s + 1.0))
    if s + 1.0 > line.length:
        p, q = line.interpolate(max(0, s - 1.0)), line.interpolate(s)
    d = math.hypot(q.x - p.x, q.y - p.y) or 1
    return p.x, p.y, (q.x - p.x) / d, (q.y - p.y) / d


def moving_cars(w, rng):
    out = []
    T = w["T"]
    inner = w["area"]
    for e in w["edges"]:
        if e.kind != "drive" or e.level != 0 or e.prof is None:
            continue
        p = e.prof
        rank = RANK.get(e.tags["highway"], 0)
        L = e.line.length
        if L < 14:
            continue
        gap = {6: 18, 5: 16, 4: 18, 3: 22, 2: 28, 1: 45, 0: 70}.get(rank, 40)
        dirs = [(1, 1)] if p.oneway else [(1, 1), (-1, -1)]
        for sgn, side in dirs:
            for k in range(p.lanes):
                t = side * ((0 if p.oneway else p.median / 2) + (k + 0.5) * p.lane_w) if not p.oneway else (k - (p.lanes - 1) / 2) * p.lane_w
                s = rng.uniform(6, gap)
                while s < L - 6:
                    x, y, tx, ty = _frame(e.line, s)
                    cx, cy = x - ty * t, y + tx * t
                    if inner.contains(Point(cx, cy)):
                        name = _vehicle(rng, rank)
                        rot = math.atan2(ty, tx) + (0 if sgn > 0 else math.pi)
                        out.append(Inst(name, cx, cy, T(cx, cy) + 0.04, rot))
                    s += gap * rng.uniform(0.5, 2.2)
    return out


def parked_cars(w, rng):
    """細い道・生活道路の路肩に平行駐車(歩道側の車線端)"""
    out = []
    T = w["T"]
    for e in w["edges"]:
        if e.kind != "drive" or e.level != 0 or e.prof is None or RANK.get(e.tags["highway"], 0) > 2 or e.line.length < 25:
            continue
        p = e.prof
        for side in (1, -1):
            if rng.random() > 0.55:
                continue
            s = 8.0
            while s < e.line.length - 8:
                if rng.random() < 0.5:
                    x, y, tx, ty = _frame(e.line, s)
                    t = side * (p.half - 1.15)
                    cx, cy = x - ty * t, y + tx * t
                    name = car_name(rng)
                    out.append(Inst(name, cx, cy, T(cx, cy) + 0.04, math.atan2(ty, tx) + (0 if rng.random() < 0.5 else math.pi)))
                s += rng.uniform(5.4, 9.0)
    return out


def pedestrians(w, rng):
    out = []
    T = w["T"]
    sw = w["info"]["sw"]
    for e in w["edges"]:
        if e.level != 0 or e.line.length < 10:
            continue
        if e.kind == "drive" and e.prof is not None:
            rank = RANK.get(e.tags["highway"], 0)
            gap = {5: 12, 4: 12, 3: 14, 2: 20, 1: 36, 0: 70}.get(rank, 40)
            for side, swd in ((1, e.prof.sw_l), (-1, e.prof.sw_r)):
                if swd <= 0:
                    continue
                s = rng.uniform(3, gap)
                while s < e.line.length - 3:
                    x, y, tx, ty = _frame(e.line, s)
                    t = side * (e.prof.half + e.prof.curb_h * 0 + swd * rng.uniform(0.3, 0.8))
                    cx, cy = x - ty * t, y + tx * t
                    if sw.contains(Point(cx, cy)):
                        walk = rng.random() < 0.6
                        nm = _ped(rng, rank, "walk" if walk else "wait")
                        out.append(Inst(nm, cx, cy, T(cx, cy) + 0.14, math.atan2(ty, tx) - math.pi / 2 + (0 if rng.random() < 0.5 else math.pi)))
                        if rng.random() < 0.3:      # 連れ(2人組)
                            out.append(Inst(_ped(rng, rank, "walk" if walk else "wait"), cx + tx * 0.7, cy + ty * 0.7, T(cx, cy) + 0.14, out[-1].rot))
                        if rng.random() < 0.06:     # 自転車
                            out.append(Inst(rng.choice(["cyclist_commuter", "cyclist_student", "cyclist_mama", "scooter_rider_0", "scooter_rider_1"]), cx + tx * 1.5, cy + ty * 1.5, T(cx, cy) + 0.14, math.atan2(ty, tx) + (0 if rng.random() < 0.5 else math.pi)))
                    s += gap * rng.uniform(0.4, 1.8)
        elif e.kind == "walk" and e.tags["highway"] in ("pedestrian", "footway", "cycleway"):
            s = rng.uniform(2, 35)
            while s < e.line.length - 2:
                x, y, tx, ty = _frame(e.line, s)
                cx, cy = x - ty * rng.uniform(-0.8, 0.8), y + tx * rng.uniform(-0.8, 0.8)
                out.append(Inst(_ped(rng, 1, "walk"), cx, cy, T(cx, cy) + 0.04, math.atan2(ty, tx) - math.pi / 2 + (0 if rng.random() < 0.5 else math.pi)))
                s += rng.uniform(15, 60)
    # 横断歩道の待ち
    for a in w["info"]["arms"]:
        _, node, e, is_start, arm, D, (px, py, tx, ty, nlx, nly) = a
        if rng.random() < 0.5:
            for sgn in (1, -1):
                if rng.random() < 0.6:
                    cx, cy = px + nlx * sgn * (e.prof.half + 1.2) + tx * rng.uniform(-1.5, 1.5), py + nly * sgn * (e.prof.half + 1.2)
                    if sw.buffer(1).contains(Point(cx, cy)):
                        out.append(Inst(_ped(rng, 3, "wait"), cx, cy, T(cx, cy) + 0.14, math.atan2(-nly * sgn, -nlx * sgn) - math.pi / 2))
    # 公園・緑地: 散策する人
    for f in w["L"]["green"]:
        if f.geom.area > 1200 and w["area"].contains(f.geom.centroid):
            n = min(14, int(f.geom.area / 2500) + 1)
            for _ in range(n):
                pt = f.geom.representative_point() if rng.random() < 0.3 else None
                if pt is None:
                    x0, y0, x1, y1 = f.geom.bounds
                    for _ in range(12):
                        q = Point(rng.uniform(x0, x1), rng.uniform(y0, y1))
                        if f.geom.contains(q):
                            pt = q
                            break
                if pt is not None:
                    r0 = rng.uniform(0, 6.28)
                    out.append(Inst(_ped(rng, 0, "park"), pt.x, pt.y, T(pt.x, pt.y) + 0.06, r0))
                    if rng.random() < 0.35:     # 向かい合って立ち話する2人組
                        qx, qy = pt.x - math.sin(r0) * 0.95, pt.y + math.cos(r0) * 0.95
                        out.append(Inst(_ped(rng, 0, "park"), qx, qy, T(qx, qy) + 0.06, r0 + math.pi))
    return out


def elevated_cars(w, rng):
    out = []
    for e in w["edges"]:
        if e.id not in w["info"]["elev"] or e.kind != "drive":
            continue
        S, zs, p = w["info"]["elev"][e.id]
        L = e.line.length
        tot = p.lanes * (1 if p.oneway else 2)
        for k in range(tot):
            t = (k - (tot - 1) / 2) * p.lane_w
            s = rng.uniform(5, 30)
            while s < L - 5:
                x, y, tx, ty = _frame(e.line, s)
                cx, cy = x - ty * t, y + tx * t
                out.append(Inst(_vehicle(rng, 5), cx, cy, float(np.interp(s, S, zs)) + 0.03, math.atan2(ty, tx) + (0 if (p.oneway or k >= tot / 2) else math.pi)))
                s += rng.uniform(20, 60)
    return out


def boats(w, rng):
    """護岸の沖(水面)に係留したヨット/ボート、ところどころに水上バス。船首は岸と平行に"""
    out = []
    land = w["land"]
    polys = [land] if land.geom_type == "Polygon" else list(land.geoms)
    for g in polys:
        for ring in [g.exterior, *g.interiors]:
            if ring.length < 80:
                continue
            s = rng.uniform(10, 60)
            while s < ring.length - 10:
                p, q = ring.interpolate(s), ring.interpolate(min(ring.length, s + 3))
                dx, dy = q.x - p.x, q.y - p.y
                d = math.hypot(dx, dy) or 1
                ox, oy = dy / d, -dx / d                  # 水側
                r = rng.random()
                kind = "boat_ferry" if r < 0.05 else ("boat_yacht" if r < 0.5 else "boat_small")
                off = {"boat_ferry": 9.0, "boat_yacht": 5.5, "boat_small": 4.0}[kind]
                x, y = p.x + ox * off, p.y + oy * off
                if w["area"].contains(Point(x, y)) and not land.contains(Point(x, y)):
                    out.append(Inst(kind, x, y, 0.0, math.atan2(dy, dx) + (0 if rng.random() < 0.6 else math.pi)))
                s += rng.uniform(25, 90)
    return out


def park_amenities(w, rng):
    """公園・緑地: ベンチ+ゴミ箱(面積に応じて)、遊具(一部の公園)、パーゴラ(一部)、周囲の照明は furniture 側"""
    out = []
    T = w["T"]
    for f in w["L"]["green"]:
        g = f.geom
        if g.area < 1500 or not w["area"].contains(g.centroid):
            continue
        inner = g.buffer(-4)
        if inner.is_empty or inner.geom_type != "Polygon":
            continue
        x0, y0, x1, y1 = inner.bounds

        def pt():
            for _ in range(25):
                q = Point(rng.uniform(x0, x1), rng.uniform(y0, y1))
                if inner.contains(q):
                    return q
        for _ in range(min(8, int(g.area / 1800) + 1)):
            q = pt()
            if q:
                a = rng.uniform(0, 6.28)
                out.append(Inst(rng.choice(["bench_wood_back", "bench_metal", "bench_backless", "bench_arc"]), q.x, q.y, T(q.x, q.y) + 0.03, a))
                if rng.random() < 0.5:
                    out.append(Inst(rng.choice(["trash_can_sorted", "trash_can_round"]), q.x + math.cos(a) * 1.3, q.y + math.sin(a) * 1.3, T(q.x, q.y) + 0.03, a))
        if g.area > 4000 and rng.random() < 0.5:
            q = pt()
            if q:
                a = rng.uniform(0, 6.28)
                for k, nm in enumerate(("playground_slide", "playground_swing", "playground_sandpit")):
                    px, py = q.x + math.cos(a) * 5.5 * k, q.y + math.sin(a) * 5.5 * k
                    if inner.contains(Point(px, py)):
                        out.append(Inst(nm, px, py, T(px, py) + 0.03, a + (math.pi / 2 if k else 0)))
        if g.area > 6000 and rng.random() < 0.4:
            q = pt()
            if q:
                out.append(Inst("pergola_wood", q.x, q.y, T(q.x, q.y) + 0.03, rng.uniform(0, 6.28)))
    return out


def rail_fences(w, rng):
    """地上線路の両側(中心から3.2m)に緑のメッシュフェンスを2m間隔で"""
    out = []
    T = w["T"]
    for f in w["L"]["rail"]:
        t = f.tags
        if t.get("railway") not in ("rail", "light_rail", "subway") or t.get("bridge") or t.get("tunnel") or t.get("layer") not in (None, "0") or t.get("name") in ("ゆりかもめ",):
            continue
        g = f.geom.intersection(w["area"])
        for ln in ([g] if g.geom_type == "LineString" else list(getattr(g, "geoms", []))):
            if ln.geom_type != "LineString" or ln.length < 20:
                continue
            for side in (1, -1):
                s = 1.0
                while s < ln.length - 1:
                    x, y, tx, ty = _frame(ln, s)
                    cx, cy = x - ty * side * 3.2, y + tx * side * 3.2
                    out.append(Inst("fence_mesh_2m", cx, cy, T(cx, cy) + 0.03, math.atan2(ty, tx)))
                    s += 2.0
    return out


def utility_lines(w, rng):
    """東京の住宅街らしい電柱+架空線: 生活道路の片側に約35m間隔で電柱、隣り合う電柱を3線(+通信線)のカテナリで結ぶ"""
    from .modules.geom import Mesh
    from .world import sweep
    insts, wires = [], Mesh()
    T = w["T"]
    prof = lambda i: [(-0.008, -0.008, "wire"), (0.008, -0.008, "wire"), (0.008, 0.008, "wire"), (-0.008, 0.008, "wire")]
    for e in w["edges"]:
        if e.kind != "drive" or e.level != 0 or e.prof is None or RANK.get(e.tags["highway"], 0) > 1 or e.line.length < 50 or rng.random() > 0.45:
            continue
        side = rng.choice((1, -1))
        off = e.prof.half + 0.7
        pts = []
        s = rng.uniform(8, 20)
        while s < e.line.length - 8:
            x, y, tx, ty = _frame(e.line, s)
            q = (x - ty * side * off, y + tx * side * off)
            if w["area"].contains(Point(*q)):
                pts.append((q[0], q[1], tx, ty))
            s += rng.uniform(30, 40)
        for k, (x, y, tx, ty) in enumerate(pts):
            insts.append(Inst(rng.choice(["utility_pole_12m", "utility_pole_12m_trans", "utility_pole_10m_comm"]), x, y, T(x, y) + 0.02, rng.choice([0.0, math.pi / 2])))
            if k + 1 < len(pts):
                x1, y1 = pts[k + 1][0], pts[k + 1][1]
                L = math.hypot(x1 - x, y1 - y)
                for dz, dx in ((11.6, -0.7), (11.6, 0.0), (11.6, 0.7), (9.6, 0.4)):
                    nx, ny = -(y1 - y) / L, (x1 - x) / L
                    n = max(6, int(L / 3))
                    P, Z = [], []
                    z0, z1 = T(x, y) + dz, T(x1, y1) + dz
                    for i in range(n + 1):
                        t = i / n
                        P.append((x + (x1 - x) * t + nx * dx, y + (y1 - y) * t + ny * dx))
                        Z.append(z0 + (z1 - z0) * t - 4 * 0.012 * L * t * (1 - t))
                    sweep(wires, P, prof, Z)
    return insts, wires


def two_wheelers(w, rng):
    """車道の路肩寄りを走るスクーター/バイク(ごく少数)"""
    out = []
    T = w["T"]
    for e in w["edges"]:
        if e.kind != "drive" or e.level != 0 or e.prof is None or e.line.length < 40:
            continue
        rank = RANK.get(e.tags["highway"], 0)
        if rank < 1:
            continue
        p = e.prof
        s = rng.uniform(5, 60)
        while s < e.line.length - 6:
            if rng.random() < 0.5:
                x, y, tx, ty = _frame(e.line, s)
                side = rng.choice((1, -1))
                t = side * (p.half - 1.0)
                cx, cy = x - ty * t, y + tx * t
                if w["area"].contains(Point(cx, cy)):
                    out.append(Inst(rng.choice(["scooter_rider_0", "scooter_rider_1", "motorbike_rider"]), cx, cy, T(cx, cy) + 0.04, math.atan2(ty, tx) + (0 if side < 0 else math.pi)))
            s += rng.uniform(80, 220)
    return out


def build_props(w, seed=21, life=True):
    rng = random.Random(seed)
    out = list(w.get("props", []))
    pole_i, wire_m = utility_lines(w, rng)
    out += pole_i
    out += park_amenities(w, rng)
    out += rail_fences(w, rng)
    w["g"].add(wire_m)
    out += boats(w, rng)
    out += moving_cars(w, rng)
    out += parked_cars(w, rng)
    out += pedestrians(w, rng)
    out += elevated_cars(w, rng)
    out += two_wheelers(w, rng)
    if life:                                       # リアリズム強化B: 路面の経年・街の生活感(自販機/室外機/鉢/足場/電柱付属物/引込線…)
        from . import city_life, overlays
        out += overlays.road_overlays(w, random.Random(seed + 7))
        pts = [(i.x, i.y) for i in list(w.get("furn", [])) + list(w.get("veg", [])) + out]
        lf, drops = city_life.build_life(w, random.Random(seed + 8), pole_i, pts)
        out += lf
        w["g"].add(drops)
    return out
