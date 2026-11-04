"""道路の手続き生成: RoadProfile → 道路グラフ → 交差点(隅切り) → 歩道/縁石/切り下げ → 路面標示/記号 → 高架道路(首都高)。"""
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import substring, unary_union

from .modules.geom import Mesh
from . import road_extras as rx
from .world import decal, fill, frames, ribbon, stripe, sweep

_stripe_raw = stripe

# 全体設定(地区ごとの倍率で上書きしやすいよう1か所に集約)
CFG = dict(seed=1, city_age=0.5, wetness=0.0, barrier_free_rate=0.9, tactile_rate=0.6, bike_lane_rate=0.25,
           parking_rate=0.1, bus_lane_rate=0.15, hump_rate=0.2, scramble_rate=0.25, escort_rate=0.35, bike_cross_rate=0.12, slow_mark_rate=0.3, crack_rate=1.0)
DRIVE = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link",
         "tertiary", "tertiary_link", "unclassified", "residential", "service", "living_street"}
WALK = {"footway", "pedestrian", "cycleway", "path"}
LEVEL_H = {1: 7.0, 2: 12.0, 3: 17.0, 4: 22.0, 5: 27.0}
BASE = {  # highway: (lane幅, 歩道幅, 既定の車線数/両方向計)
    "motorway": (3.5, 0.0, 4), "motorway_link": (3.5, 0.0, 1), "trunk": (3.25, 3.0, 4), "trunk_link": (3.25, 0.0, 1),
    "primary": (3.25, 3.0, 4), "primary_link": (3.0, 0.0, 1), "secondary": (3.0, 2.8, 2), "secondary_link": (3.0, 0.0, 1),
    "tertiary": (3.0, 2.5, 2), "tertiary_link": (3.0, 0.0, 1), "unclassified": (2.9, 2.0, 2), "residential": (2.75, 1.8, 2),
    "service": (2.5, 0.0, 1), "living_street": (2.5, 1.5, 1),
}
FIL = 4.5   # 隅切り半径


@dataclass
class Profile:
    lanes: int            # 片側車線数(一方通行なら全車線)
    lane_w: float
    oneway: bool
    sw_l: float           # 歩道幅(0=無し)
    sw_r: float
    curb_h: float
    median: float         # 中央分離帯幅(0=無し)
    median_kind: str
    bike: float           # 自転車レーン幅(片側, 0=無し)
    tactile: bool
    wear: float
    paving: str
    speed: int
    half: float = 0.0
    shoulder: float = 0.0    # 路肩・停車帯の幅(両側)
    parking: bool = False
    bus: bool = False

    def __post_init__(self):
        self.half = (self.lanes * (1 if self.oneway else 2) * self.lane_w) / 2 + self.median / 2 + self.bike + self.shoulder


def _jit(rng, v, rel):
    return v * rng.uniform(1 - rel, 1 + rel)


