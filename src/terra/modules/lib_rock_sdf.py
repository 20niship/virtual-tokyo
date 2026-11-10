"""超高ポリの岩(_hi): SDF ボクセルを彫刻(欠け・穴・割れ目・層理・皺)して marching cubes でメッシュ化する。穴やオーバーハングを作るため頂点変位ではなく SDF を使う。"""
import math

import numpy as np
from scipy.ndimage import gaussian_filter, label, laplace, map_coordinates
from skimage.measure import marching_cubes

from .registry import tex as _tex
from vt.materials import MATERIALS as _MAT

# cuts=土台の平面数 smooth=角の丸め(R 比) chips/pits=欠け・穴の量 cracks=割れ目数 strata=層理 wrinkle=皺 hmap=Bump 用高さ画像
SPEC = {
    "round": dict(cuts=9, smooth=0.16, chips=0.55, pits=0.25, cracks=3, strata=0.0, wrinkle=0.5, hmap="rockh_round.png"),
    "angular": dict(cuts=15, smooth=0.015, chips=1.2, pits=0.9, cracks=7, strata=0.0, wrinkle=0.35, hmap="rockh_angular.png"),
    "slab": dict(cuts=11, smooth=0.03, chips=0.9, pits=0.5, cracks=4, strata=1.0, wrinkle=0.6, hmap="rockh_slab.png"),
    "karst": dict(cuts=8, smooth=0.05, chips=0.7, pits=2.0, cracks=4, strata=0.3, wrinkle=0.8, hmap="rockh_karst.png"),
    "soft": dict(cuts=6, smooth=0.09, chips=0.5, pits=1.5, cracks=2, strata=0.15, wrinkle=0.6, hmap="rockh_soft.png"),
    "coastal": dict(cuts=8, smooth=0.06, chips=0.8, pits=2.6, cracks=5, strata=0.5, wrinkle=1.0, hmap="rockh_karst.png"),
}
VARIANTS = ["b0", "b1", "b2", "b3", "b4", "dark", "fresh", "rust", "lich_y", "lich_g", "lich_w", "moss", "moss_dry", "moss_dk", "wet", "algae", "salt", "streak"]


def _rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def _hex(c):
    return "#%02x%02x%02x" % tuple(int(np.clip(v, 0, 255)) for v in c)


KINDS_TINT = {}   # 岩種 → 材質の tint(hi_gain 込み, sRGB hex)。頂点色が相対値なので基準に使う


def register_materials(kinds):
    """岩種ごとに 14 変種(明度 5 段・暗色・新鮮面・錆び・地衣類 3・苔 2・濡れ)の材質を登録。Bump は高さ画像"""
    for k, sp in kinds.items():
        base = _rgb(sp["tint"]) * sp.get("hi_gain", 1.0)
        hm = SPEC[sp["shape"]]["hmap"] if sp["shape"] in SPEC else "rockh_round.png"
        tints = {"b0": base * 0.62, "b1": base * 0.8, "b2": base * 0.98, "b3": base * 1.12, "b4": base * 1.25, "dark": base * 0.5, "fresh": np.array([235, 232, 226.]),
                 "rust": base * 0.8 + np.array([48, 26, 8.]), "lich_y": np.array([190, 182, 110.]), "lich_g": np.array([135, 150, 118.]), "lich_w": np.array([218, 216, 200.]),
                 "moss": np.array([96, 150, 38.]), "moss_dry": np.array([150, 156, 62.]), "moss_dk": np.array([70, 100, 40.]), "wet": base * 0.45,
                 "algae": np.array([42, 54, 36.]), "salt": np.array([226, 222, 210.]), "streak": base * 0.42 + np.array([6, 5, 3.])}
        KINDS_TINT[k] = _hex(base)
        _MAT[f"rkv_{k}"] = dict(_tex(sp["tex"], sp["size"] * 0.22, 0.88, 1.0, tint=_hex(base)), hmap=hm, vcol=True)   # 頂点色で塗る 1 材質(crag 形)
        for v, t in tints.items():
            rough = {"wet": 0.45, "dark": 0.95, "fresh": 0.85, "moss": 1.0, "moss_dry": 1.0, "moss_dk": 1.0, "algae": 0.5, "salt": 0.95, "streak": 0.93}.get(v, 0.9)
            if v.startswith("moss"):
                mat = _tex("moss.png", 0.4, 1.0, 1.6, tint={"moss": "#8fa874", "moss_dry": "#aaa672", "moss_dk": "#5f7a48"}[v])
            else:
                mat = _tex(sp["tex"], sp["size"] * 0.22, rough, 1.0, tint=_hex(t))
                mat["hmap"] = hm
            _MAT[f"rkh_{k}_{v}"] = mat


