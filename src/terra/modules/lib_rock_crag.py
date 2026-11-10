"""海食崖(seacliff)と岩山の突起(spire)の SDF 生成(lib_rock_sdf.Field の上)。lod: hi / near / far はボクセル寸法の違い。"""
import numpy as np
from scipy.ndimage import gaussian_filter

from . import lib_rock_sdf as S
from .lib_rock_sdf import Field, _smax, fbm_pts

# lod ごとのボクセル寸法の係数(hi=1)と、実行する彫刻
LOD_H = {"hi": 1.0, "near": 1.9, "far": 7.0}


def _hash(ix, iy, iz, salt):
    h = (ix.astype(np.int64) * 73856093) ^ (iy.astype(np.int64) * 19349663) ^ (iz.astype(np.int64) * 83492791) ^ (salt * 2654435761)
    h &= 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 0x5BD1E995) & 0xFFFFFFFF
    h ^= h >> 15
    return (h & 0xFFFFFF).astype(np.float32) / float(1 << 24)


def honeycomb(f, s, dens, rng_np, r_frac=(0.2, 0.42), fresh=False):
    """蜂の巣風化(タフォニ): 3D の揺らいだ格子の各セルに球状のピットを置いて削る。dens(P)->0..1 で場所ごとの出やすさ。s=セル寸法"""
    band = 0.5 * s * r_frac[1] * 2 + f.h
    idx = np.flatnonzero(np.abs(f.d) < band)
    if len(idx) == 0:
        return
    i3 = np.unravel_index(idx, f.d.shape)
    P = np.stack([f.ax[0][i3[0]], f.ax[1][i3[1]], f.ax[2][i3[2]]], 1).astype(np.float32)
    dd = dens(P)
    salt = int(rng_np.integers(1, 1 << 20))
    cell = np.floor(P / s).astype(np.int64)
    best = np.full(len(P), 1e3, np.float32)
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            for oz in (-1, 0, 1):
                cx, cy, cz = cell[:, 0] + ox, cell[:, 1] + oy, cell[:, 2] + oz
                ctr = np.stack([(cx + 0.15 + 0.7 * _hash(cx, cy, cz, salt + 1)) * s, (cy + 0.15 + 0.7 * _hash(cx, cy, cz, salt + 2)) * s,
                                (cz + 0.15 + 0.7 * _hash(cx, cy, cz, salt + 3)) * s], 1)
                r = s * (r_frac[0] + (r_frac[1] - r_frac[0]) * _hash(cx, cy, cz, salt + 4))
                on = _hash(cx, cy, cz, salt + 5) < dd
                dist = np.linalg.norm(P - ctr, axis=1) - r
                best = np.where(on, np.minimum(best, dist), best)
    flat = f.d.reshape(-1)
    new = _smax(flat[idx], -best, 0.12 * s)
    if fresh:
        pass
    flat[idx] = new


def cleft(f, c, n, L, w, ax_up=(0, 0, 1)):
    """深い割れ目: 法線 n の板(厚さ w)を c から上下・左右 L の範囲で先細りに削る"""
    sl = f.box(c, L * 1.2)
    if sl is None:
        return
    X, Y, Z = f.coords(sl)
    q = (X - c[0]) * n[0] + (Y - c[1]) * n[1] + (Z - c[2]) * n[2]
    dist = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2)
    taper = np.clip(1 - (dist / L) ** 1.5, 0, 1)
    f.carve(sl, np.abs(q) - w * taper, 0.4 * w)
    f.cracks.append((np.asarray(c, float), np.asarray(n, float), L, w))


def _layers(rng, z0, z1, thick=(0.5, 1.9)):
    zb = [z0]
    while zb[-1] < z1:
        zb.append(zb[-1] + rng.uniform(*thick) * (1.0 if rng.random() > 0.3 else 0.45))
    hard = np.where(rng.random(len(zb)) < 0.45, rng.uniform(0.7, 0.95, len(zb)), rng.uniform(0.05, 0.4, len(zb)))
    for i in range(1, len(hard)):                                  # 硬い層が連続しすぎない
        if hard[i] > 0.7 and hard[i - 1] > 0.7:
            hard[i] -= 0.4
    return np.array(zb), hard


