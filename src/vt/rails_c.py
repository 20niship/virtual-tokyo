"""フェーズC: ゆりかもめ(複線高架桁・橋脚・全駅)と東京モノレール(跨座式軌道桁・駅)の詳細化。
rail.build_rail の置き換え。地上線路/JR高架は rail.py のものを再利用する。"""
import math
import random
from collections import defaultdict

import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import substring

from . import bridges, rail
from .assemble import Inst
from .modules.geom import Mesh
from .modules.geom3 import beam, hexa, tube3
from .roads import LEVEL_H, deck_z, level_of
from .station_signs import STATIONS
from .world import frames, ribbon, stripe, sweep

sm = bridges.sm


def _offset(pts, t):
    return [(x + nx * t, y + ny * t) for x, y, tx, ty, nx, ny in frames(pts)]


def _pair_lines(items):
    """ほぼ平行(平均距離<5m)な2本を1本の中心線にまとめる(ゆりかもめは上下線が別wayなので複線桁を二重に作らない)"""
    used, out = set(), []
    for i, a in enumerate(items):
        if i in used:
            continue
        mate = None
        for j in range(i + 1, len(items)):
            if j in used:
                continue
            b = items[j]
            ds = [a.interpolate(t, normalized=True).distance(b) for t in np.linspace(0.05, 0.95, 12)]
            if np.mean(ds) < 5.0 and 0.8 < a.length / max(b.length, 1) < 1.25:
                mate = j
                break
        if mate is None:
            out.append(a)
        else:
            used.add(mate)
            b = items[mate]
            if Point(a.coords[0]).distance(Point(b.coords[0])) > Point(a.coords[0]).distance(Point(b.coords[-1])):
                b = LineString(list(b.coords)[::-1])
            N = max(8, int(a.length / 8))
            pts = []
            for k in range(N + 1):
                p, q = a.interpolate(k / N, normalized=True), b.interpolate(k / N, normalized=True)
                pts.append(((p.x + q.x) / 2, (p.y + q.y) / 2))
            out.append(LineString(pts))
        used.add(i)
    return out


def _t_pier(mesh, ln, zf, zs, S, land, hw, col_w, col_l, beam_w, th, spacing, rng, round_col=False, lean=0.0):
    """T型橋脚: 柱(下太り)+柱頭のフレア+先細りの横梁+支承。根巻き(1.2m)と基礎付き"""
    s = spacing / 2
    while s < ln.length:
        pt = ln.interpolate(s); p2 = ln.interpolate(min(ln.length, s + 1.0))
        ang = math.atan2(p2.y - pt.y, p2.x - pt.x)
        zg = zf(pt.x, pt.y); zd = float(np.interp(s, S, zs))
        w = bridges.RB.w(pt.x, pt.y) if bridges.RB is not None else 0
        if land.contains(pt) and zd - zg > 3.0 and w < 0.4:
            h = zd - zg - th - 0.28
            d_cap = min(1.5, max(0.9, h * 0.2))
            c = Mesh()
            top = h
            col_top = top - d_cap
            if round_col:
                c.cyl(0, 0, -0.5, col_w / 2 + 0.1, col_top + 0.5, "z", "concrete_formed", 24)
                c.cyl(0, 0, col_top - 0.9, col_w / 2 + 0.4, 0.9, "z", "concrete_formed", 24)
                c.cyl(0, 0, -0.5, col_w / 2 + 0.3, 1.7, "z", "concrete_formed", 24)           # 根巻き
            else:
                c.box(-col_l / 2, -col_w / 2, -0.5, col_l / 2, col_w / 2, col_top, "concrete_formed")
                c.box(-col_l / 2 - 0.2, -col_w / 2 - 0.2, -0.5, col_l / 2 + 0.2, col_w / 2 + 0.2, 1.2, "concrete_formed")   # 根巻き
            c.box(-col_l / 2 - 1.2, -col_w / 2 - 1.2, -1.5, col_l / 2 + 1.2, col_w / 2 + 1.2, -0.5, "concrete_formed")
            for sgn in (-1, 1):
                x = sgn * beam_w / 2
                P = [(0, -0.8, top - d_cap), (x, -0.8, top - d_cap * 0.55), (x, 0.8, top - d_cap * 0.55), (0, 0.8, top - d_cap),
                     (0, -0.8, top), (x, -0.8, top), (x, 0.8, top), (0, 0.8, top)]
                hexa(c, P, "concrete_formed")
            for bx in ((-hw * 0.5, hw * 0.5) if hw > 1.5 else (0.0,)):
                c.box(bx - 0.3, -0.3, top, bx + 0.3, 0.3, top + 0.1, "steel_gray")
                c.box(bx - 0.26, -0.26, top + 0.1, bx + 0.26, 0.26, top + 0.22, "rubber")
            mesh.add(c.transformed(ang + math.pi / 2, pt.x, pt.y, zg))
        s += spacing * rng.uniform(0.92, 1.08)


