"""道路網から街区(ブロック)を作り、ロットに再分割して建物フットプリント+高さ+用途を自動割当する(Matrix/GTA風に道路沿いへ建物を敷き詰める)。
mode: osm=OSM建物のみ / infill=全て自動 / hybrid=OSM建物を残し空いた所だけ自動(既定)。"""
import math
import random

from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import split, unary_union
from shapely.strtree import STRtree

from .assemble import Inst
from .layers import Feature
from .modules.geom import Mesh
from .world import fill, stripe

# zone: (ロット面積[m²] min,max / 奥行最大[m] / 高さ[m] min,max / 側方セットバック min,max / (building, 重み)...)
ZONES = {
    "core": dict(area=(1500, 5000), depth=60, h=(60, 180), sb=(0.4, 1.5), tags=[("office", 0.5), ("hotel", 0.12), ("apartments", 0.2), ("commercial", 0.18)]),
    "urban": dict(area=(500, 1800), depth=45, h=(25, 75), sb=(0.4, 1.8), tags=[("office", 0.3), ("apartments", 0.3), ("commercial", 0.22), ("hotel", 0.06), ("retail", 0.12)]),
    "mid": dict(area=(300, 900), depth=38, h=(12, 38), sb=(0.6, 2.2), tags=[("apartments", 0.4), ("commercial", 0.25), ("office", 0.2), ("retail", 0.15)]),
    "low": dict(area=(110, 300), depth=26, h=(6.5, 14), sb=(0.8, 2.6), tags=[("house", 0.55), ("apartments", 0.28), ("commercial", 0.1), ("retail", 0.07)]),
    "industrial": dict(area=(2500, 7000), depth=70, h=(9, 18), sb=(1.5, 4.0), tags=[("warehouse", 0.7), ("industrial", 0.3)]),
}
BAD_LANDUSE = {"parking_marker"}


