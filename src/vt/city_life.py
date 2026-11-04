"""街の生活感の配置(リアリズム強化B): 建物ファサードに沿う自販機/室外機/鉢/郵便受け/雨どい/駐輪/のぼり/提灯/立て看板、道路沿いのゴミ集積所・消火設備・歩道の植込み、
工事現場(足場+養生シート+仮囲い/路上のバリケード)、電柱の付属物と引込線。決定論的。"""
import math

import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point
from shapely.geometry.polygon import orient
from shapely.strtree import STRtree

from .assemble import Inst
from .city_props import RANK, _frame

PIPE = ["gray", "brown", "white"]


class Occ:
    """占有点(家具/樹木/小物)との距離判定。r[m]以内に既存物があれば不可"""

    def __init__(self, pts):
        self.t = cKDTree(np.array(pts)) if len(pts) else None
        self.new = []

    def free(self, x, y, r):
        if self.t is not None and self.t.query_ball_point((x, y), r):
            return False
        return all((x - a) ** 2 + (y - b) ** 2 > r * r for a, b in self.new)

    def add(self, x, y):
        self.new.append((x, y))


def _bheight(b, T):
    z = max(v[2] for v in b.shell.v) if b.shell.v else 0.0
    c = b.meta["foot"].centroid
    return z - T(c.x, c.y)


def facades(w):
    """全建物の外周辺 → dict(p0,p1,n,len,h,foot,bi)。nは外向き単位法線"""
    out = []
    for bi, b in enumerate(w["builts"]):
        g = b.meta.get("foot")
        if g is None:
            continue
        if g.geom_type == "MultiPolygon":
            g = max(g.geoms, key=lambda q: q.area)
        g = orient(g, 1.0)
        h = _bheight(b, w["T"])
        cs = list(g.exterior.coords)
        for (x0, y0), (x1, y1) in zip(cs, cs[1:]):
            L = math.hypot(x1 - x0, y1 - y0)
            if L < 2.2:
                continue
            out.append(dict(p0=(x0, y0), p1=(x1, y1), n=((y1 - y0) / L, -(x1 - x0) / L), len=L, h=h, bi=bi, area=g.area))
    return out


class RoadIndex:
    def __init__(self, w):
        self.edges = [e for e in w["edges"] if e.kind == "drive" and e.level == 0 and e.prof is not None]
        self.tree = STRtree([e.line for e in self.edges])

    def nearest(self, x, y):
        i = int(self.tree.nearest(Point(x, y)))
        e = self.edges[i]
        return e, e.line.distance(Point(x, y))


def _rot(n):
    """モジュールの+y(正面)を単位ベクトルnへ向ける回転"""
    return math.atan2(n[1], n[0]) - math.pi / 2