def _joints(mesh, ln, S, zs, width, every=30.0):
    s = every
    while s < ln.length - 5:
        p = ln.interpolate(s); q = ln.interpolate(s + 1)
        bridges._joint(mesh, p.x, p.y, math.atan2(q.y - p.y, q.x - p.x), float(np.interp(s, S, zs)), width)
        s += every


def yurikamome(mesh, ln, pts, S, zs, zf, land, rng, ws):
    """複線の高架軌道桁(幅約8.6m): 傾斜ウェブの箱桁+張出し床版+パラペット(ケーブルトラフ蓋付き)、走行路、案内壁、給電レール、中央の点検歩廊、伸縮装置、T型橋脚"""
    hw = 4.3
    def prof(i):
        clear = zs[i] - zf(*pts[i])
        th = max(0.62, min(1.35, clear - 0.05))
        th = th * (1 - 0.55 * ws[i])
        bw = 5.2
        c = "concrete_formed"
        return [(-bw / 2, -th, c), (bw / 2, -th, c), (hw - 0.8, -0.5, c), (hw - 0.4, -0.36, c), (hw, -0.3, c), (hw, 0.0, c),
                (hw, 1.0, c), (hw - 0.3, 1.0, "concrete_tex"), (hw - 0.3, 0.0, "concrete_tex"),
                (-hw + 0.3, 0.0, "concrete_tex"), (-hw + 0.3, 1.0, c), (-hw, 1.0, c), (-hw, 0.0, c), (-hw, -0.3, c), (-hw + 0.4, -0.36, c), (-hw + 0.8, -0.5, c)]
    sweep(mesh, pts, prof, zs)
    for c_ in (-2.1, 2.1):
        ribbon(mesh, pts, zs, c_ - 1.05, c_ + 1.05, "asphalt", 0.012)
    ribbon(mesh, pts, zs, -0.6, 0.6, "steel_galv", 0.045)                                       # 中央の点検歩廊(グレーチング)
    guide = lambda i: [(-0.1, 0.0, "steel_white"), (0.1, 0.0, "steel_white"), (0.1, 0.45, "steel_white"), (-0.1, 0.45, "steel_white")]
    for t in (-3.35, -0.9, 0.9, 3.35):
        sweep(mesh, _offset(pts, t), guide, [z + 0.01 for z in zs])
    pw = lambda i: [(-0.04, 0.0, "steel_gray"), (0.04, 0.0, "steel_gray"), (0.04, 0.12, "steel_gray"), (-0.04, 0.12, "steel_gray")]
    for t in (-3.55, -1.1, 1.1, 3.55):
        sweep(mesh, _offset(pts, t), pw, [z + 0.3 for z in zs])
    tray = lambda i: [(-0.18, 0.0, "steel_galv"), (0.18, 0.0, "steel_galv"), (0.18, 0.2, "steel_galv"), (-0.18, 0.2, "steel_galv")]
    for t in (-3.55 - 0.45, 3.55 + 0.45):          # パラペット内側のケーブルトラフ
        sweep(mesh, _offset(pts, t * 0.93), tray, [z + 0.015 for z in zs])
    _joints(mesh, ln, S, zs, 2 * hw - 0.6)
    _t_pier(mesh, ln, zf, zs, S, land, hw, 1.7, 1.7, 7.6, 1.3, 30, rng)