def _smooth1(rng, x, wl, amp, n=4):
    out = 0
    for k in range(n):
        out = out + amp * 0.6 ** k * np.sin(x * 2 * np.pi / (wl / 2 ** k) + rng.uniform(0, 6.28))
    return out


def seacliff_sdf(f, W, D, H, rng, st, ctx_out):
    """海食崖の面(-y 向き)を f.d に入れる。W 幅・D 奥行・H 高さ(z=0 が水面)"""
    xs, ys, zs = f.ax
    X2, Z2 = np.meshgrid(xs, zs, indexing="ij")
    zb, hard = _layers(rng, -2.0, H + 3.0)
    dip = np.tan(np.radians(rng.uniform(-3.5, 3.5)))
    wave = _smooth1(rng, xs, 18.0, 0.35)
    zz = Z2 + dip * X2 + wave[:, None]
    k = np.clip(np.searchsorted(zb, zz) - 1, 0, len(hard) - 1)
    recess = (1.0 - hard[k]) * 1.1                                                 # 差別侵食: 軟らかい層ほど凹む
    # 層ごとの色の濃淡(硬い層は明るい黄褐、軟らかい層は暗い・赤茶)
    tone_l = (hard - 0.5) * 0.5 + rng.normal(0, 0.12, len(hard))
    # 垂直(やや傾いた)節理 + 斜交節理でブロック状に割れる
    u = X2 + 0.1 * Z2
    edges = np.cumsum(rng.uniform(2.6, 7.0, 16)) - W / 2 - 6.0
    j = np.searchsorted(edges, u)
    j2 = np.floor((0.6 * Z2 + 0.8 * X2 + rng.uniform(0, 7)) / rng.uniform(5.5, 9.0)).astype(np.int64)
    kk = k.astype(np.int64)
    hb = _hash(kk, j.astype(np.int64), j2, 17)
    fall = _hash(kk, j.astype(np.int64), j2, 29) < 0.08                             # 欠け落ちたブロックの跡(矩形の凹み)
    off = (hb - 0.5) * 0.7 + np.where(fall, 0.6 + 0.7 * _hash(kk, j.astype(np.int64), j2, 31), 0.0)
    lo = np.take(edges, np.clip(j - 1, 0, len(edges) - 1))
    hi_ = np.take(edges, np.clip(j, 0, len(edges) - 1))
    du = np.minimum(np.abs(u - lo), np.abs(hi_ - u))
    groove = 0.11 * np.exp(-(du / 0.07) ** 2)
    notch = 1.6 * np.exp(-((Z2 - 0.6) / 0.5) ** 2) * (0.65 + 0.35 * np.sin(X2 * 0.9 + 1.0))          # 波食ノッチ(水際のえぐれ)
    macro = _smooth1(rng, X2, 18.0, 1.0, 2) + _smooth1(rng, Z2 + 1.3 * X2, 14.0, 0.5, 2) - 0.1 * Z2   # 全体のうねりと上へ張り出す傾き
    bulge = sum(rng.uniform(1.0, 2.2) * np.exp(-(((X2 - cx) / rng.uniform(2.5, 5.0)) ** 2 + ((Z2 - cz) / rng.uniform(2.0, 4.5)) ** 2)) for cx, cz in
                ((rng.uniform(-W * 0.35, W * 0.35), rng.uniform(2, H * 0.8)) for _ in range(4)))              # 大きく張り出す塊(手前へ)
    yf = recess + off + groove + notch + macro - bulge
    yf = gaussian_filter(yf, (0.5, 0.8))                                           # 段差を 1 ボクセル程度に丸める(縞状のモアレを防ぐ)
    d = (yf[:, None, :] - ys[None, :, None]).astype(np.float32)
    d = np.clip(d, -2.5, 2.5)
    xx = xs[:, None, None]
    zz3 = zs[None, None, :]
    yy = ys[None, :, None]
    wt = _smooth1(rng, xs, W * 0.9, 1.0, 3)
    ztop = H * np.clip(0.86 + 0.1 * wt, 0.6, 1.0)[:, None, None] - 0.06 * np.clip(yy - 3, 0, None) ** 1.3 + 0 * zz3
    d = _smax(d, zz3 - ztop, 0.9)                                                   # 頂部は丸み・左右の塊で高さが違う
    d = _smax(d, yy - D, 0.8)
    ws = (1 - 0.08 * np.clip(_smooth1(rng, zs, H * 1.2, 1.0, 2), -1, 1) - 0.04) * (1 - 0.25 * (yy / D) ** 2)       # 高さごとに左右の端が出入りする
    d = _smax(d, np.abs(xx + 0.5 * np.sin(zz3 * 0.4)) - (W / 2 - 0.5) * ws, 1.2)
    d = _smax(d, -zz3 - 1.0, 0.3)
    f.d = d.astype(np.float32)
    ctx_out.update(dict(
        tone=lambda c: 0.5 * np.take(tone_l, np.clip(np.searchsorted(zb, c[:, 2] + dip * c[:, 0] + np.interp(c[:, 0], xs, wave)) - 1, 0, len(hard) - 1)),
        zw=0.0, pitdark=1))