def frontage(w, rng, occ, rix, fac):
    """ファサード沿いの小物"""
    T, area = w["T"], w["area"]
    out = []
    for f in fac:
        mx, my = (f["p0"][0] + f["p1"][0]) / 2, (f["p0"][1] + f["p1"][1]) / 2
        nx, ny = f["n"]
        e, d = rix.nearest(mx + nx * 1.0, my + ny * 1.0)
        reach = e.prof.half + max(e.prof.sw_l, e.prof.sw_r) + 7
        if d > reach or d < e.prof.half + 0.6:                                  # 道路から遠い/車道に食い込む
            continue
        px, py = e.line.interpolate(e.line.project(Point(mx, my))).coords[0]
        if (px - mx) * nx + (py - my) * ny <= 0:                                # 道路側を向いていない面
            continue
        rank = RANK.get(e.tags.get("highway", ""), 0)
        comm = rank >= 2 and f["area"] > 120
        tang = ((f["p1"][0] - f["p0"][0]) / f["len"], (f["p1"][1] - f["p0"][1]) / f["len"])
        L, h = f["len"], f["h"]

        def put(name, t, off, rot_add=0.0, z=0.0):
            x = f["p0"][0] + tang[0] * t + nx * off
            y = f["p0"][1] + tang[1] * t + ny * off
            if not area.contains(Point(x, y)) or not occ.free(x, y, 0.8):
                return False
            e2, d2 = rix.nearest(x, y)
            if d2 < e2.prof.half + 0.35:
                return False
            occ.add(x, y)
            out.append(Inst(name, x, y, T(x, y) + 0.02 + z, _rot(f["n"]) + rot_add))
            return True
        r = rng.random
        if comm:
            if L > 3.5 and r() < 0.16:
                put(f"lf_vend_{rng.randrange(8)}", rng.uniform(0.8, L - 0.8), 0.5)
            if L > 3.0 and r() < 0.12:
                put("lf_nobori_row" if r() < 0.4 else f"lf_nobori_{rng.randrange(8)}", rng.uniform(0.6, L - 1.5), 1.0, 0.0)
            if L > 3.0 and r() < 0.14:
                put("lf_stand_a" if r() < 0.7 else rng.choice(["lf_stand_panel", "lf_stand_pole"]), rng.uniform(0.6, L - 0.6), 0.9)
            if h < 12 and L > 3.0 and r() < 0.07:
                put(f"lf_chou_{rng.randrange(4)}", rng.uniform(0.6, L - 0.6), 0.0, 0.0, 0.0)
            if L > 5 and r() < 0.1:
                put("lf_bike_row_a" if r() < 0.5 else "lf_bike_row_b", rng.uniform(1.8, L - 1.8), 1.2, math.pi / 2)
            if L > 2.5 and r() < 0.12:
                put(f"lf_pot_{rng.randrange(3)}", rng.uniform(0.9, L - 0.9), 0.6)
            if L > 3 and r() < 0.05:
                put("lf_vend_recycle", rng.uniform(1.5, L - 1.5), 0.4)
        else:
            if L > 2.2 and r() < 0.25:                                             # 郵便受け(門柱)
                put(f"lf_mail_{rng.randrange(3)}", rng.uniform(0.5, L - 0.5), 0.35)
            if L > 3 and r() < 0.3:
                put(f"lf_pot_{rng.randrange(3)}", rng.uniform(0.8, L - 0.8), 0.6)
            if L > 3 and r() < 0.22:
                put(f"lf_ac_{rng.randrange(3)}", rng.uniform(0.8, L - 1.2), 0.1)
            if L > 4 and r() < 0.07:
                put(f"lf_laundry_{rng.randrange(2)}", rng.uniform(1.2, L - 1.2), 0.7)
            if L > 3 and r() < 0.1:
                put("lf_bike_group" if r() < 0.25 else "lf_bike_row_b", rng.uniform(1.8, L - 1.8), 1.2, math.pi / 2)
            if L > 4 and r() < 0.04:
                put("lf_bike_fallen", rng.uniform(1, L - 1), 1.0)
            if r() < 0.06 and rank <= 1:
                put(f"lf_garb_{rng.randrange(4)}", rng.uniform(0.8, L - 1.5), 0.9)
        if r() < 0.05:                                                              # 消火栓箱/消火器
            put("lf_hyd_box" if r() < 0.6 else "lf_fire_ext_box", rng.uniform(0.4, L - 0.4), 0.1)
        if h < 18 and r() < 0.5:                                                    # 縦樋(壁の端)+軒樋
            c = rng.choice(PIPE)
            for t in (0.15, L - 0.15):
                if r() < 0.55:
                    x = f["p0"][0] + tang[0] * t + nx * 0.02
                    y = f["p0"][1] + tang[1] * t + ny * 0.02
                    if area.contains(Point(x, y)):
                        z0 = T(x, y)
                        top = min(h, 14.0) - 0.2
                        k = 0
                        while z0 + k * 3.0 < z0 + top - 1.5:
                            out.append(Inst(f"lf_down_{c}_3m", x, y, z0 + 0.02 + k * 3.0, _rot(f["n"])))
                            k += 1
                        out.append(Inst(f"lf_down_{c}_base", x, y, z0 + 0.02, _rot(f["n"])))
    return out


def planters(w, rng, occ, rix):
    """幅の広い歩道の道路側に植込み(植樹帯)を並べる。交差点付近・既存物のある所は避ける"""
    T, area = w["T"], w["area"]
    out = []
    for e in rix.edges:
        p, L = e.prof, e.line.length
        rank = RANK.get(e.tags.get("highway", ""), 0)
        if rank < 2 or L < 50 or rng.random() > 0.45:
            continue
        for sg, sw in ((1, p.sw_l), (-1, p.sw_r)):
            if sw < 3.0 or rng.random() > 0.55:
                continue
            s = rng.uniform(16, 30)
            while s < L - 16:
                x, y, tx, ty = _frame(e.line, s)
                lat = sg * (p.half + 0.55)
                cx, cy = x - ty * lat, y + tx * lat
                k = 0
                while k < rng.randint(1, 3) and s + 2.2 * (k + 1) < L - 14:
                    sx, sy, _, _ = _frame(e.line, s + 2.2 * k)
                    qx, qy = sx - ty * lat, sy + tx * lat
                    if area.contains(Point(qx, qy)) and occ.free(qx, qy, 1.3):
                        occ.add(qx, qy)
                        out.append(Inst(rng.choice(["lf_planter_strip_a", "lf_planter_strip_b"]), qx, qy, T(qx, qy) + p.curb_h + 0.01, math.atan2(ty, tx)))
                    k += 1
                s += rng.uniform(25, 60)
    return out