def monorail(mesh, ln, pts, S, zs, zf, land, rng, ws):
    """東京モノレール(跨座式): 幅0.85m x 高さ1.6mのPC軌道桁(上角面取り)、側面の案内/安定面+集電レール、支承部の補剛、T型の橋脚"""
    def prof(i):
        c = "concrete_tex"
        return [(-0.425, -1.6, c), (0.425, -1.6, c), (0.425, -0.12, c), (0.345, 0.0, c), (-0.345, 0.0, c), (-0.425, -0.12, c)]
    sweep(mesh, pts, prof, zs)
    plate = lambda sg: (lambda i: [(sg * 0.438 - 0.012, -0.55, "steel_gray"), (sg * 0.438 + 0.012, -0.55, "steel_gray"), (sg * 0.438 + 0.012, -0.12, "steel_gray"), (sg * 0.438 - 0.012, -0.12, "steel_gray")])
    sweep(mesh, pts, plate(1), zs)
    sweep(mesh, pts, lambda i: plate(-1)(i)[::-1], zs)
    pr = lambda i: [(0.46, -0.96, "steel_galv"), (0.52, -0.96, "steel_galv"), (0.52, -0.86, "steel_galv"), (0.46, -0.86, "steel_galv")]
    sweep(mesh, pts, pr, zs)                                                                 # 集電レール
    s = 3.0
    while s < ln.length:                                                                      # 3m毎の横補剛(ダイアフラム端部)
        p = ln.interpolate(s); q = ln.interpolate(min(ln.length, s + 0.5))
        ang = math.atan2(q.y - p.y, q.x - p.x)
        b = Mesh(); b.box(-0.04, -0.45, -1.5, 0.04, 0.45, -0.2, "steel_gray")
        mesh.add(b.transformed(ang, p.x, p.y, float(np.interp(s, S, zs))))
        s += 6.0
    _joints(mesh, ln, S, zs, 0.85, 40.0)
    _t_pier(mesh, ln, zf, zs, S, land, 0.5, 1.5, 1.5, 3.0, 1.6, 22, rng, round_col=True)


# ---------------- 駅 ----------------
def _stairs(mesh, x0, y0, z0, dx, dy, zg, w, mat="concrete_tex"):
    """(x0,y0,z0)から(dx,dy)方向へ降りる直階段(段+ささら桁+手すり)。zgが接地高。戻り値=(終点x,y)"""
    rise = z0 - zg
    n = max(2, int(math.ceil(rise / 0.17)))
    rs = rise / n
    d = math.hypot(dx, dy); dx, dy = dx / d, dy / d
    nx, ny = -dy, dx
    tread = 0.29
    for i in range(n):
        a = i * tread
        cx, cy = x0 + dx * (a + tread / 2), y0 + dy * (a + tread / 2)
        z = z0 - (i + 1) * rs
        b = Mesh()
        b.box(-tread / 2, -w / 2, -rs, tread / 2, w / 2, 0.0, mat)
        b.box(-tread / 2 - 0.02, -w / 2, -0.03, tread / 2 + 0.02, w / 2, 0.0, "steel_galv")        # 踏面の滑り止めノージング
        mesh.add(b.transformed(math.atan2(dy, dx), cx, cy, z + rs))
    end = (x0 + dx * n * tread, y0 + dy * n * tread)
    for sg in (-1, 1):
        a = (x0 + nx * sg * (w / 2 + 0.06), y0 + ny * sg * (w / 2 + 0.06), z0 - rs)
        b = (end[0] + nx * sg * (w / 2 + 0.06), end[1] + ny * sg * (w / 2 + 0.06), zg)
        beam(mesh, a, b, 0.12, 0.34, "steel_white")                                                  # ささら桁
        ha = (a[0], a[1], a[2] + 1.0); hb = (b[0], b[1], b[2] + 1.0)
        tube3(mesh, [ha, hb], 0.025, "steel_galv", 8)                                                # 手すり
        tube3(mesh, [(a[0], a[1], a[2] + 0.5), (b[0], b[1], b[2] + 0.5)], 0.02, "steel_galv", 6)
        for k in range(0, n + 1, 4):
            t = k / n
            px, py, pz = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t
            mesh.box(px - 0.02, py - 0.02, pz, px + 0.02, py + 0.02, pz + 1.0, "steel_galv")
    return end


