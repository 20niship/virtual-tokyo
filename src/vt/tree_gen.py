"""樹木・低木の手続き生成。幹/枝は再帰的な枝分かれ(屈地性・向光性・乱数ゆらぎ付き)を掃引チューブに、葉は葉アトラスの
アルファ付きカード(枝先の枝カード+樹冠外殻の葉塊カード)に。1本=数千〜2万三角形。座標: 原点=根元中心, z=上。"""
import math

import numpy as np

from .leaf_atlas import load_meta
from .modules.geom import Mesh

LEAF = "leaf_atlas"
_M = {}


def atlas():
    if not _M:
        _M.update(load_meta())
    return _M


def pool(prefix, season=None):
    """アトラスのカード名を前方一致で。seasonが無ければ全季節共通名(prefix_n)"""
    cards = atlas()["cards"]
    if season:
        got = [n for n in cards if n.startswith(f"{prefix}_{season}_")]
        if got:
            return sorted(got)
    return sorted(n for n in cards if n.startswith(prefix + "_") and not any(n.startswith(f"{prefix}_{s}_") for s in ("spring", "summer", "autumn_y", "autumn_r")))


def norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else np.array([0.0, 0.0, 1.0])


def perp(v):
    a = np.array([1.0, 0, 0]) if abs(v[0]) < 0.9 else np.array([0, 1.0, 0])
    return norm(np.cross(v, a))


def rot_about(v, axis, ang):
    axis = norm(axis)
    c, s = math.cos(ang), math.sin(ang)
    return v * c + np.cross(axis, v) * s + axis * np.dot(axis, v) * (1 - c)


# ---------------------------------------------------------------- メッシュ部品
def tube(m, pts, radii, mat, sides=6, vscale=1.0, cap=False):
    """経路ptsに沿った掃引チューブ(平行移動フレーム)。UV=(周長[m], 経路長[m])"""
    pts = [np.asarray(p, float) for p in pts]
    n = len(pts)
    if n < 2:
        return
    tans = []
    for i in range(n):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        tans.append(norm(b - a))
    u = perp(tans[0])
    rings, s_acc, ss = [], 0.0, [0.0]
    for i in range(n):
        if i:
            ss.append(ss[-1] + np.linalg.norm(pts[i] - pts[i - 1]))
            ax = np.cross(tans[i - 1], tans[i])
            if np.linalg.norm(ax) > 1e-6:
                u = rot_about(u, ax, math.asin(min(1.0, np.linalg.norm(ax))))
            u = norm(u - tans[i] * np.dot(u, tans[i]))
        v = np.cross(tans[i], u)                  # u x v = t
        r = radii[i]
        rings.append([pts[i] + r * (math.cos(2 * math.pi * k / sides) * u + math.sin(2 * math.pi * k / sides) * v) for k in range(sides)])
    for i in range(n - 1):
        r_avg = (radii[i] + radii[i + 1]) / 2
        circ = 2 * math.pi * max(r_avg, 0.01)
        for k in range(sides):
            k2 = (k + 1) % sides
            m.poly([tuple(rings[i][k]), tuple(rings[i][k2]), tuple(rings[i + 1][k2]), tuple(rings[i + 1][k])], mat,
                   [(circ * k / sides, ss[i] * vscale), (circ * (k + 1) / sides, ss[i] * vscale), (circ * (k + 1) / sides, ss[i + 1] * vscale), (circ * k / sides, ss[i + 1] * vscale)])
    if cap and radii[-1] > 0.02:
        m.poly([tuple(p) for p in rings[-1]][::-1], mat, None)