def sidewalk_items(w, rng, occ, rix):
    """歩道上の駐輪/消火栓標識/防火水槽標識/ゴミ集積所(生活道路)/工事の路上設備"""
    T, area = w["T"], w["area"]
    out = []
    for e in rix.edges:
        p, L = e.prof, e.line.length
        rank = RANK.get(e.tags.get("highway", ""), 0)
        if L < 20:
            continue
        for sg, sw in ((1, p.sw_l), (-1, p.sw_r)):
            if sw < 1.2:
                continue
            for s in np.arange(8, L - 8, rng.uniform(70, 130)):
                x, y, tx, ty = _frame(e.line, float(s))
                lat = sg * (p.half + sw - 0.6)
                cx, cy = x - ty * lat, y + tx * lat
                if not area.contains(Point(cx, cy)) or not occ.free(cx, cy, 1.4):
                    continue
                face = math.atan2(ty, tx) - sg * math.pi / 2                         # 道路側を向く
                rr = rng.random()
                if rank <= 1 and rr < 0.3:
                    name = f"lf_garb_{rng.randrange(2)}"
                elif rr < 0.55:
                    name = "lf_fire_cistern_sign" if rr < 0.4 else "lf_hyd_box"
                else:
                    continue
                occ.add(cx, cy)
                out.append(Inst(name, cx, cy, T(cx, cy) + p.curb_h + 0.02, face - math.pi / 2))
    return out