def _elevator(mesh, x, y, zg, z_top, ang):
    """エレベーター塔: 角柱4本+ガラス3面+開口面+屋根+乗場への連絡通路"""
    c = Mesh()
    s = 1.3
    for sx in (-1, 1):
        for sy in (-1, 1):
            c.box(sx * s - 0.1, sy * s - 0.1, 0, sx * s + 0.1, sy * s + 0.1, z_top - zg + 2.4, "truss_white")
    for z in np.arange(0, z_top - zg + 2.4, 3.0):
        c.box(-s, -s, z, s, s, z + 0.1, "steel_white")
    c.box(-s, s - 0.02, 0.2, s, s + 0.02, z_top - zg + 2.2, "glass_clear")
    c.box(-s, -s - 0.02, 0.2, s, -s + 0.02, z_top - zg + 2.2, "glass_clear")
    c.box(s - 0.02, -s, 0.2, s + 0.02, s, z_top - zg + 2.2, "glass_clear")
    c.box(-s - 0.15, -s - 0.15, z_top - zg + 2.4, s + 0.15, s + 0.15, z_top - zg + 2.6, "alu_silver")       # 屋根
    c.box(-0.6, -s - 0.01, 0, 0.6, -s + 0.01, 2.2, "alu_black")                                              # 乗降口(足元の扉枠)
    mesh.add(c.transformed(ang, x, y, zg))


STATION_VARIANT = {"新橋": "island", "有明": "island"}


