"""roads.py から呼ぶ路面の追加要素。zf(x,y) は舗装面の高さ(カンバー込み)。"""
import math

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import substring

from .world import decal, ribbon, stripe

TOK = {"left": "L", "slight_left": "L", "sharp_left": "L", "through": "S", "right": "R", "slight_right": "R", "sharp_right": "R"}
NAME = {frozenset("L"): "arrow_left", frozenset("S"): "arrow_straight", frozenset("R"): "arrow_right",
        frozenset("SL"): "arrow_straight_left", frozenset("SR"): "arrow_straight_right"}


# ---------- 通行区分 ----------
def arm_dir(arm):
    """armの根元(交差点側)付近の外向き単位ベクトル"""
    a, b = arm.interpolate(0), arm.interpolate(min(10.0, arm.length))
    d = math.hypot(b.x - a.x, b.y - a.y) or 1.0
    return (b.x - a.x) / d, (b.y - a.y) / d


def turn_avail(me, node_arms):
    """接近路 me=(e,is_start,arm) から、他の腕へ進める方向の集合 {'left','through','right'}(日本は左側通行)"""
    e, is_start, arm = me
    tx, ty = arm_dir(arm)
    hx, hy = -tx, -ty                      # 接近車の進行方向
    out = set()
    for o, s, a in node_arms:
        if o is e and s == is_start:
            continue
        if o.prof.oneway and (o.oneway_dir == 1) != s:   # 出ていく向きに一方通行でない腕へは進入不可
            continue
        ox, oy = arm_dir(a)
        ang = math.degrees(math.atan2(hx * oy - hy * ox, hx * ox + hy * oy))
        if abs(ang) <= 22:
            out.add("through")
        elif 22 < ang <= 160:
            out.add("left")
        elif -160 <= ang < -22:
            out.add("right")
    return out


def osm_turn_lanes(tags, is_start, oneway, oneway_dir, n):
    """OSMの turn:lanes(forward/backward)から、接近レーンの矢印名を中央側(k=0)→縁石側の順で返す。無ければ None"""
    if oneway:
        key = "turn:lanes" if (oneway_dir == 1) != is_start else None
    else:
        key = "turn:lanes:backward" if is_start else "turn:lanes:forward"
    v = tags.get(key) if key else None
    if not v:
        return None
    lanes = v.split("|")
    if len(lanes) != n:
        return None
    names = []
    for tok in lanes:                              # 左(縁石側)→右の順
        s = frozenset(TOK.get(t.strip(), "") for t in tok.split(";")) - {""}
        names.append(NAME.get(s))
    return names[::-1]


def lane_arrows(e, is_start, avail, n, sig, rng):
    """接近レーンごとの路面矢印名(k=0が中央側)。OSMのturn:lanes優先、無ければ接続している腕から推定"""
    t = osm_turn_lanes(e.tags, is_start, e.prof.oneway, e.oneway_dir, n)
    if t is not None:
        return t
    thr = "through" in avail
    if n == 1:
        return ["arrow_straight" if (sig and thr and rng.random() < 0.5) else None]
    out = []
    for k in range(n):
        if k == 0 and "right" in avail:
            out.append("arrow_straight_right" if (thr and n == 2 and rng.random() < 0.4) else "arrow_right")
        elif k == n - 1 and "left" in avail:
            out.append(("arrow_straight_left" if thr else "arrow_left") if not (n >= 3 and rng.random() < 0.3) else "arrow_left")
        else:
            out.append("arrow_straight" if thr else None)
    return out


# ---------- 導流帯・誘導線 ----------
def zebra_zone(mesh, poly, zf, bar=0.45, pitch=1.0):
    """多角形を斜線(45°)の白帯で埋め、周囲を白実線で囲む(導流帯)"""
    if poly.is_empty or poly.area < 3:
        return
    rect = poly.minimum_rotated_rectangle
    c = list(rect.exterior.coords)[:4]
    e1 = (c[1][0] - c[0][0], c[1][1] - c[0][1]); e2 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
    l1, l2 = math.hypot(*e1), math.hypot(*e2)
    if l1 < l2:
        e1, e2, l1, l2 = e2, e1, l2, l1
    ux, uy = e1[0] / l1, e1[1] / l1
    ang = math.radians(45)
    dx, dy = ux * math.cos(ang) - uy * math.sin(ang), ux * math.sin(ang) + uy * math.cos(ang)
    cx, cy = rect.centroid.x, rect.centroid.y
    inner = poly.buffer(-0.2)
    if inner.is_empty:
        return
    reach = l1 + l2
    n = int(reach / pitch) + 2
    for i in range(-n, n + 1):
        px, py = cx + ux * i * pitch / math.sin(ang), cy + uy * i * pitch / math.sin(ang)
        seg = LineString([(px - dx * reach, py - dy * reach), (px + dx * reach, py + dy * reach)]).intersection(inner)
        for g in ([seg] if seg.geom_type == "LineString" else list(getattr(seg, "geoms", []))):
            if g.geom_type == "LineString" and g.length > 0.6:
                stripe(mesh, g, 0, bar, 1, 0, "paint_road_white", zf, 0.012)
    stripe(mesh, LineString(list(poly.exterior.coords)), 0, 0.15, 1, 0, "paint_road_white", zf, 0.013)