# ---- ノイズ ----
def _lattice(rng, n):
    return rng.random((n, n, n), dtype=np.float32) * 2 - 1


def fbm_pts(P, rng, wl0, wl1, ridged=False, gain=0.55):
    """点群 P(N,3) 上の 3 次元 fBm(値ノイズ、周期格子)。波長 wl0 → wl1、1 オクターブごとに半分。ridged=1-|n| の尖った稜線。範囲はおよそ [-1, 1]"""
    out, tot, amp, wl = np.zeros(len(P), np.float32), 0.0, 1.0, wl0
    while wl >= wl1 * 0.999:
        n = 24
        lat = _lattice(rng, n)
        q = (P / wl + rng.random(3) * n).T % n
        v = map_coordinates(lat, q, order=3 if wl > 6 * wl1 else 1, mode="grid-wrap").astype(np.float32)
        out += amp * ((1 - 2 * np.abs(v)) if ridged else v)
        tot += amp
        amp *= gain
        wl /= 2
    return out / tot


def _smax(a, b, k):
    if k <= 0:
        return np.maximum(a, b)
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.maximum(a, b) + h * h * k * 0.25


def _smin(a, b, k):
    return -_smax(-a, -b, k)


class Field:
    def __init__(self, lo, hi, h, rng):
        self.h, self.rng = h, rng
        self.o = np.asarray(lo, float)
        self.n = np.ceil((np.asarray(hi, float) - self.o) / h).astype(int) + 1
        self.ax = [self.o[i] + h * np.arange(self.n[i], dtype=np.float32) for i in range(3)]
        self.d = np.full(self.n, 1e3, np.float32)
        self.fresh = np.zeros(self.n, np.uint8)
        self.cracks = []                                   # (c, n, L, w)

    def box(self, c, r):
        i0 = np.maximum(np.floor((np.asarray(c) - r - self.o) / self.h).astype(int), 0)
        i1 = np.minimum(np.ceil((np.asarray(c) + r - self.o) / self.h).astype(int) + 1, self.n)
        if (i1 <= i0).any():
            return None
        return tuple(slice(a, b) for a, b in zip(i0, i1))

    def coords(self, sl):
        return np.meshgrid(self.ax[0][sl[0]], self.ax[1][sl[1]], self.ax[2][sl[2]], indexing="ij")

    def surface(self):
        return np.argwhere(np.abs(self.d) < 0.75 * self.h)

    def grad_at(self, idx):
        i = np.clip(idx, 1, self.n - 2)
        g = np.array([self.d[i[0] + 1, i[1], i[2]] - self.d[i[0] - 1, i[1], i[2]], self.d[i[0], i[1] + 1, i[2]] - self.d[i[0], i[1] - 1, i[2]],
                      self.d[i[0], i[1], i[2] + 1] - self.d[i[0], i[1], i[2] - 1]], float)
        return g / max(np.linalg.norm(g), 1e-9)

    def pos(self, idx):
        return self.o + idx * self.h

    def blob(self, c, R, sc, cuts, smooth, k_union):
        """多面体の塊を c に追加(sc=軸ごとの伸縮)。内部は d<0"""
        rng = self.rng
        sl = self.box(c, 1.5 * R * max(sc))
        if sl is None:
            return
        X, Y, Z = self.coords(sl)
        Q = [(X - c[0]) / sc[0], (Y - c[1]) / sc[1], (Z - c[2]) / sc[2]]
        d = np.sqrt(Q[0] ** 2 + Q[1] ** 2 + Q[2] ** 2) - R * 1.12
        for _ in range(cuts):
            n = rng.normal(size=3)
            n /= np.linalg.norm(n)
            off = R * rng.uniform(0.5, 0.88)
            d = _smax(d, Q[0] * n[0] + Q[1] * n[1] + Q[2] * n[2] - off, smooth * R)
        d *= min(sc)
        self.d[sl] = _smin(self.d[sl], d, k_union) if k_union > 0 else np.minimum(self.d[sl], d)

    def carve(self, sl, sdf_region, k, fresh=False):
        """範囲の SDF(内側が負)を削る"""
        cur = self.d[sl]
        new = _smax(cur, -sdf_region, k)
        if fresh:
            self.fresh[sl][(np.abs(sdf_region) < 1.6 * self.h) & (new > -1.5 * self.h) & (new < 1.5 * self.h)] = 255
        self.d[sl] = new

    def chips(self, spec_scale, R, rmin, depth_k=(0.08, 0.3)):
        rng, h = self.rng, self.h
        r = 0.34 * R
        lvl = 0
        while r >= rmin:
            cand = self.surface()
            if len(cand) == 0:
                break
            area = len(cand) * h * h
            cnt = max(2, int(0.045 * area / r ** 2 * spec_scale))
            for _ in range(cnt):
                idx = cand[rng.integers(len(cand))]
                n0 = self.grad_at(idx)
                n = n0 + 0.6 * rng.normal(size=3)
                n /= np.linalg.norm(n)
                c = self.pos(idx)
                rr = r * rng.uniform(0.7, 1.25)
                depth = rr * rng.uniform(*depth_k)
                sl = self.box(c, rr + h)
                if sl is None:
                    continue
                X, Y, Z = self.coords(sl)
                q = (X - c[0]) * n[0] + (Y - c[1]) * n[1] + (Z - c[2]) * n[2]
                ball = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2) - rr
                self.carve(sl, np.maximum(ball, -q - depth), 0.15 * rr, fresh=lvl >= 2)
            r *= 0.55
            lvl += 1

    def pits(self, amount, R, rmin):
        rng, h = self.rng, self.h
        r = 0.11 * R
        while r >= rmin:
            cand = self.surface()
            if len(cand) == 0:
                break
            area = len(cand) * h * h
            cnt = int(0.005 * area / r ** 2 * amount)
            for _ in range(cnt):
                idx = cand[rng.integers(len(cand))]
                n = self.grad_at(idx)
                rr = r * rng.uniform(0.6, 1.3)
                c = self.pos(idx) + n * rr * rng.uniform(0.35, 0.85)
                ax = rr * np.array([1, rng.uniform(0.6, 1.5), rng.uniform(0.6, 1.5)])
                sl = self.box(c, 1.6 * ax.max())
                if sl is None:
                    continue
                X, Y, Z = self.coords(sl)
                e = np.sqrt(((X - c[0]) / ax[0]) ** 2 + ((Y - c[1]) / ax[1]) ** 2 + ((Z - c[2]) / ax[2]) ** 2) - 1
                self.carve(sl, e * ax.min(), 0.3 * rr)
            r *= 0.5

    def add_cracks(self, count, R, wmin):
        rng, h = self.rng, self.h
        cand = self.surface()
        for _ in range(count if len(cand) else 0):
            idx = cand[rng.integers(len(cand))]
            c = self.pos(idx)
            n = rng.normal(size=3)
            n /= np.linalg.norm(n)
            L = R * rng.uniform(0.35, 0.9)
            w = max(wmin, R * rng.uniform(0.002, 0.006))
            sl = self.box(c, L)
            if sl is None:
                continue
            X, Y, Z = self.coords(sl)
            dist = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2)
            q = (X - c[0]) * n[0] + (Y - c[1]) * n[1] + (Z - c[2]) * n[2]
            taper = np.clip(1 - (dist / L) ** 2, 0, 1)
            self.carve(sl, np.abs(q) - w * taper, 0.5 * w)
            self.cracks.append((c, n, L, w))


