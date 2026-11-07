"""地面系の生成: 陸地(DEM追従TIN)、水面、護岸(直立/石積み傾斜/階段)、土地利用(芝/広場/砂利/土)、駐車場の区画線。"""
import math
import random

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import polygonize, unary_union

from .layers import HIGHWAY_DEFAULT
from .modules.geom import Mesh
from .world import decal, fill, stripe

SEA = 0.0          # 水面(T.P.±0)
QUAY_BOTTOM = -3.0


def land_polygon(L, area):
    """陸地: 海岸線の閉じた島 ∪ (道路・建物・緑地・土地利用の周辺を丸めた領域) − 水域"""
    parts = []
    try:
        for g in polygonize(unary_union([f.geom for f in L["coastline"]])):
            if g.area > 1000:
                parts.append(g)
    except Exception:
        pass
    parts += [f.geom.buffer(10) for f in L["roads"] if f.geom.intersects(area) and HIGHWAY_DEFAULT.get(f.tags["highway"], (0, 0, 0))[1] > 0
              and f.tags.get("bridge") is None and f.tags.get("tunnel") is None]
    parts += [f.geom.buffer(14) for f in L["buildings"] if f.geom.intersects(area)]
    parts += [f.geom.buffer(2) for f in L["green"] + L["landuse"] if f.geom.intersects(area)]
    land = unary_union(parts).buffer(12).buffer(-12)
    water = unary_union([f.geom for f in L["water"] if f.geom.intersects(area)]) if L["water"] else None
    if water is not None and not water.is_empty:
        from .roads import diff
        land = diff(land, water)
    land = land.intersection(area).simplify(0.6)
    return land


def _ring_segments(land):
    polys = [land] if land.geom_type == "Polygon" else [g for g in land.geoms if g.geom_type == "Polygon"]
    for g in polys:
        g = orient(g, 1.0)
        for ring in [g.exterior, *g.interiors]:
            yield ring


