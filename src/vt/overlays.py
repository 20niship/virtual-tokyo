"""路面・歩道の経年ディテール(リアリズム強化B): 落ち葉/水たまり/油染み/タイヤ痕/掘削復旧帯/各種マンホール(デカール)と、縁石の欠け・縁石際や割れ目の雑草(インスタンス)。
決定論的(rng固定)。デカールは w["r"](道路メッシュ)に追記する。"""
import math

from shapely.geometry import Point

from .assemble import Inst
from .city_props import RANK, _frame
from .world import decal

COVER = [("decal_overlay_cover_round_sewer", 0.66, 0.66), ("decal_overlay_cover_round_water", 0.5, 0.5), ("decal_overlay_cover_square_water", 0.4, 0.4),
         ("decal_overlay_cover_gas", 0.4, 0.45), ("decal_overlay_cover_hand", 0.8, 0.56)]


def _lane_offsets(p):
    if p.oneway:
        return [(k - (p.lanes - 1) / 2) * p.lane_w for k in range(p.lanes)]
    return [s * (p.median / 2 + (k + 0.5) * p.lane_w) for s in (1, -1) for k in range(p.lanes)]


def _walk(L, rng, lo, hi, margin):
    s = margin + rng.uniform(0, lo)
    while s < L - margin:
        yield s
        s += rng.uniform(lo, hi)