def _crack_mask(P, cracks):
    m = np.zeros(len(P), np.float32)
    for c, n, L, w in cracks:
        dist = np.linalg.norm(P - c, axis=1)
        q = np.abs((P - c) @ n)
        m = np.maximum(m, np.exp(-(q / (w * 2.5 + 1e-6)) ** 2) * (dist < L))
    return m


def sculpt(f, R, sp, st, rng_np, strata_scale, noise_extent):
    """層理・皺・粒の変位(d への加算)"""
    h = f.h
    X, Y, Z = np.meshgrid(*f.ax, indexing="ij")
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], -1)
    near = np.abs(f.d.ravel()) < 0.5 * R                                 # 表面から離れた点は計算しない
    idx = np.flatnonzero(near)
    Pn = P[idx]
    add = np.zeros(len(Pn), np.float32)
    A = noise_extent
    add += 0.05 * A * fbm_pts(Pn, rng_np, 0.9 * A, 0.3 * A)                                   # 平面を崩す低周波
    warp = fbm_pts(Pn + 11.3, rng_np, 0.3 * A, 0.1 * A)
    Pw = Pn + warp[:, None] * 0.14 * A
    add += sp["wrinkle"] * 0.03 * A * fbm_pts(Pw, rng_np, 0.3 * A, 2.2 * h, ridged=True)    # 皺・稜線(ridged fBm)
    add += 0.35 * h * fbm_pts(Pn + 5.7, rng_np, 6 * h, 2 * h, ridged=True)                    # 粒
    if sp["strata"] > 0:
        s = Pn[:, 2] / (strata_scale) + 0.35 * fbm_pts(Pn + 3.1, rng_np, 0.7 * A, 0.25 * A)
        band = np.abs(((s % 1.0) - 0.5) * 2)                                                  # 三角波: 硬い層は出っ張り、軟らかい層はへこむ
        band = np.clip(band * 1.6 - 0.3, 0, 1)
        add += sp["strata"] * 0.028 * strata_scale * (band - 0.5) * 2
    flat = f.d.reshape(-1)
    flat[idx] += add