def _polys(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [x for geom in getattr(g, "geoms", []) for x in _polys(geom)]


def free_area(w, mode, extra_obstacles=()):
    """道路(車道+歩道)・緑地・水域・線路・高架・既存建物・水際を除いた、建物を置ける地面"""
    area, land, info, L = w["area"], w["land"], w["info"], w["L"]
    roadmask = unary_union([info["cw"].buffer(0.6), info["sw"].buffer(0.3)])
    free = land.intersection(area).difference(roadmask)
    free = free.intersection(land.buffer(-6))                                    # 護岸から離す
    obs = [f.geom.buffer(1.0) for f in L["green"] if f.geom.intersects(area)]
    obs += [f.geom.buffer(1.0) for f in L["water"] if f.geom.intersects(area)]
    obs += [f.geom.buffer(1.0) for f in L.get("landuse", []) if f.geom.intersects(area) and (f.tags.get("amenity") == "parking" or f.tags.get("leisure") in ("pitch", "stadium", "track", "marina", "swimming_pool", "park", "playground") or f.tags.get("man_made") in ("pier", "breakwater"))]
    obs += [f.geom.buffer(7.0) for f in L["rail"] if f.tags.get("railway") in ("rail", "light_rail", "monorail", "subway") and f.geom.intersects(area) and f.tags.get("tunnel") not in ("yes",)]
    for e in w["edges"]:
        if e.level > 0 and e.prof is not None and e.line.intersects(area):
            obs.append(e.line.buffer(e.prof.half + 4.0))
    for st in L.get("stations", []):
        obs.append(st.geom.buffer(12))
    if mode == "hybrid":
        obs += [f.geom.buffer(1.5) for f in L["buildings"] if f.geom.intersects(area)]
    obs += list(extra_obstacles)
    if obs:
        free = free.difference(unary_union(obs))
    return free


def split_lot(poly, rng, target, depth_max, cnt=0):
    """最小外接矩形の長手を横切るように分割(奥行が深すぎるなら長手に平行に分割)。間口=短手方向の長さを保つ"""
    if poly.area <= target or cnt > 12:
        return [poly]
    rect = poly.minimum_rotated_rectangle
    c = list(rect.exterior.coords)[:4]
    e1 = (c[1][0] - c[0][0], c[1][1] - c[0][1])
    e2 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
    l1, l2 = math.hypot(*e1), math.hypot(*e2)
    if l1 < l2:
        e1, e2, l1, l2 = e2, e1, l2, l1
    u = (e1[0] / l1, e1[1] / l1)             # 長手
    v = (e2[0] / l2, e2[1] / l2)             # 短手
    cen = rect.centroid
    t = rng.uniform(0.38, 0.62)
    if l2 > depth_max * 1.9:                  # 深い: 長手に平行に切る(短手方向を2分)
        p = (cen.x + v[0] * (t - 0.5) * l2, cen.y + v[1] * (t - 0.5) * l2)
        d = u
    else:
        p = (cen.x + u[0] * (t - 0.5) * l1, cen.y + u[1] * (t - 0.5) * l1)
        d = v
    big = (l1 + l2) * 2
    line = LineString([(p[0] - d[0] * big, p[1] - d[1] * big), (p[0] + d[0] * big, p[1] + d[1] * big)])
    try:
        parts = [g for g in split(poly, line).geoms if g.geom_type == "Polygon" and g.area > 25]
    except Exception:
        return [poly]
    if len(parts) < 2:
        return [poly]
    out = []
    for g in parts:
        out += split_lot(g, rng, target, depth_max, cnt + 1)
    return out


def _density_fn(w):
    lines = [e.line for e in w["edges"] if e.kind == "drive" and e.level == 0]
    tree = STRtree(lines)

    def dens(x, y, r=150.0):
        circ = Point(x, y).buffer(r)
        n = 0.0
        for i in tree.query(circ):
            n += lines[i].intersection(circ).length
        return n / (math.pi * r * r)
    return dens


def _zone(score, rng, big):
    if big and rng.random() < 0.15 and score < 0.55:
        return "industrial"
    if score > 0.75:
        return "core"
    if score > 0.5:
        return "urban"
    if score > 0.3:
        return "mid"
    return "low"


def _pick(tags, rng):
    names, ws = zip(*tags)
    return rng.choices(names, ws)[0]


def parking_lot(poly, zf, rng, n_id):
    """駐車場ロット: アスファルト+白線の区画(2.5x5m、通路6m)+駐車車両。(Mesh, [Inst])"""
    m = Mesh()
    insts = []
    fill(m, poly, lambda x, y: zf(x, y) + 0.03, "asphalt", 8.0, False)
    try:
        r = poly.minimum_rotated_rectangle
    except Exception:
        return m, insts
    c = list(r.exterior.coords)[:4]
    e1 = (c[1][0] - c[0][0], c[1][1] - c[0][1]); e2 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
    l1, l2 = math.hypot(*e1), math.hypot(*e2)
    if l1 < l2:
        e1, e2, l1, l2 = e2, e1, l2, l1
        c = [c[1], c[2], c[3], c[0]]
    u = (e1[0] / l1, e1[1] / l1); v = (e2[0] / l2, e2[1] / l2)
    o = c[0]
    inner = poly.buffer(-0.6)
    ang = math.atan2(v[1], v[0])
    rows, y = [], 0.8
    while y + 5.0 < l2 - 0.5:
        rows.append(y)
        y += 5.0 + (6.0 if len(rows) % 2 else 0.4)
    cars = ["car_sedan_white", "car_hatch_silver", "car_suv_black", "car_kei_white", "car_minivan_silver", "car_sedan_gray", "car_hatch_red", "car_sedan_black", "car_kei_blue", "car_suv_gray", "car_sedan_beige"]
    for ry in rows:
        x = 1.0
        while x < l1 - 1.0:
            a = (o[0] + u[0] * x + v[0] * ry, o[1] + u[1] * x + v[1] * ry)
            b = (a[0] + v[0] * 5.0, a[1] + v[1] * 5.0)
            seg = LineString([a, b])
            if inner.contains(seg):
                stripe(m, seg, 0, 0.1, 1, 0, "paint_road_white", zf, 0.05)
                if rng.random() < 0.62:
                    cx, cy = (a[0] + b[0]) / 2 + u[0] * 1.25, (a[1] + b[1]) / 2 + u[1] * 1.25
                    insts.append(Inst(rng.choice(cars), cx, cy, zf(cx, cy) + 0.04, ang + (0.0 if rng.random() < 0.5 else math.pi)))
            x += 2.5
    return m, insts


def yard_lot(poly, zf, rng):
    """工業/物流ロットの資材置場: 砂利敷き+コンテナの積み(1〜3段、20ft/40ft)+周囲の工事フェンス。(Mesh, [Inst])"""
    m = Mesh()
    insts = []
    inner = poly.buffer(-1.2, join_style=2)
    if inner.is_empty or inner.geom_type != "Polygon" or inner.area < 200:
        return m, insts
    fill(m, poly, lambda x, y: zf(x, y) + 0.03, "gravel", 8.0, False)
    rect = inner.minimum_rotated_rectangle
    c = list(rect.exterior.coords)[:4]
    e1 = (c[1][0] - c[0][0], c[1][1] - c[0][1]); e2 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
    l1, l2 = math.hypot(*e1), math.hypot(*e2)
    u = (e1[0] / l1, e1[1] / l1); v = (e2[0] / l2, e2[1] / l2)
    ang = math.atan2(u[1], u[0])
    colors = ["blue", "red", "gray", "green", "orange"]
    y = 1.5
    while y + 2.5 < l2:
        x = 1.5
        while x + 6.2 < l1:
            n20 = rng.random() < 0.45
            L = 6.06 if n20 else 12.19
            if x + L + 0.4 > l1:
                break
            cx = c[0][0] + u[0] * (x + L / 2) + v[0] * (y + 1.2)
            cy = c[0][1] + u[1] * (x + L / 2) + v[1] * (y + 1.2)
            foot = Polygon([(cx - u[0] * L / 2 - v[0] * 1.2, cy - u[1] * L / 2 - v[1] * 1.2), (cx + u[0] * L / 2 - v[0] * 1.2, cy + u[1] * L / 2 - v[1] * 1.2),
                            (cx + u[0] * L / 2 + v[0] * 1.2, cy + u[1] * L / 2 + v[1] * 1.2), (cx - u[0] * L / 2 + v[0] * 1.2, cy - u[1] * L / 2 + v[1] * 1.2)])
            if rng.random() < 0.8 and inner.contains(foot):
                col = rng.choice(colors)
                for h in range(rng.choice([1, 1, 2, 2, 3])):
                    insts.append(Inst(f"container_{'20' if n20 else '40'}_{col if h == 0 else rng.choice(colors)}", cx, cy, zf(cx, cy) + 0.05 + h * 2.59, ang))
            x += L + 0.5
        y += 2.44 + rng.choice([0.4, 0.4, 5.5])
    # 周囲のフェンス(約2m間隔)
    ring = poly.buffer(-0.4, join_style=2)
    if ring.geom_type == "Polygon":
        cs = list(ring.exterior.coords)
        for (x0, y0), (x1, y1) in zip(cs, cs[1:]):
            Ls = math.hypot(x1 - x0, y1 - y0)
            n = max(1, int(Ls // 2.0))
            for i in range(n):
                t = (i + 0.5) / n
                insts.append(Inst("construction_fence_2m", x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, zf(x0, y0) + 0.03, math.atan2(y1 - y0, x1 - x0), Ls / n / 2.0))
    return m, insts


def infill(w, mode="hybrid", seed=7, log=print):
    """戻り値: dict(features=[Feature...], pads=Mesh(駐車場の舗装等), props=[Inst], stats)"""
    rng = random.Random(seed)
    zf = w["T"]
    free = free_area(w, mode)
    blocks = [p for p in _polys(free) if p.area > 150]
    dens = _density_fn(w)
    cx, cy = w["center"]
    half = w["area"].bounds[2] - cx
    feats, pad, props = [], Mesh(), []
    stats = dict(blocks=len(blocks), lots=0, parking=0, micro=0)
    uid = 9_000_000_000
    for bk in blocks:
        cen = bk.centroid
        d = min(1.0, dens(cen.x, cen.y) / 0.028)
        hot = max(0.0, 1.0 - math.hypot(cen.x - cx, cen.y - cy) / (half * 1.25))
        bscore = 0.5 * d + 0.4 * hot + rng.uniform(-0.04, 0.04)
        big = bk.area > 6000
        zone = _zone(bscore, rng, big)
        Z = ZONES[zone]
        lots = split_lot(bk, rng, rng.uniform(*Z["area"]), Z["depth"])
        for lot in lots:
            stats["lots"] += 1
            lc = lot.centroid
            sc = min(1.0, max(0.0, bscore + rng.uniform(-0.08, 0.08)))
            lz = zone if zone == "industrial" else _zone(sc, rng, False)
            ZZ = ZONES[lz]
            sb = rng.uniform(*ZZ["sb"])
            foot = lot.buffer(-sb, join_style=2)
            fp = [p for p in _polys(foot) if p.area > 55]
            if not fp:
                if lot.area > 25:
                    sm = [p for p in _polys(lot.buffer(-0.5, join_style=2) if lot.area > 40 else lot) if p.area > 15]
                    if sm:
                        uid += 1
                        stats["micro"] += 1
                        feats.append(Feature(uid, max(sm, key=lambda p: p.area), dict(building="yes", _top=4.0, _min=0.0, _hsrc="infill")))
                continue
            foot = max(fp, key=lambda p: p.area)
            if lz == "industrial" and lot.area > 800 and rng.random() < 0.3:
                m, ins = yard_lot(lot, zf, rng)
                if ins:
                    pad.add(m)
                    props += ins
                    stats["yard"] = stats.get("yard", 0) + 1
                    continue
            if lz in ("mid", "low", "urban") and lot.area > 250 and rng.random() < (0.10 if lz != "low" else 0.05):
                m, ins = parking_lot(lot.buffer(-0.4, join_style=2), zf, rng, uid)
                pad.add(m)
                props += ins
                stats["parking"] += 1
                continue
            # 角地の面取り/L字: 一部だけ
            if lz in ("core", "urban") and foot.area > 800 and rng.random() < 0.3:
                minx, miny, maxx, maxy = foot.bounds
                notch = Polygon([(minx, miny), (minx + (maxx - minx) * rng.uniform(0.2, 0.35), miny), (minx, miny + (maxy - miny) * rng.uniform(0.2, 0.35))])
                nf = foot.difference(notch)
                if nf.geom_type == "Polygon" and nf.area > 55:
                    foot = nf
            tag = _pick(ZZ["tags"], rng)
            h = rng.uniform(*ZZ["h"])
            # 中心ほど高い(スコアに連動)
            h = ZZ["h"][0] + (ZZ["h"][1] - ZZ["h"][0]) * (0.25 * rng.random() + 0.75 * min(1.0, sc / 0.9) ** 1.2 * rng.random() ** 0.5)
            if foot.area < 150:
                h = min(h, 14)
            uid += 1
            feats.append(Feature(uid, foot, dict(building=tag, _top=h, _min=0.0, _hsrc="infill")))
    log(f"infill {mode}: blocks={stats['blocks']} lots={stats['lots']} buildings={len(feats)} parking={stats['parking']} micro={stats['micro']}")
    return dict(features=feats, pads=pad, props=props, stats=stats)