def seacliff(f, W, D, H, rng_np, sp, st, lod):
    ctx = {}
    seacliff_sdf(f, W, D, H, rng_np, st, ctx)
    h = f.h
    # 洞状の窪み(ノッチの奥)とオーバーハングの下の庇
    for _ in range(3 if lod == "hi" else 1):
        c = np.array([rng_np.uniform(-W * 0.35, W * 0.35), rng_np.uniform(0.2, 1.0), rng_np.uniform(0.4, 1.6)])
        sl = f.box(c, 3.0)
        if sl is None:
            continue
        X, Y, Z = f.coords(sl)
        ax = np.array([rng_np.uniform(1.0, 2.2), rng_np.uniform(1.2, 2.2), rng_np.uniform(0.5, 1.0)])
        e = np.sqrt(((X - c[0]) / ax[0]) ** 2 + ((Y - c[1]) / ax[1]) ** 2 + ((Z - c[2]) / ax[2]) ** 2) - 1
        f.carve(sl, e * ax.min(), 0.4)
    z_c = lambda P: P[:, 2] / H
    nz_ = lambda P: fbm_pts(P + 71.0, rng_np, 6.0, 1.5)
    # タフォニ: 軟らかい下部・側面に出やすい。大小 3 スケール(下限はボクセル寸法)
    for s_, a_ in ((1.1, 0.12), (0.45, 0.2), (0.2, 0.28)):
        if s_ < 3.2 * h:
            continue
        honeycomb(f, s_, lambda P, a_=a_ * (1.0 if lod == "hi" else 0.35): np.clip(a_ * (1.0 + 1.1 * nz_(P)) * (1.1 - 0.7 * z_c(P)), 0, 0.9), rng_np)
    ctx["tafoni"] = True
    return ctx


def spire(f, R, rng_np, sp, st, lod):
    """複雑な岩山の突起: 尖塔 2〜3 本+鞍部+瘤。深い割れ目と蜂の巣状ピットが多段階で入る"""
    h = f.h
    f.blob(np.array([0, 0.1 * R, 0.1 * R]), R * 1.05, (1.5, 1.0, 0.5), 9, 0.09, 0)                       # 鞍部を作る広い土台
    n_sp = 2 + int(rng_np.integers(0, 2))
    for i in range(n_sp):
        a = (i - (n_sp - 1) / 2) * 1.15 + rng_np.uniform(-0.2, 0.2)
        c = np.array([a * R * 0.95, rng_np.uniform(-0.2, 0.25) * R, R * rng_np.uniform(0.35, 0.6)])
        f.blob(c, R * rng_np.uniform(0.42, 0.6), (rng_np.uniform(0.7, 1.0), rng_np.uniform(0.7, 1.0), rng_np.uniform(1.5, 2.2)), 10, 0.07, 0.35 * R)
    for _ in range(5):                                                                                   # 丸みのある瘤(縁や肩)
        c = np.array([rng_np.uniform(-1.4, 1.4) * R, rng_np.uniform(-0.3, 0.4) * R, rng_np.uniform(0.15, 1.3) * R])
        f.blob(c, R * rng_np.uniform(0.16, 0.3), (1, 1, rng_np.uniform(0.7, 1.1)), 0, 0.2, 0.2 * R)
    f.d = _smax(f.d, -(f.ax[2][None, None, :] + 0.08 * R), 0.05 * R)
    rmin = 3.2 * h
    for _ in range(2):                                                                                   # 深い割れ目(縦に長い)
        c = np.array([rng_np.uniform(-0.9, 0.9) * R, rng_np.uniform(-0.2, 0.2) * R, rng_np.uniform(0.4, 1.0) * R])
        n = np.array([1.0, rng_np.uniform(-0.5, 0.5), rng_np.uniform(-0.25, 0.25)])
        n /= np.linalg.norm(n)
        cleft(f, c, n, R * rng_np.uniform(1.0, 1.6), max(0.03 * R, 2.2 * h))
    f.chips(sp["chips"] * 0.45, R, rmin)
    return dict(tone=lambda c: -0.12 + 0.0 * c[:, 2], pitdark=1)