def build_station(mesh, insts, ln, S, zs, zf, name, kind, land, rng):
    """高架駅: 両側ホーム(1.05m嵩上げ)+点字ブロック+黄線、ホームドア、曲面屋根ベイ、駅名標、階段、エレベーター塔、支柱"""
    info = STATIONS.get(name)
    if info is None:
        return
    code = info[1]
    if kind == "yurikamome":
        hw, plat_w, length, pf = 4.3, 3.4, 78.0, 1.05
    else:
        hw, plat_w, length, pf = 0.425 + 1.75, 3.6, 96.0, 0.95
    s0 = ln.project(Point(*_station_xy(name))) if _station_xy(name) else ln.length / 2
    a, b = max(0, s0 - length / 2), min(ln.length, s0 + length / 2)
    sub = substring(ln, a, b)
    if sub.geom_type != "LineString" or sub.length < 30:
        return
    n = max(4, int(sub.length / 3))
    sp = [sub.length * i / n for i in range(n + 1)]
    pts = [(sub.interpolate(s).x, sub.interpolate(s).y) for s in sp]
    z0 = [float(np.interp(a + s, S, zs)) for s in sp]
    fr = frames(pts)
    for side in (-1, 1):
        t0, t1 = side * hw, side * (hw + plat_w)
        lo, hi = min(t0, t1), max(t0, t1)
        slab = lambda i, lo=lo, hi=hi: [(lo, -0.7, "concrete_tex"), (hi, -0.7, "concrete_tex"), (hi, pf - 0.02, "concrete_tex"), (lo, pf - 0.02, "concrete_tex")]
        sweep(mesh, pts, slab, z0)
        ribbon(mesh, pts, z0, lo + (0.0 if side > 0 else 0.0), hi, "sidewalk_tile", pf)
        # 点字ブロック(縁から0.35m)と黄色の縁線
        e0 = side * (hw + 0.45)
        ribbon(mesh, pts, z0, min(e0 - 0.3, e0 + 0.3), max(e0 - 0.3, e0 + 0.3), "tbs_line_tiled", pf + 0.012, swap=True)
        ln_pts = LineString(pts)
        stripe(mesh, ln_pts, side * (hw + 1.05), 0.1, 1, 0, "paint_road_yellow", lambda x, y: float(np.interp(ln_pts.project(Point(x, y)), sp, z0)) + pf, 0.014)
        # ホームドア(軌道側)と屋根ベイ・駅名標
        k = 0
        s = 6.0
        nrm = lambda i: (fr[i][4], fr[i][5])
        while s < sub.length - 6.0:
            i = min(n, int(round(s / (sub.length / n))))
            x, y, tx, ty, nx_, ny_ = fr[i]
            face = (side * nx_, side * ny_)                       # 乗客側(軌道から外向き)
            insts.append(Inst("platform_door_unit", x + nx_ * side * (hw - 0.15), y + ny_ * side * (hw - 0.15), z0[i] + (1.0 if kind == "yurikamome" else pf), math.atan2(face[1], face[0]) - math.pi / 2 + 0.0, 1.0, 1.0, 1.0))
            s += 3.0
        s = 4.5
        while s < sub.length - 4.5:
            i = min(n, int(round(s / (sub.length / n))))
            x, y, tx, ty, nx_, ny_ = fr[i]
            inward = (-side * nx_, -side * ny_)                   # 軌道側へ張り出す
            insts.append(Inst("station_roof_bay", x + nx_ * side * (hw + plat_w - 0.35), y + ny_ * side * (hw + plat_w - 0.35), z0[i] + pf, math.atan2(inward[1], inward[0]) - math.pi / 2))
            s += 9.0
        for frac, sg in ((0.2, 1), (0.8, -1)):
            i = int(n * frac)
            x, y, tx, ty, nx_, ny_ = fr[i]
            insts.append(Inst(f"station_sign_{code.replace('-', '_')}", x + nx_ * side * (hw + 1.9), y + ny_ * side * (hw + 1.9), z0[i] + pf + 2.95, math.atan2(ty * sg, tx * sg) - math.pi / 2))
        # 支柱(台座の下): 12m毎、陸上のみ
        s = 6.0
        while s < sub.length - 3.0:
            i = min(n, int(round(s / (sub.length / n))))
            x, y, tx, ty, nx_, ny_ = fr[i]
            px, py = x + nx_ * side * (hw + plat_w - 0.5), y + ny_ * side * (hw + plat_w - 0.5)
            zg = zf(px, py)
            if land.contains(Point(px, py)) and z0[i] - zg > 2.5:
                mesh.box(px - 0.25, py - 0.25, zg, px + 0.25, py + 0.25, z0[i] - 0.7, "concrete_formed")
            s += 12.0
    # 階段+エレベーター: 両端から延長方向へ降りる(降りる先が陸上のときだけ)
    for end in (0, 1):
        i = 0 if end == 0 else n
        x, y, tx, ty, nx_, ny_ = fr[i]
        dx, dy = (-tx, -ty) if end == 0 else (tx, ty)
        side = 1 if (sum(map(ord, name)) + end) % 2 == 0 else -1
        sx, sy = x + nx_ * side * (hw + plat_w / 2), y + ny_ * side * (hw + plat_w / 2)
        rise = z0[i] + pf - zf(sx, sy)
        gx, gy = sx + dx * rise / 0.17 * 0.29, sy + dy * rise / 0.17 * 0.29
        if land.contains(Point(gx, gy)) and rise > 2.0:
            _stairs(mesh, sx, sy, z0[i] + pf, dx, dy, zf(gx, gy), 2.2)
        ex, ey = sx - dx * 3.5 + nx_ * side * 1.8, sy - dy * 3.5 + ny_ * side * 1.8
        if land.contains(Point(ex, ey)):
            _elevator(mesh, ex, ey, zf(ex, ey), z0[i] + pf, math.atan2(dy, dx))


_XY = {}


def set_station_xy(L):
    """駅名→(x,y)(同名はゆりかもめ/モノレール優先)"""
    _XY.clear()
    for f in L["stations"]:
        n = f.tags.get("name", "")
        op = f.tags.get("operator", "")
        if n in STATIONS and ((STATIONS[n][0] == "yurikamome" and op == "ゆりかもめ") or (STATIONS[n][0] == "monorail" and ("モノレール" in op or "モノレール" in n))):
            _XY[n] = (f.geom.x, f.geom.y)