def _keep_largest(f):
    """彫刻で切り離された破片を消す(最大の連結成分だけ残す)"""
    lab, n = label(f.d < 0)
    if n > 1:
        big = np.argmax(np.bincount(lab.ravel())[1:]) + 1
        f.d[(lab != big) & (f.d < 0)] = f.h


def _mesh_from(f):
    d = f.d
    try:
        v, fa, nr, _ = marching_cubes(d, 0.0, spacing=(f.h, f.h, f.h))
    except (ValueError, RuntimeError):
        return None
    return v + f.o, fa, nr


def _assign(v, fa, nr, f, st, kind, rng_np, R, zbase, spec, ctx=None):
    """面ごとの材質: 明度の色ムラ・窪み・稜線・新鮮面・錆び・地衣類・苔・濡れ"""
    cen = v[fa].mean(1)
    fn = -nr[fa].mean(1)                                                              # skimage の法線は内向き(d<0 が内側)なので外向きへ
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-9)
    nz = fn[:, 2]
    # 曲率(ガウシアンした d のラプラシアン): 小スケール=稜線/細かい窪み、大スケール=大きな窪み
    q = ((cen - f.o) / f.h).T
    lap_s = laplace(gaussian_filter(f.d, 1.6)) / f.h ** 2
    lap_l = laplace(gaussian_filter(f.d, 6.0)) / f.h ** 2
    cs = map_coordinates(lap_s, q, order=1) * R
    cl = map_coordinates(lap_l, q, order=1) * R
    fresh = map_coordinates(f.fresh.astype(np.float32) / 255.0, q, order=1)
    crack = _crack_mask(cen, f.cracks)
    tone = fbm_pts(cen, rng_np, 0.9 * R, 0.12 * R)
    pat = fbm_pts(cen + 40.0, rng_np, 0.8 * R, 0.1 * R)
    pat2 = fbm_pts(cen + 80.0, rng_np, 0.5 * R, 0.06 * R)
    streak = fbm_pts(cen * np.array([2.5, 2.5, 0.35]) + 9.0, rng_np, 0.5 * R, 0.1 * R)
    fine = fbm_pts(cen + 120.0, rng_np, 0.12 * R, 0.02 * R)
    # 基本: 明度 5 段(色ムラ)。凸の稜線は明るく、窪みは暗く(参考: 稜線のドライブラシ)
    lvl = 0.5 + 0.5 * tone + 0.12 * fine + 0.22 * np.tanh(cs * 0.35) - 0.2 * np.tanh(-cl * 0.4)
    if ctx:
        lvl = lvl + ctx["tone"](cen)                                                   # 層ごとの色の濃淡
    idx = np.clip((lvl * 5).astype(int), 0, 4)
    var = np.array(["b0", "b1", "b2", "b3", "b4"], dtype=object)[idx]
    w = st["weathering"]
    if st["chipped"] > 0:
        var = np.where(fresh > 0.4 + 0.5 * (1 - st["chipped"]), "fresh", var)
    stain = (streak > 0.45 - 0.4 * w) & (nz < 0.55) & (w > 0.3)
    var = np.where(stain, "rust", var)
    dark = (crack > (0.6 if ctx else 0.25)) | (cl < (np.percentile(cl, 3) if ctx else -0.9)) & (cs < (np.percentile(cs, 20) if ctx else -0.2))
    var = np.where(dark, "dark", var)
    wet = (cen[:, 2] < zbase + 0.07 * R) & (w > 0.3)
    var = np.where(wet, "wet", var)
    if ctx:
        sx = fbm_pts(cen * np.array([4.0, 4.0, 0.25]) + 33.0, rng_np, 0.9 * R, 0.1 * R)     # 縦長ノイズ = 雨筋
        var = np.where((sx > 0.52) & (nz < 0.8) & (cen[:, 2] > ctx.get("zw", -9) + 1.5) & (var != "dark"), "streak", var)
        if "zw" in ctx:                                                                # 水際: 濡れ帯・藻・塩の帯
            zr = cen[:, 2] - ctx["zw"] - 0.25 * fine
            var = np.where(zr < 1.9, np.where(zr < 0.9, "wet", "salt"), var)
            var = np.where((zr < 0.45) & (fine > -0.25), "algae", var)
            var = np.where((zr >= 0.9) & (zr < 1.9) & (pat2 < 0.1), np.where(var == "salt", "b4", var), var)
    pit = (cs < np.percentile(cs, 7)) if ctx else (cs < -1.1) & (cl > -0.9)
    if ctx:
        var = np.where(pit & (ctx.get("pitdark", 0) > 0), "dark", var)
    if st["lichen"] > 0:
        edge = 0.4 * np.tanh(cs * 0.6) if ctx else 0.0                                 # 地衣類は上面・縁(凸部)に優先
        lich = (nz > 0.05) & (pat * 0.7 + pat2 * 0.3 + edge + (0.4 * nz + 0.5 * (cen[:, 2] - cen[:, 2].min()) / max(float(np.ptp(cen[:, 2])), 1e-6) if ctx else 0) > 0.55 - 0.9 * st["lichen"]) & ~dark
        kind_l = np.where(pat2 > 0.2, "lich_y", np.where(pat2 > -0.2, "lich_g", "lich_w"))
        var = np.where(lich, kind_l, var)
    if st["moss"] > 0:
        mm = st["moss"]
        up = np.clip((nz - 0.1) / 0.6, 0, 1)                                            # 上向きほど苔が乗る
        cav = np.clip(-cl * 0.6, 0, 1)                                                  # 窪み・割れ目に溜まる
        cover = up * (0.7 + 0.5 * mm) + (0.25 if ctx else 0.6) * cav + 0.3 * crack
        thr = 1.0 - 1.05 * mm
        mossy = (cover + 0.5 * pat + 0.18 * fine) > thr
        var = np.where(mossy, np.where(pat2 > 0.35, "moss_dry", np.where(fine < -0.15, "moss_dk", "moss")), var)
    return [f"rkh_{kind}_{x}" for x in var]


