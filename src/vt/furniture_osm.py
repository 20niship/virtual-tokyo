"""OSM(街灯/バス停/ベンチ/自販機/ポスト/駐輪/ガードレール/ボラード/電柱/広告 など)に沿った道路ファニチャの配置。
OSMに無い所は道路種別から規則で補う(ガードパイプ、ボラード、カーブミラー、サイネージ)。"""
import math
import random

import numpy as np
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

from .assemble import Inst
from .modules.geom import Mesh
from .modules.library import REG
from .roads import LEVEL_H
from .world import sweep

RANK = {"motorway": 6, "trunk": 5, "primary": 4, "secondary": 3, "tertiary": 2, "unclassified": 1, "residential": 1, "living_street": 0, "service": 0}


def facing_rot(dx, dy):
    return math.atan2(dy, dx) - math.pi / 2


class Ctx:
    def __init__(self, world, edges, info, cfg, seed):
        self.zf = world["zf"]
        self.area = world["area"]
        self.land = world["land"]
        self.cw = info["cw"]
        self.sw = info["sw"]
        self.info = info
        self.rng = random.Random(seed)
        self.out = []
        self.edges = [e for e in edges if e.level == 0 and e.line.geom_type == "LineString"]
        self.lines = [e.line for e in self.edges]
        self.tree = STRtree(self.lines) if self.lines else None
        self.elev = [(e, info["elev"][e.id]) for e in edges if e.id in info["elev"]]
        self.taken = {}

    def near(self, x, y, maxd=30.0, only=None):
        """最寄りのエッジ。(edge, 距離, 道路への単位ベクトル, 接線)"""
        if self.tree is None:
            return None
        p = Point(x, y)
        best = None
        for idx in self.tree.query(p.buffer(maxd)):
            e = self.edges[idx]
            if only and e.kind != only:
                continue
            d = e.line.distance(p)
            if d <= maxd and (best is None or d < best[1]):
                best = (e, d)
        if not best:
            return None
        e, d = best
        s = e.line.project(p)
        q = e.line.interpolate(s)
        q2 = e.line.interpolate(min(e.line.length, s + 0.8)) if s < e.line.length - 0.8 else e.line.interpolate(max(0.0, s - 0.8))
        tx, ty = (q2.x - q.x, q2.y - q.y)
        if s >= e.line.length - 0.8:
            tx, ty = -tx, -ty
        n = math.hypot(tx, ty) or 1
        tx, ty = tx / n, ty / n
        vx, vy = q.x - x, q.y - y
        vn = math.hypot(vx, vy)
        vx, vy = (vx / vn, vy / vn) if vn > 1e-6 else (-ty, tx)
        return e, d, (vx, vy), (tx, ty), s

    def z(self, x, y):
        on = self.sw.contains(Point(x, y))
        return self.zf(x, y) + (0.02 + 0.12 if on else 0.02)

    def put(self, name, x, y, rot, z=None, sx=1.0):
        if name not in REG:
            return False
        if not self.area.contains(Point(x, y)):
            return False
        self.out.append(Inst(name, x, y, self.z(x, y) if z is None else z, rot, sx))
        return True

    def free(self, x, y, r=0.8):
        k = (int(x // 4), int(y // 4))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for (px, py) in self.taken.get((k[0] + dx, k[1] + dy), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < r * r:
                        return False
        self.taken.setdefault(k, []).append((x, y))
        return True

    def off_road(self, x, y, near):
        """車道の中にあれば縁石の外側へ押し出す"""
        if near is None:
            return x, y
        e, d, (vx, vy), t, s = near
        if self.cw.buffer(-0.05).contains(Point(x, y)):
            half = e.prof.half if e.prof else 3.0
            q = e.line.interpolate(s)
            return q.x - vx * (half + 0.7), q.y - vy * (half + 0.7)
        return x, y


def _poi_modules(C, f, near):
    """OSMタグ→(モジュール名, 向き, オプション)。向きは道路側(v)へ前面を向ける"""
    t = f.tags
    rng = C.rng
    x, y = f.geom.x, f.geom.y
    e = near[0] if near else None
    v = near[2] if near else (math.cos(f.id % 6.28), math.sin(f.id % 6.28))
    tdir = near[3] if near else (1.0, 0.0)
    hw = t.get("highway")
    am = t.get("amenity")
    out = []
    if hw == "street_lamp":
        rank = RANK.get(e.tags["highway"], 0) if e is not None and e.kind == "drive" else -1
        if rank >= 4:
            nm = rng.choice(["light_cobra_12m_white", "light_led_flat_8m", "light_cobra_9m_dark"])
        elif rank >= 1:
            nm = rng.choice(["light_cobra_9m", "light_led_flat_8m", "light_old_mercury_9m"])
        elif rank == 0 and rng.random() < 0.6:
            nm = "light_led_flat_8m"
        else:
            nm = rng.choice(["light_postop_globe_4m", "light_postop_lantern_3m", "light_ped_low_3m"])
        rot = math.atan2(v[1], v[0]) if "cobra" in nm or "flat" in nm or "mercury" in nm else 0.0
        out.append((nm, rot))
    elif hw == "bus_stop":
        out.append(("bus_stop_post", facing_rot(-tdir[0] if True else 0, -tdir[1])))
        if t.get("shelter") == "yes" or t.get("covered") == "yes":
            out.append(("bldg_bus_shelter", math.atan2(tdir[1], tdir[0])))
    elif am == "bench":
        out.append((rng.choice(["bench_wood_back", "bench_metal", "bench_backless", "bench_arc"]), facing_rot(*v)))
    elif am == "vending_machine":
        out.append((rng.choice(["vending_machine", "vending_double"]), facing_rot(*v)))
    elif am in ("waste_basket", "waste_disposal"):
        out.append((rng.choice(["trash_can_sorted", "trash_can_round"]), facing_rot(*v)))
    elif am == "post_box":
        out.append(("post_box_red", facing_rot(*v)))
    elif am == "bicycle_parking":
        out.append(("bicycle_rack_u", math.atan2(tdir[1], tdir[0])))
    elif am == "bicycle_rental":
        out.append(("bike_share_dock", math.atan2(tdir[1], tdir[0])))
    elif am == "telephone":
        out.append(("phone_booth_green", facing_rot(*v)))
    elif am in ("drinking_water", "fountain"):
        out.append(("drinking_fountain", facing_rot(*v)))
    elif am == "clock":
        out.append(("clock_post", facing_rot(*v)))
    elif t.get("emergency") == "fire_hydrant":
        out.append(("hydrant_marker", facing_rot(*v)))
    elif t.get("man_made") == "street_cabinet":
        out.append((rng.choice(["street_cabinet_pillar", "street_cabinet_small"]), facing_rot(*v)))
    elif t.get("man_made") == "flagpole":
        out.append(("flagpole_8m", 0.0))
    elif t.get("tourism") == "information":
        out.append(("info_map_board", facing_rot(*v)))
    elif t.get("barrier") == "bollard":
        out.append((rng.choice(["bollard_fixed", "bollard_fixed", "bollard_white", "bollard_removable"]), 0.0))
    elif t.get("advertising") in ("board", "billboard", "totem", "poster_box"):
        out.append((f"billboard_roadside_{rng.choice([0, 3, 6, 9, 12, 15])}", facing_rot(-v[0], -v[1]) + math.pi))
    elif t.get("power") in ("pole", "tower", "portal"):
        out.append((rng.choice(["utility_pole_12m", "utility_pole_12m_trans", "utility_pole_10m_comm"]), rng.choice([0.0, math.pi / 2])))
    return out


def place_pois(C, X):
    rng = C.rng
    n = 0
    lamp_xy = []
    for f in X["pois"]:
        if not C.area.contains(f.geom):
            continue
        t = f.tags
        need_road = t.get("highway") in ("street_lamp", "bus_stop") or t.get("amenity") in ("bench", "vending_machine", "post_box", "waste_basket", "bicycle_parking", "telephone", "drinking_water", "clock", "bicycle_rental") or t.get("emergency") or t.get("man_made") == "street_cabinet" or t.get("tourism") == "information" or t.get("advertising")
        if t.get("highway") == "bus_stop" and (t.get("railway") or t.get("tram") == "yes") and False:
            continue
        near = C.near(f.geom.x, f.geom.y, 40.0 if need_road else 25.0)
        mods = _poi_modules(C, f, near)
        if not mods:
            continue
        x, y = f.geom.x, f.geom.y
        if t.get("highway") in ("bus_stop", "street_lamp") and near and near[0].kind == "drive":
            x, y = C.off_road(x, y, near)
        if not C.land.contains(Point(x, y)) and not C.sw.buffer(2).contains(Point(x, y)):
            continue
        if not C.free(x, y, 0.5):
            continue
        for nm, rot in mods:
            if C.put(nm, x, y, rot):
                n += 1
        if t.get("highway") == "street_lamp":
            lamp_xy.append((x, y))
    return n, lamp_xy


def place_barriers(C, X):
    """OSMのguard_rail/fenceに沿ってスパンを並べる。道路側に前面を向け、両端に終端、橋上(自前のパラペット)は除外"""
    cnt = 0
    elev_polys = [(e, ep, ep[2].half + 1.6) for e, ep in C.elev]
    for f in X["barriers"]:
        t = f.tags
        kind = t["barrier"]
        if kind not in ("guard_rail", "fence", "jersey_barrier") or not f.geom.intersects(C.area):
            continue
        ln = f.geom.intersection(C.area)
        parts = [ln] if ln.geom_type == "LineString" else [g for g in getattr(ln, "geoms", []) if g.geom_type == "LineString"]
        for g in parts:
            L = g.length
            if L < 2.0:
                continue
            on_bridge = t.get("bridge") in ("yes", "viaduct") or str(t.get("layer", "0")) not in ("0", "")
            span = 4.0 if kind == "guard_rail" else 4.0
            n = max(1, int(round(L / span)))
            step = L / n
            for i in range(n):
                s = (i + 0.5) * step
                p, p2 = g.interpolate(s), g.interpolate(min(L, s + 0.6)) if s + 0.6 < L else g.interpolate(max(0, s - 0.6))
                tx, ty = (p2.x - p.x, p2.y - p.y) if s + 0.6 < L else (p.x - p2.x, p.y - p2.y)
                d = math.hypot(tx, ty) or 1
                tx, ty = tx / d, ty / d
                P = Point(p.x, p.y)
                if on_bridge and any(ep_e.line.distance(P) < hw for ep_e, _, hw in elev_polys):
                    continue
                near = C.near(p.x, p.y, 25.0, "drive")
                nl = (-ty, tx)
                toward_road = nl
                if near is not None:
                    toward_road = near[2]
                flip = (toward_road[0] * nl[0] + toward_road[1] * nl[1]) < 0
                rot = math.atan2(ty, tx) + (math.pi if flip else 0.0)
                name = "guardrail_beam_4m" if kind == "guard_rail" else "ped_fence_4m"
                if kind == "jersey_barrier":
                    name = "concrete_barrier_nj_4m"
                if abs(step - 4.0) > 0.9:
                    name = {"guardrail_beam_4m": "guardrail_beam_2m"}.get(name, name)
                sx = step / REG[name]["W"]
                if C.put(name, p.x, p.y, rot, sx=sx):
                    cnt += 1
            if kind == "guard_rail" and L > 6:
                for s, sgn in ((0.0, 1), (L, -1)):
                    p, p2 = g.interpolate(s), g.interpolate(min(L, s + 0.8) if sgn > 0 else max(0, s - 0.8))
                    tx, ty = (p2.x - p.x) * sgn, (p2.y - p.y) * sgn
                    d = math.hypot(tx, ty) or 1
                    tx, ty = tx / d, ty / d
                    nl = (-ty, tx)
                    near = C.near(p.x, p.y, 25.0, "drive")
                    flip = near is not None and (near[2][0] * nl[0] + near[2][1] * nl[1]) < 0
                    ang = math.atan2(ty, tx)
                    # 終端は「ビームが続く側」へ向ける(終端の向き=外向き)
                    C.put("guardrail_terminal", p.x, p.y, ang + (math.pi if flip else 0.0) + math.pi)
    return cnt


def rule_guardpipes(C, X, edges, info):
    """OSMにガードレール無し & 歩道のある幹線の縁石沿いにガードパイプ(交差点付近と乗入れ部は空ける)"""
    rng = C.rng
    have = [f.geom for f in X["barriers"] if f.tags.get("barrier") == "guard_rail"]
    guard_tree = STRtree(have) if have else None
    clear = {}
    for a in info["arms"]:
        _, node, e, is_start, arm, D, fr = a
        clear[(e.id, is_start)] = D + 9.0
    n = 0
    for e in C.edges:
        if e.kind != "drive" or e.prof is None or RANK.get(e.tags["highway"], 0) < 4 or e.line.length < 40:
            continue
        p = e.prof
        s0 = clear.get((e.id, True), 6.0)
        s1 = e.line.length - clear.get((e.id, False), 6.0)
        for side, sw in ((1, p.sw_l), (-1, p.sw_r)):
            if sw <= 0 or rng.random() < 0.55:
                continue
            s = s0
            gap_next = rng.uniform(40, 90)
            while s < s1 - 4:
                if s > gap_next:           # 乗入れ/横断のための切れ目
                    s += rng.uniform(5, 9)
                    gap_next = s + rng.uniform(40, 90)
                    continue
                q, q2 = e.line.interpolate(s + 2), e.line.interpolate(min(e.line.length, s + 2.8))
                tx, ty = q2.x - q.x, q2.y - q.y
                d = math.hypot(tx, ty) or 1
                tx, ty = tx / d, ty / d
                nlx, nly = -ty, tx
                x, y = q.x + nlx * side * (p.half + 0.28), q.y + nly * side * (p.half + 0.28)
                if guard_tree is not None and any(g.distance(Point(x, y)) < 6 for g in [have[i] for i in guard_tree.query(Point(x, y).buffer(6))]):
                    s += 4
                    continue
                # 前面=歩道側(車道から見て外)ではなく車道側。ガードパイプは歩道側に面を向ける
                rot = math.atan2(ty, tx) + (math.pi if side > 0 else 0.0)
                if C.put("guardpipe_4m", x, y, rot - (0.0)):
                    n += 1
                s += 4
    return n


def rule_bollards(C, info):
    """横断歩道の歩道側の切り下げ脇に車止めポール(2本)。道路が主要なほど確率を高く"""
    rng = C.rng
    n = 0
    for a in info["arms"]:
        _, node, e, is_start, arm, D, (px, py, tx, ty, nlx, nly) = a
        p = e.prof
        for sgn, sw in ((1, p.sw_l), (-1, p.sw_r)):
            if sw < 1.8 or rng.random() > 0.12 + 0.06 * RANK.get(e.tags["highway"], 0):
                continue
            for dt in (-1.6, 1.6):
                x, y = px + nlx * sgn * (p.half + 0.9) + tx * dt, py + nly * sgn * (p.half + 0.9) + ty * dt
                if C.free(x, y, 0.8) and C.put(rng.choice(["bollard_fixed", "bollard_white"]), x, y, 0.0):
                    n += 1
    return n


def rule_curve_mirrors(C, info):
    """無信号のT字路: 側道(細い腕)の正面となる反対側にカーブミラー"""
    by = {}
    for a in info["arms"]:
        by.setdefault(a[1], []).append(a)
    n = 0
    for node, arms in by.items():
        if len(arms) != 3:
            continue
        rank = [RANK.get(a[2].tags["highway"], 0) for a in arms]
        if max(rank) >= 3:
            continue
        # 側道=他の2本と直交気味の腕
        dirs = [(a[6][2], a[6][3]) for a in arms]
        best = None
        for i, (tx, ty) in enumerate(dirs):
            others = [dirs[j] for j in range(3) if j != i]
            dot = abs(sum(o[0] * tx + o[1] * ty for o in others) / 2)
            if best is None or dot < best[0]:
                best = (dot, i)
        i = best[1]
        a = arms[i]
        tx, ty = dirs[i]
        thr = max(arms[j][2].prof.half for j in range(3) if j != i)
        x, y = node[0] - tx * (thr + 1.4), node[1] - ty * (thr + 1.4)
        if C.free(x, y, 1.5) and C.land.contains(Point(x, y)):
            C.put("curve_mirror_round", x, y, facing_rot(tx, ty))
            n += 1
    return n


def station_furniture(C, L):
    """駅の近く: デジタルサイネージ・案内図板・時計"""
    rng = C.rng
    n = 0
    for st in L.get("stations", []):
        if not C.area.contains(st.geom):
            continue
        near = C.near(st.geom.x, st.geom.y, 40.0)
        if not near:
            continue
        e, d, v, tdir, s = near
        for k, nm in enumerate(("digital_signage_vertical", "info_map_board", "clock_post")):
            x, y = st.geom.x + tdir[0] * (3 + k * 3), st.geom.y + tdir[1] * (3 + k * 3)
            if C.sw.contains(Point(x, y)) or C.land.contains(Point(x, y)):
                if C.free(x, y, 1.5):
                    C.put(nm, x, y, facing_rot(*v))
                    n += 1
    return n


def power_lines(C, X):
    """OSMの電線(power=line/minor_line)の頂点に電柱を立て、各スパンに3線のカテナリ曲線を張る"""
    wires = Mesh()
    cnt = 0
    for f in X["powerlines"]:
        g = f.geom.intersection(C.area)
        parts = [g] if g.geom_type == "LineString" else [x for x in getattr(g, "geoms", []) if x.geom_type == "LineString"]
        for ln in parts:
            cs = list(ln.coords)
            h = 12.0 if f.tags.get("power") == "minor_line" else 14.0
            for (x0, y0), (x1, y1) in zip(cs, cs[1:]):
                L = math.hypot(x1 - x0, y1 - y0)
                if L < 5:
                    continue
                for dx in (-0.7, 0.0, 0.7):
                    n = max(6, int(L / 3))
                    nx, ny = -(y1 - y0) / L, (x1 - x0) / L
                    pts, zs = [], []
                    z0 = C.zf(x0, y0) + h - 0.4; z1 = C.zf(x1, y1) + h - 0.4
                    for i in range(n + 1):
                        t = i / n
                        x, y = x0 + (x1 - x0) * t + nx * dx, y0 + (y1 - y0) * t + ny * dx
                        sag = 4 * 0.012 * L * t * (1 - t) * 1.0
                        pts.append((x, y)); zs.append(z0 + (z1 - z0) * t - sag)
                    sweep(wires, pts, lambda i: [(-0.008, -0.008, "wire"), (0.008, -0.008, "wire"), (0.008, 0.008, "wire"), (-0.008, 0.008, "wire")], zs)
            for (x, y) in cs:
                if C.free(x, y, 3.0) and C.put("utility_pole_12m" if f.tags.get("power") == "minor_line" else "utility_pole_12m_trans", x, y, 0.0, z=C.zf(x, y)):
                    cnt += 1
    return cnt, wires


def build_osm_furniture(L, X, world, edges, info, cfg, seed=11):
    C = Ctx(world, edges, info, cfg, seed)
    stats = {}
    stats["pois"], lamp_xy = place_pois(C, X)
    stats["barriers"] = place_barriers(C, X)
    stats["guardpipes"] = rule_guardpipes(C, X, edges, info)
    stats["bollards"] = rule_bollards(C, info)
    stats["mirrors"] = rule_curve_mirrors(C, info)
    stats["station"] = station_furniture(C, L)
    stats["poles"], wires = power_lines(C, X)
    return C.out, wires, lamp_xy, stats
