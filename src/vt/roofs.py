"""日本の住宅・農家・アパート・工場の屋根: 切妻/寄棟/入母屋/片流れ。瓦/セメント瓦/スレート/金属の材質をメートルUVで貼る。
軒・破風・棟・鬼瓦・軒樋・竪樋を付ける。ほぼ長方形の平面のみ(それ以外はFalseを返して呼び出し側が陸屋根にする)。"""
import math

from .modules.geom3 import beam

# 屋根材: (材質, 種別, 勾配範囲[deg], 軒の出[m], ケラバ[m], 棟瓦を付けるか)
ROOF_MATS = {
    "kawara": ("roof_kawara", 27, 35, 0.75, 0.35, True),
    "kawara_brown": ("roof_kawara_brown", 27, 35, 0.7, 0.35, True),
    "kawara_hon": ("roof_kawara_hon", 30, 38, 0.95, 0.45, True),
    "cement_red": ("roof_cement_red", 22, 30, 0.55, 0.3, True),
    "cement_blue": ("roof_cement_blue", 22, 30, 0.55, 0.3, True),
    "tanshiki_blue": ("roof_tanshiki_blue", 14, 24, 0.45, 0.25, False),
    "tanshiki_green": ("roof_tanshiki_green", 14, 24, 0.45, 0.25, False),
    "tanshiki_red": ("roof_tanshiki_red", 14, 24, 0.45, 0.25, False),
    "tanshiki_gray": ("roof_tanshiki_gray", 12, 22, 0.45, 0.25, False),
    "slate_dark": ("roof_slate_dark", 18, 28, 0.55, 0.3, False),
    "slate_brown": ("roof_slate_brown", 18, 28, 0.55, 0.3, False),
}


def _rect(poly):
    try:
        r = poly.minimum_rotated_rectangle
    except Exception:
        return None
    if r.geom_type != "Polygon" or poly.area / r.area < 0.85:
        return None
    c = list(r.exterior.coords)[:4]
    e1 = (c[1][0] - c[0][0], c[1][1] - c[0][1])
    e2 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
    l1, l2 = math.hypot(*e1), math.hypot(*e2)
    if l2 > l1:
        e1, e2, l1, l2 = e2, e1, l2, l1
    return r.centroid.x, r.centroid.y, (e1[0] / l1, e1[1] / l1), (e2[0] / l2, e2[1] / l2), l1, l2