def card(m, name, c, right, up, w, h, flip=False, vflip=False):
    """アトラスのカード(name)を中心c・横軸right・縦軸up・幅w・高さhのクアッドで。両面材質なので向きは任意。"""
    u0, v0, u1, v1 = atlas()["cards"][name]["uv"]
    if flip:
        u0, u1 = u1, u0
    if vflip:
        v0, v1 = v1, v0
    r = norm(right) * (w / 2)
    u = norm(up) * (h / 2)
    P = [c - r - u, c + r - u, c + r + u, c - r + u]
    m.poly([tuple(p) for p in P], LEAF, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def card_aspect(name):
    x, y, w, h = atlas()["cards"][name]["rect"]
    return w / h


# ---------------------------------------------------------------- 樹冠プロファイル
def profile(kind, t):
    t = min(max(t, 0.0), 1.0)
    if kind == "cone":
        return (1 - t) ** 0.85 * min(1.0, 0.35 + t * 5) if False else (1 - t) ** 0.9 * (0.55 + 0.45 * math.sin(min(t * 6, math.pi / 2)))
    if kind == "ovoid":
        return math.sin(math.pi * (t ** 0.8)) ** 0.8
    if kind == "vase":
        return min(1.0, 0.25 + 1.5 * t ** 0.6) * (1 - 0.55 * t ** 2.2)
    if kind == "dome":
        return math.sqrt(max(0.0, 1 - (2 * t ** 0.8 - 1) ** 2)) ** 0.7
    if kind == "spread":
        return math.sin(math.pi * min(1.0, t * 1.15) ** 0.65) ** 0.8
    if kind == "column":
        return 0.72 * math.sin(math.pi * min(1.0, t * 0.9 + 0.05)) ** 0.6
    return 1.0


class Spec:
    def __init__(self, **kw):
        self.__dict__.update(dict(
            bark="bark_furrow", girth=1.0, crown="ovoid", crown_w=0.42, crown_base=0.3, n_main=14, ang=45, ang_var=15, grav=0.1, up=0.06,
            sub=4, sub_ang=45, decay=0.62, noise=0.12, lean=0.0, twist=0.0, leaf="oval", leaf_size=0.17, shell=130, twigs=3, seasons=("summer",),
            trunk_noise=0.05, flare=0.7, evergreen=False, trunk_taper=0.3))
        self.__dict__.update(kw)


SPECIES = {
    "ichou": Spec(bark="bark_furrow", crown="cone", crown_w=0.36, crown_base=0.28, n_main=16, ang=42, ang_var=14, grav=0.04, up=0.12, leaf="ginkgo", leaf_size=0.15,
                  seasons=("summer", "autumn_y", "spring", "winter"), shell=110),
    "keyaki": Spec(bark="bark_furrow", crown="vase", crown_w=0.5, crown_base=0.32, n_main=11, ang=34, ang_var=12, grav=0.0, up=0.18, leaf="oval", leaf_size=0.15,
                   seasons=("summer", "autumn_y", "spring", "winter"), shell=140, sub=5),
    "platanus": Spec(bark="bark_plane", crown="ovoid", crown_w=0.46, crown_base=0.35, n_main=12, ang=50, ang_var=14, grav=0.05, up=0.05, leaf="lobed", leaf_size=0.2,
                     seasons=("summer", "autumn_y", "spring", "winter"), shell=130),
    "sakura": Spec(bark="bark_smooth", crown="spread", crown_w=0.62, crown_base=0.28, n_main=9, ang=62, ang_var=14, grav=0.1, up=0.02, leaf="oval", leaf_size=0.14,
                   seasons=("spring", "summer", "autumn_r", "winter"), shell=150, sub=5, girth=0.9),
    "kusunoki": Spec(bark="bark_furrow_dark", crown="dome", crown_w=0.62, crown_base=0.3, n_main=10, ang=52, ang_var=14, grav=0.06, up=0.08, leaf="evergreen", leaf_size=0.18,
                     evergreen=True, shell=200, girth=1.25),
    "shii": Spec(bark="bark_smooth", crown="dome", crown_w=0.5, crown_base=0.25, n_main=10, ang=45, ang_var=14, grav=0.04, up=0.08, leaf="evergreen", leaf_size=0.15,
                 evergreen=True, shell=190, girth=1.1),
    "tokaikaede": Spec(bark="bark_smooth", crown="ovoid", crown_w=0.46, crown_base=0.3, n_main=9, ang=50, ang_var=14, grav=0.03, up=0.1, leaf="lobed", leaf_size=0.15,
                       seasons=("summer", "autumn_r", "spring", "winter"), shell=110, girth=0.85),
    "hanamizuki": Spec(bark="bark_smooth", crown="spread", crown_w=0.5, crown_base=0.3, n_main=8, ang=58, ang_var=12, grav=0.06, up=0.02, leaf="oval", leaf_size=0.12,
                       seasons=("summer", "autumn_r", "spring", "winter"), shell=90, girth=0.7),
}


def leaf_pool(sp, kind, season):
    """樹種の葉タイプ→(クラスタ用, 枝カード用)のカード名プール"""
    if kind == "ginkgo":
        return pool("ginkgo", season), pool("ginkgo", season)
    if kind == "lobed":
        return pool("lobed_cluster", season), pool("lobed_cluster", season)
    if kind == "evergreen":
        return pool("evergreen_cluster"), pool("evergreen_cluster") + pool("oval_twig", "summer")
    return pool("oval_cluster", season), pool("oval_twig", season)


# ---------------------------------------------------------------- 枝の成長
def grow_branch(rng, p0, d0, length, r0, spec, level, step=0.5, g_scale=1.0):
    n = max(3, int(length / step))
    st = length / n
    p = np.asarray(p0, float)
    d = norm(np.asarray(d0, float))
    nodes, rad = [p.copy()], [r0]
    for i in range(n):
        d = norm(d + rng.normal(0, spec.noise, 3) + np.array([0, 0, -spec.grav * g_scale * (1 + level * 0.3) + spec.up * (0.5 if level == 1 else 0.3)]) * st)
        p = p + d * st
        t = (i + 1) / n
        nodes.append(p.copy())
        rad.append(max(r0 * (1 - 0.82 * t), 0.004))
    return nodes, rad


def build_tree(name, H=9.0, seed=0, season="summer"):
    sp = SPECIES[name]
    rng = np.random.default_rng(seed * 977 + hash(name) % 997)
    m = Mesh()
    H = float(H)
    r0 = (0.012 * H + 0.06) * sp.girth
    # 幹: ゆるい曲がり+捩れ+根張り
    n_t = max(8, int(H / 0.6))
    trunk, tr = [np.zeros(3)], [r0 * (1 + sp.flare * 0.6)]
    d = np.array([0, 0, 1.0])
    lean_dir = rng.normal(0, 1, 2)
    for i in range(1, n_t + 1):
        t = i / n_t
        d = norm(d + np.array([lean_dir[0] * sp.lean, lean_dir[1] * sp.lean, 0]) * 0.1 + rng.normal(0, sp.trunk_noise, 3) * np.array([1, 1, 0.2]))
        trunk.append(trunk[-1] + d * (H * 0.9 / n_t))
        base_flare = 1 + sp.flare * 0.6 * max(0, 1 - t * 14) ** 2
        tr.append(r0 * (1 - (1 - sp.trunk_taper) * t ** 0.8) * base_flare)
    ztop = trunk[-1][2]
    # 幹の上は枝へ移行するので半径を絞る
    tube(m, trunk, tr, sp.bark, 8, 1.0, False)
    tips = []                                                   # (pos, dir, level)
    crown_r = sp.crown_w * H
    h0 = sp.crown_base * H

    def r_allowed(z):
        return crown_r * profile(sp.crown, (z - h0) / max(H - h0, 0.1))

    winter = season == "winter"
    # 主枝: 幹の上部に黄金角で配置
    golden = math.radians(137.5)
    az0 = rng.uniform(0, 6.28)
    branches = []
    for i in range(sp.n_main):
        t = (i + 0.5) / sp.n_main
        z = h0 + (H * 0.92 - h0) * t ** 0.9
        # 幹の該当高さの位置
        k = min(int(z / (H * 0.9 / n_t)), n_t - 1)
        base = trunk[k] + (trunk[k + 1] - trunk[k]) * ((z - trunk[k][2]) / max(trunk[k + 1][2] - trunk[k][2], 1e-6)) if k + 1 <= n_t else trunk[-1]
        az = az0 + i * golden
        ang = math.radians(sp.ang * (0.55 + 0.7 * t) + rng.normal(0, sp.ang_var))
        d0 = np.array([math.sin(ang) * math.cos(az), math.sin(ang) * math.sin(az), math.cos(ang)])
        L = max(1.0, r_allowed(z) * 1.2 / max(math.sin(ang), 0.45)) * rng.uniform(0.85, 1.1)
        rb = max(0.015, r0 * 0.5 * (1 - 0.55 * t))
        nodes, rad = grow_branch(rng, base, d0, L, rb, sp, 1, step=max(0.45, H / 20))
        branches.append((nodes, rad, 1, L))
        # 側枝
        nsub = sp.sub + int(rng.integers(0, 2))
        for s in range(nsub):
            ti = rng.uniform(0.28, 0.92)
            idx = max(1, min(len(nodes) - 2, int(ti * (len(nodes) - 1))))
            pdir = norm(nodes[idx + 1] - nodes[idx - 1])
            sa = math.radians(sp.sub_ang + rng.normal(0, 12))
            az2 = rng.uniform(0, 6.28)
            ax = perp(pdir)
            sd = rot_about(pdir, rot_about(ax, pdir, az2), sa)
            Ls = L * (1 - ti) * sp.decay * rng.uniform(0.8, 1.2) + 0.5
            rs = max(0.008, rad[idx] * 0.55)
            sn, sr = grow_branch(rng, nodes[idx], sd, Ls, rs, sp, 2, step=0.45)
            branches.append((sn, sr, 2, Ls))
            for tw in range(sp.twigs):
                tj = int(rng.integers(1, max(2, len(sn) - 1)))
                tdir = rot_about(norm(sn[min(tj + 1, len(sn) - 1)] - sn[tj - 1]), rot_about(perp(sd), sd, rng.uniform(0, 6.28)), math.radians(rng.uniform(30, 65)))
                tn, tr2 = grow_branch(rng, sn[tj], tdir, rng.uniform(0.4, 0.9) * max(0.6, H / 9), 0.006, sp, 3, step=0.35)
                branches.append((tn, tr2, 3, 0.6))
                tips.append((tn[-1], norm(tn[-1] - tn[-2]), 3))
            tips.append((sn[-1], norm(sn[-1] - sn[-2]), 2))
        tips.append((nodes[-1], norm(nodes[-1] - nodes[-2]), 1))
    # 枝チューブ(細い小枝は冬だけ)
    for nodes, rad, lvl, L in branches:
        if lvl == 3 and not winter:
            continue
        sides = 6 if rad[0] > 0.05 else (4 if rad[0] > 0.012 else 3)
        tube(m, nodes, rad, sp.bark, sides, 1.0, False)
    if winter:
        return m, dict(W=crown_r * 2, H=H + 1)
    # 葉
    cl_pool, tw_pool = leaf_pool(sp, sp.leaf, season)
    if season == "spring" and sp.leaf in ("oval",) and name in ("sakura",):
        cl_pool = pool("sakura_bloom") + pool("sakura_mixed")
        tw_pool = cl_pool
    ls = sp.leaf_size * H
    for pos, dr, lvl in tips:
        nm = tw_pool[int(rng.integers(len(tw_pool)))]
        up = dr
        right = norm(np.cross(up, rot_about(perp(up), up, rng.uniform(0, 6.28))))
        asp = card_aspect(nm)
        h = ls * rng.uniform(0.9, 1.3)
        if "twig" in nm or "ginkgo" in nm:
            card(m, nm, pos + up * h * 0.45, right, up, h * asp, h, flip=rng.random() < 0.5)
        else:
            card(m, nm, pos, right, up, h * 1.25, h * 1.25, flip=rng.random() < 0.5)
            card(m, nm, pos, norm(np.cross(up, right)), up, h * 1.25, h * 1.25, flip=rng.random() < 0.5)
    # 樹冠外殻: 包絡面に外向きの葉塊カード(密度と輪郭を作る)
    for i in range(sp.shell):
        t = rng.uniform(0.02, 1.0)
        z = h0 + (H * 1.0 - h0) * t
        ra = r_allowed(z)
        if ra < 0.2:
            continue
        az = rng.uniform(0, 6.28)
        rr = ra * rng.uniform(0.55, 1.0)
        c = np.array([math.cos(az) * rr, math.sin(az) * rr, z]) + trunk[min(int(z / (H * 0.9 / n_t)), n_t)] * np.array([1, 1, 0])
        out = norm(np.array([math.cos(az), math.sin(az), 0.35 * (1 - 2 * t) + 0.35]))
        nm = cl_pool[int(rng.integers(len(cl_pool)))]
        sz = ls * rng.uniform(1.7, 2.6)
        right = norm(np.cross(out, np.array([0, 0, 1.0]))) if abs(out[2]) < 0.9 else np.array([1.0, 0, 0])
        up = norm(np.cross(right, out))
        # カードの面は外向き(out)に直交しつつ、少し傾ける
        right = rot_about(right, out, rng.uniform(-0.6, 0.6))
        up = norm(np.cross(out, right))
        card(m, nm, c, right, up, sz, sz, flip=rng.random() < 0.5)
    return m, dict(W=crown_r * 2.1, H=H + 1)


# ---------------------------------------------------------------- 特殊な樹形
def build_pine(H=8.0, seed=0):
    """クロマツ: 捩れ傾いた幹+不規則な輪生枝+枝先の針葉パッド(針束カード)"""
    rng = np.random.default_rng(seed * 131 + 7)
    m = Mesh()
    r0 = 0.012 * H + 0.07
    n_t = 14
    trunk, tr = [np.zeros(3)], [r0 * 1.5]
    lean = rng.uniform(0.15, 0.45)
    az = rng.uniform(0, 6.28)
    d = np.array([0, 0, 1.0])
    for i in range(1, n_t + 1):
        t = i / n_t
        d = norm(d + np.array([math.cos(az + t * 3), math.sin(az + t * 3), 0]) * lean * 0.18 + rng.normal(0, 0.06, 3) * np.array([1, 1, 0.2]))
        trunk.append(trunk[-1] + d * (H * 0.95 / n_t))
        tr.append(r0 * (1 - 0.7 * t ** 0.8) * (1 + 0.5 * max(0, 1 - t * 12) ** 2))
    tube(m, trunk, tr, "bark_pine", 8, 1.0)
    pads = []
    nb = int(H * 1.6)
    for i in range(nb):
        t = 0.28 + 0.72 * (i / nb) ** 0.95
        z = H * 0.95 * t
        k = min(int(t * n_t), n_t - 1)
        base = trunk[k]
        a = rng.uniform(0, 6.28)
        L = (1 - t) ** 0.7 * H * 0.42 + 0.6
        droop = rng.uniform(0.0, 0.25)
        d0 = np.array([math.cos(a) * 0.94, math.sin(a) * 0.94, droop * 0.2 + 0.16])
        spec = Spec(noise=0.14, grav=0.04, up=0.12)
        nodes, rad = grow_branch(rng, base, d0, L, max(0.012, r0 * 0.28 * (1 - t * 0.5)), spec, 1, step=0.5)
        tube(m, nodes, rad, "bark_pine", 5, 1.0)
        for j in range(2):                                    # 枝先2つのパッド
            pads.append((nodes[-1 - j * max(1, len(nodes) // 4)], norm(nodes[-1] - nodes[0])))
        pads.append((nodes[len(nodes) // 2], norm(nodes[-1] - nodes[0])))
    tuft = pool("pine_tuft")
    ls = max(1.2, H * 0.22)
    for pos, dr in pads:
        nm = tuft[int(rng.integers(len(tuft)))]
        a = norm(np.array([dr[0], dr[1], 0]))
        up_h = norm(a * 0.55 + np.array([0, 0, 0.8]))
        right = norm(np.cross(up_h, np.array([0, 0, 1.0]))) if abs(up_h[2]) < 0.95 else np.array([1.0, 0, 0])
        asp = card_aspect(nm)
        card(m, nm, pos + up_h * ls * 0.35, right, up_h, ls * asp, ls, flip=rng.random() < 0.5)
        n2 = norm(np.cross(up_h, right))
        card(m, nm, pos + up_h * ls * 0.35, n2, up_h, ls * asp * 0.9, ls * 0.95, flip=rng.random() < 0.5)
        # 水平パッド(上から見ても密に)
        card(m, nm, pos + np.array([0, 0, 0.15]), right, a, ls * asp * 0.85, ls * 0.8, flip=rng.random() < 0.5)
    return m, dict(W=H * 0.9, H=H + 1)


def build_palm(kind="canary", H=7.0, seed=0):
    """ヤシ: 輪紋のある幹+放射状に弧を描く羽状葉(カナリー/ワシントニア=掌状)。シュロは細い毛羽立った幹+掌状葉"""
    rng = np.random.default_rng(seed * 53 + 3)
    m = Mesh()
    fan = kind in ("washingtonia", "shuro")
    r0 = (0.022 * H + 0.14) if kind == "canary" else (0.012 * H + 0.1 if kind == "washingtonia" else 0.007 * H + 0.08)
    bark = "bark_shuro" if kind == "shuro" else "bark_palm"
    n_t = 12
    trunk, tr = [np.zeros(3)], [r0 * 1.35]
    lean = rng.normal(0, 1, 2) * 0.03
    for i in range(1, n_t + 1):
        t = i / n_t
        trunk.append(trunk[-1] + np.array([lean[0] * 0.2, lean[1] * 0.2, 1.0]) * (H / n_t) + rng.normal(0, 0.02, 3) * np.array([1, 1, 0]))
        tr.append(r0 * (1 - 0.18 * t) * (1 + 0.35 * max(0, 1 - t * 10) ** 2))
    tube(m, trunk, tr, bark, 10, 1.0, True)
    top = trunk[-1]
    n_f = {"canary": 22, "washingtonia": 24, "shuro": 16}[kind]
    names = pool("palm_frond") if not fan else pool("palm_fan")
    for i in range(n_f):
        az = i * 2.399 + rng.normal(0, 0.1)
        t = i / n_f
        elev = math.radians(75 - 95 * t + rng.normal(0, 5))   # 上向きから垂れ下がりへ
        dirv = np.array([math.cos(az) * math.cos(elev), math.sin(az) * math.cos(elev), math.sin(elev)])
        nm = names[int(rng.integers(len(names)))]
        if not fan:
            L = (H * 0.62 + 1.6) * rng.uniform(0.85, 1.05)
            seg = 3
            p = top.copy()
            side0 = norm(np.cross(dirv, np.array([0, 0, 1.0])))
            u0, v0, u1, v1 = atlas()["cards"][nm]["uv"]
            d = dirv.copy()
            for s in range(seg):
                d2 = norm(d + np.array([0, 0, -0.32 * (1 + t)]) * (s + 1) / seg)
                q = p + d2 * (L / seg)
                cx = (p + q) / 2
                right = norm(q - p)
                uu0 = u0 + (u1 - u0) * s / seg
                uu1 = u0 + (u1 - u0) * (s + 1) / seg
                Wd = L * 0.34
                P = [cx - right * (L / seg) / 2 - side0 * Wd / 2, cx + right * (L / seg) / 2 - side0 * Wd / 2, cx + right * (L / seg) / 2 + side0 * Wd / 2, cx - right * (L / seg) / 2 + side0 * Wd / 2]
                m.poly([tuple(x) for x in P], LEAF, [(uu0, v0), (uu1, v0), (uu1, v1), (uu0, v1)])
                p, d = q, d2
        else:
            L = (1.0 + H * 0.05) * rng.uniform(0.9, 1.1)
            pet = 0.7 + H * 0.06
            pd = norm(dirv * 0.7 + np.array([0, 0, 0.5 * (1 - t)]))
            tip = top + pd * pet
            tube(m, [top, top + pd * pet * 0.5 + np.array([0, 0, 0.06]), tip], [0.02, 0.016, 0.012], "bark_palm", 4, 1.0)
            fd = norm(pd + np.array([0, 0, 0.45]))
            right = norm(np.cross(fd, np.array([0, 0, 1.0]))) if abs(fd[2]) < 0.95 else np.array([1.0, 0, 0])
            up = norm(np.cross(right, norm(np.cross(fd, right))))
            fup = fd
            card(m, nm, tip + fup * L * 0.45, right, fup, L * 1.15, L * 1.0, flip=rng.random() < 0.5)
    return m, dict(W=H * 0.8 + 3, H=H + 2)


def build_willow(H=8.0, seed=0):
    """枝垂れ柳: 太い幹から分かれ、弧を描いて垂れる枝+垂れ下がる細枝カード(willow_twig)"""
    rng = np.random.default_rng(seed * 71 + 11)
    m = Mesh()
    r0 = 0.012 * H + 0.1
    trunk = [np.zeros(3)]
    tr = [r0 * 1.4]
    d = np.array([0, 0, 1.0])
    n_t = 6
    for i in range(1, n_t + 1):
        t = i / n_t
        d = norm(d + rng.normal(0, 0.08, 3) * np.array([1, 1, 0.2]))
        trunk.append(trunk[-1] + d * (H * 0.4 / n_t))
        tr.append(r0 * (1 - 0.35 * t) * (1 + 0.4 * max(0, 1 - t * 6) ** 2))
    tube(m, trunk, tr, "bark_furrow_dark", 8, 1.0)
    top = trunk[-1]
    twig = pool("willow_twig")
    cl = pool("oval_cluster", "summer")
    nl = 7
    for i in range(nl):
        az = i * 2.399 + rng.normal(0, 0.2)
        d0 = np.array([math.cos(az) * 0.6, math.sin(az) * 0.6, 0.8])
        spec = Spec(noise=0.07, grav=0.5, up=0.2)
        nodes, rad = grow_branch(rng, top - np.array([0, 0, 0.3]), d0, H * 0.75, r0 * 0.45, spec, 1, step=0.5, g_scale=1.0)
        tube(m, nodes, rad, "bark_furrow_dark", 5, 1.0)
        for j in range(2, len(nodes)):
            p = nodes[j]
            for k in range(3):
                nm = twig[int(rng.integers(len(twig)))]
                h = rng.uniform(1.5, 2.8) * max(0.6, H / 8)
                w = h * 0.42
                a2 = rng.uniform(0, math.pi)
                right = np.array([math.cos(a2), math.sin(a2), 0])
                card(m, nm, p + np.array([0, 0, -h / 2]) + right * rng.normal(0, 0.15), right, np.array([0, 0, 1.0]), w, h, flip=rng.random() < 0.5, vflip=True)
        # 枝先の房
        for _k in range(2):
            nm = cl[int(rng.integers(len(cl)))]
            sz = H * 0.18
            c = nodes[-1] + np.array([0, 0, -sz * 0.4])
            card(m, nm, c, np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), sz, sz)
            card(m, nm, c, np.array([0, 1.0, 0]), np.array([0, 0, 1.0]), sz, sz)
    return m, dict(W=H * 1.1, H=H + 1)


# ---------------------------------------------------------------- 低木・生垣・地被
def _core_ellipsoid(m, c, rx, ry, rz, n=8, rings=4, mat="foliage_core"):
    """葉カードの裏の低ポリ芯(透け防止)"""
    pts = []
    for i in range(rings + 1):
        phi = math.pi / 2 * i / rings
        ring = []
        for k in range(n):
            a = 2 * math.pi * k / n
            ring.append(np.array([c[0] + rx * math.cos(phi) * math.cos(a), c[1] + ry * math.cos(phi) * math.sin(a), c[2] + rz * math.sin(phi)]))
        pts.append(ring)
    for i in range(rings):
        for k in range(n):
            k2 = (k + 1) % n
            m.poly([tuple(pts[i][k2]), tuple(pts[i][k]), tuple(pts[i + 1][k]), tuple(pts[i + 1][k2])], mat) if i + 1 < rings else m.poly([tuple(pts[i][k2]), tuple(pts[i][k]), tuple(pts[rings][k])], mat)


def build_dome_shrub(kind="azalea", R=0.7, seed=0, color=0, n=70):
    """刈り込み低木(ツツジ/サツキ/ヒラドツツジ/ツゲ)・アジサイ: 半楕円体の表面に外向きの葉カード+暗い芯"""
    rng = np.random.default_rng(seed * 17 + color)
    m = Mesh()
    rz = R * (0.7 if kind in ("azalea", "tsuge") else 0.8)
    _core_ellipsoid(m, (0, 0, 0), R * 0.8, R * 0.8, rz * 0.85)
    if kind == "azalea":
        names = [f"azalea_bloom_{color % 3}"] if color >= 0 else pool("shrub_cluster")
        base = pool("shrub_cluster")
    elif kind == "hydrangea":
        names = [f"hydrangea_{color % 2}"]
        base = pool("oval_cluster", "summer")
    else:
        names = pool("shrub_cluster")
        base = names
    for i in range(n):
        phi = rng.uniform(0.05, 1.45)
        a = rng.uniform(0, 6.28)
        c = np.array([R * math.cos(phi) * math.cos(a), R * math.cos(phi) * math.sin(a), rz * math.sin(phi) * 0.95])
        out = norm(np.array([math.cos(phi) * math.cos(a) / R, math.cos(phi) * math.sin(a) / R, math.sin(phi) / rz]))
        right = norm(np.cross(out, np.array([0, 0, 1.0]))) if abs(out[2]) < 0.97 else np.array([1.0, 0, 0])
        up = norm(np.cross(out, right))
        nm = (names if (i % 3 == 0 or kind == "tsuge") else base)[int(rng.integers(len(names if (i % 3 == 0 or kind == "tsuge") else base)))]
        sz = R * rng.uniform(0.7, 1.1)
        card(m, nm, c, right, up, sz, sz, flip=rng.random() < 0.5)
    return m, dict(W=R * 2, H=rz + 0.1)


def build_hedge(L=2.0, Wd=0.6, Hh=1.2, seed=0, round_top=True):
    """生垣1スパン(長さL): 角丸の箱の表面に葉カードを敷き詰め、暗い芯で透けを防ぐ。端部で連結できるよう両端は開放"""
    rng = np.random.default_rng(seed * 29 + 5)
    m = Mesh()
    core = [(-L / 2, -Wd / 2 + 0.05, 0), (L / 2, -Wd / 2 + 0.05, 0), (L / 2, Wd / 2 - 0.05, 0), (-L / 2, Wd / 2 - 0.05, 0)]
    z1 = Hh - 0.08
    m.poly([(L / 2, -Wd / 2 + 0.06, 0), (L / 2, -Wd / 2 + 0.06, z1), (-L / 2, -Wd / 2 + 0.06, z1), (-L / 2, -Wd / 2 + 0.06, 0)], "foliage_core")
    m.poly([(-L / 2, Wd / 2 - 0.06, 0), (-L / 2, Wd / 2 - 0.06, z1), (L / 2, Wd / 2 - 0.06, z1), (L / 2, Wd / 2 - 0.06, 0)], "foliage_core")
    m.poly([(-L / 2, -Wd / 2 + 0.06, z1), (L / 2, -Wd / 2 + 0.06, z1), (L / 2, Wd / 2 - 0.06, z1), (-L / 2, Wd / 2 - 0.06, z1)], "foliage_core")
    names = pool("hedge_fill")
    cs = 0.55
    nx = max(2, int(L / cs * 1.6))
    nz = max(2, int(Hh / cs * 1.5))
    for i in range(nx):
        for j in range(nz):
            x = -L / 2 + (i + rng.uniform(0.2, 0.8)) * L / nx
            z = (j + rng.uniform(0.2, 0.8)) * (Hh - 0.1) / nz + 0.05
            for side in (-1, 1):
                nm = names[int(rng.integers(len(names)))]
                y = side * (Wd / 2 - 0.03 + rng.normal(0, 0.02))
                card(m, nm, np.array([x, y, z]), np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), cs * 1.3, cs * 1.3, flip=rng.random() < 0.5)
    for i in range(max(2, int(L / cs * 1.2))):
        for jy in range(max(1, int(Wd / cs * 1.3))):
            x = -L / 2 + (i + rng.uniform(0.2, 0.8)) * L / max(2, int(L / cs * 1.2))
            y = -Wd / 2 + (jy + rng.uniform(0.3, 0.8)) * Wd / max(1, int(Wd / cs * 1.3))
            nm = names[int(rng.integers(len(names)))]
            card(m, nm, np.array([x, y, Hh - 0.02]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), cs * 1.35, cs * 1.35, flip=rng.random() < 0.5)
    return m, dict(W=L, H=Hh)


def build_flowerbed(Lx=2.0, Ly=1.0, seed=0, kind="flowerbed"):
    """花壇/地被パッチ: 地面に寝かせた葉+花カードと、立ち上がるカードで盛り上げる(0.35m)"""
    rng = np.random.default_rng(seed * 41 + 2)
    m = Mesh()
    names = pool(kind) if pool(kind) else pool("flowerbed")
    cs = 0.5
    for i in range(int(Lx / cs * 1.6)):
        for j in range(int(Ly / cs * 1.6)):
            x, y = rng.uniform(-Lx / 2, Lx / 2), rng.uniform(-Ly / 2, Ly / 2)
            nm = names[int(rng.integers(len(names)))]
            h = rng.uniform(0.04, 0.22)
            card(m, nm, np.array([x, y, h]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), cs * rng.uniform(0.9, 1.3), cs * rng.uniform(0.9, 1.3), flip=rng.random() < 0.5)
    for i in range(int(Lx / cs * 1.2)):
        x, y = rng.uniform(-Lx / 2, Lx / 2), rng.uniform(-Ly / 2, Ly / 2)
        a = rng.uniform(0, math.pi)
        nm = names[int(rng.integers(len(names)))]
        card(m, nm, np.array([x, y, 0.22]), np.array([math.cos(a), math.sin(a), 0]), np.array([0, 0, 1.0]), cs, 0.4, flip=rng.random() < 0.5)
    return m, dict(W=Lx, H=0.5)


def build_grass(kind="tuft", R=0.6, seed=0):
    """観賞用イネ科(クロスカード5枚の房)"""
    rng = np.random.default_rng(seed * 13 + 1)
    m = Mesh()
    names = pool("grass_plume" if kind == "plume" else "grass_tuft")
    for i in range(6):
        a = i * math.pi / 6 + rng.uniform(-0.1, 0.1)
        nm = names[int(rng.integers(len(names)))]
        h = R * rng.uniform(1.3, 1.9)
        card(m, nm, np.array([0, 0, h / 2]), np.array([math.cos(a), math.sin(a), 0]), np.array([0, 0, 1.0]), R * 1.8, h, flip=rng.random() < 0.5)
    return m, dict(W=R * 2, H=R * 2)


def build_ivy_wall(Wd=2.0, Hh=2.0, seed=0, hang=0.0):
    """壁面緑化(アイビー): 壁に貼る面(+y向き)にカードを重ねる。壁面 y=0、葉は y=0.03〜0.1 に張り出す。"""
    rng = np.random.default_rng(seed * 23 + 9)
    m = Mesh()
    names = pool("ivy_wall")
    vines = pool("ivy_vine")
    cs = 0.55
    for i in range(int(Wd / cs * 2)):
        for j in range(int(Hh / cs * 2)):
            x = -Wd / 2 + (i + rng.uniform(0.2, 0.8)) * Wd / int(Wd / cs * 2)
            z = (j + rng.uniform(0.2, 0.8)) * Hh / int(Hh / cs * 2)
            nm = names[int(rng.integers(len(names)))]
            card(m, nm, np.array([x, 0.03 + rng.uniform(0, 0.06), z]), np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), cs * 1.25, cs * 1.25, flip=rng.random() < 0.5)
    for i in range(int(Wd / 0.45)):
        x = -Wd / 2 + rng.uniform(0, Wd)
        nm = vines[int(rng.integers(len(vines)))]
        top = Hh * rng.uniform(0.6, 1.0)
        h = rng.uniform(0.7, 1.4)
        card(m, nm, np.array([x, 0.1, top - h / 2]), np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), h * 0.6, h, vflip=True)
    return m, dict(W=Wd, H=Hh)


def tris(m):
    return sum(len(f) - 2 for f in m.f)
