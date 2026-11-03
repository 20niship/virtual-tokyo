"""フェーズC: 高架道路(首都高)の詳細化とレインボーブリッジ。
install(L, world) で roads.elevated_roads を本モジュールの詳細版に差し替える(roads.py/rail.py は無改変)。"""
import math
import random
from collections import defaultdict

import numpy as np
from shapely.geometry import LineString, Point

from . import roads
from .assemble import Inst
from .modules.geom import Mesh
from .modules.geom3 import beam, frustum, hexa, tube3
from .roads import LEVEL_H, deck_z
from .world import frames, stripe, sweep

ZU, ZL = 52.5, 44.5          # レインボーブリッジ 上段(首都高)/下段(臨港道路+ゆりかもめ)の路面高(海面上)
TOWER_TOP = 126.0
MAIN_SPAN = 570.0
HALF_T = 13.5                # 主ケーブル/側面トラス面の中心線からの距離


def sm(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


class Rainbow:
    """東京港連絡橋の中心線と、位置から橋の高さへの重みを与える(接続する高架も滑らかに持ち上げるため中心線の延長上で評価)"""

    EXT = 900.0
    RAMP = 380.0

    def __init__(self, cl):
        self.cl = cl
        self.Lc = cl.length
        c = list(cl.coords)
        t0 = np.array(c[1]) - np.array(c[0]); t0 /= np.hypot(*t0)
        t1 = np.array(c[-1]) - np.array(c[-2]); t1 /= np.hypot(*t1)
        self.ext = LineString([tuple(np.array(c[0]) - t0 * self.EXT)] + c + [tuple(np.array(c[-1]) + t1 * self.EXT)])
        self.u_a, self.u_b = 56.0, self.Lc - 56.0
        mid = self.Lc / 2
        self.u_t = (mid - MAIN_SPAN / 2, mid + MAIN_SPAN / 2)

    def at(self, u, off=0.0):
        """中心線上のu[m]からoff(左+)の点 (x,y,tx,ty)"""
        p = self.cl.interpolate(min(max(u, 0), self.Lc)); q = self.cl.interpolate(min(max(u, 0) + 1.0, self.Lc))
        if q.distance(p) < 1e-6:
            p = self.cl.interpolate(self.Lc - 1.0); q = self.cl.interpolate(self.Lc)
        tx, ty = q.x - p.x, q.y - p.y
        d = math.hypot(tx, ty) or 1
        tx, ty = tx / d, ty / d
        return p.x - ty * off, p.y + tx * off, tx, ty

    def w(self, x, y):
        pt = Point(x, y)
        u = self.ext.project(pt) - self.EXT
        d = self.ext.distance(pt)
        wu = sm((u - (self.u_a - self.RAMP)) / self.RAMP) * sm(((self.u_b + self.RAMP) - u) / self.RAMP)
        return wu * (1 - sm((d - 28) / 24))

    def zb(self, level):
        return ZU if level >= 4 else ZL if level == 3 else None


RB = None


def find_rainbow(L):
    ups = [f for f in L["roads"] if f.tags.get("highway") == "motorway" and "東京港連絡橋" in f.tags.get("name", "") and f.geom.length > 800]
    if len(ups) < 2:
        return None
    a, b = ups[0].geom, ups[1].geom
    if Point(a.coords[0]).distance(Point(b.coords[0])) > 100:
        a = LineString(list(a.coords)[::-1])
    N = 60
    pts = []
    for i in range(N + 1):
        p, q = a.interpolate(i / N, normalized=True), b.interpolate(i / N, normalized=True)
        pts.append(((p.x + q.x) / 2, (p.y + q.y) / 2))
    return Rainbow(LineString(pts))


def blended(zs, pts, level):
    """既定の高架高さzsを、橋の中心線に沿って橋の路面高へ滑らかに持ち上げる。戻り値(新zs, 各点の橋重みw)"""
    if RB is None or RB.zb(level) is None:
        return zs, [0.0] * len(zs)
    zb = RB.zb(level)
    ws = [RB.w(x, y) for x, y in pts]
    return [z + w * (zb - z) for z, w in zip(zs, ws)], ws


# ---------------- 橋脚 ----------------
def _cap_arm(m, x0, x1, ydir, ycen, z_top, d0, d1, wy, mat):
    """柱から張り出す横梁(梁せいがd0→d1と先細り)。x方向=橋軸直角, y=橋軸"""
    P = [(x0, ycen - wy / 2, z_top - d0), (x1, ycen - wy / 2, z_top - d1), (x1, ycen + wy / 2, z_top - d1), (x0, ycen + wy / 2, z_top - d0),
         (x0, ycen - wy / 2, z_top), (x1, ycen - wy / 2, z_top), (x1, ycen + wy / 2, z_top), (x0, ycen + wy / 2, z_top)]
    return P


def pier(mesh, x, y, ang, z_ground, z_deck, th, hw, rng, kind=None, in_water=False):
    """首都高の橋脚。T型(1本柱+先細り横梁) または 門型(2本柱+横梁)。柱脚に根巻き、桁との間に支承。
    ローカル: x=橋軸直角(左+), y=橋軸"""
    H = z_deck - th - 0.28 - z_ground       # 柱底→横梁天端
    if H < 2.0:
        return
    kind = kind or ("portal" if hw > 6.5 else "T")
    m = Mesh()
    base_z = z_ground - (6.0 if in_water else 0.5)
    d_cap = min(2.0, max(1.1, H * 0.22))
    top = z_deck - th - 0.28
    cols = [0.0] if kind == "T" else [-hw * 0.55, hw * 0.55]
    cw, cl_ = (2.2, 2.0) if kind == "T" else (1.9, 1.8)
    for cx in cols:
        col_top = top - d_cap
        # 柱: 下がやや太い先細り + 柱頭の張り出し
        frustum(m, cx, 0, base_z, col_top, cw + 0.4, cl_ + 0.3, cw, cl_, 0.0, "concrete_formed")
        frustum(m, cx, 0, col_top - 0.9, col_top, cw, cl_, cw + 0.5, cl_ + 0.3, 0.0, "concrete_formed")
        # 根巻き(1.2m)と基礎(フーチング)
        m.box(cx - (cw + 0.7) / 2, -(cl_ + 0.6) / 2, z_ground - 0.5, cx + (cw + 0.7) / 2, (cl_ + 0.6) / 2, z_ground + 1.2, "concrete_formed")
        m.box(cx - (cw + 2.4) / 2, -(cl_ + 2.4) / 2, z_ground - 1.5, cx + (cw + 2.4) / 2, (cl_ + 2.4) / 2, z_ground - 0.5, "concrete_formed")
    # 横梁(中央が深く両端が浅い)
    xs = hw * 0.9 if kind == "T" else hw * 0.95
    wy = 1.9
    if kind == "T":
        for sgn in (-1, 1):
            hexa(m, _cap_arm(m, 0, sgn * xs, 1, 0, top, d_cap * 1.15, d_cap * 0.55, wy, ""), "concrete_formed")
    else:
        hexa(m, _cap_arm(m, -xs, xs, 1, 0, top, d_cap, d_cap, wy, ""), "concrete_formed")
    # 支承(ゴム+鋼製)
    for bx in ([-hw * 0.28, hw * 0.28] if kind == "T" else [cx * 0.9 for cx in cols]):
        m.box(bx - 0.4, -0.35, top, bx + 0.4, 0.35, top + 0.1, "steel_gray")
        m.box(bx - 0.34, -0.3, top + 0.1, bx + 0.34, 0.3, top + 0.26, "rubber")
    mesh.add(m.transformed(ang, x, y, 0.0))


# ---------------- 高架道路(首都高) ----------------
def _deck_profile(hw, bw, th, webmat, botmat):
    b = "concrete_formed"
    return [(-bw / 2, -th, botmat), (bw / 2, -th, webmat), (hw - 0.9, -0.55, webmat), (hw - 0.45, -0.38, "concrete_formed"), (hw, -0.28, b), (hw, 0.0, b),
            (hw, 0.3, b), (hw - 0.1, 0.82, b), (hw - 0.32, 0.82, b), (hw - 0.5, 0.3, b), (hw - 0.5, 0.0, "asphalt"),
            (-hw + 0.5, 0.0, b), (-hw + 0.5, 0.3, b), (-hw + 0.32, 0.82, b), (-hw + 0.1, 0.82, b), (-hw, 0.3, b), (-hw, 0.0, b),
            (-hw, -0.28, b), (-hw + 0.45, -0.38, "concrete_formed"), (-hw + 0.9, -0.55, webmat)]


def _joint(mesh, x, y, ang, z, width):
    """伸縮装置: 鋼製プレート+両側のゴム目地(路面を横切る)"""
    j = Mesh()
    j.box(-0.17, -width / 2, 0, 0.17, width / 2, 0.035, "steel_gray")
    for dx in (-0.24, 0.24):
        j.box(dx - 0.05, -width / 2, 0, dx + 0.05, width / 2, 0.02, "rubber")
    mesh.add(j.transformed(ang, x, y, z + 0.012))


def elevated_roads(edges, world, cfg, rng, elev=None):
    zf, land = world["zf"], world["land"]
    mesh = Mesh()
    insts = []
    el = [e for e in edges if e.kind == "drive" and e.level > 0 and world["area"].intersects(e.line)]
    nh = {}
    allnodes = defaultdict(list)
    for e in edges:
        if e.kind == "drive":
            for k in (e.a, e.b):
                allnodes[k].append(e)
    for k, lst in allnodes.items():
        nh[k] = min(LEVEL_H.get(x.level, 0.0) if x.level > 0 else 0.0 for x in lst)
    hw_of = {e.id: max(e.prof.half + 1.0, 3.0) for e in el}
    for e in el:
        p = e.prof
        L = e.line.length
        Hl = LEVEL_H.get(e.level, 7.0 * e.level)
        n = max(2, int(L / 3))
        S = [L * i / n for i in range(n + 1)]
        pts = [(e.line.interpolate(s).x, e.line.interpolate(s).y) for s in S]
        ga, gb = zf(*pts[0]), zf(*pts[-1])
        zfn = deck_z(e.line, zf, Hl, ga + nh[e.a], gb + nh[e.b], ga, gb)
        zs, ws = blended([zfn(s) for s in S], pts, e.level)
        if elev is not None:
            elev[e.id] = (S, zs, p)
        hw0 = hw_of[e.id]
        # ランプ分岐/合流のテーパー: 接続する別の高架の幅へ端から70mで遷移
        def taper_w(end_key, s_from_end):
            others = [hw_of[o.id] for o in allnodes[end_key] if o.id != e.id and o.id in hw_of]
            if not others:
                return hw0
            oth = max(others)
            if abs(oth - hw0) < 0.4:
                return hw0
            return oth + (hw0 - oth) * sm(s_from_end / 70.0)
        hws = [min(taper_w(e.a, s), taper_w(e.b, L - s)) if True else hw0 for s in S]
        hws = [max(taper_w(e.a, s) if s < 70 else (taper_w(e.b, L - s) if L - s < 70 else hw0), 2.6) for s in S]
        steel = (e.id % 3 != 0)
        webmat, botmat = ("steel_gray", "steel_gray") if steel else ("concrete_formed", "concrete_formed")
        ths = []
        for i in range(n + 1):
            clear = zs[i] - zf(*pts[i])
            th = max(0.62, min(1.9, clear - 0.05))
            ths.append(th * (1 - 0.62 * ws[i]) if ws[i] > 0.02 else th)     # 橋の本体区間は薄い床版(下はトラス)
        def prof(i):
            hw, th = hws[i], max(0.6, ths[i])
            bw = max(1.6, 2 * hw - 2 * min(2.3, hw * 0.4))
            return _deck_profile(hw, bw, th, webmat, botmat)
        sweep(mesh, pts, prof, zs)
        # 側面のリブ(鋼桁ウェブの水平補剛材)と排水管
        mid = lambda i: (max(1.6, 2 * hws[i] - 2 * min(2.3, hws[i] * 0.4)) / 2 + hws[i] - 0.9) / 2
        for sg in (-1, 1):
            if steel:
                rib = lambda i, sg=sg: [(sg * (mid(i) + 0.03) - 0.05, -0.18 + (-ths[i] - 0.55) / 2, "steel_gray"), (sg * (mid(i) + 0.03) + 0.05, -0.18 + (-ths[i] - 0.55) / 2, "steel_gray"),
                                         (sg * (mid(i) + 0.03) + 0.05, -0.1 + (-ths[i] - 0.55) / 2, "steel_gray"), (sg * (mid(i) + 0.03) - 0.05, -0.1 + (-ths[i] - 0.55) / 2, "steel_gray")]
                # 向きをCCWに揃える(sgで反転)
                def rib_p(i, sg=sg):
                    r = rib(i, sg)
                    return r if sg > 0 else r[::-1]
                sweep(mesh, pts, rib_p, zs)
            pipe = lambda i, sg=sg: [(sg * (hws[i] - 0.72) + 0.09 * math.cos(2 * math.pi * k / 8), -0.74 + 0.09 * math.sin(2 * math.pi * k / 8), "steel_gray") for k in range(8)]
            sweep(mesh, pts, lambda i, sg=sg: pipe(i, sg) if sg > 0 else pipe(i, sg)[::-1], zs)
        # 路面標示(従来どおり)
        zline = lambda x, y, line=e.line, S=S, zs=zs: float(np.interp(line.project(Point(x, y)), S, zs))
        tot = p.lanes * (1 if p.oneway else 2)
        for k in range(1, tot):
            off = (k - tot / 2) * p.lane_w
            mid_line = (not p.oneway and k == tot / 2)
            stripe(mesh, e.line, off, 0.15, 6, 0 if mid_line else 9, "paint_road_yellow" if mid_line else "paint_road_white", zline, 0.012)
        for sg in (-1, 1):
            stripe(mesh, e.line, sg * (tot * p.lane_w / 2 + 0.1), 0.2, 1, 0, "paint_road_white", zline, 0.012)
        # 遮音壁(透明パネル+鋼製支柱): 本線の一部区間のみ。橋の主径間は無し
        if e.tags["highway"] == "motorway" and e.id % 2 == 0:
            for sg in (-1, 1):
                for i in range(0, n, 2):
                    if ws[i] > 0.3:
                        continue
                    x, y = pts[i]; nx_, ny_ = frames(pts)[i][4], frames(pts)[i][5]
                    pc = Mesh()
                    pc.box(-0.04, -0.06, 0, 0.04, 0.06, 2.1, "steel_gray")
                    pc.box(-0.01, 0.0, 0.25, 0.01, 6.0, 2.0, "glass_clear")
                    tx_, ty_ = frames(pts)[i][2], frames(pts)[i][3]
                    mesh.add(pc.transformed(math.atan2(ty_, tx_) - math.pi / 2, x + nx_ * sg * (hws[i] - 0.2), y + ny_ * sg * (hws[i] - 0.2), zs[i] + 0.82))
        # 伸縮装置(両端と90m毎)・照明柱ベース(30m毎)
        for s in sorted({0.5, L - 0.5, *[x for x in np.arange(90, L - 40, 90.0)]}):
            i = min(n, int(round(s / (L / n))))
            x, y, tx_, ty_, nx_, ny_ = frames(pts)[i]
            _joint(mesh, x, y, math.atan2(ty_, tx_), zs[i], 2 * hws[i] - 1.0)
        for s in np.arange(20, L - 10, 30.0):
            i = min(n, int(round(s / (L / n))))
            if ws[i] > 0.9:
                continue
            x, y, tx_, ty_, nx_, ny_ = frames(pts)[i]
            for sg in (-1, 1):
                b = Mesh()
                b.box(-0.18, -0.14, 0, 0.18, 0.14, 0.04, "steel_galv")
                for dx in (-0.13, 0.13):
                    for dy in (-0.09, 0.09):
                        b.cyl(dx, dy, 0.04, 0.016, 0.04, "z", "steel_galv", 6)
                mesh.add(b.transformed(math.atan2(ty_, tx_), x + nx_ * sg * (hws[i] - 0.21), y + ny_ * sg * (hws[i] - 0.21), zs[i] + 0.82))
        # 橋脚(陸上 + 海上の接続高架)。橋の本体区間(w>0.4)では橋脚を作らない
        spacing = 34.0 if hw0 <= 6.5 else 42.0
        s = spacing / 2
        while s < L:
            i = min(n, int(round(s / (L / n))))
            x, y = pts[i]
            zg = zf(x, y)
            on_land = land.contains(Point(x, y))
            if ws[i] < 0.4 and zs[i] - zg > 3.5 and (on_land or (e.level <= 3 and zs[i] < 30)):
                tx_, ty_ = frames(pts)[i][2], frames(pts)[i][3]
                pier(mesh, x, y, math.atan2(ty_, tx_) - math.pi / 2 + math.pi / 2 * 0, zg, zs[i], max(0.6, ths[i]), hws[i], rng, in_water=not on_land)
            s += spacing * rng.uniform(0.93, 1.07)
    if RB is not None:
        m2, i2 = rainbow_structure(RB, world)
        mesh.add(m2)
        insts.extend(i2)
    elevated_roads.insts = insts
    return mesh


elevated_roads.insts = []


# ---------------- レインボーブリッジ(吊橋) ----------------
def rainbow_structure(rb, world):
    """補剛トラス(2層)、主塔2基、主ケーブル+ハンガー、アンカレイジ、橋脚。ハンガー金具はモジュール(hanger_clamp)としてInst出力"""
    m = Mesh()
    insts = []
    ua, ub = rb.u_a, rb.u_b
    ut1, ut2 = rb.u_t
    TC_U, TC_L = ZU - 1.2, ZL - 1.2          # 上弦材/下弦材(各デッキ直下)
    PANEL = 16.0
    xs = np.arange(ua, ub + 0.1, PANEL)
    bot_u, bot_l = ZU - 12.5, ZL - 4.6
    # 側面トラス(2層: 上段デッキと下段デッキの間に垂直材+斜材、さらに下段の下に下弦材)
    for sg in (-1, 1):
        P = lambda u, z, sg=sg: (*rb.at(u, sg * HALF_T)[:2], z)
        for a, b in zip(xs, xs[1:]):
            beam(m, P(a, ZU - 1.0), P(b, ZU - 1.0), 1.0, 1.1, "truss_white")                  # 上弦材(上段デッキ下)
            beam(m, P(a, ZL - 1.0), P(b, ZL - 1.0), 0.9, 1.0, "truss_white")                  # 中弦材(下段デッキ下)
            beam(m, P(a, ZL - 4.6), P(b, ZL - 4.6), 0.9, 1.0, "truss_white")                  # 下弦材
            beam(m, P(a, ZU - 1.0), P((a + b) / 2, ZL - 4.6), 0.55, 0.7, "truss_white")       # ワーレン斜材
            beam(m, P((a + b) / 2, ZL - 4.6), P(b, ZU - 1.0), 0.55, 0.7, "truss_white")
        for a in xs:
            beam(m, P(a, ZL - 4.6), P(a, ZU - 1.0), 0.6, 0.8, "truss_white")                  # 垂直材
        # ハンドレール付き側面の防護: 上段デッキ縁の高欄
        for a, b in zip(xs, xs[1:]):
            beam(m, P(a, ZU + 1.0), P(b, ZU + 1.0), 0.1, 0.1, "steel_white")
            beam(m, P(a, ZU + 0.5), P(b, ZU + 0.5), 0.08, 0.08, "steel_white")
    # デッキ床版(オーソトロピック)と横桁
    for a, b in zip(xs, xs[1:]):
        x0, y0, tx, ty = rb.at(a)
        x1, y1, _, _ = rb.at(b)
        ang = math.atan2(y1 - y0, x1 - x0)
        d = Mesh()
        L_ = math.hypot(x1 - x0, y1 - y0)
        d.box(0, -HALF_T - 0.4, ZU - 0.66, L_ + 0.02, HALF_T + 0.4, ZU - 0.04, "steel_gray")
        d.box(0, -HALF_T - 0.4, ZL - 0.66, L_ + 0.02, HALF_T + 0.4, ZL - 0.04, "steel_gray")
        d.box(0.1, -HALF_T, ZU - 2.3, 0.5, HALF_T, ZU - 0.66, "truss_white")           # 上段の横桁
        d.box(0.1, -HALF_T, ZL - 2.3, 0.5, HALF_T, ZL - 0.66, "truss_white")           # 下段の横桁
        m.add(d.transformed(ang, x0, y0, 0.0))
    # 主塔(2基): 門型(斜材なし)。脚は上へ向かって細り、わずかに内側へ傾斜
    for u_t in (ut1, ut2):
        cx, cy, tx, ty = rb.at(u_t)
        rot = math.atan2(ty, tx)
        legs = []
        for sg in (-1, 1):
            lx, ly = rb.at(u_t, sg * HALF_T)[:2]
            frustum(m, lx, ly, -2.0, TOWER_TOP, 4.4, 5.0, 2.6, 3.0, rot, "truss_white", 0.0, -sg * 1.3)
            # 脚の縦リブと外側のプレート継ぎ目
            for z in range(10, 125, 12):
                f = z / TOWER_TOP
                frustum(m, lx, ly, z, z + 0.25, 4.4 - 1.8 * f + 0.1, 5.0 - 2.0 * f + 0.1, 4.4 - 1.8 * f + 0.1, 5.0 - 2.0 * f + 0.1, rot, "steel_white", 0.0, -sg * 1.3 * f)
            legs.append((lx, ly, sg))
        for z in (37.0, 64.0, 92.0, 116.0):          # 門型の横梁
            f = (z + 2) / (TOWER_TOP + 2)
            off = HALF_T - 1.3 * f - (5.0 - 2.0 * f) / 2
            a = (*rb.at(u_t, -off)[:2], z); b = (*rb.at(u_t, off)[:2], z)
            beam(m, a, b, 2.8 - 0.8 * f, 3.0 - 0.6 * f, "truss_white")
        # 頂部のサドル室+航空障害灯
        for sg in (-1, 1):
            lx, ly = rb.at(u_t, sg * (HALF_T - 1.3))[:2]
            hb = Mesh(); hb.box(-1.6, -1.9, 0, 1.6, 1.9, 2.4, "truss_white")
            m.add(hb.transformed(rot, lx, ly, TOWER_TOP - 0.2))
            m.cyl(lx, ly, TOWER_TOP + 2.2, 0.3, 0.5, "z", "beacon_red", 10)
        # 橋脚(ケーソン): 水中から海面上へ
        pb = Mesh()
        pb.box(-9.0, -HALF_T - 6.0, -8.0, 9.0, HALF_T + 6.0, 5.0, "concrete_formed")
        pb.box(-8.0, -HALF_T - 5.0, 5.0, 8.0, HALF_T + 5.0, 7.0, "concrete_formed")
        m.add(pb.transformed(rot, cx, cy, 0.0))
    # アンカレイジ(両端): 直方体基部+台形上部
    anchors = []
    for u_c, sgn in ((ua - 24.0, -1), (ub + 24.0, 1)):
        cx, cy, tx, ty = rb.at(u_c)
        rot = math.atan2(ty, tx)
        ab = Mesh()
        ab.box(-22, -22, -8, 22, 22, 18, "concrete_formed")
        frustum(ab, 0, 0, 18, 33, 44.0, 44.0, 34.0, 36.0, 0.0, "concrete_formed")
        ab.box(-22.5, -22.5, 17.6, 22.5, 22.5, 18.2, "steel_gray")
        m.add(ab.transformed(rot, cx, cy, 0.0))
        anchors.append(u_c)
    # 主ケーブル: アンカレイジ → 塔頂 → (放物線)中央 → 塔頂 → アンカレイジ
    Z_TOP = TOWER_TOP - 1.2
    Z_MID = ZU + 11.0
    Z_ANCH = 31.0
    def zc(u):
        if u <= ut1:
            return Z_ANCH + (Z_TOP - Z_ANCH) * ((u - ua) / (ut1 - ua)) ** 1.1
        if u >= ut2:
            return Z_ANCH + (Z_TOP - Z_ANCH) * ((ub - u) / (ub - ut2)) ** 1.1
        t = (u - (ut1 + ut2) / 2) / (MAIN_SPAN / 2)
        return Z_MID + (Z_TOP - Z_MID) * t * t
    us = list(np.arange(ua, ub, 8.0)) + [ub]
    for sg in (-1, 1):
        off = sg * (HALF_T - 1.3 * 0.0)
        path = [(*rb.at(u, off)[:2], zc(u)) for u in us]
        tube3(m, path, 0.34, "steel_gray", 10)
        # ハンガーロープ(16m毎)とケーブルバンド
        for a in xs:
            if a < ut1 - 1 or a > ut2 + 1:
                if not (ut1 - 130 < a < ut1 or ut2 < a < ut2 + 130):
                    continue
            if abs(a - ut1) < 12 or abs(a - ut2) < 12:
                continue
            px, py, tx, ty = rb.at(a, off)
            zcab = zc(a)
            tube3(m, [(px, py, zcab - 0.4), (px, py, ZU - 0.3)], 0.045, "steel_gray", 6)
            insts.append(Inst("hanger_clamp", px, py, zcab, math.atan2(ty, tx)))
    return m, insts


def install(L):
    """roads.elevated_roads を詳細版へ差し替え、レインボーブリッジ中心線を検出する(多重呼び出し可)"""
    global RB
    RB = find_rainbow(L)
    roads.elevated_roads = elevated_roads
    return RB