def bezier(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def arm_point(arm, d, t):
    """arm上 d[m] の位置から左へ t[m] ずらした点と、外向き接線"""
    d = max(0.0, min(d, arm.length - 0.2))
    a, b = arm.interpolate(d), arm.interpolate(min(arm.length, d + 0.6))
    L = math.hypot(b.x - a.x, b.y - a.y) or 1.0
    tx, ty = (b.x - a.x) / L, (b.y - a.y) / L
    return a.x - ty * t, a.y + tx * t, tx, ty


def guide_line(mesh, A, B, zf):
    """接近腕Aから出口腕Bへの右折誘導線(白の点線)。A,B={arm, D, t(腕の座標系での車線中心の横位置)}"""
    ax, ay, atx, aty = arm_point(A["arm"], A["D"] - 1.0, A["t"])
    bx, by, btx, bty = arm_point(B["arm"], B["D"] - 1.0, B["t"])
    chord = math.hypot(bx - ax, by - ay)
    k = 0.45 * chord
    pts = bezier((ax, ay), (ax - atx * k, ay - aty * k), (bx - btx * k, by - bty * k), (bx, by))
    stripe(mesh, LineString(pts), 0, 0.15, 0.6, 0.9, "paint_road_white", zf, 0.012)


# ---------- 道路鋲・減速・ハンプ ----------
def studs(mesh, line, s0, s1, offsets, spacing, mat, zf, only_curves=False):
    """道路鋲(キャッツアイ)。only_curves=Trueなら曲線部(5m区間の方位変化>5°)のみ"""
    s = s0 + spacing / 2
    while s < s1 - 1:
        a, b, c = line.interpolate(max(0, s - 4)), line.interpolate(s), line.interpolate(min(line.length, s + 4))
        h1 = math.atan2(b.y - a.y, b.x - a.x); h2 = math.atan2(c.y - b.y, c.x - b.x)
        turn = abs((h2 - h1 + math.pi) % (2 * math.pi) - math.pi)
        if not only_curves or turn > math.radians(5):
            nx, ny = -math.sin(h2), math.cos(h2)
            for off in offsets:
                x, y = b.x + nx * off, b.y + ny * off
                z = zf(x, y)
                mesh.box(x - 0.06, y - 0.06, z, x + 0.06, y + 0.06, z + 0.02, mat)
        s += spacing if not only_curves else spacing * 0.5


def bars_across(mesh, px, py, tx, ty, nlx, nly, t0, t1, dists, bar, zf, mat="paint_road_white"):
    """点(px,py)を基準に、進行方向tへ dists[m] ずらした位置で、横(法線nl)方向 t0..t1 の横棒を引く"""
    for d in dists:
        cx, cy = px + tx * d, py + ty * d
        stripe(mesh, LineString([(cx + nlx * t0, cy + nly * t0), (cx + nlx * t1, cy + nly * t1)]), 0, bar, 1, 0, mat, zf, 0.012)


def hump(mesh, line, s, half, zf, length=3.6, height=0.08):
    """台形ハンプ(ランプ1.0m+天端1.6m+ランプ1.0m)。両端に白帯を引く"""
    ss = [s, s + 1.0, s + length - 1.0, s + length]
    hh = [0.004, height, height, 0.004]
    sl = []
    for si, h in zip(ss, hh):
        p, q = line.interpolate(si), line.interpolate(min(line.length, si + 0.6))
        L = math.hypot(q.x - p.x, q.y - p.y) or 1.0
        nx, ny = -(q.y - p.y) / L, (q.x - p.x) / L
        lx, ly, rx, ry = p.x + nx * half, p.y + ny * half, p.x - nx * half, p.y - ny * half
        sl.append(((rx, ry, zf(rx, ry) + h), (lx, ly, zf(lx, ly) + h)))
    for i in range(3):
        r0, l0 = sl[i]; r1, l1 = sl[i + 1]
        mesh.oriented([r0, l0, l1, r1], (0, 0, 1), "asphalt")
    for si, h in ((s + 0.35, height * 0.35), (s + length - 0.35, height * 0.35)):
        p, q = line.interpolate(si), line.interpolate(min(line.length, si + 0.6))
        L = math.hypot(q.x - p.x, q.y - p.y) or 1.0
        nx, ny = -(q.y - p.y) / L, (q.x - p.x) / L
        stripe(mesh, LineString([(p.x + nx * (half - 0.2), p.y + ny * (half - 0.2)), (p.x - nx * (half - 0.2), p.y - ny * (half - 0.2))]), 0, 0.45, 1, 0,
               "paint_road_white", lambda x, y, h=h: zf(x, y) + h, 0.012)


# ---------- 横断歩道まわり ----------
def escort_zone(mesh, px, py, tx, ty, nlx, nly, half, zf):
    """エスコートゾーン: 横断歩道内(進行方向-1.5m)を横切る突起ブロック列(黄)"""
    n = max(2, int(2 * half / 3.0))
    pts = [(px - tx * 1.55 + nlx * (-half + 2 * half * i / n), py - ty * 1.55 + nly * (-half + 2 * half * i / n)) for i in range(n + 1)]
    ribbon(mesh, pts, [zf(x, y) + 0.004 for x, y in pts], -0.15, 0.15, "tbs_dot_tiled", 0.006, swap=True)


def bike_crossing(mesh, px, py, tx, ty, nlx, nly, half, zf, offset=-3.0):
    """自転車横断帯: 横断歩道に並走する2列の点線帯 + 両端に自転車マーク"""
    for off in (offset - 0.9, offset + 0.9):
        a = (px + tx * off - nlx * (half - 0.2), py + ty * off - nly * (half - 0.2))
        b = (px + tx * off + nlx * (half - 0.2), py + ty * off + nly * (half - 0.2))
        stripe(mesh, LineString([a, b]), 0, 0.3, 0.45, 0.45, "paint_road_white", zf, 0.012)
    for sgn in (1, -1):
        x, y = px + tx * offset + nlx * sgn * (half - 1.3), py + ty * offset + nly * sgn * (half - 1.3)
        decal(mesh, x, y, math.atan2(nly * -sgn, nlx * -sgn), 0.9, 1.4, "decal_bike_symbol", zf, 0.016)


def scramble(mesh, arms, zf):
    """スクランブル交差点: 4本の腕の横断歩道の隅を結ぶ2本の斜め横断歩道(進行方向に直交する白帯を並べる)。
    arms=[(px,py,tx,ty,nlx,nly,half)]"""
    if len(arms) != 4:
        return
    arms = sorted(arms, key=lambda a: math.atan2(a[3], a[2]))
    K = []
    for i in range(4):
        a, b = arms[i], arms[(i + 1) % 4]
        ea = (a[0] + a[4] * a[6], a[1] + a[5] * a[6])           # 腕aの左端(次の腕=反時計回り側)
        eb = (b[0] - b[4] * b[6], b[1] - b[5] * b[6])           # 腕bの右端
        K.append(((ea[0] + eb[0]) / 2, (ea[1] + eb[1]) / 2))
    for p, q in ((K[0], K[2]), (K[1], K[3])):
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        if L < 8:
            continue
        ux, uy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
        d = 1.8
        while d < L - 1.8:
            cx, cy = p[0] + ux * d, p[1] + uy * d
            stripe(mesh, LineString([(cx - (-uy) * 1.8, cy - ux * 1.8), (cx + (-uy) * 1.8, cy + ux * 1.8)]), 0, 0.45, 1, 0, "paint_road_white", zf, 0.012)
            d += 0.9


# ---------- 劣化・排水 ----------
def wear_decals(mesh, e, s0, s1, zf, rng, cfg):
    """ひび割れ/補修パッチ/わだち。量は city_age(wear)で変わり、(edge id, seed)で再現可能"""
    p = e.prof
    L = e.line.length
    if s1 - s0 < 8:
        return
    k = cfg.get("crack_rate", 1.0)
    span = s1 - s0
    for _ in range(int(span / 28 * p.wear * 1.6 * k + rng.random())):
        s = rng.uniform(s0 + 2, s1 - 2); t = rng.uniform(-(p.half - p.shoulder) + 0.8, (p.half - p.shoulder) - 0.8) if p.half > 2 else 0
        a, b = e.line.interpolate(s), e.line.interpolate(min(L, s + 0.6))
        ang = math.atan2(b.y - a.y, b.x - a.x)
        x, y = a.x - math.sin(ang) * t, a.y + math.cos(ang) * t
        decal(mesh, x, y, ang + rng.uniform(-0.6, 0.6), 2.4, 2.4, f"decal_asphalt_crack_{rng.randint(1, 3)}", zf, 0.009)
    for _ in range(int(span / 60 * p.wear * 1.2 * k + (rng.random() < 0.2))):
        s = rng.uniform(s0 + 3, s1 - 3); t = rng.uniform(-(p.half - p.shoulder) + 1.2, (p.half - p.shoulder) - 1.2) if p.half > 3 else 0
        a, b = e.line.interpolate(s), e.line.interpolate(min(L, s + 0.6))
        ang = math.atan2(b.y - a.y, b.x - a.x)
        x, y = a.x - math.sin(ang) * t, a.y + math.cos(ang) * t
        if rng.random() < 0.6:      # 埋設工事の短冊(路面を横断): 幅=車線幅、長さ0.9m
            decal(mesh, x, y, ang + math.pi / 2, 0.9, min(3.0, 2 * p.lane_w), "decal_asphalt_patch_1", zf, 0.008)
        else:
            decal(mesh, x, y, ang + rng.choice([0, math.pi / 2]), 1.2, 1.2, "decal_asphalt_patch_2", zf, 0.008)
    if p.wear > 0.45 and span > 15:     # わだち: 各車線のタイヤ通過帯(車線中心±0.85m)
        sub = substring(e.line, s0, s1)
        if sub.geom_type != "LineString":
            return
        lanes = p.lanes * (1 if p.oneway else 2)
        for lane in range(lanes):
            tc = (lane + 0.5 - lanes / 2) * p.lane_w if (p.oneway or p.median == 0) else ((lane % p.lanes + 0.5) * p.lane_w + p.median / 2) * (-1 if lane < p.lanes else 1)
            for dt in (-0.85, 0.85):
                try:
                    o = sub.offset_curve(tc + dt - 0.35)
                except Exception:
                    continue
                if o.geom_type != "LineString" or o.length < 6 or rng.random() > p.wear + 0.2:
                    continue
                n = max(2, int(o.length / 3))
                pts = [(o.interpolate(o.length * i / n).x, o.interpolate(o.length * i / n).y) for i in range(n + 1)]
                ribbon(mesh, pts, [zf(x, y) + 0.006 for x, y in pts], 0.0, 0.7, "asphalt_rut", 0.0)


def drainage(mesh, e, s0, s1, zf, rng, both_curb=True):
    """縁石沿いの側溝(U字溝蓋)と、25〜40m間隔のグレーチング+集水桝"""
    p = e.prof
    base = p.half - p.shoulder if False else p.half
    sub = substring(e.line, s0, s1) if s1 - s0 > 6 else None
    for side, sw in ((1, p.sw_l), (-1, p.sw_r)):
        if sw <= 0 or sub is None or sub.geom_type != "LineString":
            continue
        try:
            o = sub.offset_curve(side * (base - 0.15))
        except Exception:
            continue
        if o.geom_type == "LineString" and o.length > 4:
            n = max(2, int(o.length / 3))
            pts = [(o.interpolate(o.length * i / n).x, o.interpolate(o.length * i / n).y) for i in range(n + 1)]
            # 側溝は縁石沿い 0.3m 幅(道路側へ)。pathの左を+とするので、左側(side>0)は内向き=-0.15..+0.15
            ribbon(mesh, pts, [zf(x, y) + 0.004 for x, y in pts], -0.15, 0.15, "gutter", 0.0)
    s = s0 + rng.uniform(8, 25)
    alt = rng.choice((1, -1))
    while s < s1 - 6:
        a, b = e.line.interpolate(s), e.line.interpolate(min(e.line.length, s + 0.6))
        ang = math.atan2(b.y - a.y, b.x - a.x)
        side = alt
        sw = p.sw_l if side > 0 else p.sw_r
        if sw > 0:
            t = side * (base - 0.4)
            x, y = a.x - math.sin(ang) * t, a.y + math.cos(ang) * t
            if rng.random() < 0.65:
                decal(mesh, x, y, ang, 0.3, 0.6, "decal_grating", zf, 0.012)
            else:
                decal(mesh, x, y, ang, 0.5, 0.5, "decal_drain_inlet", zf, 0.012)
        alt = -alt
        s += rng.uniform(25, 40)