def road_overlays(w, rng, wet=0.3, age=0.5):
    """w: build_world の戻り。wet: 水たまりの量(0..1)、age: 劣化度(0..1)。戻り値: 追加インスタンス(縁石欠け/雑草)"""
    T, area, mesh = w["T"], w["area"], w["r"]
    inst = []
    n = dict(leaf=0, puddle=0, oil=0, tire=0, trench=0, cover=0, chip=0, weed=0)

    def D(x, y, ang, wd, ln, mat, off):
        decal(mesh, x, y, ang, wd, ln, mat, T, off)

    for e in w["edges"]:
        if e.kind != "drive" or e.level != 0 or e.prof is None or e.line.length < 16:
            continue
        p, L = e.prof, e.line.length
        rank = RANK.get(e.tags.get("highway", ""), 0)
        lanes = _lane_offsets(p)
        gutter = [(+1, p.half - 0.55), (-1, -p.half + 0.55)]

        def at(s, t):
            x, y, tx, ty = _frame(e.line, s)
            return x - ty * t, y + tx * t, math.atan2(ty, tx)

        for s in _walk(L, rng, 30, 70, 8):                                       # 落ち葉(縁石際)
            if rng.random() < 0.5 * (0.5 + age):
                sg, t = rng.choice(gutter)
                x, y, a = at(s, t)
                if area.contains(Point(x, y)):
                    D(x, y, rng.uniform(0, 6.28), rng.uniform(1.4, 2.6), rng.uniform(1.4, 2.6), f"decal_overlay_leaf_litter_{rng.randint(1, 2)}", 0.013)
                    n["leaf"] += 1
        for s in _walk(L, rng, 40, 120, 8):                                      # 水たまり(轍・縁石際)
            if rng.random() < 0.5 * wet + 0.1:
                sg, t = rng.choice(gutter)
                x, y, a = at(s, t * rng.uniform(0.7, 1.0))
                if area.contains(Point(x, y)):
                    D(x, y, a + rng.uniform(-0.3, 0.3), rng.uniform(1.0, 2.0), rng.uniform(2.0, 3.8), "decal_overlay_puddle", 0.015)
                    n["puddle"] += 1
        for s in _walk(L, rng, 50, 160, 10):                                     # 油染み(車線の中央寄り=停車位置)
            if rng.random() < 0.5 * (0.5 + age):
                x, y, a = at(s, rng.choice(lanes) + rng.uniform(-0.4, 0.4))
                if area.contains(Point(x, y)):
                    D(x, y, rng.uniform(0, 6.28), rng.uniform(0.6, 1.3), rng.uniform(0.6, 1.3), "decal_overlay_oil", 0.011)
                    n["oil"] += 1
        if rank >= 2:                                                       # タイヤ痕: 交差点手前のブレーキ痕と車線上の擦れ
            for s0 in (rng.uniform(9, 20), L - rng.uniform(9, 20)):
                if 9 < s0 < L - 9 and rng.random() < 0.45 * (0.4 + age):
                    x, y, a = at(s0, rng.choice(lanes))
                    if area.contains(Point(x, y)):
                        D(x, y, a, 1.9, rng.uniform(4.0, 8.0), "decal_overlay_tire_marks", 0.011)
                        n["tire"] += 1
        if rank <= 3 and L > 40 and rng.random() < 0.22 * (0.5 + age):     # 掘削復旧帯(ガス/水道の埋設工事の跡)
            ln = rng.uniform(8, min(30, L - 20))
            s0 = rng.uniform(10, L - 10 - ln)
            x, y, a = at(s0 + ln / 2, rng.choice(lanes) + rng.uniform(-0.5, 0.5))
            if area.contains(Point(x, y)):
                D(x, y, a, rng.uniform(0.8, 1.2), ln, "decal_overlay_trench", 0.010)
                n["trench"] += 1
        for s in _walk(L, rng, 60, 140, 12):                                     # マンホール類
            if rng.random() < 0.8:
                mat, cw, cl = rng.choices(COVER[:4], weights=[5, 2, 2, 1])[0]
                x, y, a = at(s, rng.choice(lanes) + rng.uniform(-0.3, 0.3))
                if area.contains(Point(x, y)):
                    D(x, y, a, cw, cl, mat, 0.016)
                    n["cover"] += 1
        for sg, sw in ((1, p.sw_l), (-1, p.sw_r)):                           # 歩道側: ハンドホール/水道制水弁/縁石欠け/雑草
            if sw <= 0.5:
                continue
            curb = max(0.0, p.curb_h)
            for s in _walk(L, rng, 45, 110, 10):
                if rng.random() < 0.7:
                    mat, cw, cl = rng.choice([COVER[4], COVER[2], COVER[3], COVER[4]])
                    x, y, a = at(s, sg * (p.half + sw * rng.uniform(0.3, 0.7)))
                    if area.contains(Point(x, y)):
                        D(x, y, a, cw, cl, mat, curb + 0.012)
                        n["cover"] += 1
            for s in _walk(L, rng, 25, 70, 6):                              # 歩道の落ち葉(街路樹の下)
                if rng.random() < 0.45 * (0.5 + age):
                    x, y, a = at(s, sg * (p.half + sw * rng.uniform(0.2, 0.9)))
                    if area.contains(Point(x, y)):
                        D(x, y, rng.uniform(0, 6.28), rng.uniform(1.0, 2.2), rng.uniform(1.0, 2.2), f"decal_overlay_leaf_litter_{rng.randint(1, 2)}", curb + 0.013)
                        n["leaf"] += 1
            for s in _walk(L, rng, 14, 40, 6):
                if curb >= 0.07 and rng.random() < 0.4 * (0.4 + age):
                    x, y, a = at(s, sg * (p.half + 0.0))
                    if area.contains(Point(x, y)):
                        face = a - sg * math.pi / 2                                 # 縁石面の法線=道路中心向き(モジュール+y)
                        inst.append(Inst("lf_curb_chip", x, y, T(x, y), face - math.pi / 2))
                        n["chip"] += 1
            for s in _walk(L, rng, 7, 22, 4):                                    # 縁石際/歩道端の雑草
                if rng.random() < 0.7 * age:
                    lat = p.half + 0.03 if rng.random() < 0.7 else p.half + sw - 0.08
                    x, y, a = at(s, sg * lat)
                    if area.contains(Point(x, y)):
                        sc = rng.uniform(0.5, 1.0)
                        inst.append(Inst(rng.choice(["veg_grass_tuft_0", "veg_grass_tuft_1", "veg_grass_plume_0"]), x, y, T(x, y) + curb, rng.uniform(0, 6.28), sc, sc, sc))
                        n["weed"] += 1
    w["overlay_stats"] = n
    return inst