def build(m, kind, sp_name, st, rng, R, form, sc, w_extent=None):
    """岩を 1 つ作って Mesh m に追加する。form: boulder / outcrop"""
    sp = SPEC[sp_name]
    rng_np = np.random.default_rng(rng.getrandbits(32))
    h = R / 78 if form == "boulder" else R / 60
    scale_chip = sp["chips"] * (1 - 0.45 * st["weathering"]) + 0.2 * st["chipped"]
    smooth = sp["smooth"] * (1 + 1.5 * st["weathering"])
    if form == "boulder":
        ext = R * 1.45 * max(sc)
        f = Field((-ext, -ext, -R * 0.45), (ext, ext, R * 1.3), h, rng_np)
        f.blob(np.array([0, 0, 0.3 * R * sc[2]]), R, sc, sp["cuts"], smooth, 0)
        A = R
    else:
        ext = 2.6 * R
        f = Field((-ext - 1, -ext, -0.8), (ext + 1, ext, 2.6 * R), h, rng_np)
        for _ in range(3 + int(rng_np.integers(0, 3))):
            c = np.array([rng_np.uniform(-1.6, 1.6) * R * 0.9, rng_np.uniform(-1.2, 1.2) * R * 0.9, rng_np.uniform(0.0, 0.6) * R])
            Rb = R * rng_np.uniform(0.55, 0.95)
            f.blob(c, Rb, (rng_np.uniform(0.85, 1.3), rng_np.uniform(0.85, 1.3), rng_np.uniform(0.5, 0.8)), sp["cuts"], smooth, 0.12 * R)
        A = R * 1.6
    zb = f.o[2] + 0.25 * R * 0.0
    f.d = _smax(f.d, -(f.ax[2][None, None, :] + 0.1 * R), 0.05 * R)                         # 底は地面に埋める(z=-0.1R で平らに切る)
    rmin = 3.2 * h
    f.chips(scale_chip, A, rmin)
    f.pits(sp["pits"] * (0.6 + 0.8 * st["weathering"]), A, rmin)
    f.add_cracks(int(sp["cracks"] * (1.3 - st["weathering"] * 0.5)), A, 0.9 * h)
    sculpt(f, A, sp, st, rng_np, strata_scale=max(0.18 * A, 0.06), noise_extent=A)
    f.chips(0.25 * scale_chip, A * 0.3, rmin * 1.1)                                          # 皺の後にも小さな欠けを足す
    _keep_largest(f)
    out = _mesh_from(f)
    if out is None:
        return
    v, fa, nr = out
    mats = _assign(v, fa, nr, f, st, kind, rng_np, A, -0.1 * R, sp)
    base = len(m.v)
    m.v.extend(map(tuple, v.tolist()))
    m.f.extend((base + a, base + b, base + c) for a, b, c in fa.tolist())
    m.m.extend(mats)
    m.uv.extend([None] * len(fa))
    m.smooth = True