def roadworks(w, rng, occ, rix):
    """数か所の道路工事: バリケード+コーン+工事標識(路肩寄り)。歩行者通行止めの仮囲いは工事建物側で"""
    T, area = w["T"], w["area"]
    out = []
    es = [e for e in rix.edges if RANK.get(e.tags.get("highway", ""), 0) in (1, 2, 3) and e.line.length > 40]
    rng.shuffle(es)
    for e in es[:max(1, len(rix.edges) // 140)]:
        p = e.prof
        s0 = rng.uniform(14, e.line.length - 30)
        sg = rng.choice((1, -1))
        for k in range(rng.randint(2, 4)):
            x, y, tx, ty = _frame(e.line, s0 + k * 2.4)
            lat = sg * (p.half - 1.4)
            cx, cy = x - ty * lat, y + tx * lat
            if area.contains(Point(cx, cy)):
                out.append(Inst("lf_barri_fence", cx, cy, T(cx, cy) + 0.02, math.atan2(ty, tx)))
        for k, s in enumerate((s0 - 6, s0 - 3, s0 + 12, s0 + 15)):
            x, y, tx, ty = _frame(e.line, max(1, min(e.line.length - 1, s)))
            lat = sg * (p.half - 1.0 - 0.4 * k)
            cx, cy = x - ty * lat, y + tx * lat
            if area.contains(Point(cx, cy)):
                out.append(Inst("lf_cone_bar", cx, cy, T(cx, cy) + 0.02, math.atan2(ty, tx) + math.pi / 2))
        x, y, tx, ty = _frame(e.line, s0 - 9)
        lat = sg * (p.half - 0.5)
        out.append(Inst("lf_barri_sign", x - ty * lat, y + tx * lat, T(x - ty * lat, y + tx * lat) + 0.02, math.atan2(ty, tx) + math.pi))
    return out


def construction(w, rng, rix, fac, n_max=8):
    """中層建物の一部を足場+養生シートで覆い、道路側に仮囲いを立てる"""
    T = w["T"]
    out = []
    by = {}
    for f in fac:
        by.setdefault(f["bi"], []).append(f)
    cand = [bi for bi, fs in by.items() if 8 < fs[0]["h"] < 32 and fs[0]["area"] > 60]
    rng.shuffle(cand)
    for bi in cand[:n_max]:
        fs = by[bi]
        h = fs[0]["h"]
        lifts = max(2, min(9, int(h / 1.9)))
        mat = rng.choice(["white", "gray", "blue", "green"])
        for f in fs:
            mx, my = (f["p0"][0] + f["p1"][0]) / 2, (f["p0"][1] + f["p1"][1]) / 2
            e, d = rix.nearest(mx + f["n"][0] * 3, my + f["n"][1] * 3)
            toward = (d < 40)
            if f["len"] < 3.6 or (not toward and rng.random() < 0.5):
                continue
            nx, ny = f["n"]
            tx, ty = (f["p1"][0] - f["p0"][0]) / f["len"], (f["p1"][1] - f["p0"][1]) / f["len"]
            nb = int(f["len"] / 1.8)
            for i in range(nb):
                t = 0.9 + i * 1.8 + (f["len"] - nb * 1.8) / 2 - 0.9
                # モジュールは中心x=0, y=0..0.9: 壁から0.15m離す
                cx = f["p0"][0] + tx * (t + 0.9) + nx * 0.15
                cy = f["p0"][1] + ty * (t + 0.9) + ny * 0.15
                z0 = T(cx, cy)
                rot = _rot(f["n"])
                out.append(Inst("lf_scaf_base", cx, cy, z0, rot))
                for k in range(lifts):
                    out.append(Inst("lf_scaf_bay", cx, cy, z0 + 0.2 + k * 1.9, rot))
                    out.append(Inst(f"lf_scaf_sheet_{mat}", cx + nx * 0.93, cy + ny * 0.93, z0 + 0.2 + k * 1.9 + 0.05, rot))
            if toward and f["len"] > 6:                                              # 道路側の仮囲い(歩道に近い面だけ)
                nh = int(f["len"] / 3.0)
                for i in range(nh):
                    cx = f["p0"][0] + tx * (1.5 + i * 3.0) + nx * 2.2
                    cy = f["p0"][1] + ty * (1.5 + i * 3.0) + ny * 2.2
                    out.append(Inst(f"lf_hoard_{rng.choice(['white', 'gray', 'green'])}", cx, cy, T(cx, cy), _rot(f["n"])))
                    if i == nh // 2:
                        out.append(Inst("lf_hoard_gate", cx, cy, T(cx, cy), _rot(f["n"])))
    return out


def pole_extras(w, rng, poles):
    """電柱に巻き看板/番号札/防犯灯/昇柱ボルトを付ける"""
    out = []
    for p in poles:
        if not p.name.startswith("utility_pole"):
            continue
        r = rng.random
        if r() < 0.4:
            out.append(Inst(f"lf_pole_banner_{rng.randrange(3)}", p.x, p.y, p.z, p.rot))
        if r() < 0.7:
            out.append(Inst("lf_pole_plate", p.x, p.y, p.z, p.rot))
        if r() < 0.3:
            out.append(Inst("lf_pole_lamp", p.x, p.y, p.z, p.rot + rng.choice([0, math.pi])))
        if r() < 0.5:
            out.append(Inst("lf_pole_steps", p.x, p.y, p.z, p.rot))
    return out


def service_drops(w, rng, poles, fac):
    """電柱から最寄りの建物壁面への引込線(たるみ付きの細線)。ワイヤの Mesh を返す"""
    from .modules.geom import Mesh
    from .world import sweep
    T = w["T"]
    M = Mesh()
    if not fac:
        return M
    mids = np.array([[(f["p0"][0] + f["p1"][0]) / 2, (f["p0"][1] + f["p1"][1]) / 2] for f in fac])
    kd = cKDTree(mids)
    prof = lambda i: [(-0.006, -0.006, "wire"), (0.006, -0.006, "wire"), (0.006, 0.006, "wire"), (-0.006, 0.006, "wire")]
    for p in poles:
        if not p.name.startswith("utility_pole") or rng.random() > 0.8:
            continue
        for d, j in zip(*kd.query((p.x, p.y), k=3, distance_upper_bound=26)):
            if not np.isfinite(d) or rng.random() > 0.55:
                continue
            f = fac[int(j)]
            nx, ny = f["n"]
            if (p.x - mids[j][0]) * nx + (p.y - mids[j][1]) * ny <= 0:              # 柱が壁の外側にあること
                continue
            tx, ty = (f["p1"][0] - f["p0"][0]) / f["len"], (f["p1"][1] - f["p0"][1]) / f["len"]
            t = max(0.5, min(f["len"] - 0.5, (p.x - f["p0"][0]) * tx + (p.y - f["p0"][1]) * ty))
            bx, by = f["p0"][0] + tx * t + nx * 0.1, f["p0"][1] + ty * t + ny * 0.1
            zb = T(bx, by) + min(f["h"] - 0.5, rng.choice([3.4, 5.6, 6.0]))
            z0 = p.z + rng.choice([8.8, 9.2, 9.6])
            Ln = math.hypot(bx - p.x, by - p.y)
            n = max(5, int(Ln / 2))
            P, Z = [], []
            for i in range(n + 1):
                u = i / n
                P.append((p.x + (bx - p.x) * u, p.y + (by - p.y) * u))
                Z.append(z0 + (zb - z0) * u - 4 * 0.015 * Ln * u * (1 - u))
            sweep(M, P, prof, Z)
    return M


def build_life(w, rng, poles, occ_pts):
    """全部入り: 戻り値 (インスタンス, 引込線Mesh)"""
    rix = RoadIndex(w)
    fac = facades(w)
    occ = Occ(occ_pts)
    out = []
    out += frontage(w, rng, occ, rix, fac)
    out += planters(w, rng, occ, rix)
    out += sidewalk_items(w, rng, occ, rix)
    out += roadworks(w, rng, occ, rix)
    out += construction(w, rng, rix, fac)
    out += pole_extras(w, rng, poles)
    return out, service_drops(w, rng, poles, fac)
