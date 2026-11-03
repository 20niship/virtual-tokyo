"""道路ファニチャの配置: 信号機(交差点の各腕: 車両用/歩行者用/アーム式/押ボタン/制御機)、街路灯(道路種別・遊歩道・護岸・ハイマスト)、標識(規制/警戒/指示/補助/案内/路線番号)。
出力は assemble.Inst のリスト(建物と同じ PointInstancer 方式でUSD化)。"""
import math
import random
from collections import defaultdict

import numpy as np
from shapely.geometry import LineString, Point
from shapely.prepared import prep

from .assemble import Inst
from .ground import land_polygon  # noqa: F401
from .modules.library import REG
from .signs import load_meta

CLASS_RANK = {"motorway": 6, "trunk": 5, "primary": 4, "secondary": 3, "tertiary": 2, "unclassified": 1, "residential": 1, "living_street": 0, "service": 0}


def facing_rot(dx, dy):
    """モジュールの+y(前)が方向(dx,dy)を向くz回転"""
    return math.atan2(dy, dx) - math.pi / 2


def arm_rot(dx, dy):
    """モジュールの+x が方向(dx,dy)を向くz回転(アーム/街路灯)"""
    return math.atan2(dy, dx)


class Placer:
    def __init__(self, world, info, cfg, seed):
        self.zf = world["zf"]
        self.land = prep(world["land"])
        self.cw = prep(info["cw"].buffer(0.02))
        self.sw = info["sw"]
        self.rng = random.Random(seed)
        self.cfg = cfg
        self.out = []
        self.taken = defaultdict(list)    # グリッド→位置(ポール同士の最小間隔)
        self.meta = load_meta()["signs"]

    def ok(self, x, y, r=0.9):
        if self.cw.contains(Point(x, y)) or not self.land.contains(Point(x, y)):
            return False
        g = (int(x // 6), int(y // 6))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for (px, py) in self.taken[(g[0] + dx, g[1] + dy)]:
                    if (px - x) ** 2 + (py - y) ** 2 < r * r:
                        return False
        self.taken[g].append((x, y))
        return True

    def z(self, x, y):
        return self.zf(x, y) + (0.02 + 0.12 if self.sw.contains(Point(x, y)) else 0.02)

    def put(self, name, x, y, z, rot, sx=1.0, sy=1.0, sz=1.0):
        assert name in REG, name
        self.out.append(Inst(name, x, y, z, rot, sx, sy, sz))

    # ---- 標識(柱+板) ----
    def sign(self, x, y, face, boards, pole=None, z0=None):
        """boards=[(sign名, 板中心の地上高)]。face=(dx,dy)=板が向く方向(接近する車両側)"""
        if not self.ok(x, y, 0.8):
            return False
        z = self.z(x, y) if z0 is None else z0
        big = max(self.meta[b[0]]["w"] for b in boards) > 0.9
        if pole is None:
            pole = "pole_sign_double_large" if big else f"pole_sign_round_{30 if max(b[1] for b in boards) <= 3.0 else 36}"
        rot = facing_rot(*face)
        fx, fy = face
        if pole == "pole_sign_double_large":
            w = max(self.meta[b[0]]["w"] for b in boards)
            self.put(pole, x, y, z, rot, sx=max(1.0, w / 1.1))
            off = 0.14
        else:
            self.put(pole, x, y, z, rot)
            off = 0.075
        for name, h in boards:
            info = self.meta[name]
            self.put(f"sign_{name}", x + fx * off, y + fy * off, z + h, rot)
        return True


def _signal_style(rng, cfg):
    age = cfg["city_age"]
    era = rng.choices(["old", "led", "slim"], [0.15 + age * 0.35, 0.5 - age * 0.1, 0.35 - age * 0.25])[0]
    pole = rng.choices(["galv", "white", "dark"], [0.55, 0.3, 0.15])[0]
    cd = rng.random() < 0.35
    return era, pole, cd


def signals(P, info, edges):
    """交差点ごとに信号機一式。接近側ごとに 車両用灯器(柱 or アーム式)、横断歩道の両端に歩行者用灯器+押ボタン、角に制御機"""
    by_node = defaultdict(list)
    for a in info["arms"]:
        by_node[a[1]].append(a)
    rng = P.rng
    for node, arms in by_node.items():
        rank = max(CLASS_RANK.get(a[2].tags["highway"], 0) for a in arms)
        signalized = rank >= 3 or len(arms) >= 4 or (rank >= 2 and rng.random() < 0.6)
        if not signalized:
            continue
        era, pole_style, countdown = _signal_style(rng, P.cfg)
        a0 = arms[0][4]
        # フェーズ: 腕0と平行(±)なものがA相
        def dir_of(a):
            _, _, e, is_start, arm, D, (px, py, tx, ty, nlx, nly) = a
            return (tx, ty)
        d0 = dir_of(arms[0])
        placed_ctrl = False
        for a in arms:
            _, _, e, is_start, arm, D, (px, py, tx, ty, nlx, nly) = a
            half = e.prof.half
            approach = (not e.prof.oneway) or ((e.oneway_dir == 1) != is_start)
            phaseA = abs(tx * d0[0] + ty * d0[1]) > 0.7
            vs = "g" if phaseA else "r"
            if rng.random() < 0.08:
                vs = "y"
            ps = "g" if vs == "r" else "r"
            lanes = e.prof.lanes
            if approach:
                # 車両用: 接近車線の左側歩道(-Nl側)に柱。停止線(D+5.2)の少し手前(D+6.5)
                bx, by = px + tx * 4.4 - nlx * (half + 0.85), py + ty * 4.4 - nly * (half + 0.85)
                head = f"sigv_h3_{era}_{vs}"
                if lanes >= 2 and arm.length > D + 14:
                    L = min(12, [x for x in (3, 6, 9, 12) if x >= half * 0.9 + 0.8 + e.prof.bike][0] if half * 0.9 + 0.8 + e.prof.bike <= 12 else 12)
                    if P.ok(bx, by, 1.0):
                        pn = f"pole_signal_arm_{L}m_{'white' if pole_style == 'white' else 'galv'}"
                        P.put(pn, bx, by, P.z(bx, by), arm_rot(nlx, nly))
                        for k in range(lanes):
                            xk = 0.8 + e.prof.bike + (k + 0.5) * e.prof.lane_w + (e.prof.median / 2 if False else 0)
                            if xk > L - 0.4:
                                break
                            hx, hy = bx + nlx * xk, by + nly * xk
                            hz = P.z(bx, by) + 5.85 + 0.18 * xk / L - 0.3
                            P.put(head if k else (head + "_arrow" if (era != "old" and rng.random() < 0.4 and f"{head}_arrow" in REG) else head), hx + tx * 0.14, hy + ty * 0.14, hz, facing_rot(tx, ty))
                else:
                    # 柱式: 歩道の信号柱から標準2.0〜3.5mの腕を車道側へ出し、腕に灯器を取り付ける(灯器底部≥5.1m)
                    if P.ok(bx, by, 1.0):
                        zp = P.z(bx, by)
                        P.put(f"pole_signal_{pole_style}", bx, by, zp, 0)
                        xh_des = 0.85 + e.prof.bike + 0.5 * e.prof.lane_w
                        La = 2.0 if xh_des < 1.7 else (3.0 if xh_des < 2.6 else 3.5)
                        xh = min(La - 0.45, xh_des)
                        kind = {"old": rng.choice(["arc", "single", "parallel"]), "led": rng.choice(["parallel", "parallel", "single"]), "slim": "parallel"}[era]
                        if kind == "arc":
                            La = 2.0; xh = min(xh, 1.55)
                        if kind == "single" and La == 3.5:
                            La = 3.0; xh = min(xh, 2.55)
                        zh = zp + 5.55
                        z_arm = zh if kind == "parallel" else zh + 0.3
                        P.put(f"signal_arm_{kind}_{int(La * 10)}", bx, by, z_arm, arm_rot(nlx, nly))
                        heads = [xh] + ([xh + e.prof.lane_w] if lanes >= 2 and xh + e.prof.lane_w <= La - 0.45 else [])
                        for hx in heads:
                            P.put(head, bx + nlx * hx + tx * 0.14, by + nly * hx + ty * 0.14, zh, facing_rot(tx, ty))
                # 対向(遠側)の2基目: 停止線より先の交差点中心側(信号機は対面にもある)
            # 歩行者用: 横断歩道の両端
            for sgn in (1, -1):
                ex, ey = px + nlx * sgn * (half + 0.9) + tx * 0.0, py + nly * sgn * (half + 0.9)
                if P.ok(ex, ey, 0.9):
                    pole = "pole_signal_ped_3m" if pole_style != "white" else "pole_signal_ped_white"
                    P.put(pole, ex, ey, P.z(ex, ey), 0)
                    face = (-nlx * sgn, -nly * sgn)
                    name = f"sigp_{era}_{ps}" if not (countdown and era == "led") else f"sigp_led_countdown_{ps}"
                    P.put(name, ex + face[0] * 0.16, ey + face[1] * 0.16, P.z(ex, ey) + 2.95, facing_rot(*face))
                    if sgn == 1 or rng.random() < 0.5:
                        P.put("sigp_pushbutton", ex + tx * 0.07, ey + ty * 0.07, P.z(ex, ey) + 1.1, facing_rot(tx, ty)) if False else \
                            P.put("sigp_pushbutton", ex + (-nlx * sgn) * 0.0 + tx * 0.065, ey + ty * 0.065, P.z(ex, ey) + 1.1, facing_rot(tx, ty))
            if not placed_ctrl and rng.random() < 0.8:
                cx, cy = px + tx * 9 - nlx * (half + 1.6), py + ty * 9 - nly * (half + 1.6)
                if P.ok(cx, cy, 1.3):
                    P.put("signal_controller", cx, cy, P.z(cx, cy), facing_rot(nlx, nly))
                    placed_ctrl = True


def stop_and_crossing_signs(P, info):
    """信号のない交差点: 一時停止標識(細い腕)、横断歩道標識。信号交差点の先: 『信号機あり』警戒標識(高速な道路)"""
    by_node = defaultdict(list)
    for a in info["arms"]:
        by_node[a[1]].append(a)
    rng = P.rng
    for node, arms in by_node.items():
        rank = max(CLASS_RANK.get(a[2].tags["highway"], 0) for a in arms)
        signalized = rank >= 3 or len(arms) >= 4
        for a in arms:
            _, _, e, is_start, arm, D, (px, py, tx, ty, nlx, nly) = a
            half = e.prof.half
            approach = (not e.prof.oneway) or ((e.oneway_dir == 1) != is_start)
            if not approach:
                continue
            bx, by = px + tx * 5.8 - nlx * (half + 0.55), py + ty * 5.8 - nly * (half + 0.55)
            if not signalized:
                if CLASS_RANK.get(e.tags["highway"], 0) <= rank - 1 or rng.random() < 0.5:
                    boards = [("reg_stop", 2.55)]
                    if rng.random() < 0.15:
                        boards.append(("aux_pedestrian_priority" if False else "aux_100m", 1.95))
                    P.sign(bx, by, (tx, ty), boards)
                else:
                    P.sign(bx, by, (tx, ty), [("warn_pedestrian_crossing_ahead", 2.6), ("ins_crosswalk", 1.85)] if rng.random() < 0.3 else [("ins_crosswalk", 2.4)])
            else:
                if arm.length > D + 90 and e.prof.speed >= 40 and rng.random() < 0.6:
                    qx, qy = px + tx * 70 - nlx * (half + 0.8), py + ty * 70 - nly * (half + 0.8)
                    P.sign(qx, qy, (tx, ty), [("warn_signal", 2.6), ("aux_100m", 2.0)] if rng.random() < 0.5 else [("warn_signal", 2.6)])
                # 指示/案内: 主要交差点の腕に方向案内(青)
                if CLASS_RANK.get(e.tags["highway"], 0) >= 4 and arm.length > D + 50 and rng.random() < 0.55:
                    gname = rng.choice(["gd_odaiba_left", "gd_odaiba_right", "gd_tokyo_left", "gd_shinagawa_right", "gd_aomi", "gd_ariake", "gd_big_sight", "gd_station_yurikamome", "gd_straight_toyosu", "gd_fuji"])
                    qx, qy = px + tx * 28 - nlx * (half + 1.3), py + ty * 28 - nly * (half + 1.3)
                    P.sign(qx, qy, (tx, ty), [(gname, 3.9)], pole="pole_sign_double_large")
                    if rng.random() < 0.6:
                        qx, qy = px + tx * 24 - nlx * (half + 0.7), py + ty * 24 - nly * (half + 0.7)
                        P.sign(qx, qy, (tx, ty), [(rng.choice(["route_kokudo_357", "route_kokudo_15", "route_kendo_316", "route_kendo_482", "route_shuto_B"]), 2.7)], pole="pole_sign_round_30")


def street_lights(P, edges, info):
    rng = P.rng
    zf = P.zf
    for e in edges:
        if e.kind != "drive" or e.level != 0 or e.tags["highway"] in ("motorway", "motorway_link"):
            continue
        hw = e.tags["highway"]
        rank = CLASS_RANK.get(hw, 0)
        p = e.prof
        L = e.line.length
        if hw == "service" and rng.random() < 0.6 or L < 20:
            continue
        spacing = {5: 32, 4: 32, 3: 34, 2: 38}.get(rank, 42) * rng.uniform(0.9, 1.1)
        age = P.cfg["city_age"]
        if rank >= 4:
            kind = rng.choices(["light_cobra_12m_white", "light_cobra_9m_dark", "light_led_flat_8m", "light_cobra_9m"], [0.3, 0.2, 0.35, 0.15])[0]
        elif rank >= 2:
            kind = rng.choices(["light_cobra_9m", "light_led_flat_8m", "light_old_mercury_9m", "light_cobra_9m_dark"], [0.3, 0.3, 0.1 + age * 0.2, 0.2])[0]
        else:
            kind = rng.choices(["light_led_flat_8m", "light_ped_low_3m", "light_postop_lantern_3m", "light_old_mercury_9m"], [0.4, 0.25, 0.2, 0.15])[0]
        has_med = p.median >= 1.4
        s = spacing * rng.uniform(0.3, 0.8) + 8
        side = rng.choice((1, -1))
        while s < L - 8:
            pt, pt2 = e.line.interpolate(s), e.line.interpolate(min(L, s + 0.8))
            tx, ty = pt2.x - pt.x, pt2.y - pt.y
            d = math.hypot(tx, ty) or 1; tx, ty = tx / d, ty / d
            nlx, nly = -ty, tx
            if has_med and rank >= 3:
                x, y = pt.x, pt.y
                if P.land.contains(Point(x, y)):
                    taken_ok = P.ok(x, y, 1.0) if False else True
                    P.put("light_cobra_double_10m", x, y, zf(x, y) + 0.17, arm_rot(nlx, nly))
            else:
                sw = p.sw_l if side > 0 else p.sw_r
                off = p.half + (0.55 if sw > 0 else 0.9)
                x, y = pt.x + nlx * side * off, pt.y + nly * side * off
                if P.ok(x, y, 1.4):
                    # 腕は道路中心へ(−side*Nl)
                    if kind in ("light_ped_low_3m", "light_postop_lantern_3m"):
                        P.put(kind, x, y, P.z(x, y), 0)
                    else:
                        P.put(kind, x, y, P.z(x, y), arm_rot(-nlx * side, -nly * side))
                side = -side if rank >= 3 else side
            s += spacing * rng.uniform(0.92, 1.08)
    # 歩行者専用路・遊歩道
    for e in edges:
        if e.kind != "walk" or e.level != 0 or e.line.length < 25 or e.tags["highway"] not in ("pedestrian", "footway", "cycleway"):
            continue
        if e.tags["highway"] == "footway" and rng.random() < 0.7:
            continue
        s = 10.0
        kind = rng.choices(["light_postop_globe_4m", "light_postop_lantern_3m", "light_ped_low_3m", "light_bollard_led_1m"], [0.35, 0.25, 0.25, 0.15])[0]
        side = 1
        while s < e.line.length - 6:
            pt, pt2 = e.line.interpolate(s), e.line.interpolate(min(e.line.length, s + 0.8))
            d = math.hypot(pt2.x - pt.x, pt2.y - pt.y) or 1
            nlx, nly = -(pt2.y - pt.y) / d, (pt2.x - pt.x) / d
            x, y = pt.x + nlx * side * 1.5, pt.y + nly * side * 1.5
            if P.ok(x, y, 1.2):
                P.put(kind, x, y, P.z(x, y), 0)
            side = -side
            s += rng.uniform(18, 24)


def quay_lights(P, world):
    """護岸の内側3mに沿って歩行者灯(ポストトップ/ランタン)を約22m間隔で"""
    land = world["land"]
    polys = [land] if land.geom_type == "Polygon" else list(land.geoms)
    rng = P.rng
    for g in polys:
        for ring in [g.exterior, *g.interiors]:
            ring = LineString(ring.coords)
            s = rng.uniform(5, 20)
            kind = rng.choice(["light_postop_globe_4m", "light_postop_lantern_3m"])
            while s < ring.length:
                a, b = ring.interpolate(s), ring.interpolate(min(ring.length, s + 1))
                d = math.hypot(b.x - a.x, b.y - a.y) or 1
                nx, ny = (b.y - a.y) / d, -(b.x - a.x) / d      # 水側(右)
                x, y = a.x - nx * 3.0, a.y - ny * 3.0
                if world["area"].contains(Point(x, y)) and P.ok(x, y, 2.0):
                    P.put(kind, x, y, P.zf(x, y) + 0.02, 0)
                s += 22 * rng.uniform(0.9, 1.1)


def highmasts(P, L, world):
    rng = P.rng
    for f in L.get("landuse", []):
        if f.tags.get("amenity") != "parking" or f.geom.area < 1800 or not world["area"].contains(f.geom.centroid):
            continue
        g = f.geom.buffer(-8)
        if g.is_empty or g.geom_type != "Polygon":
            continue
        n = max(1, int(f.geom.area / 2200))
        x0, y0, x1, y1 = g.bounds
        c = 0
        for _ in range(60):
            if c >= n:
                break
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if g.contains(Point(x, y)) and P.ok(x, y, 25):
                P.put("light_highmast_25m", x, y, P.zf(x, y) + 0.02, 0)
                c += 1


def edge_signs(P, edges, info):
    """区間の標識: 最高速度(+補助)、駐車禁止+時間、車両進入禁止(一方通行の出口)、横断歩道予告、区域内、路線番号など"""
    rng = P.rng
    for e in edges:
        if e.kind != "drive" or e.level != 0 or e.prof is None:
            continue
        p = e.prof
        L = e.line.length
        hw = e.tags["highway"]
        if L < 60 or hw in ("service", "motorway", "motorway_link") or "link" in hw:
            continue
        for end, sgn in ((0.0, 1), (1.0, -1)):
            if p.oneway and ((e.oneway_dir == 1) != (end == 0.0)):
                continue
            s = 22 if end == 0.0 else L - 22
            pt, pt2 = e.line.interpolate(s), e.line.interpolate(min(L, s + 0.8))
            d = math.hypot(pt2.x - pt.x, pt2.y - pt.y) or 1
            tx, ty = (pt2.x - pt.x) / d, (pt2.y - pt.y) / d
            nlx, nly = -ty, tx
            # 接近車の進行方向 = sgn*T、その左 = sgn*Nl 側の歩道/路端
            side = sgn
            sw = p.sw_l if side > 0 else p.sw_r
            off = p.half + (0.55 if sw > 0 else 0.9)
            x, y = pt.x + nlx * side * off, pt.y + nly * side * off
            face = (-tx * sgn, -ty * sgn)
            r = rng.random()
            sp = p.speed if p.speed in (20, 30, 40, 50, 60) else 40
            if r < 0.45:
                P.sign(x, y, face, [(f"reg_speed_{sp}", 2.75)] + ([("aux_zone", 2.15)] if sp <= 30 and rng.random() < 0.5 else []))
            elif r < 0.7:
                P.sign(x, y, face, [("reg_no_parking", 2.75), (rng.choice(["aux_time_8_20", "aux_except_sun", "aux_time_24h"]), 2.2)])
            elif r < 0.8:
                P.sign(x, y, face, [("reg_no_stopping", 2.75)])
            elif r < 0.88 and hw in ("residential", "unclassified", "living_street"):
                P.sign(x, y, face, [("warn_school", 2.65), ("aux_school", 2.15)])
            elif r < 0.94:
                P.sign(x, y, face, [(rng.choice(["warn_bike_crossing", "warn_pedestrian", "warn_two_way", "warn_other"]), 2.6)])
    # 一方通行の出口側に進入禁止
    for e in edges:
        if e.kind == "drive" and e.level == 0 and e.prof and e.prof.oneway and "link" not in e.tags["highway"] and e.line.length > 25:
            end_s = e.line.length - 6 if e.oneway_dir == 1 else 6
            pt, pt2 = e.line.interpolate(end_s), e.line.interpolate(min(e.line.length, end_s + 0.8))
            d = math.hypot(pt2.x - pt.x, pt2.y - pt.y) or 1
            tx, ty = (pt2.x - pt.x) / d, (pt2.y - pt.y) / d
            fdir = 1 if e.oneway_dir == 1 else -1           # 進入禁止は出口側から入ろうとする車に向ける=進行方向
            x, y = pt.x - ty * (-fdir) * (e.prof.half + 0.6), pt.y + tx * (-fdir) * (e.prof.half + 0.6)
            P.sign(x, y, (tx * fdir, ty * fdir), [("reg_no_entry", 2.6)])


def expressway_signs(P, info, edges):
    """高架(首都高)の路側に緑の案内標識(片持ち柱)を約400m間隔、ルート番号付き"""
    rng = P.rng
    names = ["ex_odaiba_exit", "ex_wangan", "ex_toshin", "ex_rainbow", "ex_distance"]
    for e in edges:
        if e.id not in info["elev"] or e.tags["highway"] not in ("motorway",):
            continue
        S, zs, p = info["elev"][e.id]
        L = e.line.length
        s = 120.0
        while s < L - 60:
            pt, pt2 = e.line.interpolate(s), e.line.interpolate(s + 0.8)
            d = math.hypot(pt2.x - pt.x, pt2.y - pt.y) or 1
            tx, ty = (pt2.x - pt.x) / d, (pt2.y - pt.y) / d
            nlx, nly = -ty, tx
            hw = p.half + 1.0
            z = float(np.interp(s, S, zs))
            # 路側(左)の防護壁外側に立て、アームが車線の上へ。板は進行方向に正対(= -T が向き先: 接近車へ)
            x, y = pt.x + nlx * (hw + 0.5), pt.y + nly * (hw + 0.5)
            name = rng.choice(names)
            info_b = P.meta[name]
            P.put("pole_sign_cantilever", x, y, z, arm_rot(-nlx, -nly) )
            # 板: アーム先端付近(車道側へ3m), 柱上方4.5m, 前面はT方向(接近車)に向ける
            bx, by = x - nlx * 3.0 + tx * 0.1, y - nly * 3.0 + ty * 0.1
            P.put(f"sign_{name}", bx, by, z + 5.0, facing_rot(-tx, -ty))
            s += rng.uniform(380, 460)
    return


def build_furniture(L, world, edges, info, cfg, seed=7):
    P = Placer(world, info, cfg, seed)
    signals(P, info, edges)
    stop_and_crossing_signs(P, info)
    street_lights(P, edges, info)
    edge_signs(P, edges, info)
    quay_lights(P, world)
    highmasts(P, L, world)
    expressway_signs(P, info, edges)
    return P.out