def _station_xy(name):
    return _XY.get(name)


def build_rail(L, world, stations=True, seed=1):
    """rail.build_rail の詳細版。戻り値=(mesh, insts)"""
    set_station_xy(L)
    zf, land, area = world["zf"], world["land"], world["area"]
    rng = random.Random(seed)
    mesh = Mesh()
    insts = []
    ways = []
    for f in L["rail"]:
        t = f.tags
        if t.get("railway") not in rail.KINDS or f.geom.geom_type != "LineString" or not f.geom.intersects(area):
            continue
        if t.get("tunnel") in ("yes", "building_passage", "covered") or t.get("service") in ("siding", "yard", "spur", "crossover"):
            continue
        lv = level_of(t)
        if lv < 0:
            continue
        ways.append((f, lv))
    nh = defaultdict(lambda: 1e9)
    for f, lv in ways:
        h = LEVEL_H.get(lv, 7.0 * lv) if lv > 0 else 0.0
        for c in (f.geom.coords[0], f.geom.coords[-1]):
            nh[rail._key(c)] = min(nh[rail._key(c)], h)
    def near_h(c):
        best = min(nh.items(), key=lambda kv: (kv[0][0] - c[0]) ** 2 + (kv[0][1] - c[1]) ** 2, default=None)
        return best[1] if best and (best[0][0] - c[0]) ** 2 + (best[0][1] - c[1]) ** 2 < 100 and best[1] < 1e8 else 0.0
    groups = defaultdict(list)
    for f, lv in ways:
        groups[(rail.classify(f.tags), lv)].append(f)
    elevated_lines = []
    for (kind, lv), feats in groups.items():
        geoms = []
        for f in feats:
            cs = list(f.geom.coords)
            sm_ = rail._chaikin(cs, 2) if len(cs) > 2 else cs
            geoms.append(LineString(sm_).intersection(area.buffer(30)))
        flat = []
        for g in geoms:
            flat += [g] if g.geom_type == "LineString" else [x for x in getattr(g, "geoms", []) if x.geom_type == "LineString"]
        flat = [g for g in flat if g.length > 3]
        if kind == "yurikamome":
            flat = _pair_lines(flat)
        for ln in flat:
            n = max(2, int(ln.length / 3))
            S = [ln.length * i / n for i in range(n + 1)]
            pts = [(ln.interpolate(s).x, ln.interpolate(s).y) for s in S]
            if kind == "ground":
                rail._ground_track(mesh, pts, zf, feats[0].tags, rng, land)
                continue
            Hl = LEVEL_H.get(lv, 7.0 * lv)
            ga, gb = zf(*pts[0]), zf(*pts[-1])
            ha, hb = near_h(ln.coords[0]), near_h(ln.coords[-1])
            zfn = deck_z(ln, zf, Hl, ga + ha, gb + hb, ga, gb)
            zs, ws = bridges.blended([zfn(s) for s in S], pts, 3)
            if kind == "yurikamome":
                yurikamome(mesh, ln, pts, S, zs, zf, land, rng, ws)
            elif kind == "monorail":
                monorail(mesh, ln, pts, S, zs, zf, land, rng, ws)
            else:
                rail._viaduct(mesh, ln, pts, S, zs, zf, land, rng)
            if kind in ("yurikamome", "monorail"):
                elevated_lines.append((ln, S, zs, kind))
    if stations:
        for name, (x, y) in _XY.items():
            if not area.contains(Point(x, y)):
                continue
            kind = STATIONS[name][0]
            best = None
            for ln, S, zs, k in elevated_lines:
                if k != kind:
                    continue
                d = ln.distance(Point(x, y))
                if d < 60 and (best is None or d < best[0]):
                    best = (d, ln, S, zs)
            if best:
                build_station(mesh, insts, best[1], best[2], best[3], zf, name, kind, land, rng)
    return mesh, insts