def quay(mesh, land, zf, area, seed=0):
    """護岸: 水は常に進行方向の右側。区間ごと(30〜120m)に 直立/石積み斜面/階段 を切替。天端に笠(コーピング)+係船柱。"""
    rng = random.Random(seed)
    for ring in _ring_segments(land):
        ring = ring.segmentize(3.0)
        cs = list(ring.coords)
        kind, left = 0, 0.0
        for i in range(len(cs) - 1):
            (x0, y0), (x1, y1) = cs[i][:2], cs[i + 1][:2]
            if not area.contains(Point((x0 + x1) / 2, (y0 + y1) / 2)):
                continue
            seg = math.hypot(x1 - x0, y1 - y0)
            if left <= 0:
                kind, left = rng.choices([0, 1, 2], [0.6, 0.25, 0.15])[0], rng.uniform(30, 120)
            left -= seg
            dx, dy = (x1 - x0) / seg, (y1 - y0) / seg
            ox, oy = dy, -dx   # 右=水側
            zt0, zt1 = zf(x0, y0), zf(x1, y1)
            top0, top1 = (x0, y0, zt0), (x1, y1, zt1)
            u0, u1 = (i * 3.0), (i + 1) * 3.0
            if kind == 0:     # 直立コンクリート
                b0, b1 = (x0, y0, QUAY_BOTTOM), (x1, y1, QUAY_BOTTOM)
                mesh.oriented([top0, b0, b1, top1], (ox, oy, 0), "concrete_formed", [(u0, zt0), (u0, QUAY_BOTTOM), (u1, QUAY_BOTTOM), (u1, zt1)])
            elif kind == 1:   # 石積み斜面(1:1.2)
                h0, h1 = zt0 - SEA + 0.3, zt1 - SEA + 0.3
                w0, w1 = (x0 + ox * h0 * 1.2, y0 + oy * h0 * 1.2, SEA - 0.3), (x1 + ox * h1 * 1.2, y1 + oy * h1 * 1.2, SEA - 0.3)
                mesh.oriented([top0, w0, w1, top1], (ox, oy, 1), "riprap", [(u0, 0), (u0, h0 * 1.5), (u1, h1 * 1.5), (u1, 0)])
                w2, w3 = (w0[0], w0[1], QUAY_BOTTOM), (w1[0], w1[1], QUAY_BOTTOM)
                mesh.oriented([w0, w2, w3, w1], (ox, oy, 0), "riprap", [(u0, 0), (u0, 1), (u1, 1), (u1, 0)])
            else:             # 階段状(3段)
                n = 3
                zs0 = [zt0 - (zt0 - SEA + 0.4) * k / n for k in range(n + 1)]
                zs1 = [zt1 - (zt1 - SEA + 0.4) * k / n for k in range(n + 1)]
                for k in range(n):
                    d = 0.45 * k
                    a0, a1 = (x0 + ox * d, y0 + oy * d, zs0[k]), (x1 + ox * d, y1 + oy * d, zs1[k])
                    b0, b1 = (a0[0], a0[1], zs0[k + 1]), (a1[0], a1[1], zs1[k + 1])
                    mesh.oriented([a0, b0, b1, a1], (ox, oy, 0), "concrete_formed", [(u0, 0), (u0, 1), (u1, 1), (u1, 0)])
                    c0, c1 = (b0[0] + ox * 0.45, b0[1] + oy * 0.45, zs0[k + 1]), (b1[0] + ox * 0.45, b1[1] + oy * 0.45, zs1[k + 1])
                    mesh.oriented([b0, c0, c1, b1], (0, 0, 1), "concrete_formed", [(u0, 0), (u0, 1), (u1, 1), (u1, 0)])
                zb0, zb1 = zs0[n], zs1[n]
                p0, p1 = (x0 + ox * 1.35, y0 + oy * 1.35, zb0), (x1 + ox * 1.35, y1 + oy * 1.35, zb1)
                mesh.oriented([p0, (p0[0], p0[1], QUAY_BOTTOM), (p1[0], p1[1], QUAY_BOTTOM), p1], (ox, oy, 0), "concrete_formed", [(u0, 0), (u0, 1), (u1, 1), (u1, 0)])
            # 天端の笠コンクリート(幅0.4, 高さ0.22)
            c_in0, c_in1 = (x0 - ox * 0.4, y0 - oy * 0.4), (x1 - ox * 0.4, y1 - oy * 0.4)
            h = 0.22
            q0, q1 = (x0, y0, zt0 + h), (x1, y1, zt1 + h)
            r0, r1 = (c_in0[0], c_in0[1], zt0 + h), (c_in1[0], c_in1[1], zt1 + h)
            mesh.oriented([q0, r0, r1, q1], (0, 0, 1), "concrete_tex")
            mesh.oriented([top0, q0, q1, top1], (ox, oy, 0), "concrete_tex")
            mesh.oriented([r0, (c_in0[0], c_in0[1], zt0), (c_in1[0], c_in1[1], zt1), r1], (-ox, -oy, 0), "concrete_tex")
            # 係船柱(約15mごと、乱数で間引き)
            if i % 5 == 0 and rng.random() < 0.7:
                cx, cy = (x0 + x1) / 2 - ox * 0.9, (y0 + y1) / 2 - oy * 0.9
                b = Mesh()
                b.cyl(0, 0, 0, 0.18, 0.35, "z", "steel_gray", 12)
                b.cyl(0, 0, 0.35, 0.26, 0.12, "z", "steel_gray", 12)
                mesh.add(b.transformed(0, cx, cy, zf(cx, cy)))