def build_crag(m, kind, form, st, rng, lod="hi", size=None):
    """form: seacliff / spire。m に頂点・面・材質を追加する"""
    sp = S.SPEC["coastal"]
    rng_np = np.random.default_rng(rng.getrandbits(32))
    if form == "seacliff":
        W, D, H = 22.0, 11.0, 13.0
        W, D, H = (size or W), D * (size or W) / 22.0, H * (size or W) / 22.0
        h = 0.095 * (W / 22.0) * LOD_H[lod]
        f = Field((-W / 2 - 0.5, -3.2, -1.6), (W / 2 + 0.5, D + 0.5, H + 0.6), h, rng_np)
        ctx = seacliff(f, W, D, H, rng_np, sp, st, lod)
        A = H * 0.55
        zbase = -1.0
    else:
        R = size or 1.7
        h = 0.03 * (R / 1.7) * LOD_H[lod]
        ext = 2.6 * R
        f = Field((-ext, -1.8 * R, -0.3 * R), (ext, 1.8 * R, 2.8 * R), h, rng_np)
        ctx = spire(f, R, rng_np, sp, st, lod)
        A = R
        zbase = -0.08 * R
        dens = lambda P: np.clip(0.5 + 0.8 * fbm_pts(P + 51.0, rng_np, 1.6 * R, 0.3 * R), 0.05, 0.75)
        for s_, fr in ((0.55 * R, (0.18, 0.4)), (0.22 * R, (0.2, 0.4)), (0.09 * R, (0.2, 0.42)), (0.04 * R, (0.2, 0.42))):
            if s_ >= 3.4 * h:
                honeycomb(f, s_, dens, rng_np, fr)
    rmin = 3.2 * h
    sp2 = dict(sp, wrinkle=0.9, strata=0.0)
    if lod != "far":
        f.add_cracks(int(4 + 6 * (W / 22.0 if form == "seacliff" else 1)), A, 0.9 * h)
        S.sculpt(f, A * (0.5 if form == "seacliff" else 1.0), sp2, st, rng_np, strata_scale=1.0, noise_extent=A * (0.5 if form == "seacliff" else 1.0))
        f.chips(0.25 * sp["chips"], A * 0.3, rmin * 1.1)
    S._keep_largest(f)
    out = S._mesh_from(f)
    if out is None:
        return
    v, fa, nr = out
    ctx = dict(ctx)
    if form == "spire":
        ctx.pop("zw", None)
    st2 = dict(st, weathering=max(st["weathering"], 0.5))
    if form == "spire":
        st2.update(lichen=min(1.0, st["lichen"] * 1.5 + 0.2))                              # 岩山は地衣類の斑(上面・縁)が目立つ
    if form == "seacliff":                                                                  # 海食崖は地衣類・苔が控えめ(塩分・波しぶきで乾いた肌)
        st2.update(lichen=st["lichen"] * 0.3, moss=st["moss"] * 0.4)
    mats = S._assign(v, fa, nr, f, st2, kind, rng_np, A, zbase, sp, ctx)
    base = len(m.v)
    m.v.extend(map(tuple, v.tolist()))
    m.f.extend((base + a, base + b, base + c) for a, b, c in fa.tolist())
    m.m.extend(mats)
    m.uv.extend([None] * len(fa))
    m.smooth = True
