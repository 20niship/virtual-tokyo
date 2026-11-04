"""線路の手続き生成: 地上線路(バラスト/枕木/レール/架線柱)、高架(JR高架橋)、ゆりかもめ(複線案内軌条式の高架)、東京モノレール(跨座式軌道桁)、駅。"""
import math
import random
from collections import defaultdict

import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import substring

from .modules.geom import Mesh
from .roads import LEVEL_H, deck_z, level_of
from .world import frames, ribbon, stripe, sweep

KINDS = ("rail", "light_rail", "monorail")


def _chaikin(pts, it=2):
    for _ in range(it):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        out.append(pts[-1])
        pts = out
    return pts


def _key(p):
    return (round(p[0], 1), round(p[1], 1))


def classify(t):
    name = t.get("name", "")
    if t["railway"] == "monorail":
        return "monorail"
    if name == "ゆりかもめ" or (t["railway"] == "light_rail" and level_of(t) > 0):
        return "yurikamome"
    if level_of(t) > 0:
        return "viaduct"
    return "ground"


def _t_pier(mesh, line, zf, zs, S, land, hw, col_w, col_l, beam_w, th, spacing, rng, round_col=False):
    s = spacing / 2
    while s < line.length:
        pt = line.interpolate(s); p2 = line.interpolate(min(line.length, s + 1.0))
        ang = math.atan2(p2.y - pt.y, p2.x - pt.x)
        zg = zf(pt.x, pt.y); zd = float(np.interp(s, S, zs))
        if land.contains(pt) and zd - zg > 3.0:
            h = zd - zg - th
            c = Mesh()
            if round_col:
                c.cyl(0, 0, 0, col_w / 2, h - 0.8, "z", "concrete_formed", 20)
            else:
                c.box(-col_l / 2, -col_w / 2, 0, col_l / 2, col_w / 2, h - 1.0, "concrete_formed")
            c.box(-col_l / 2 - 0.2, -beam_w / 2, h - 1.0, col_l / 2 + 0.2, beam_w / 2, h, "concrete_formed")
            mesh.add(c.transformed(ang, pt.x, pt.y, zg - 0.5))
        s += spacing * rng.uniform(0.92, 1.08)


def build_rail(L, world, stations=True, seed=1):
    zf, land, area = world["zf"], world["land"], world["area"]
    rng = random.Random(seed)
    mesh = Mesh()
    ways = []
    for f in L["rail"]:
        t = f.tags
        if t.get("railway") not in KINDS or f.geom.geom_type != "LineString" or not f.geom.intersects(area):
            continue
        if t.get("tunnel") in ("yes", "building_passage", "covered") or t.get("service") in ("siding", "yard", "spur", "crossover"):
            continue
        lv = level_of(t)
        if lv < 0:
            continue
        ways.append((f, lv))
    # 端点高さ: 接続先の最小高さ(同種鉄道)
    nh = defaultdict(lambda: 1e9)
    for f, lv in ways:
        h = LEVEL_H.get(lv, 7.0 * lv) if lv > 0 else 0.0
        for c in (f.geom.coords[0], f.geom.coords[-1]):
            nh[_key(c)] = min(nh[_key(c)], h)
    elevated_lines = []
    for f, lv in ways:
        kind = classify(f.tags)
        cs = list(f.geom.coords)
        if len(cs) < 2:
            continue
        sm = _chaikin(cs, 2) if len(cs) > 2 else cs
        line = LineString(sm)
        # bbox外にはみ出す部分は削る
        line = line.intersection(area.buffer(30))
        if line.is_empty:
            continue
        parts = [line] if line.geom_type == "LineString" else [g for g in getattr(line, "geoms", []) if g.geom_type == "LineString"]
        for ln in parts:
            if ln.length < 3:
                continue
            n = max(2, int(ln.length / 3))
            S = [ln.length * i / n for i in range(n + 1)]
            pts = [(ln.interpolate(s).x, ln.interpolate(s).y) for s in S]
            if kind == "ground":
                _ground_track(mesh, pts, zf, f.tags, rng, land)
                continue
            Hl = LEVEL_H.get(lv, 7.0 * lv)
            ga, gb = zf(*pts[0]), zf(*pts[-1])
            ha = nh[_key(f.geom.coords[0])] if ln.coords[0] == tuple(f.geom.coords[0]) or True else 0
            hb = nh[_key(f.geom.coords[-1])]
            zfn = deck_z(ln, zf, Hl, ga + (ha if ha < 1e8 else 0), gb + (hb if hb < 1e8 else 0), ga, gb)
            zs = [zfn(s) for s in S]
            if kind == "yurikamome":
                _yurikamome(mesh, ln, pts, S, zs, zf, land, rng)
            elif kind == "monorail":
                _monorail(mesh, ln, pts, S, zs, zf, land, rng)
            else:
                _viaduct(mesh, ln, pts, S, zs, zf, land, rng)
            if kind in ("yurikamome", "monorail"):
                elevated_lines.append((ln, S, zs, kind))
    if stations:
        for st in L["stations"]:
            if not area.contains(st.geom):
                continue
            best = None
            for ln, S, zs, kind in elevated_lines:
                d = ln.distance(st.geom)
                if d < 40 and (best is None or d < best[0]):
                    best = (d, ln, S, zs, kind)
            if best and best[4] == "yurikamome":
                _station(mesh, best[1], best[2], best[3], st.geom, zf)
    return mesh