def parking_lines(mesh, geom, zf, rng):
    """駐車場: 最小外接矩形を軸に、5.0m奥行きの区画を2列+通路6mで並べ、2.5mピッチの区画線を白で引く"""
    try:
        r = geom.minimum_rotated_rectangle
    except Exception:
        return
    if r.geom_type != "Polygon" or geom.area < 150:
        return
    c = list(r.exterior.coords)[:4]
    e1 = (c[1][0] - c[0][0], c[1][1] - c[0][1]); e2 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
    l1, l2 = math.hypot(*e1), math.hypot(*e2)
    if l1 < l2:
        e1, e2, l1, l2 = e2, e1, l2, l1
        c = [c[1], c[2], c[3], c[0]]
    u = (e1[0] / l1, e1[1] / l1); v = (e2[0] / l2, e2[1] / l2)
    o = c[0]
    ang = math.atan2(u[1], u[0])
    pitch = 2.5
    for row_y in (0.5, l2 - 0.5 - 5.0) if l2 > 11 else (0.5,):
        pass
    rows = []
    y = 0.4
    while y + 5.0 < l2 - 0.3:
        rows.append(y)
        y += 5.0 + (6.0 if len(rows) % 2 else 0.2)
    for ry in rows:
        x = 0.8
        while x < l1 - 0.8:
            a = (o[0] + u[0] * x + v[0] * ry, o[1] + u[1] * x + v[1] * ry)
            b = (a[0] + v[0] * 5.0, a[1] + v[1] * 5.0)
            seg = LineString([a, b])
            if geom.buffer(-0.1).contains(seg):
                stripe(mesh, seg, 0, 0.1, 1, 0, "paint_road_white", zf, 0.012)
            x += pitch


LANDUSE_MAT = {"industrial": "gravel", "railway": "gravel", "port": "gravel", "construction": "soil", "brownfield": "soil",
               "commercial": "ground", "retail": "ground", "residential": "ground", "education": "ground", "institutional": "ground",
               "military": "gravel", "garages": "asphalt", "religious": "gravel", "cemetery": "grass"}


def build_ground(L, world, seed=0):
    """world: dict(area, land, zf) を返し、メッシュ(地面・護岸・水面)を作る"""
    from shapely.geometry import box
    zf = world["zf"]
    area, land = world["area"], world["land"]
    rng = random.Random(seed)
    m = Mesh()
    hole = world.get("road_hole")
    base = land.difference(hole) if hole is not None and not hole.is_empty else land   # quay は元の land を使う
    # 地面ベース(わずかに下げて、上に重ねる面とのZファイトを避ける)
    fill(m, base, lambda x, y: zf(x, y) - 0.03, "ground", 6.0, True, uv=lambda x, y: (x, y))
    # 緑地・土地利用(上に重ねる)
    for f in L["green"]:
        g = f.geom.intersection(base)
        if not g.is_empty:
            fill(m, g, lambda x, y: zf(x, y) + 0.06, "grass", 6.0, True, uv=lambda x, y: (x, y))
    for f in L["landuse"]:
        t = f.tags
        g = f.geom.intersection(base)
        if g.is_empty or g.area < 20:
            continue
        mat = None
        if t.get("amenity") == "parking":
            mat = "asphalt"
        elif t.get("natural") in ("sand", "beach"):
            mat = "gravel"
        elif t.get("landuse") in LANDUSE_MAT:
            mat = LANDUSE_MAT[t["landuse"]]
        elif t.get("leisure") in ("pitch", "stadium", "track"):
            mat = "grass" if t.get("leisure") != "track" else "sidewalk_asphalt"
        if not mat:
            continue
        fill(m, g, lambda x, y: zf(x, y) + 0.08, mat, 6.0, True, uv=lambda x, y: (x, y))
        if t.get("amenity") == "parking":
            parking_lines(m, g, zf, rng)
    quay(m, land, zf, area, seed)
    return m


def water_mesh(world):
    m = Mesh()
    cx, cy = world["center"]
    h = 4000
    m.poly([(cx - h, cy - h, SEA), (cx + h, cy - h, SEA), (cx + h, cy + h, SEA), (cx - h, cy + h, SEA)], "water")
    return m
