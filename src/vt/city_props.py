"""街の生活感(走行車両/路駐/バス/タクシー/歩行者/自転車)を道路網と歩道から手続き配置する。決定論的(seed固定)。"""
import math
import random

import numpy as np
from shapely.geometry import Point

from .assemble import Inst

COLORS = ["white"] * 28 + ["black"] * 20 + ["silver"] * 18 + ["gray"] * 12 + ["blue"] * 6 + ["red"] * 5 + ["beige"] * 4
KINDS = ["sedan"] * 30 + ["hatch"] * 20 + ["suv"] * 16 + ["minivan"] * 14 + ["kei"] * 20
RANK = {"motorway": 6, "trunk": 5, "primary": 4, "secondary": 3, "tertiary": 2, "unclassified": 1, "residential": 1, "living_street": 0, "service": 0}


def _vehicle(rng, rank):
    r = rng.random()
    if rank >= 3 and r < 0.06:
        return "car_taxi"
    if rank >= 4 and r < 0.09:
        return "bus_city"
    if rank >= 2 and r < 0.14:
        return rng.choice(["truck_box_white", "truck_box_silver"])
    return f"car_{rng.choice(KINDS)}_{rng.choice(COLORS)}"


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
                    name = f"car_{rng.choice(KINDS)}_{rng.choice(COLORS)}"
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
            gap = {5: 22, 4: 20, 3: 22, 2: 30, 1: 55, 0: 90}.get(rank, 50)
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
                        nm = f"person_{'walk' if walk else 'stand'}_{rng.randrange(7)}" if rng.random() > 0.08 else rng.choice(["person_child_0", "person_child_1"])
                        out.append(Inst(nm, cx, cy, T(cx, cy) + 0.14, math.atan2(ty, tx) - math.pi / 2 + (0 if rng.random() < 0.5 else math.pi)))
                        if rng.random() < 0.3:      # 連れ(2人組)
                            out.append(Inst(f"person_walk_{rng.randrange(7)}", cx + tx * 0.7, cy + ty * 0.7, T(cx, cy) + 0.14, out[-1].rot))
                        if rng.random() < 0.06:     # 自転車
                            out.append(Inst("bicycle_plain", cx + tx * 1.5, cy + ty * 1.5, T(cx, cy) + 0.14, math.atan2(ty, tx) + (0 if rng.random() < 0.5 else math.pi)))
                    s += gap * rng.uniform(0.4, 1.8)
        elif e.kind == "walk" and e.tags["highway"] in ("pedestrian", "footway", "cycleway"):
            s = rng.uniform(2, 35)
            while s < e.line.length - 2:
                x, y, tx, ty = _frame(e.line, s)
                cx, cy = x - ty * rng.uniform(-0.8, 0.8), y + tx * rng.uniform(-0.8, 0.8)
                out.append(Inst(f"person_{'walk' if rng.random() < 0.7 else 'stand'}_{rng.randrange(7)}", cx, cy, T(cx, cy) + 0.04, math.atan2(ty, tx) - math.pi / 2 + (0 if rng.random() < 0.5 else math.pi)))
                s += rng.uniform(15, 60)
    # 横断歩道の待ち
    for a in w["info"]["arms"]:
        _, node, e, is_start, arm, D, (px, py, tx, ty, nlx, nly) = a
        if rng.random() < 0.5:
            for sgn in (1, -1):
                if rng.random() < 0.6:
                    cx, cy = px + nlx * sgn * (e.prof.half + 1.2) + tx * rng.uniform(-1.5, 1.5), py + nly * sgn * (e.prof.half + 1.2)
                    if sw.buffer(1).contains(Point(cx, cy)):
                        out.append(Inst(f"person_stand_{rng.randrange(7)}", cx, cy, T(cx, cy) + 0.14, math.atan2(-nly * sgn, -nlx * sgn) - math.pi / 2))
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
                    out.append(Inst(f"person_{rng.choice(['walk', 'stand'])}_{rng.randrange(7)}", pt.x, pt.y, T(pt.x, pt.y) + 0.06, rng.uniform(0, 6.28)))
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


def build_props(w, seed=21):
    rng = random.Random(seed)
    out = list(w.get("props", []))
    out += boats(w, rng)
    out += moving_cars(w, rng)
    out += parked_cars(w, rng)
    out += pedestrians(w, rng)
    out += elevated_cars(w, rng)
    return out