def make_profile(tags, rng, cfg, edge_key=0):
    """OSMタグ → 種別デフォルト → 乱数。検証用に vt_lanes/vt_sw/vt_bike/vt_median/vt_oneway/vt_shoulder/vt_bus タグで強制指定できる"""
    hw = tags["highway"]
    lane_w, sw, nl = BASE.get(hw, (3.0, 2.0, 2))
    oneway = tags.get("oneway") in ("yes", "1", "true") or hw in ("motorway", "motorway_link") or "link" in hw
    if "vt_oneway" in tags:
        oneway = tags["vt_oneway"] == "yes"
    try:
        n = int(float(tags.get("lanes", nl)))
    except ValueError:
        n = nl
    per_dir = max(1, n if oneway else max(1, n // 2))
    if "vt_lanes" in tags:
        per_dir = int(tags["vt_lanes"])
    lane_w = _jit(rng, lane_w, 0.06)
    s = tags.get("vt_sw") or tags.get("sidewalk", "")
    sw_eff = sw or (2.0 if "vt_sw" in tags else 0.0)
    has_l = has_r = sw_eff > 0
    if s in ("no", "none"):
        has_l = has_r = False
    elif s == "left":
        has_r = False
    elif s == "right":
        has_l = False
    elif s == "both":
        has_l = has_r = sw_eff > 0
    elif "vt_sw" not in tags and hw in ("residential", "unclassified", "living_street", "tertiary") and rng.random() < 0.18:
        has_l = False if rng.random() < 0.5 else has_l
        has_r = has_r if has_l else False if rng.random() < 0.5 else has_r
    w = lambda: min(6.0, max(1.5, _jit(rng, sw_eff, 0.3))) if sw_eff else 0
    sw_l, sw_r = (w() if has_l else 0.0), (w() if has_r else 0.0)
    if tags.get("junction") == "roundabout":
        sw_r = 0.0                 # 環道の右側(時計回りの中央島側)には歩道を付けない
    bf = rng.random() < cfg["barrier_free_rate"]
    curb = rng.choice([0.05, 0.05, 0.08]) if bf else rng.choice([0.12, 0.15, 0.18])
    median, mk = 0.0, "paint"
    if "vt_median" in tags:
        mk = tags["vt_median"]
        median = {"none": 0.0, "paint": 0.5, "planter": rng.uniform(1.8, 2.6), "barrier": 0.6}[mk]
        mk = "paint" if mk == "none" else mk
    elif not oneway and per_dir >= 2:
        mk = rng.choices(["paint", "planter", "barrier"], [0.55, 0.3, 0.15])[0]
        median = {"paint": 0.5, "planter": rng.uniform(1.4, 2.6), "barrier": 0.6}[mk]
    bike = 0.0
    if "vt_bike" in tags:
        bike = 1.2 if tags["vt_bike"] == "yes" else 0.0
    elif hw in ("primary", "secondary", "tertiary", "residential") and not oneway and (
            tags.get("cycleway") == "lane" or tags.get("cycleway:left") == "lane" or tags.get("cycleway:right") == "lane" or rng.random() < cfg["bike_lane_rate"]):
        bike = 1.2
    speed = {"motorway": 60, "trunk": 50, "primary": 50, "secondary": 40, "tertiary": 40}.get(hw, 30)
    try:
        speed = int(float(tags.get("maxspeed", speed)))
    except ValueError:
        pass
    # 路肩・停車帯(OSM parking:lane があれば優先)
    shoulder, parking = 0.0, False
    pk = [tags.get(k) for k in ("parking:lane:both", "parking:lane:left", "parking:lane:right", "parking:lane")]
    if "vt_shoulder" in tags:
        shoulder = float(tags["vt_shoulder"]); parking = shoulder >= 1.8
    elif any(v and v not in ("no", "no_parking", "no_stopping", "none", "separate") for v in pk):
        shoulder, parking = rng.choice([2.0, 2.0, 2.3]), True
    elif hw in ("residential", "unclassified", "tertiary", "secondary") and not oneway and rng.random() < cfg.get("parking_rate", 0.1):
        shoulder, parking = rng.choice([1.8, 2.0, 2.3]), True
    elif hw in ("trunk", "primary") and rng.random() < 0.25:
        shoulder = rng.choice([0.5, 0.75, 1.0])
    bus = (tags.get("vt_bus") == "yes" or tags.get("busway") in ("lane", "opposite_lane", "both") or any(k in tags for k in ("bus:lanes", "lanes:bus", "psv:lanes"))
           or (hw in ("trunk", "primary") and per_dir >= 2 and "vt_lanes" not in tags and rng.random() < cfg.get("bus_lane_rate", 0.15)))
    pav = rng.choices(["sidewalk_paver", "sidewalk_tile", "sidewalk_asphalt", "sidewalk_granite"], [0.38, 0.27, 0.25, 0.10])[0]
    return Profile(per_dir, lane_w, oneway, sw_l, sw_r, curb, median, mk, bike, rng.random() < cfg["tactile_rate"] and max(sw_l, sw_r) >= 2.0,
                   min(1, max(0, cfg["city_age"] + rng.gauss(0, 0.2))), pav, min(speed, 60) // 10 * 10, shoulder=shoulder, parking=parking, bus=bus)


@dataclass
class Edge:
    id: int
    line: LineString
    tags: dict
    kind: str
    level: int
    a: tuple = None
    b: tuple = None
    prof: Profile = None
    oneway_dir: int = 0   # +1: a→b のみ


def _key(p):
    return (round(p[0], 1), round(p[1], 1))


def level_of(tags):
    if tags.get("tunnel") in ("yes", "building_passage", "covered"):
        return -1
    try:
        lay = int(float(tags.get("layer", 0)))
    except ValueError:
        lay = 0
    if lay < 0:
        return -1
    if tags.get("bridge") not in (None, "no") or lay > 0:
        return max(1, lay)
    return 0


def build_edges(roads, area, cfg):
    rng = random.Random(cfg["seed"])
    ways = []
    for f in roads:
        t = f.tags
        hw = t["highway"]
        if hw not in DRIVE and hw not in WALK:
            continue
        lv = level_of(t)
        if lv < 0 or not f.geom.intersects(area) or f.geom.geom_type != "LineString":
            continue
        if hw in WALK and lv > 0:
            continue
        ways.append((f, lv))
    use = defaultdict(set)
    for f, lv in ways:
        for c in f.geom.coords:
            use[_key(c)].add(f.id)
    edges = []
    for f, lv in ways:
        cs = list(f.geom.coords)
        cuts = [0] + [i for i in range(1, len(cs) - 1) if len(use[_key(cs[i])]) >= 2] + [len(cs) - 1]
        for i0, i1 in zip(cuts, cuts[1:]):
            seg = cs[i0:i1 + 1]
            if len(seg) < 2:
                continue
            ln = LineString(seg)
            if ln.length < 0.5:
                continue
            kind = "drive" if f.tags["highway"] in DRIVE else "walk"
            e = Edge(len(edges), ln, f.tags, kind, lv, _key(seg[0]), _key(seg[-1]))
            if kind == "drive":
                e.prof = make_profile(f.tags, random.Random(f.id * 31 + i0), cfg)
                if e.prof.oneway:
                    e.oneway_dir = -1 if f.tags.get("oneway") == "-1" else 1
            edges.append(e)
    return edges


def _op(a, b, op):
    from shapely.validation import make_valid
    try:
        return getattr(a, op)(b)
    except Exception:
        try:
            return getattr(make_valid(a), op)(make_valid(b).buffer(0))
        except Exception:
            return a if op == "difference" else Polygon()


def diff(a, *bs):
    for b in bs:
        a = _op(a, b, "difference")
    return a


def inter(a, *bs):
    for b in bs:
        a = _op(a, b, "intersection")
    return a


def lift_fn(zf, off):
    return lambda x, y: zf(x, y) + off


def _polys(g):
    return [g] if g.geom_type == "Polygon" else [x for x in getattr(g, "geoms", []) if x.geom_type == "Polygon"]


def _curb_faces(mesh, piece, cw, zf, h, mat="concrete_tex"):
    """歩道ポリゴンの車道側境界に縁石の垂直面(車道側向き)を立てる"""
    inner = cw.buffer(0.05)
    for g in _polys(piece):
        for ring in [g.exterior, *g.interiors]:
            ring = ring.segmentize(3.0)
            cs = list(ring.coords)
            for i in range(len(cs) - 1):
                (x0, y0), (x1, y1) = cs[i][:2], cs[i + 1][:2]
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                if not inner.contains(Point(mx, my)):
                    continue
                dx, dy = x1 - x0, y1 - y0
                L = math.hypot(dx, dy) or 1
                nx, ny = dy / L, -dx / L
                if not cw.contains(Point(mx + nx * 0.15, my + ny * 0.15)):
                    nx, ny = -nx, -ny
                    if not cw.contains(Point(mx + nx * 0.15, my + ny * 0.15)):
                        continue
                z0, z1 = zf(x0, y0), zf(x1, y1)
                mesh.oriented([(x0, y0, z0 + h), (x0, y0, z0), (x1, y1, z1), (x1, y1, z1 + h)], (nx, ny, 0), mat,
                              [(0, h), (0, 0), (L, 0), (L, h)])


RANK = {"motorway": 6, "trunk": 5, "primary": 4, "secondary": 3, "tertiary": 2, "unclassified": 1, "residential": 1, "living_street": 0, "service": 0,
        "motorway_link": 3, "trunk_link": 3, "primary_link": 3, "secondary_link": 2, "tertiary_link": 2}
LAST = {}          # 直近の build_ground_roads が作った補助情報(plans/mid/…)を build_roads が info に載せる
HUMP_TAGS = ("hump", "table", "bump", "cushion")


def camber_fn(e, clear_a, clear_b, amp):
    """横断勾配(カマボコ断面): 中心線で+amp、縁石で0。交差点側(clear)に向けて0へ戻して隣接面と段差を作らない"""
    line, L, h = e.line, e.line.length, e.prof.half

    def f(x, y):
        p = Point(x, y)
        d = line.distance(p)
        if d >= h:
            return 0.0
        s = line.project(p)
        w = 1.0
        if clear_a > 0:
            w = min(w, s / clear_a)
        if clear_b > 0:
            w = min(w, (L - s) / clear_b)
        return amp * (1 - d / h) * max(0.0, w)
    return f


def lane_t(p, k):
    """接近レーンkの横位置(腕の座標系, 左が+)。k=0 が中央側(右折側)。双方向は縁石側が-、一方通行は車線が左右対称に並ぶ"""
    if p.oneway:
        return (p.lanes / 2 - 0.5 - k) * p.lane_w
    return -(p.median / 2 + (k + 0.5) * p.lane_w)


def approach_span(p):
    """接近側の走行部の横幅範囲(腕の座標系)"""
    if p.oneway:
        return -p.lanes * p.lane_w / 2, p.lanes * p.lane_w / 2
    return -(p.median / 2 + p.lanes * p.lane_w), -p.median / 2


def _gore_zones(inc):
    """リンク道路(ランプ)の分合流部: 本線とリンクの間にできる楔形(導流帯)を返す [(polygon, lineA, lineB)]"""
    out = []
    for node, lst in inc.items():
        links = [(e, s) for e, s in lst if "link" in e.tags["highway"]]
        mains = [(e, s) for e, s in lst if "link" not in e.tags["highway"]]
        if len(lst) != 3 or len(links) != 1 or not mains:
            continue
        le, ls = links[0]
        lo = le.line if ls else LineString(list(le.line.coords)[::-1])
        ld = rx.arm_dir(lo)
        best = None
        for me, ms in mains:
            mo = me.line if ms else LineString(list(me.line.coords)[::-1])
            md = rx.arm_dir(mo)
            cosang = md[0] * ld[0] + md[1] * ld[1]
            if best is None or cosang > best[0]:
                best = (cosang, me, mo, md)
        if best is None or best[0] < 0.5:
            continue
        _, me, mo, md = best
        Lg = min(34.0, mo.length * 0.9, lo.length * 0.9)
        if Lg < 12:
            continue
        sgn = 1 if (md[0] * ld[1] - md[1] * ld[0]) > 0 else -1       # リンクが本線の左(+)か右(-)か
        try:
            a = substring(mo, 0, Lg).offset_curve(sgn * me.prof.half)
            b = substring(lo, 0, Lg).offset_curve(-sgn * le.prof.half)
        except Exception:
            continue
        if a.geom_type != "LineString" or b.geom_type != "LineString":
            continue
        n0 = Point(node)
        if a.coords[0] != min(a.coords[0], a.coords[-1], key=lambda c: n0.distance(Point(c))):
            a = LineString(list(a.coords)[::-1])
        if b.coords[0] != min(b.coords[0], b.coords[-1], key=lambda c: n0.distance(Point(c))):
            b = LineString(list(b.coords)[::-1])
        poly = Polygon(list(a.coords) + list(b.coords)[::-1]).buffer(0)
        wend = Point(a.coords[-1]).distance(Point(b.coords[-1]))
        if poly.is_empty or poly.geom_type != "Polygon" or poly.area < 8 or not 1.5 < wend < 14:
            continue
        out.append((poly, a, b))
    return out


def build_ground_roads(edges, world, cfg, nodes_deg, rng):
    """ground(level0)の車道/歩道/縁石/中央分離帯、交差点、路面標示を生成"""
    zf = world["zf"]
    land = world["land"]
    mesh = Mesh()
    drive = [e for e in edges if e.kind == "drive" and e.level == 0]
    walk = [e for e in edges if e.kind == "walk" and e.level == 0]
    drive.sort(key=lambda e: -e.prof.half)
    inc = defaultdict(list)    # node -> [(edge, is_start)]
    for e in drive:
        inc[e.a].append((e, True)); inc[e.b].append((e, False))
    ra_nodes = {k for k, lst in inc.items() if any(e.tags.get("junction") == "roundabout" for e, _ in lst) and any(e.tags.get("junction") != "roundabout" for e, _ in lst)}
    # 0) 通行区分: 各接近路が進める方向 → 矢印・右折レーン長
    node_arms = {}
    for node, lst in inc.items():
        if len(lst) >= 3:
            node_arms[node] = [(e, s, e.line if s else LineString(list(e.line.coords)[::-1])) for e, s in lst]
    plans = {}
    for node, arms in node_arms.items():
        for me in arms:
            e, s, arm = me
            if e.tags.get("junction") == "roundabout":
                continue
            avail = rx.turn_avail(me, arms)
            arrows = rx.lane_arrows(e, s, avail, e.prof.lanes, RANK.get(e.tags["highway"], 0) >= 2, rng)
            rt = 28.0 if (e.prof.lanes >= 2 and arrows and arrows[0] == "arrow_right") else 0.0
            plans[(e.id, s)] = dict(avail=avail, arrows=arrows, rt=rt, node=node)
    # 1) 車道ポリゴン
    rib = {e.id: e.line.buffer(e.prof.half, cap_style=2, join_style=2) for e in drive}
    cw = unary_union(list(rib.values())).buffer(0)
    # 交差点の隅切り(ノード周辺だけに閉処理を適用: 平行道路の間を埋めない)
    fil = []
    for k, lst in inc.items():
        if len(lst) >= 3 or (len(lst) == 2 and abs(lst[0][0].prof.half - lst[1][0].prof.half) > 1.0):
            Rn = max(e.prof.half for e, _ in lst) + 2 * FIL
            fil.append(Point(k).buffer(Rn))
    if fil:
        near = unary_union(fil)
        closed = cw.buffer(FIL, join_style=1).buffer(-FIL, join_style=1)
        cw = unary_union([cw, inter(closed, near)]).buffer(0)
    gores = _gore_zones(inc)
    if gores:
        cw = unary_union([cw] + [g[0] for g in gores]).buffer(0)
    cw = inter(cw, world["area"])
    # 2) 横断歩道・停止線・切り下げの位置(OSMの footway=crossing があればそこへ合わせる)
    from shapely.strtree import STRtree
    xs = []
    if drive:
        tree = STRtree([e.line for e in drive])
        for c in walk:
            if c.tags.get("footway") != "crossing" or c.line.length < 3:
                continue
            for idx in tree.query(c.line):
                e2 = drive[int(idx)]
                g = e2.line.intersection(c.line)
                for q in ([g] if g.geom_type == "Point" else [q for q in getattr(g, "geoms", []) if q.geom_type == "Point"]):
                    xs.append([q, e2, False])
    cands = []
    ramps = []

    def ramp_candidates(e, P, tx, ty, nlx, nly):
        for sgn, sw in ((1, e.prof.sw_l), (-1, e.prof.sw_r)):
            if sw <= 0:
                continue
            ex, ey = P.x + nlx * sgn * e.prof.half, P.y + nly * sgn * e.prof.half
            if not cw.buffer(0.3).contains(Point(ex, ey)):
                continue
            ax, ay = tx * 0.9, ty * 0.9
            bx, by = nlx * sgn * 1.5, nly * sgn * 1.5
            R = Polygon([(ex - ax + nlx * sgn * 0.05, ey - ay + nly * sgn * 0.05), (ex + ax + nlx * sgn * 0.05, ey + ay + nly * sgn * 0.05),
                         (ex + ax + bx, ey + ay + by), (ex - ax + bx, ey - ay + by)])
            if cfg["barrier_free_rate"] > rng.random():
                ramps.append((R, (nlx * sgn, nly * sgn), (tx, ty), e.prof.curb_h, e.prof.tactile))

    shift = {}
    for node, lst in inc.items():
        if len(lst) < 3 or not world["area"].contains(Point(node)):
            continue
        if any("link" in e.tags["highway"] for e, _ in lst):
            continue          # ランプの分合流部には横断歩道を置かない(導流帯になる)
        for e, is_start in lst:
            if e.tags.get("junction") == "roundabout":
                continue
            arm = e.line if is_start else LineString(list(e.line.coords)[::-1])
            maxo = max([o.prof.half for o, _ in lst if o is not e] + [3.0])
            D = maxo + 0.6 * FIL + 0.8
            if arm.length < D + 8:
                continue
            best = None
            for rec in xs:
                if rec[1] is e and not rec[2]:
                    sp = arm.project(rec[0])
                    if D + 1.0 <= sp <= arm.length - 6 and abs(sp - (D + 2.0)) < 14 and (best is None or abs(sp - D - 2) < abs(best[0] - D - 2)):
                        best = (sp, rec)
            if best:
                best[1][2] = True
                D = best[0] - 2.0
                shift[(e.id, is_start)] = best[0]
            P = arm.interpolate(D + 2.0)
            Pa, Pb = arm.interpolate(D + 1.5), arm.interpolate(D + 2.5)
            tx, ty = Pb.x - Pa.x, Pb.y - Pa.y
            L = math.hypot(tx, ty) or 1
            tx, ty = tx / L, ty / L
            nlx, nly = -ty, tx
            cands.append(dict(node=node, e=e, is_start=is_start, arm=arm, D=D, frame=(P.x, P.y, tx, ty, nlx, nly), zebra=True, mid=False))
            ramp_candidates(e, P, tx, ty, nlx, nly)
    # OSMの横断歩道が交差点の腕に対応しなかったもの = 街区の途中の横断歩道(両側に停止線)
    mids = []
    for q, e, used in xs:
        L = e.line.length
        s = e.line.project(q)
        if used or e.prof.half > 10.5 or "link" in e.tags["highway"] or s < 20 or L - s < 20 or not world["area"].contains(q):
            continue
        if any(Point(q).distance(Point(m[0])) < 10 for m in mids):
            continue
        mids.append((q.coords[0], e, s))
        for fwd, zebra in ((True, True), (False, False)):
            arm = substring(e.line, s, L) if fwd else LineString(list(substring(e.line, 0, s).coords)[::-1])
            Pa, Pb = arm.interpolate(0), arm.interpolate(1.0)
            tx, ty = Pb.x - Pa.x, Pb.y - Pa.y
            Ld = math.hypot(tx, ty) or 1
            tx, ty = tx / Ld, ty / Ld
            nlx, nly = -ty, tx
            cands.append(dict(node=None, e=e, is_start=fwd, arm=arm, D=-2.0, frame=(Pa.x, Pa.y, tx, ty, nlx, nly), zebra=zebra, mid=True))
            if zebra:
                ramp_candidates(e, Pa, tx, ty, nlx, nly)
    # 交差点側の標示開始位置(停止線の先から)
    node_clear = {}
    for node, lst in inc.items():
        if len(lst) >= 3:
            for e, is_start in lst:
                maxo = max([o.prof.half for o, _ in lst if o is not e] + [3.0])
                node_clear[(e.id, is_start)] = 0.0 if e.tags.get("junction") == "roundabout" else max(maxo + 0.6 * FIL + 0.8 + 5.5, shift.get((e.id, is_start), 0) + 6.0)
    # 材質: 車道は幅員の広い順に区間ごとに(老朽化=wearで補修パッチ入りテクスチャ)。横断勾配(カマボコ断面)を頂点高さへ反映
    cams = {}
    for e in drive:
        amp = min(0.04, random.Random(e.id * 131 + cfg["seed"]).uniform(0.012, 0.02) * e.prof.half) if e.prof.half > 2.5 else 0.0
        cams[e.id] = camber_fn(e, node_clear.get((e.id, True), 0.0), node_clear.get((e.id, False), 0.0), amp) if amp > 0 else (lambda x, y: 0.0)
    acc = Polygon()
    for e in drive:
        piece = diff(inter(rib[e.id], cw), acc)
        if piece.is_empty:
            continue
        acc = unary_union([acc, piece])
        cz = cams[e.id]
        fill(mesh, piece, lambda x, y, cz=cz: zf(x, y) + 0.02 + cz(x, y), "asphalt_worn" if e.prof.wear > 0.55 else "asphalt", 5.0, True, tol=0.012)
    rest = diff(cw, acc)
    if not rest.is_empty:
        fill(mesh, rest, lift_fn(zf, 0.02), "asphalt", 6.0, False)
    cut_u = Polygon()
    pieces = []
    # 3) 歩道(左右別・幅/高さ/舗装が区間ごとに変わる)
    swacc = Polygon()
    base_cw = cw
    for e in drive:
        for sgn, sw in ((1, e.prof.sw_l), (-1, e.prof.sw_r)):
            if sw <= 0:
                continue
            h = e.prof.half
            try:
                band = e.line.buffer(sgn * (h + sw), single_sided=True, cap_style=2, join_style=2)
            except Exception:
                continue
            piece = inter(diff(band, base_cw, swacc, cut_u), land, world["area"])
            piece = unary_union([g for g in _polys(piece) if g.area > 0.4]) if not piece.is_empty else piece
            if piece.is_empty:
                continue
            swacc = unary_union([swacc, piece])
            pieces.append((piece, e.prof.curb_h, e.prof.paving))
    # 交差点の角の歩道(隅切り部の穴埋め)
    for node, lst in inc.items():
        if len(lst) < 3:
            continue
        if not all((e.prof.sw_l > 0 and e.prof.sw_r > 0) for e, _ in lst):
            continue
        Rn = max(e.prof.half + max(e.prof.sw_l, e.prof.sw_r) for e, _ in lst) + FIL
        patch = diff(inter(Point(node).buffer(Rn), base_cw.buffer(max(e.prof.sw_l for e, _ in lst) + 0.5)), base_cw, swacc, cut_u)
        patch = inter(patch, land)
        if patch.is_empty or patch.area < 0.5:
            continue
        e0 = lst[0][0]
        swacc = unary_union([swacc, patch])
        pieces.append((patch, e0.prof.curb_h, e0.prof.paving))
    # 歩行者専用道(footway/pedestrian/cycleway): 幅は種別から、車道/歩道と重ならない部分
    for e in walk:
        w = {"pedestrian": 4.0, "footway": 2.0, "cycleway": 2.5, "path": 1.5}.get(e.tags["highway"], 2.0)
        w = _jit(rng, w, 0.2)
        if e.tags.get("footway") == "crossing":
            continue
        piece = inter(diff(e.line.buffer(w / 2, cap_style=2), base_cw, swacc), land, world["area"])
        if piece.is_empty or piece.area < 0.5:
            continue
        swacc = unary_union([swacc, piece])
        fill(mesh, piece, lift_fn(zf, 0.04), "sidewalk_asphalt" if e.tags["highway"] == "cycleway" else "sidewalk_paver", 6.0, False)
    # 4) 切り下げ: 歩道に十分重なる候補だけ採用し、歩道から抜いてスロープを入れる
    sw_all = unary_union([p for p, _, _ in pieces]) if pieces else Polygon()
    ok = []
    for R, n, tt, ch, tact in ramps:
        if inter(R, sw_all).area > 0.6 * R.area and inter(R, base_cw).area < 0.15 * R.area:
            ok.append((R, n, tt, ch, tact))
    cut_u = unary_union([r[0] for r in ok]) if ok else Polygon()
    for piece, ch, pav in pieces:
        piece = diff(piece, cut_u)
        if piece.is_empty:
            continue
        fill(mesh, piece, lift_fn(zf, 0.02 + ch), pav, 6.0, False)
        _curb_faces(mesh, piece, base_cw, lambda x, y: zf(x, y) + 0.02, ch)
    for R, (nx, ny), (tx, ty), ch, tact in ok:
        _ramp(mesh, R, (nx, ny), ch, zf, tact)
    # 5) 区間ごとの標示・ハンプ・排水・劣化 / 交差点の標示・導流帯・誘導線・スクランブル
    zm = lift_fn(zf, 0.02)   # 標示は舗装面(+0.02)の上に載せる
    zme = {e.id: (lambda x, y, e=e: zm(x, y) + cams[e.id](x, y)) for e in drive}
    mid_s = defaultdict(list)
    for _q, _e, _s in mids:
        mid_s[_e.id].append(_s)
    for e in drive:
        _edge_markings(mesh, e, zme[e.id], node_clear, rng, cfg, plans, mid_s.get(e.id, []))
    ctx = dict(plans=plans, ra_nodes=ra_nodes)
    for c in cands:
        _crossing(mesh, c, zme[c["e"].id], rng, cfg, plans.get((c["e"].id, c["is_start"])), ctx)
    for poly, a, b in gores:     # 導流帯(分合流部の楔)
        rx.zebra_zone(mesh, poly, zm)
    by_node = defaultdict(list)
    for c in cands:
        if c["node"] is not None:
            by_node[c["node"]].append(c)
    for node, cs in by_node.items():
        scr = len(cs) == 4 and all(RANK.get(c["e"].tags["highway"], 0) >= 3 for c in cs) and rng.random() < cfg.get("scramble_rate", 0.25)
        # 右折誘導線: 右折専用レーンから最も右方向の出口腕へ(スクランブル交差点では引かない)
        for c in ([] if scr else cs):
            pl = plans.get((c["e"].id, c["is_start"]))
            if not pl or not pl["rt"] or "right" not in pl["avail"]:
                continue
            tA = rx.arm_dir(c["arm"])
            bestB, bang = None, 1e9
            # 右折=接近の進行方向(-tA)から時計回りに約90°の腕
            for o in cs:
                if o is c:
                    continue
                if o["e"].prof.oneway and (o["e"].oneway_dir == 1) != o["is_start"]:
                    continue
                tB = rx.arm_dir(o["arm"])
                hx, hy = -tA[0], -tA[1]
                ang = math.degrees(math.atan2(hx * tB[1] - hy * tB[0], hx * tB[0] + hy * tB[1]))
                if -160 <= ang < -22 and abs(ang + 90) < bang:
                    bestB, bang = o, abs(ang + 90)
            if bestB is not None:
                pB = bestB["e"].prof
                tB_signed = (pB.median / 2 + pB.lane_w / 2) if not pB.oneway else -(pB.lanes / 2 - 0.5) * pB.lane_w
                rx.guide_line(mesh, dict(arm=c["arm"], D=c["D"], t=lane_t(c["e"].prof, 0)), dict(arm=bestB["arm"], D=bestB["D"], t=tB_signed), zm)
        # スクランブル(4方向の幹線のみ、一部)
        if scr:
            rx.scramble(mesh, [(c["frame"][0], c["frame"][1], c["frame"][2], c["frame"][3], c["frame"][4], c["frame"][5], c["e"].prof.half) for c in cs], zm)
    deco = [("cross", c["node"], c["e"], c["is_start"], c["arm"], c["D"], c["frame"]) for c in cands if not c["mid"]]
    LAST.clear()
    LAST.update(plans=plans, mid=[(c["e"], c["frame"]) for c in cands if c["mid"] and c["zebra"]], gores=[g[0] for g in gores], cams=cams)
    return mesh, cw, swacc, deco


def _ramp(mesh, R, n, ch, zf, tactile):
    """切り下げ: 車道側(縁)が0.02、歩道側が歩道高ch。両側は三角の壁(歩道側を向く)"""
    pts = list(R.exterior.coords)[:4]
    nx, ny = n
    # 縁に近い2点(法線の逆方向に近い=車道側)を求める
    d = [(p[0] * nx + p[1] * ny, p) for p in pts]
    d.sort()
    near, far = [p for _, p in d[:2]], [p for _, p in d[2:]]
    zN = lambda p: zf(p[0], p[1]) + 0.02
    zF = lambda p: zf(p[0], p[1]) + 0.02 + ch
    # 上面
    q = [(near[0][0], near[0][1], zN(near[0])), (near[1][0], near[1][1], zN(near[1])), (far[1][0], far[1][1], zF(far[1])), (far[0][0], far[0][1], zF(far[0]))]
    # near[i]とfar[i]の対応: 近い方の点同士で並べる
    far.sort(key=lambda p: (p[0] - near[0][0]) ** 2 + (p[1] - near[0][1]) ** 2)
    q = [(near[0][0], near[0][1], zN(near[0])), (near[1][0], near[1][1], zN(near[1])), (far[1][0], far[1][1], zF(far[1])), (far[0][0], far[0][1], zF(far[0]))]
    mesh.oriented(q, (0, 0, 1), "sidewalk_asphalt", [(0, 0), (1.8, 0), (1.8, 1.5), (0, 1.5)])
    # 両側の壁(スロープの側面)
    for i in (0, 1):
        a, b = (near[i][0], near[i][1], zN(near[i])), (far[i][0], far[i][1], zF(far[i]))
        a0, b0 = (a[0], a[1], a[2] - 0.0), (b[0], b[1], b[2])
        a1, b1 = (a[0], a[1], a[2] + (ch if False else 0)), b0
        w = [(a[0], a[1], a[2]), (b[0], b[1], b[2]), (b[0], b[1], b[2] - 0.0)]
        # 側面は歩道天端(ch)までの三角: a(低) b(高) と b直下の歩道天端
        tri = [(a[0], a[1], a[2]), (b[0], b[1], b[2]), (a[0], a[1], a[2] + ch)]
        # 外向き(スロープの外側へ)
        other = near[1 - i]
        out = (a[0] - other[0], a[1] - other[1], 0)
        mesh.oriented([(a[0], a[1], a[2]), (b[0], b[1], b[2]), (b[0], b[1], b[2] + 0.0), (a[0], a[1], a[2])][:3], out, "concrete_tex")
        mesh.oriented([(a[0], a[1], a[2]), (b[0], b[1], b[2]), (a[0], a[1], a[2] + ch)], out, "concrete_tex")
    # 点状ブロック(警告)を縁側0.6mに
    cx = sum(p[0] for p in near) / 2; cy = sum(p[1] for p in near) / 2
    if tactile or True:
        ang = math.atan2(-ny, -nx)   # 縁→歩道方向の逆(進行=車道へ向く)
        decal(mesh, cx + nx * 0.4, cy + ny * 0.4, ang, 1.5, 0.6, "decal_tbs_dot", zf, 0.04 + ch * 0.2)


def _crossing(mesh, c, zf, rng, cfg, plan, ctx):
    """1つの腕の横断歩道・停止線(ゆずれ線)・路面矢印・右折レーンの繰返し矢印・予告標示・減速/ランブル・エスコート・自転車横断帯"""
    e, is_start, arm, D = c["e"], c["is_start"], c["arm"], c["D"]
    px, py, tx, ty, nlx, nly = c["frame"]
    p = e.prof
    h = p.half
    rank = RANK.get(e.tags["highway"], 0)
    yield_ = c["node"] in ctx["ra_nodes"]
    # ゼブラ(縞0.45m/空き0.45m, 長さ4m)。街区途中の横断歩道は片側だけが描く
    if c["zebra"]:
        n = int((2 * h - 0.6) / 0.9)
        t0 = -(n * 0.9 - 0.45) / 2
        for k in range(n):
            t = t0 + k * 0.9 + 0.225
            a = (px + nlx * t - tx * 2.0, py + nly * t - ty * 2.0); b = (px + nlx * t + tx * 2.0, py + nly * t + ty * 2.0)
            stripe(mesh, LineString([a, b]), 0, 0.45, 4, 0, "paint_road_white", zf, 0.012)
        if rank >= 3 and rng.random() < cfg.get("escort_rate", 0.35):
            rx.escort_zone(mesh, px, py, tx, ty, nlx, nly, h, zf)
        if (p.bike > 0 and rng.random() < 0.7) or (rank >= 4 and rng.random() < cfg.get("bike_cross_rate", 0.12)):
            rx.bike_crossing(mesh, px, py, tx, ty, nlx, nly, h, zf, -3.1)
    # 停止線(接近側=進行方向左側=外向き接線に対して右)。一方通行で出ていく向きなら無し
    approach = (not p.oneway) or ((e.oneway_dir == 1) != is_start)
    if not approach:
        return
    t_lo, t_hi = approach_span(p)
    t_lo = max(t_lo, -(h - p.shoulder - p.bike)) if not p.oneway else t_lo
    sx, sy = px + tx * 3.2, py + ty * 3.2
    a = (sx + nlx * t_hi, sy + nly * t_hi); b = (sx + nlx * t_lo, sy + nly * t_lo)
    if yield_:                                   # ロータリー進入: ゆずれ線(点線) + 逆三角
        stripe(mesh, LineString([a, b]), 0, 0.45, 0.45, 0.45, "paint_road_white", zf, 0.012)
        decal(mesh, px + tx * 8.0 + nlx * (t_lo + t_hi) / 2, py + ty * 8.0 + nly * (t_lo + t_hi) / 2, math.atan2(-ty, -tx), 1.2, 1.6, "decal_triangle", zf, 0.013)
    else:
        stripe(mesh, LineString([a, b]), 0, 0.45, 1, 0, "paint_road_white", zf, 0.012)
    ang = math.atan2(-ty, -tx)
    sig = rank >= 2 and e.tags["highway"] in ("trunk", "primary", "secondary", "tertiary")
    arrows = plan["arrows"] if plan else [None] * p.lanes
    rt = plan["rt"] if plan else 0.0
    for k, name in enumerate(arrows):
        if not name:
            continue
        t = lane_t(p, k)
        decal(mesh, px + tx * 11 + nlx * t, py + ty * 11 + nly * t, ang, 1.2, 5.0, "decal_" + name, zf, 0.013)
        if k == 0 and rt >= 24 and arm.length > D + 40:        # 右折専用レーンは矢印を繰り返す
            decal(mesh, px + tx * 26 + nlx * t, py + ty * 26 + nly * t, ang, 1.2, 5.0, "decal_" + name, zf, 0.013)
    if not sig and p.lane_w < 3.2 and not yield_:
        t = lane_t(p, 0)
        decal(mesh, px + tx * 7.5 + nlx * t, py + ty * 7.5 + nly * t, ang, 1.6, 4.0, "decal_text_tomare", zf, 0.013)
    if arm.length > 60 and rng.random() < 0.5:
        t = lane_t(p, 0)
        decal(mesh, px + tx * 33 + nlx * t, py + ty * 33 + nly * t, ang, 1.0, 2.0, "decal_diamond", zf, 0.013)
    # 高速な幹線: ランブルストリップ(停止線の手前38〜43m)。生活道路: 速度低減マーク
    if p.speed >= 50 and arm.length > D + 55 and rng.random() < 0.7:
        rx.bars_across(mesh, px, py, tx, ty, nlx, nly, t_lo + 0.2, t_hi - 0.2, [38 + 1.2 * i for i in range(5)], 0.3, zf)
    elif rank <= 1 and arm.length > D + 30 and rng.random() < cfg.get("slow_mark_rate", 0.3):
        rx.bars_across(mesh, px, py, tx, ty, nlx, nly, t_lo + 0.3, t_hi - 0.3, [10.5, 11.5, 12.4, 13.2, 13.9, 14.5], 0.45, zf)


def _edge_markings(mesh, e, zf, clear, rng, cfg, plans, mid_s=()):
    p = e.prof
    L = e.line.length
    s0 = clear.get((e.id, True), 0.0)
    s1 = L - clear.get((e.id, False), 0.0)
    if s1 - s0 < 6:
        return
    line = e.line
    gp = zf
    ex = [(m - 6.5, m + 6.5) for m in mid_s]     # 街区途中の横断歩道の前後は車線標示を切る

    def spans(a, b):
        out = [(a, b)]
        for lo, hi in ex:
            out = [(x, y) for (u, v) in out for (x, y) in ((u, min(v, lo)), (max(u, hi), v)) if y - x > 0.5]
        return out

    def stripe(mesh_, ln, off, width, on, gap, mat, zf_, zo=0.01, start=0.0, end=None):
        if ln is not line or not ex:
            return _stripe_raw(mesh_, ln, off, width, on, gap, mat, zf_, zo, start, line.length if end is None else end)
        for a, b in spans(start, line.length if end is None else end):
            _stripe_raw(mesh_, ln, off, width, on, gap, mat, zf_, zo, a, b)
    rank = RANK.get(e.tags["highway"], 0)
    bb = p.half - p.shoulder                     # 走行部(路肩を除く)の半幅 = 外側線の位置
    ra = e.tags.get("junction") == "roundabout"
    ta = plans.get((e.id, True), {}).get("rt", 0.0); tb = plans.get((e.id, False), {}).get("rt", 0.0)
    ta, tb = min(ta, (s1 - s0) * 0.4), min(tb, (s1 - s0) * 0.4)
    wide_med = (not p.oneway) and p.median_kind in ("planter", "barrier") and p.median > 1.0
    na, nb = (ta, tb) if wide_med else (0.0, 0.0)
    # 中央線・分離帯(右折レーン区間は分離帯を切って導流帯にする)
    if not p.oneway:
        if p.median == 0.5 and p.median_kind == "paint":
            for o in (-0.25, 0.25):
                stripe(mesh, line, o, 0.15, 1, 0, "paint_road_yellow", gp, 0.012, s0, s1)
        elif wide_med:
            _median(mesh, e, zf, s0 + na, s1 - nb, p, p.median_kind, (na > 0, nb > 0))
            for lo, hi in ((s0, s0 + na), (s1 - nb, s1)):
                if hi - lo > 5:
                    zone = substring(line, lo, hi).buffer(p.median / 2 - 0.1, cap_style=2)
                    rx.zebra_zone(mesh, zone, zf)
        else:
            solid = rng.random() < 0.3
            stripe(mesh, line, 0, 0.15, 5, 0 if solid else 5, "paint_road_yellow" if solid else "paint_road_white", gp, 0.012, s0, s1)
    # 車線境界: 右折専用レーンの境界は交差点手前で白実線、その他は破線
    divs = []
    if not p.oneway:
        for side in (-1, 1):
            for k in range(1, p.lanes):
                sa = ta if (k == 1 and side == -1) else 0.0
                sb = tb if (k == 1 and side == 1) else 0.0
                divs.append((side * (p.median / 2 + k * p.lane_w), sa, sb))
    else:
        for k in range(1, p.lanes):
            sa = sb = 0.0
            if e.oneway_dir == 1 and k == 1:
                sb = tb
            if e.oneway_dir != 1 and k == p.lanes - 1:
                sa = ta
            divs.append(((k - p.lanes / 2) * p.lane_w, sa, sb))
    for off, sa, sb in divs:
        if sa > 4:
            stripe(mesh, line, off, 0.15, 1, 0, "paint_road_white", gp, 0.012, s0, s0 + sa)
        if sb > 4:
            stripe(mesh, line, off, 0.15, 1, 0, "paint_road_white", gp, 0.012, s1 - sb, s1)
        stripe(mesh, line, off, 0.15, 5, 5, "paint_road_white", gp, 0.012, s0 + sa, s1 - sb)
    # 自転車レーン(青)+境界線 / 路肩・停車帯の外側線と駐車枠 / 歩道なしの路側帯
    if p.bike > 0:
        for side in (-1, 1):
            c0, c1 = side * (bb - p.bike), side * bb
            for a_, b_ in spans(s0, s1):
                ribbon_line(mesh, line, min(c0, c1), max(c0, c1), a_, b_, "paint_road_blue", zf)
            stripe(mesh, line, c0, 0.15, 1, 0, "paint_road_white", gp, 0.014, s0, s1)
            if (s1 - s0) > 20:
                ss = s0 + 6
                while ss < s1 - 6:
                    pt, pt2 = line.interpolate(ss), line.interpolate(ss + 0.5)
                    ang = math.atan2(pt2.y - pt.y, pt2.x - pt.x)
                    if side < 0:
                        ang += math.pi
                    nx, ny = -math.sin(ang if side > 0 else ang - math.pi), math.cos(ang if side > 0 else ang - math.pi)
                    decal(mesh, pt.x + nx * (c0 + c1) / 2, pt.y + ny * (c0 + c1) / 2, ang, 0.9, 1.4, "decal_bike_symbol", zf, 0.016)
                    ss += rng.uniform(40, 70)
    if p.shoulder > 0:
        for side in (-1, 1):
            stripe(mesh, line, side * bb, 0.15, 1, 0, "paint_road_white", gp, 0.012, s0, s1)
            if p.parking:
                ss = s0 + 3.0
                while ss < s1 - 3:        # 駐車枠(車室の仕切り): 6mごとに縁石側へ短い横線
                    a, b = line.interpolate(ss), line.interpolate(ss + 0.5)
                    d = math.hypot(b.x - a.x, b.y - a.y) or 1
                    nx, ny = -(b.y - a.y) / d, (b.x - a.x) / d
                    stripe(mesh, LineString([(a.x + nx * side * bb, a.y + ny * side * bb), (a.x + nx * side * (bb + p.shoulder - 0.15), a.y + ny * side * (bb + p.shoulder - 0.15))]),
                           0, 0.12, 1, 0, "paint_road_white", gp, 0.012)
                    ss += 6.0
    elif p.sw_l <= 0 and p.sw_r <= 0 and not ra:
        dbl = rng.random() < 0.3            # 歩行者専用の路側帯は白の二重線
        for side in (-1, 1):
            stripe(mesh, line, side * (p.half - 0.75), 0.15, 1, 0, "paint_road_white", gp, 0.012, s0, s1)
            if dbl:
                stripe(mesh, line, side * (p.half - 0.95), 0.15, 1, 0, "paint_road_white", gp, 0.012, s0, s1)
    if ra:                                  # ロータリー環道: 外側線
        for side in (-1, 1):
            stripe(mesh, line, side * (bb - 0.15), 0.15, 1, 0, "paint_road_white", gp, 0.012, s0, s1)
    # バスレーン着色(縁石側の車線)+「バス」文字
    if p.bus:
        for side in ((-1, 1) if not p.oneway else (1, )):
            c0 = side * (p.median / 2 + (p.lanes - 1) * p.lane_w) if not p.oneway else (p.lanes / 2 - 1) * p.lane_w
            c1 = c0 + side * p.lane_w if not p.oneway else p.lanes / 2 * p.lane_w
            for a_, b_ in spans(s0, s1):
                ribbon_line(mesh, line, min(c0, c1), max(c0, c1), a_, b_, "paint_road_bus", zf)
            ss = s0 + 12
            while ss < s1 - 12:
                a, b = line.interpolate(ss), line.interpolate(ss + 0.5)
                ang = math.atan2(b.y - a.y, b.x - a.x)
                if side < 0 and not p.oneway:
                    ang += math.pi
                tc = (c0 + c1) / 2
                decal(mesh, a.x - math.sin(math.atan2(b.y - a.y, b.x - a.x)) * tc, a.y + math.cos(math.atan2(b.y - a.y, b.x - a.x)) * tc, ang, 1.4, 3.6, "decal_text_bus", zf, 0.016)
                ss += 70
    # 歩道の誘導ブロック(線状): 縁石から0.6m
    if p.tactile:
        for side, sw in ((1, p.sw_l), (-1, p.sw_r)):
            if sw >= 2.0:
                try:
                    off = side * (p.half + 0.7)
                    sub = substring(line, s0 + 2, s1 - 2) if s1 - s0 > 8 else None
                    if sub is not None and sub.geom_type == "LineString":
                        o = sub.offset_curve(off)
                        if o.geom_type == "LineString" and o.length > 3:
                            pts, _ = _samples(o, 3.0)
                            zs = [zf(x, y) + p.curb_h for x, y in pts]
                            ribbon(mesh, pts, zs, -0.15, 0.15, "tbs_line_tiled", 0.012, swap=True)
                except Exception:
                    pass
    # 速度表示(各進行方向の車線中心)
    if L > 80 and not p.oneway and rng.random() < 0.6 and p.speed in (30, 40, 50, 60):
        for frac, side in ((0.35, 1), (0.65, -1)):
            a, b = line.interpolate(L * frac), line.interpolate(L * frac + 0.5)
            hd = math.atan2(b.y - a.y, b.x - a.x)
            tc = side * (p.median / 2 + p.lane_w * 0.5)
            decal(mesh, a.x - math.sin(hd) * tc, a.y + math.cos(hd) * tc, hd if side > 0 else hd + math.pi, 0.9, 2.2, f"decal_speed_{p.speed}", zf, 0.013)
    # 道路鋲(曲線部の中央線/高速な幹線の車線境界)・ハンプ
    if not p.oneway and rank >= 2 and p.speed >= 40 and not wide_med:
        rx.studs(mesh, line, s0, s1, [0.0], 10.0, "cats_eye_yellow", zf, only_curves=True)
    if rank >= 4 and p.speed >= 50:
        for off, _, _ in divs:
            rx.studs(mesh, line, s0, s1, [off], 14.0, "cats_eye_white", zf)
    tc_tag = e.tags.get("traffic_calming")
    if tc_tag in HUMP_TAGS and s1 - s0 > 10:
        rx.hump(mesh, line, (s0 + s1) / 2 - 1.8, p.half, zf)
    elif tc_tag is None and rank <= 1 and L > 70 and s1 - s0 > 40 and p.half < 6 and rng.random() < cfg.get("hump_rate", 0.2):
        rx.hump(mesh, line, rng.uniform(s0 + 15, s1 - 20), p.half, zf)
    # マンホール
    n_mh = int(L / 55)
    for _ in range(n_mh):
        s = rng.uniform(s0, max(s0 + 1, s1)); pt = line.interpolate(s)
        t = rng.uniform(-p.half + 1.2, p.half - 1.2) if p.half > 2 else 0
        pt2 = line.interpolate(min(L, s + 0.5)); ang = math.atan2(pt2.y - pt.y, pt2.x - pt.x)
        decal(mesh, pt.x - math.sin(ang) * t, pt.y + math.cos(ang) * t, ang, 0.65, 0.65, "decal_manhole", zf, 0.014)
    # 排水(側溝・グレーチング)と劣化(ひび/パッチ/わだち)
    erng = random.Random(e.id * 977 + cfg["seed"])
    if rank >= 1 and (p.sw_l > 0 or p.sw_r > 0):
        rx.drainage(mesh, e, s0, s1, zf, erng)
    rx.wear_decals(mesh, e, s0, s1, zf, erng, cfg)


def _samples(line, step):
    n = max(1, int(math.ceil(line.length / step)))
    return [(line.interpolate(line.length * i / n).x, line.interpolate(line.length * i / n).y) for i in range(n + 1)], line.length


def ribbon_line(mesh, line, c0, c1, s0, s1, mat, zf):
    sub = substring(line, s0, s1)
    if sub.geom_type != "LineString" or sub.length < 1:
        return
    pts, _ = _samples(sub, 3.0)
    ribbon(mesh, pts, [zf(x, y) + 0.011 for x, y in pts], c0, c1, mat)


def _median(mesh, e, zf, s0, s1, p, kind, taper=(False, False)):
    """中央分離帯(植栽帯/ガードレール型)。taper=(始端,終端) の端は6mかけて先細り(右折レーンの鼻先)"""
    sub = substring(e.line, s0, s1)
    if sub.geom_type != "LineString" or sub.length < 3:
        return
    pts, total = _samples(sub, 3.0)
    n = len(pts)
    zs = [zf(x, y) + 0.0 for x, y in pts]
    w0 = p.median / 2
    fs = []
    for i in range(n):
        s = total * i / max(1, n - 1)
        f = 1.0
        if taper[0]:
            f = min(f, 0.3 + 0.7 * min(1.0, s / 6.0))
        if taper[1]:
            f = min(f, 0.3 + 0.7 * min(1.0, (total - s) / 6.0))
        fs.append(f)
    if kind == "planter":
        h = 0.15
        prof = lambda i: [(-w0 * fs[i], 0, "concrete_tex"), (w0 * fs[i], 0, "concrete_tex"), (w0 * fs[i], h, "concrete_tex"), (w0 * fs[i] - 0.15, h, "grass"), (-w0 * fs[i] + 0.15, h, "grass"), (-w0 * fs[i], h, "concrete_tex")]
    else:
        h = 0.8
        prof = lambda i: [(-w0 * fs[i], 0, "concrete_formed"), (w0 * fs[i], 0, "concrete_formed"), (w0 * fs[i] * 0.7, h * 0.4, "concrete_formed"), (w0 * fs[i] * 0.35, h, "concrete_formed"),
                          (-w0 * fs[i] * 0.35, h, "concrete_formed"), (-w0 * fs[i] * 0.7, h * 0.4, "concrete_formed")]
    sweep(mesh, pts, prof, zs)


# ---------- 高架道路(首都高など) ----------
def deck_z(edge_line, zf, level_h, za, zb, base_a, base_b):
    L = edge_line.length
    top = (base_a + base_b) / 2 + level_h
    RA = min(L * 0.5, max(0.1, (top - za) * 25)); RB = min(L * 0.5, max(0.1, (top - zb) * 25))
    sm = lambda x: x * x * (3 - 2 * x)

    def z(s):
        v = top
        if s < RA and top > za + 0.3:
            v = top - (top - za) * sm(1 - s / RA)
        if L - s < RB and top > zb + 0.3:
            v = min(v, top - (top - zb) * sm(1 - (L - s) / RB))
        return v
    return z


def elevated_roads(edges, world, cfg, rng, elev=None):
    zf, land = world["zf"], world["land"]
    mesh = Mesh()
    el = [e for e in edges if e.kind == "drive" and e.level > 0]
    # ノード高さ(接続先の最小)
    nh = {}
    allnodes = defaultdict(list)
    for e in edges:
        if e.kind == "drive":
            for k in (e.a, e.b):
                allnodes[k].append(e)
    for k, lst in allnodes.items():
        nh[k] = min(LEVEL_H.get(x.level, 0.0) if x.level > 0 else 0.0 for x in lst)
    for e in el:
        p = e.prof
        if not world["area"].intersects(e.line):
            continue
        Hl = LEVEL_H.get(e.level, 7.0 * e.level)
        n = max(2, int(e.line.length / 4))
        pts = [(e.line.interpolate(e.line.length * i / n).x, e.line.interpolate(e.line.length * i / n).y) for i in range(n + 1)]
        ga, gb = zf(*pts[0]), zf(*pts[-1])
        zfn = deck_z(e.line, zf, Hl, ga + nh[e.a], gb + nh[e.b], ga, gb)
        S = [e.line.length * i / n for i in range(n + 1)]
        zs = [zfn(s) for s in S]
        if elev is not None:
            elev[e.id] = (S, zs, p)
        hw = p.half + (1.0 if p.lanes >= 1 else 0.5)
        hw = max(hw, 3.0)
        # 下端の厚み: 地面近く(スロープ端)では薄くして地中に潜らせない
        def prof(i, hw=hw, zs=zs, pts=pts):
            clear = zs[i] - zf(*pts[i])
            th = max(0.25, min(1.6, clear - 0.05))
            return [(-hw + 1.0, -th, "concrete_formed"), (hw - 1.0, -th, "concrete_formed"), (hw, -th * 0.35, "concrete_formed"), (hw, 0.85, "concrete_formed"),
                    (hw - 0.45, 0.85, "concrete_formed"), (hw - 0.45, 0.0, "asphalt"), (-hw + 0.45, 0.0, "concrete_formed"), (-hw + 0.45, 0.85, "concrete_formed"),
                    (-hw, 0.85, "concrete_formed"), (-hw, -th * 0.35, "concrete_formed")]
        sweep(mesh, pts, prof, zs)
        # 路面標示(デッキ上)
        zline = lambda x, y, line=e.line, S=S, zs=zs: float(np.interp(line.project(Point(x, y)), S, zs))
        if e.prof.lanes >= 1:
            tot = e.prof.lanes * (1 if p.oneway else 2)
            for k in range(1, tot):
                off = (k - tot / 2) * p.lane_w
                stripe(mesh, e.line, off, 0.15, 6, 9 if not (not p.oneway and k == tot / 2) else 0, "paint_road_white" if not (not p.oneway and k == tot / 2) else "paint_road_yellow", zline, 0.012)
            for side in (-1, 1):
                stripe(mesh, e.line, side * (tot * p.lane_w / 2 + 0.1), 0.2, 1, 0, "paint_road_white", zline, 0.012)
        # 橋脚(30m間隔、陸上のみ): T型(角柱+横梁)
        spacing = 32.0
        s = spacing / 2
        while s < e.line.length:
            pt = e.line.interpolate(s); pt2 = e.line.interpolate(min(e.line.length, s + 1.0))
            ang = math.atan2(pt2.y - pt.y, pt2.x - pt.x)
            zg = zf(pt.x, pt.y)
            zd = float(np.interp(s, S, zs))
            if land.contains(pt) and zd - zg > 3.5:
                col = Mesh()
                th = 1.6
                col.box(-0.9, -0.8, 0, 0.9, 0.8, zd - zg - th - 1.2, "concrete_formed")
                col.box(-1.3, -hw * 0.45 if False else -1.3, zd - zg - th - 1.2, 1.3, 1.3, zd - zg - th, "concrete_formed") if False else None
                col.box(-1.2, -(hw - 1.5), zd - zg - th - 1.2, 1.2, hw - 1.5, zd - zg - th, "concrete_formed")
                mesh.add(col.transformed(ang, pt.x, pt.y, zg - 0.5))
            s += spacing * rng.uniform(0.9, 1.1)
    return mesh


def build_roads(L, world, cfg=CFG):
    rng = random.Random(cfg["seed"])
    edges = build_edges(L["roads"], world["area"], cfg)
    m1, cw, sw, arms = build_ground_roads(edges, world, cfg, None, rng)
    elev = {}
    m2 = elevated_roads(edges, world, cfg, rng, elev)
    m1.add(m2)
    return m1, edges, dict(cw=cw, sw=sw, arms=arms, elev=elev, plans=LAST.get("plans", {}), mid_crossings=LAST.get("mid", []), gores=LAST.get("gores", []))
