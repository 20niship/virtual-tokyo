"""道路の手続き生成: RoadProfile → 道路グラフ → 交差点(隅切り) → 歩道/縁石/切り下げ → 路面標示/記号 → 高架道路(首都高)。"""
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import substring, unary_union

from .modules.geom import Mesh
from .world import decal, fill, frames, ribbon, stripe, sweep

# 全体設定(地区ごとの倍率で上書きしやすいよう1か所に集約)
CFG = dict(seed=1, city_age=0.5, wetness=0.0, barrier_free_rate=0.9, tactile_rate=0.6, bike_lane_rate=0.25)
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

    def __post_init__(self):
        self.half = (self.lanes * (1 if self.oneway else 2) * self.lane_w) / 2 + self.median / 2 + self.bike


def _jit(rng, v, rel):
    return v * rng.uniform(1 - rel, 1 + rel)


def make_profile(tags, rng, cfg, edge_key=0):
    hw = tags["highway"]
    lane_w, sw, nl = BASE.get(hw, (3.0, 2.0, 2))
    oneway = tags.get("oneway") in ("yes", "1", "true") or hw in ("motorway", "motorway_link") or "link" in hw
    try:
        n = int(float(tags.get("lanes", nl)))
    except ValueError:
        n = nl
    per_dir = max(1, n if oneway else max(1, n // 2))
    lane_w = _jit(rng, lane_w, 0.06)
    s = tags.get("sidewalk", "")
    has_l = has_r = sw > 0
    if s in ("no", "none"):
        has_l = has_r = False
    elif s == "left":
        has_r = False
    elif s == "right":
        has_l = False
    elif hw in ("residential", "unclassified", "living_street", "tertiary") and rng.random() < 0.18:
        has_l = False if rng.random() < 0.5 else has_l
        has_r = has_r if has_l else False if rng.random() < 0.5 else has_r
    w = lambda: min(6.0, max(1.5, _jit(rng, sw, 0.3))) if sw else 0
    sw_l, sw_r = (w() if has_l else 0.0), (w() if has_r else 0.0)
    bf = rng.random() < cfg["barrier_free_rate"]
    curb = rng.choice([0.05, 0.05, 0.08]) if bf else rng.choice([0.12, 0.15, 0.18])
    median, mk = 0.0, "paint"
    if not oneway and per_dir >= 2:
        mk = rng.choices(["paint", "planter", "barrier"], [0.55, 0.3, 0.15])[0]
        median = {"paint": 0.5, "planter": rng.uniform(1.4, 2.6), "barrier": 0.6}[mk]
    bike = 0.0
    if hw in ("primary", "secondary", "tertiary", "residential") and not oneway and rng.random() < cfg["bike_lane_rate"]:
        bike = 1.2
    speed = {"motorway": 60, "trunk": 50, "primary": 50, "secondary": 40, "tertiary": 40}.get(hw, 30)
    try:
        speed = int(float(tags.get("maxspeed", speed)))
    except ValueError:
        pass
    pav = rng.choices(["sidewalk_paver", "sidewalk_tile", "sidewalk_asphalt", "sidewalk_granite"], [0.38, 0.27, 0.25, 0.10])[0]
    return Profile(per_dir, lane_w, oneway, sw_l, sw_r, curb, median, mk, bike, rng.random() < cfg["tactile_rate"] and max(sw_l, sw_r) >= 2.0,
                   min(1, max(0, cfg["city_age"] + rng.gauss(0, 0.2))), pav, min(speed, 60) // 10 * 10)


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
    cw = inter(cw, world["area"])
    # 材質: 車道は幅員の広い順に区間ごとに(老朽化=wearで補修パッチ入りテクスチャ)
    acc = Polygon()
    for e in drive:
        piece = diff(inter(rib[e.id], cw), acc)
        if piece.is_empty:
            continue
        acc = unary_union([acc, piece])
        fill(mesh, piece, lift_fn(zf, 0.02), "asphalt_worn" if e.prof.wear > 0.55 else "asphalt", 6.0, False)
    rest = diff(cw, acc)
    if not rest.is_empty:
        fill(mesh, rest, lift_fn(zf, 0.02), "asphalt", 6.0, False)
    # 2) 横断歩道・停止線・切り下げの位置を先に決める(歩道から切り下げ分を抜くため)
    deco = []      # (関数, 引数) 後で描画
    cuts = []
    ramps = []
    for node, lst in inc.items():
        if len(lst) < 3 or not world["area"].contains(Point(node)):
            continue
        for e, is_start in lst:
            arm = e.line if is_start else LineString(list(e.line.coords)[::-1])
            maxo = max([o.prof.half for o, _ in lst if o is not e] + [3.0])
            D = maxo + 0.6 * FIL + 0.8
            if arm.length < D + 8:
                continue
            P = arm.interpolate(D + 2.0)
            Pn = arm.interpolate(D + 2.5)
            tx, ty = Pn.x - arm.interpolate(D + 1.5).x, Pn.y - arm.interpolate(D + 1.5).y
            L = math.hypot(tx, ty) or 1
            tx, ty = tx / L, ty / L
            nlx, nly = -ty, tx
            deco.append(("cross", node, e, is_start, arm, D, (P.x, P.y, tx, ty, nlx, nly)))
            for sgn, sw in ((1, e.prof.sw_l), (-1, e.prof.sw_r)):
                if sw <= 0:
                    continue
                ex, ey = P.x + nlx * sgn * (e.prof.half), P.y + nly * sgn * (e.prof.half)
                if not cw.buffer(0.3).contains(Point(ex, ey)):
                    continue
                # 切り下げ: 幅1.8m x 奥行1.5m(歩道側)
                ax, ay = tx * 0.9, ty * 0.9
                bx, by = nlx * sgn * 1.5, nly * sgn * 1.5
                R = Polygon([(ex - ax - bx * 0.0, ey - ay), (ex + ax, ey + ay), (ex + ax + bx, ey + ay + by), (ex - ax + bx, ey - ay + by)])
                # curb線(ex,ey)付近から歩道内へ
                R = Polygon([(ex - ax + nlx * sgn * 0.05, ey - ay + nly * sgn * 0.05), (ex + ax + nlx * sgn * 0.05, ey + ay + nly * sgn * 0.05),
                             (ex + ax + bx, ey + ay + by), (ex - ax + bx, ey - ay + by)])
                if cfg["barrier_free_rate"] > rng.random():
                    ramps.append((R, (nlx * sgn, nly * sgn), (tx, ty), e.prof.curb_h, e.prof.tactile))
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
    # 5) 区間ごとの標示(中央線/車線境界/外側線/自転車レーン/誘導ブロック/分離帯/記号)
    node_clear = {}
    for node, lst in inc.items():
        if len(lst) >= 3:
            for e, is_start in lst:
                maxo = max([o.prof.half for o, _ in lst if o is not e] + [3.0])
                node_clear[(e.id, is_start)] = maxo + 0.6 * FIL + 0.8 + 5.5
    zm = lift_fn(zf, 0.02)   # 標示は舗装面(+0.02)の上に載せる
    for e in drive:
        _edge_markings(mesh, e, zm, node_clear, rng, cfg)
    for d in deco:
        _crossing(mesh, d, zm, rng, cfg)
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


def _crossing(mesh, d, zf, rng, cfg):
    _, node, e, is_start, arm, D, (px, py, tx, ty, nlx, nly) = d
    h = e.prof.half
    # ゼブラ(縞0.45m/空き0.45m, 長さ4m)
    n = int((2 * h - 0.6) / 0.9)
    t0 = -(n * 0.9 - 0.45) / 2
    for k in range(n):
        t = t0 + k * 0.9 + 0.225
        a = (px + nlx * t - tx * 2.0, py + nly * t - ty * 2.0); b = (px + nlx * t + tx * 2.0, py + nly * t + ty * 2.0)
        stripe(mesh, LineString([a, b]), 0, 0.45, 4, 0, "paint_road_white", zf, 0.012)
    # 停止線(接近側=進行方向左側=外向き接線に対して右)。一方通行で出ていく向きなら無し
    approach = (not e.prof.oneway) or ((e.oneway_dir == 1) != is_start)
    if approach:
        sx, sy = px + tx * 3.2, py + ty * 3.2
        h0 = e.prof.median / 2
        a = (sx - nlx * h0, sy - nly * h0); b = (sx - nlx * (h - e.prof.bike), sy - nly * (h - e.prof.bike))
        stripe(mesh, LineString([a, b]), 0, 0.45, 1, 0, "paint_road_white", zf, 0.012)
        # 路面記号: 矢印(車線ごと)・「止まれ」(細街路)・ひし形(予告)
        lane_n = e.prof.lanes
        ang = math.atan2(-ty, -tx)
        sig = e.tags["highway"] in ("trunk", "primary", "secondary", "tertiary")
        for k in range(lane_n):
            t = -(e.prof.median / 2 + (k + 0.5) * e.prof.lane_w)
            ax, ay = px + tx * 11 + nlx * t, py + ty * 11 + nly * t
            if lane_n >= 2:
                kind = "arrow_straight_left" if k == lane_n - 1 else ("arrow_straight_right" if k == 0 and rng.random() < 0.6 else "arrow_straight")
                if k == lane_n - 1 and rng.random() < 0.3:
                    kind = "arrow_left"
            elif sig and rng.random() < 0.5:
                kind = "arrow_straight"
            else:
                continue
            decal(mesh, ax, ay, ang, 1.2, 5.0, "decal_" + kind, zf, 0.013)
        if not sig and e.prof.lane_w < 3.2:
            t = -(e.prof.median / 2 + e.prof.lane_w / 2)
            decal(mesh, px + tx * 7.5 + nlx * t, py + ty * 7.5 + nly * t, ang, 1.6, 4.0, "decal_text_tomare", zf, 0.013)
        if arm.length > 60 and rng.random() < 0.5:
            t = -(e.prof.median / 2 + e.prof.lane_w / 2)
            decal(mesh, px + tx * 33 + nlx * t, py + ty * 33 + nly * t, ang, 1.0, 2.0, "decal_diamond", zf, 0.013)


def _edge_markings(mesh, e, zf, clear, rng, cfg):
    p = e.prof
    L = e.line.length
    s0 = clear.get((e.id, True), 0.0)
    s1 = L - clear.get((e.id, False), 0.0)
    if s1 - s0 < 6:
        return
    line = e.line
    gp = lambda x, y: zf(x, y)
    # 中央線・車線境界
    if not p.oneway:
        if p.median == 0.5 and p.median_kind == "paint":
            for o in (-0.25, 0.25):
                stripe(mesh, line, o, 0.15, 1, 0, "paint_road_yellow", gp, 0.012, s0, s1)
        elif p.median_kind == "planter" and p.median > 1.0:
            _median(mesh, e, zf, s0, s1, p, "planter")
        elif p.median_kind == "barrier":
            _median(mesh, e, zf, s0, s1, p, "barrier")
        else:
            solid = rng.random() < 0.3
            stripe(mesh, line, 0, 0.15, 5, 0 if solid else 5, "paint_road_yellow" if solid else "paint_road_white", gp, 0.012, s0, s1)
    for side in ((-1, 1) if not p.oneway else (1,)):
        for k in range(1, p.lanes):
            off = side * (p.median / 2 + k * p.lane_w) if not p.oneway else (k - p.lanes / 2) * p.lane_w
            stripe(mesh, line, off, 0.15, 5, 5, "paint_road_white", gp, 0.012, s0, s1)
    # 自転車レーン(青)+境界線
    if p.bike > 0:
        for side in (-1, 1):
            c0, c1 = side * (p.half - p.bike), side * p.half
            ribbon_line(mesh, line, min(c0, c1), max(c0, c1), s0, s1, "paint_road_blue", zf)
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
    elif max(p.sw_l, p.sw_r) <= 0 and not p.oneway or (p.sw_l <= 0 and p.sw_r <= 0):
        # 歩道なし: 外側線(白実線)
        for side in (-1, 1):
            stripe(mesh, line, side * (p.half - 0.75), 0.15, 1, 0, "paint_road_white", gp, 0.012, s0, s1)
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
                            zs = [zf(x, y) + 0.02 + p.curb_h for x, y in pts]
                            ribbon(mesh, pts, zs, -0.15, 0.15, "tbs_line_tiled", 0.012, swap=True)
                except Exception:
                    pass
    # 速度表示 / マンホール
    if L > 80 and not p.oneway and rng.random() < 0.6 and p.speed in (30, 40, 50, 60):
        for frac, side in ((0.35, -1), (0.65, 1)):
            s = L * frac
            pt, pt2 = line.interpolate(s), line.interpolate(s + 0.5)
            ang = math.atan2(pt2.y - pt.y, pt2.x - pt.x)
            if side < 0:
                ang += math.pi
            nx, ny = -math.sin(ang), math.cos(ang)
            off = -(p.median / 2 + p.lane_w * 0.5) * (1 if side > 0 else -1) * -1
            decal(mesh, pt.x + math.cos(ang + math.pi / 2) * (p.median / 2 + p.lane_w * 0.5) * -1 * -1, pt.y + math.sin(ang + math.pi / 2) * (p.median / 2 + p.lane_w * 0.5) * -1 * -1, ang, 0.9, 2.2, f"decal_speed_{p.speed}", zf, 0.013)
    n_mh = int(L / 55)
    for _ in range(n_mh):
        s = rng.uniform(s0, max(s0 + 1, s1)); pt = line.interpolate(s)
        t = rng.uniform(-p.half + 1.2, p.half - 1.2) if p.half > 2 else 0
        pt2 = line.interpolate(min(L, s + 0.5)); ang = math.atan2(pt2.y - pt.y, pt2.x - pt.x)
        decal(mesh, pt.x - math.sin(ang) * t, pt.y + math.cos(ang) * t, ang, 0.65, 0.65, "decal_manhole", zf, 0.014)


def _samples(line, step):
    n = max(1, int(math.ceil(line.length / step)))
    return [(line.interpolate(line.length * i / n).x, line.interpolate(line.length * i / n).y) for i in range(n + 1)], line.length


def ribbon_line(mesh, line, c0, c1, s0, s1, mat, zf):
    sub = substring(line, s0, s1)
    if sub.geom_type != "LineString" or sub.length < 1:
        return
    pts, _ = _samples(sub, 3.0)
    ribbon(mesh, pts, [zf(x, y) + 0.011 for x, y in pts], c0, c1, mat)


def _median(mesh, e, zf, s0, s1, p, kind):
    sub = substring(e.line, s0, s1)
    if sub.geom_type != "LineString" or sub.length < 3:
        return
    pts, _ = _samples(sub, 3.0)
    zs = [zf(x, y) + 0.02 for x, y in pts]
    w = p.median / 2
    if kind == "planter":
        h = 0.15
        prof = lambda i: [(-w, 0, "concrete_tex"), (w, 0, "concrete_tex"), (w, h, "concrete_tex"), (w - 0.15, h, "grass"), (-w + 0.15, h, "grass"), (-w, h, "concrete_tex")]
    else:
        h = 0.8
        prof = lambda i: [(-w, 0, "concrete_formed"), (w, 0, "concrete_formed"), (w * 0.7, h * 0.4, "concrete_formed"), (w * 0.35, h, "concrete_formed"), (-w * 0.35, h, "concrete_formed"), (-w * 0.7, h * 0.4, "concrete_formed")]
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
    return m1, edges, dict(cw=cw, sw=sw, arms=arms, elev=elev)