def _ground_track(mesh, pts, zf, tags, rng, land):
    """地上線路: バラスト + コンクリート枕木 + レール2本 + 架線柱(50m)と架線"""
    zs = [zf(x, y) + 0.05 for x, y in pts]
    bal = lambda i: [(-3.0, -0.35, "ballast"), (3.0, -0.35, "ballast"), (2.3, 0.0, "ballast"), (-2.3, 0.0, "ballast")]
    sweep(mesh, pts, bal, zs)
    line = LineString(pts)
    # 枕木(0.6m)
    s = 0.3
    while s < line.length:
        p = line.interpolate(s); p2 = line.interpolate(min(line.length, s + 0.3))
        ang = math.atan2(p2.y - p.y, p2.x - p.x)
        sl = Mesh(); sl.box(-0.12, -1.3, 0, 0.12, 1.3, 0.16, "concrete_tex")
        mesh.add(sl.transformed(ang, p.x, p.y, zf(p.x, p.y) + 0.05))
        s += 0.6
    rail = lambda i: [(-0.035, 0.16, "rail_steel"), (0.035, 0.16, "rail_steel"), (0.035, 0.32, "rail_steel"), (-0.035, 0.32, "rail_steel")]
    # CCW: (−,0.16)→(+,0.16)→(+,0.32)→(−,0.32)
    for t in (-0.5335, 0.5335):
        sweep(mesh, [(x + 0, y + 0) for x, y in _offset(pts, t)], rail, zs)
    # 架線柱
    s = 20.0
    while s < line.length - 5:
        p = line.interpolate(s); p2 = line.interpolate(s + 0.5)
        ang = math.atan2(p2.y - p.y, p2.x - p.x)
        m = Mesh()
        m.box(-0.12, 3.0, 0, 0.12, 3.3, 7.0, "steel_gray")
        m.box(-0.1, -3.2, 5.5, 0.1, 3.3, 5.7, "steel_gray")
        m.box(-0.05, -0.05, 5.1, 0.05, 0.05, 5.5, "steel_gray")
        mesh.add(m.transformed(ang, p.x, p.y, zf(p.x, p.y)))
        s += 50.0
    wire = lambda i: [(-0.012, 0, "steel_gray"), (0.012, 0, "steel_gray"), (0.012, 0.024, "steel_gray"), (-0.012, 0.024, "steel_gray")]
    sweep(mesh, pts, wire, [z + 5.1 for z in zs])


def _offset(pts, t):
    fr = frames(pts)
    return [(x + nx * t, y + ny * t) for x, y, tx, ty, nx, ny in fr]


def _viaduct(mesh, ln, pts, S, zs, zf, land, rng):
    """JR等の高架橋: 箱桁 + ガードパラペット + 軌道(バラスト+レール) + 橋脚"""
    hw = 4.2
    def prof(i):
        clear = zs[i] - zf(*pts[i])
        th = max(0.3, min(1.5, clear - 0.05))
        return [(-hw + 0.8, -th, "concrete_formed"), (hw - 0.8, -th, "concrete_formed"), (hw, -0.3, "concrete_formed"), (hw, 0.9, "concrete_formed"), (hw - 0.4, 0.9, "concrete_formed"),
                (hw - 0.4, 0.0, "ballast"), (-hw + 0.4, 0.0, "ballast"), (-hw + 0.4, 0.9, "concrete_formed"), (-hw, 0.9, "concrete_formed"), (-hw, -0.3, "concrete_formed")]
    sweep(mesh, pts, prof, zs)
    rail = lambda i: [(-0.035, 0.0, "rail_steel"), (0.035, 0.0, "rail_steel"), (0.035, 0.16, "rail_steel"), (-0.035, 0.16, "rail_steel")]
    for t in (-2.0 - 0.5335, -2.0 + 0.5335, 2.0 - 0.5335, 2.0 + 0.5335):
        sweep(mesh, _offset(pts, t), rail, [z + 0.02 for z in zs])
    _t_pier(mesh, ln, zf, zs, S, land, hw, 1.8, 1.8, 7.0, 1.5, 28, rng)