def _uv(pts):
    """傾斜面の点列からメートルUV(軒に沿う水平方向, 勾配方向)"""
    a, b, c = pts[0], pts[1], pts[2]
    n = ((b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]), (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]),
         (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
    if n[2] < 0:
        n = (-n[0], -n[1], -n[2])
    ln = math.sqrt(sum(x * x for x in n)) or 1
    n = tuple(x / ln for x in n)
    fall = (-n[0] * n[2], -n[1] * n[2], n[0] ** 2 + n[1] ** 2)
    lf = math.sqrt(sum(x * x for x in fall))
    if lf < 1e-6:
        return None
    fall = tuple(x / lf for x in fall)
    ue = (fall[1] * n[2] - fall[2] * n[1], fall[2] * n[0] - fall[0] * n[2], fall[0] * n[1] - fall[1] * n[0])
    return [(sum((p[i] - a[i]) * ue[i] for i in range(3)), sum((p[i] - a[i]) * fall[i] for i in range(3))) for p in pts]


def build(B, poly, z, rng, kind=None, mat_key=None, wall_mat="spray_main", trim="paint_white", gutters=True):
    """B.shell に屋根を作る。成功でTrue。z=軒の取り付く高さ(壁頂部)"""
    R = _rect(poly)
    if R is None:
        return False
    cx, cy, u, v, l1, l2 = R
    mat_key = mat_key or rng.choice(list(ROOF_MATS))
    mat, d0, d1, ov, ovk, ridge_cap = ROOF_MATS[mat_key]
    kind = kind or rng.choice(["gable", "hip", "gable", "hip", "irimoya" if ridge_cap and l2 > 6.5 else "gable"])
    if l2 < 3.5:
        kind = "katanagare"
    a0, b0 = l1 / 2, l2 / 2
    a, b = a0 + ovk, b0 + ov
    tn = math.tan(math.radians(rng.uniform(d0, d1)))
    sh = B.shell

    def P(s, t, zz):
        return (cx + u[0] * s + v[0] * t, cy + u[1] * s + v[1] * t, zz)

    def plane(pts, m=mat):
        sh.oriented(pts, (0, 0, 1), m, _uv(pts))

    def tri_wall(pts, out, m=wall_mat):
        sh.oriented(pts, out, m)

    def bm(p, q, w, h, m, up=(0, 0, 1)):
        beam(sh, p, q, w, h, m, up)
    ridge_m = "roof_ridge" if ridge_cap else "alu_silver"
    t_fas = 0.2 if ridge_cap else 0.13
    ridge_z = None
    ridge_pts = None
    if kind == "gable":
        h = b * tn
        for sgn in (-1, 1):
            plane([P(-a, sgn * b, z), P(a, sgn * b, z), P(a, 0, z + h), P(-a, 0, z + h)] if sgn < 0 else [P(a, b, z), P(-a, b, z), P(-a, 0, z + h), P(a, 0, z + h)])
        hw = h * (b0 / b)
        for sgn in (-1, 1):
            tri_wall([P(sgn * a0, -b0, z), P(sgn * a0, b0, z), P(sgn * a0, 0, z + hw)], (u[0] * sgn, u[1] * sgn, 0))
            for ss in (-1, 1):                                                           # 破風板(ケラバの見付)
                bm(P(sgn * a, ss * b, z), P(sgn * a, 0, z + h), 0.03, t_fas, trim, (u[0] * sgn, u[1] * sgn, 0))
        ridge_pts = (P(-a, 0, z + h), P(a, 0, z + h))
        eaves = [(P(-a, -b, z), P(a, -b, z)), (P(a, b, z), P(-a, b, z))]
        top = z + h
    elif kind == "hip":
        h = b * tn
        rl = max(0.25, a - b)
        plane([P(-a, -b, z), P(a, -b, z), P(rl, 0, z + h), P(-rl, 0, z + h)])
        plane([P(a, b, z), P(-a, b, z), P(-rl, 0, z + h), P(rl, 0, z + h)])
        plane([P(a, -b, z), P(a, b, z), P(rl, 0, z + h)])
        plane([P(-a, b, z), P(-a, -b, z), P(-rl, 0, z + h)])
        for p, q in ((P(a, -b, z), P(rl, 0, z + h)), (P(a, b, z), P(rl, 0, z + h)), (P(-a, -b, z), P(-rl, 0, z + h)), (P(-a, b, z), P(-rl, 0, z + h))):
            bm(p, q, 0.22 if ridge_cap else 0.06, 0.16 if ridge_cap else 0.05, ridge_m)             # 隅棟
        ridge_pts = (P(-rl, 0, z + h), P(rl, 0, z + h))
        eaves = [(P(-a, -b, z), P(a, -b, z)), (P(a, b, z), P(-a, b, z)), (P(a, -b, z), P(a, b, z)), (P(-a, b, z), P(-a, -b, z))]
        top = z + h
    elif kind == "irimoya":
        b2 = b0 * 0.42
        k = b - b2
        h1 = k * tn
        a2 = a - k
        if a2 < 1.0:
            return build(B, poly, z, rng, "hip", mat_key, wall_mat, trim, gutters)
        h2 = b2 * tn * 1.15
        # 下の寄棟(裾)
        plane([P(-a, -b, z), P(a, -b, z), P(a2, -b2, z + h1), P(-a2, -b2, z + h1)])
        plane([P(a, b, z), P(-a, b, z), P(-a2, b2, z + h1), P(a2, b2, z + h1)])
        plane([P(a, -b, z), P(a, b, z), P(a2, b2, z + h1), P(a2, -b2, z + h1)])
        plane([P(-a, b, z), P(-a, -b, z), P(-a2, -b2, z + h1), P(-a2, b2, z + h1)])
        # 上の切妻(妻飾りの三角)
        plane([P(-a2, -b2, z + h1), P(a2, -b2, z + h1), P(a2, 0, z + h1 + h2), P(-a2, 0, z + h1 + h2)])
        plane([P(a2, b2, z + h1), P(-a2, b2, z + h1), P(-a2, 0, z + h1 + h2), P(a2, 0, z + h1 + h2)])
        for sgn in (-1, 1):
            tri_wall([P(sgn * a2, -b2, z + h1), P(sgn * a2, b2, z + h1), P(sgn * a2, 0, z + h1 + h2)], (u[0] * sgn, u[1] * sgn, 0), "plaster_white")
            for ss in (-1, 1):
                bm(P(sgn * a2, ss * b2, z + h1), P(sgn * a2, 0, z + h1 + h2), 0.04, 0.2, "wood_dark", (u[0] * sgn, u[1] * sgn, 0))
            B.insts.append(_inst("onigawara", P(sgn * (a2 - 0.1), 0, z + h1 + h2 - 0.05), math.atan2(u[1], u[0]) + (0 if sgn > 0 else math.pi)))
        for p, q in ((P(a, -b, z), P(a2, -b2, z + h1)), (P(a, b, z), P(a2, b2, z + h1)), (P(-a, -b, z), P(-a2, -b2, z + h1)), (P(-a, b, z), P(-a2, b2, z + h1))):
            bm(p, q, 0.24, 0.16, ridge_m)
        ridge_pts = (P(-a2, 0, z + h1 + h2), P(a2, 0, z + h1 + h2))
        eaves = [(P(-a, -b, z), P(a, -b, z)), (P(a, b, z), P(-a, b, z)), (P(a, -b, z), P(a, b, z)), (P(-a, b, z), P(-a, -b, z))]
        top = z + h1 + h2
    else:                                                    # katanagare: 片流れ(長辺方向の下がり)
        tn2 = math.tan(math.radians(rng.uniform(8, 16)))
        hh = 2 * b * tn2
        plane([P(-a, -b, z), P(a, -b, z), P(a, b, z + hh), P(-a, b, z + hh)])
        zhi = z + hh * ((b0 + b) / (2 * b))
        zlo = z + hh * ((-b0 + b) / (2 * b))
        for sgn in (-1, 1):
            tri_wall([P(sgn * a0, -b0, z), P(sgn * a0, b0, z), P(sgn * a0, b0, zhi), P(sgn * a0, -b0, zlo)], (u[0] * sgn, u[1] * sgn, 0))
        tri_wall([P(-a0, b0, z), P(a0, b0, z), P(a0, b0, zhi), P(-a0, b0, zhi)], (v[0], v[1], 0))
        bm(P(-a, b, z + hh), P(a, b, z + hh), 0.3, 0.12, ridge_m)                                   # 棟包み
        eaves = [(P(-a, -b, z), P(a, -b, z))]
        for sgn in (-1, 1):
            bm(P(sgn * a, -b, z), P(sgn * a, b, z + hh), 0.03, t_fas, trim, (u[0] * sgn, u[1] * sgn, 0))
        top = z + hh
        ridge_pts = None
    # 棟
    if ridge_pts and kind != "katanagare":
        bm(ridge_pts[0], ridge_pts[1], 0.34 if ridge_cap else 0.2, 0.28 if ridge_cap else 0.1, ridge_m)
        if ridge_cap and kind in ("gable", "hip") and (ridge_pts[1][0] - ridge_pts[0][0]) ** 2 + (ridge_pts[1][1] - ridge_pts[0][1]) ** 2 > 1:
            ang = math.atan2(u[1], u[0])
            for pp, rr in ((ridge_pts[0], ang + math.pi), (ridge_pts[1], ang)):
                B.insts.append(_inst("onigawara", (pp[0] + math.cos(rr) * -0.1, pp[1] + math.sin(rr) * -0.1, pp[2] + 0.1), rr))
    # 鼻隠し(軒先の厚み)+軒樋+軒天
    for p, q in eaves:
        bm((p[0], p[1], p[2] - 0.0), (q[0], q[1], q[2] - 0.0), 0.04, t_fas, trim, (0, 0, 1))
        if gutters:
            gp = ((p[0] + 0.0, p[1], p[2] - 0.16), (q[0], q[1], q[2] - 0.16))
            bm(gp[0], gp[1], 0.11, 0.09, "alu_silver")
    for pts in ([P(-a0, -b0, z - 0.02), P(a0, -b0, z - 0.02), P(a, -b, z - 0.02), P(-a, -b, z - 0.02)], [P(a0, b0, z - 0.02), P(-a0, b0, z - 0.02), P(-a, b, z - 0.02), P(a, b, z - 0.02)]):
        sh.oriented(pts, (0, 0, -1), "wood_light")
    if kind in ("hip", "irimoya"):
        for pts in ([P(a0, -b0, z - 0.02), P(a0, b0, z - 0.02), P(a, b, z - 0.02), P(a, -b, z - 0.02)], [P(-a0, b0, z - 0.02), P(-a0, -b0, z - 0.02), P(-a, -b, z - 0.02), P(-a, b, z - 0.02)]):
            sh.oriented(pts, (0, 0, -1), "wood_light")
    # 竪樋(対角の2隅)
    if gutters:
        for s_, t_ in ((-a0 + 0.1, -b0), (a0 - 0.1, b0)):
            r = math.atan2(v[0] * (1 if t_ < 0 else -1), -v[1] * (1 if t_ < 0 else -1))
            B.insts.append(_inst("house_downpipe", P(s_, t_, 0.15), r, sz=(z - 0.15) / 3.0))
    # 古い家のTVアンテナ
    if ridge_pts and rng.random() < 0.35:
        B.insts.append(_inst("tv_antenna_yagi", (ridge_pts[0][0] * 0.7 + ridge_pts[1][0] * 0.3, ridge_pts[0][1] * 0.7 + ridge_pts[1][1] * 0.3, ridge_pts[0][2]), math.atan2(v[1], v[0])))
    B.meta["roof"] = (kind, mat_key)
    return True


def _inst(name, p, rot, sz=1.0):
    from .assemble import Inst
    return Inst(name, p[0], p[1], p[2], rot, 1.0, 1.0, sz)