def build_cliff(m, kind, sp_name, st, rng, W, H, v_idx):
    """崖パネル(幅 W・高さ H、面は -y 向き)。低周波の起伏 + 層理 + 欠け・穴・割れ目"""
    sp = SPEC[sp_name]
    rng_np = np.random.default_rng(rng.getrandbits(32))
    h = 0.07
    f = Field((-W / 2, -1.6, -0.6), (W / 2, 2.2, H - 0.6), h, rng_np)
    nxz = (int(f.n[0]), int(f.n[2]))
    cx, cz = np.linspace(0, 1, 36), np.linspace(0, 1, 24)
    gx, gz = np.meshgrid(cx * W - W / 2, cz * H, indexing="ij")
    big = fbm_pts(np.stack([gx.ravel() * 0.25, gz.ravel() * 0.35, np.full(gx.size, v_idx * 0.7)], -1), rng_np, 1.4, 0.35).reshape(gx.shape)
    ledge = 0.45 * np.sin(gz * 1.9 + v_idx) + 0.25 * np.sin(gz * 4.3) if sp["strata"] > 0 else 0.15 * np.sin(gz * 1.2 + v_idx)
    Y = 0.2 + 0.9 * big + ledge + 0.35 * np.sin(gx * 1.3 + gz * 0.7)
    Yf = map_coordinates(Y, np.meshgrid(np.linspace(0, 35, nxz[0]), np.linspace(0, 23, nxz[1]), indexing="ij"), order=3, mode="nearest")
    f.d = (Yf[:, None, :] - f.ax[1][None, :, None]).astype(np.float32)
    f.chips(sp["chips"], 1.4, 3.2 * h)
    f.pits(sp["pits"] * 0.5, 1.4, 3.2 * h)
    f.add_cracks(int(sp["cracks"] * 3), 1.6, 1.5 * h)
    sculpt(f, 1.5, sp, st, rng_np, strata_scale=0.55, noise_extent=1.5)
    _keep_largest(f)
    out = _mesh_from(f)
    if out is None:
        return
    v, fa, nr = out
    mats = _assign(v, fa, nr, f, st, kind, rng_np, 1.5, -0.6, sp)
    base = len(m.v)
    m.v.extend(map(tuple, v.tolist()))
    m.f.extend((base + a, base + c, base + b) for a, b, c in fa.tolist())                   # 外向き(-y)が表になるよう反転
    m.m.extend(mats)
    m.uv.extend([None] * len(fa))
    m.smooth = True