def _yurikamome(mesh, ln, pts, S, zs, zf, land, rng):
    """ゆりかもめ: 複線の高架軌道桁(幅約8.6m)。両側に走行路(ゴムタイヤ用コンクリート)と鉄製の案内壁、給電レール、両端に防護壁。"""
    hw = 4.3
    def prof(i):
        clear = zs[i] - zf(*pts[i])
        th = max(0.3, min(1.3, clear - 0.05))
        return [(-hw + 0.9, -th, "concrete_formed"), (hw - 0.9, -th, "concrete_formed"), (hw, -0.35, "concrete_formed"), (hw, 1.0, "concrete_formed"), (hw - 0.3, 1.0, "concrete_formed"),
                (hw - 0.3, 0.0, "concrete_tex"), (-hw + 0.3, 0.0, "concrete_tex"), (-hw + 0.3, 1.0, "concrete_formed"), (-hw, 1.0, "concrete_formed"), (-hw, -0.35, "concrete_formed")]
    sweep(mesh, pts, prof, zs)
    # 走行路(アスファルト調)
    for c in (-2.1, 2.1):
        ribbon(mesh, pts, zs, c - 1.05, c + 1.05, "asphalt", 0.012)
    # 案内壁(各走行路の外側と中央の計4本 0.2幅 x 0.45高)+ 給電レール
    guide = lambda i: [(-0.1, 0.0, "steel_white"), (0.1, 0.0, "steel_white"), (0.1, 0.45, "steel_white"), (-0.1, 0.45, "steel_white")]
    for t in (-3.35, -0.9, 0.9, 3.35):
        sweep(mesh, _offset(pts, t), guide, [z + 0.01 for z in zs])
    pw = lambda i: [(-0.04, 0.0, "steel_gray"), (0.04, 0.0, "steel_gray"), (0.04, 0.12, "steel_gray"), (-0.04, 0.12, "steel_gray")]
    for t in (-3.55, -1.1, 1.1, 3.55):
        sweep(mesh, _offset(pts, t), pw, [z + 0.3 for z in zs])
    _t_pier(mesh, ln, zf, zs, S, land, hw, 1.7, 1.7, 7.6, 1.3, 30, rng)


def _monorail(mesh, ln, pts, S, zs, zf, land, rng):
    """東京モノレール(跨座式): 幅0.85m x 高さ1.5mのコンクリート軌道桁 + 角柱の橋脚(丸みあり)"""
    prof = lambda i: [(-0.425, -1.5, "concrete_tex"), (0.425, -1.5, "concrete_tex"), (0.425, 0.0, "concrete_tex"), (-0.425, 0.0, "concrete_tex")]
    sweep(mesh, pts, prof, zs)
    # 走行面の両側に案内/給電板(側面の薄板)
    plate = lambda i: [(-0.01, -0.5, "steel_gray"), (0.01, -0.5, "steel_gray"), (0.01, -0.1, "steel_gray"), (-0.01, -0.1, "steel_gray")]
    for t in (-0.436, 0.436):
        sweep(mesh, _offset(pts, t), plate, zs)
    _t_pier(mesh, ln, zf, zs, S, land, 0.5, 1.3, 1.3, 2.6, 1.5, 22, rng, round_col=True)


def _station(mesh, ln, S, zs, st, zf):
    """高架駅: 軌道両側のホーム(長さ90m)+屋根(ガラス/アルミ)+柱"""
    s0 = ln.project(st)
    a, b = max(0, s0 - 45), min(ln.length, s0 + 45)
    sub = substring(ln, a, b)
    if sub.geom_type != "LineString" or sub.length < 30:
        return
    n = max(2, int(sub.length / 3))
    sp = [sub.length * i / n for i in range(n + 1)]
    pts = [(sub.interpolate(s).x, sub.interpolate(s).y) for s in sp]
    z0 = [float(np.interp(a + s, S, zs)) for s in sp]
    for side in (-1, 1):
        pf = lambda i, side=side: [(side * 4.3, -0.2, "concrete_tex"), (side * 8.3, -0.2, "concrete_tex"), (side * 8.3, 1.1, "concrete_tex"), (side * 4.3, 1.1, "concrete_tex")] if side > 0 else \
            [(side * 8.3, -0.2, "concrete_tex"), (side * 4.3, -0.2, "concrete_tex"), (side * 4.3, 1.1, "concrete_tex"), (side * 8.3, 1.1, "concrete_tex")]
        sweep(mesh, pts, pf, z0)
        # 黄色い点字ブロック(ホーム縁)
        ribbon(mesh, pts, z0, side * 4.5 - 0.3, side * 4.5 + 0.3, "tbs_line_tiled", 1.115, swap=True)
    roof = lambda i: [(-7.0, 4.5, "alu_main"), (7.0, 4.5, "alu_main"), (7.0, 4.9, "alu_main"), (-7.0, 4.9, "alu_main")]
    sweep(mesh, pts, roof, z0)
    for j in range(0, n + 1, 4):
        x, y = pts[j]
        fr = frames(pts)[j]
        for t in (-7.2, 7.2):
            m = Mesh(); m.box(-0.15, -0.15, 0, 0.15, 0.15, 4.5, "steel_white")
            mesh.add(m.transformed(0, x + fr[4] * t, y + fr[5] * t, z0[j]))
