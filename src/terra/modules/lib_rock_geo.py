"""lib_rock の拡張: 岩種 × 形 × 状態(苔・地衣類・風化・欠け・草・堆積土) × 詳細度(near / far)。
名前: rock_<岩種>_<形>_<v>(near)と同名 + "_far"(低ポリ)。形: boulder_s|m|l / outcrop / cliff / column(安山岩のみ)。
状態は module のパラメータ(STATES): moss=上向き面に苔、lichen=地衣類の斑、weathering=丸み・水染み、chipped=欠けた新鮮面、grass=根元の草の房、soil=堆積土の裾。"""
import math

import numpy as np
from vt import tree_gen as _tg
from vt.materials import MATERIALS as _MAT

from .lib_rock import _ICO, _ico, _noise_dir
from .registry import reg
from .registry import tex as _tex

KINDS = {   # shape: round(丸い)/angular(角)/slab(板状・層理)/karst(溶食)/soft(崩れやすい)、cuts=切り落とし面数、rough=歪み、flat=扁平率
    "granite": dict(ja="花崗岩", tex="rock_granite.png", tint="#b8b6b0", size=2.4, shape="round", cuts=5, rough=0.13, flat=0.78),
    "andesite": dict(ja="安山岩/玄武岩", tex="rock_basalt.png", tint="#b0b0b4", size=3.0, shape="angular", cuts=10, rough=0.20, flat=0.72),
    "sandstone": dict(ja="砂岩/泥岩", tex="rock_sandstone.png", tint="#e6d8c0", size=2.0, shape="slab", cuts=8, rough=0.12, flat=0.5),
    "limestone": dict(ja="石灰岩", tex="rock_limestone.png", tint="#f0eee8", size=2.6, shape="karst", cuts=6, rough=0.22, flat=0.7),
    "tuff": dict(ja="凝灰岩", tex="rock_tuff.png", tint="#e0d8c0", size=2.4, shape="soft", cuts=4, rough=0.20, flat=0.75),
    "river": dict(ja="川原の丸石", tex="rock_river.png", tint="#d0ccc4", size=1.0, shape="round", cuts=0, rough=0.06, flat=0.62),
}
STATES = [
    dict(name="fresh", ja="新鮮・欠け", weathering=0.05, moss=0.0, lichen=0.0, chipped=0.8, grass=0, soil=0.0),
    dict(name="weathered", ja="風化・地衣類", weathering=0.6, moss=0.1, lichen=0.55, chipped=0.1, grass=0, soil=0.2),
    dict(name="mossy", ja="苔むし・草", weathering=0.7, moss=0.9, lichen=0.15, chipped=0.0, grass=3, soil=0.6),
    dict(name="stained", ja="水染み・汚れ", weathering=0.5, moss=0.25, lichen=0.1, chipped=0.15, grass=1, soil=0.3),
]
for _k, _s in KINDS.items():
    _MAT[f"rk_{_k}"] = _tex(_s["tex"], _s["size"], 0.92 if _k != "river" else 0.6, 0.8, tint=_s["tint"])
    _MAT[f"rk_{_k}_fresh"] = _tex(_s["tex"], _s["size"], 0.9, 0.7, tint="#ffffff")
    _MAT[f"rk_{_k}_lichen"] = _tex(_s["tex"], _s["size"], 0.95, 0.9, tint="#b9b27a")
    _MAT[f"rk_{_k}_stain"] = _tex(_s["tex"], _s["size"], 0.9, 0.8, tint="#6a625a")
_MAT["rk_moss"] = _tex("moss.png", 0.5, 0.98, 1.2, tint="#a8ac90")
_MAT["rk_sediment"] = _tex("soil_humus.png", 0.8, 0.98, 0.6)


def _face_normals(m):
    V = np.array(m.v, float)
    n = np.zeros((len(m.f), 3))
    for i, f in enumerate(m.f):
        n[i] = np.cross(V[f[1]] - V[f[0]], V[f[2]] - V[f[0]])
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12), V


def apply_state(m, kind, rng, st, cut_faces=None, grass=True):
    """面ごとに材質を割り当てて状態を表す: 上向き(n_z>0.45)に苔、下部に水染み、斑状に地衣類、切り落とし面は欠けた新鮮面。根元に草の房と堆積土の裾を足す"""
    if not m.f:
        return
    n, V = _face_normals(m)
    nz = n[:, 2]
    zmin = V[:, 2].min()
    zr = max(V[:, 2].max() - zmin, 1e-6)
    cz = np.array([V[list(f), 2].mean() for f in m.f])
    r = np.array([rng.random() for _ in m.f])
    patch = np.array([(math.sin(V[f[0]][0] * 4.1 + 1.7) * math.sin(V[f[0]][1] * 3.7) + 1) / 2 for f in m.f])      # 斑(近い面は同じ材質になりやすい)
    base = f"rk_{kind}"
    for i in range(len(m.f)):
        mat = base
        if cut_faces is not None and cut_faces[i] and r[i] < st["chipped"]:
            mat = base + "_fresh"
        elif st["lichen"] > 0 and nz[i] > 0.1 and patch[i] * 0.7 + r[i] * 0.3 < st["lichen"] * 0.6:
            mat = base + "_lichen"
        elif st["weathering"] > 0.3 and (cz[i] - zmin) / zr < 0.45 and r[i] < st["weathering"] * 0.6 and nz[i] < 0.6:
            mat = base + "_stain"
        if st["moss"] > 0 and nz[i] > 0.45 and (patch[i] * 0.5 + r[i] * 0.5) < st["moss"] * (0.35 + 0.65 * nz[i]):
            mat = "rk_moss"
        m.m[i] = mat
    if grass and st["grass"] > 0:
        low = np.flatnonzero((nz > 0.3) & ((cz - zmin) / zr < 0.5))
        for _ in range(int(st["grass"])):
            if not len(low):
                break
            f = m.f[int(low[int(rng.random() * len(low))])]
            p = np.mean([V[j] for j in f], 0)
            tuft, _meta = _tg.build_grass("tuft", 0.12 + 0.1 * rng.random(), int(rng.random() * 99))
            sc = 0.45 + 0.3 * rng.random()
            i0 = len(m.v)
            m.v.extend((x * sc + p[0], y * sc + p[1], z * sc + p[2] - 0.02) for x, y, z in tuft.v)
            m.f.extend(tuple(j + i0 for j in ff) for ff in tuft.f)
            m.m.extend(tuft.m)
            m.uv.extend(tuft.uv)
    if st["soil"] > 0:
        R = max(np.ptp(V[:, 0]), np.ptp(V[:, 1])) * 0.5 * (1.0 + 0.1 * st["soil"])
        c = V[:, :2].mean(0)
        k = 12
        ring = [(c[0] + R * math.cos(2 * math.pi * i / k) * (0.9 + 0.2 * rng.random()), c[1] + R * math.sin(2 * math.pi * i / k) * (0.9 + 0.2 * rng.random()), zmin + 0.02) for i in range(k)]
        i0 = len(m.v)
        m.v.extend(ring + [(c[0], c[1], zmin + zr * (0.05 + 0.04 * st["soil"]))])
        for i in range(k):
            m.f.append((i0 + i, i0 + (i + 1) % k, i0 + k))
            m.m.append("rk_sediment")
            m.uv.append(None)


def _smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def _fbm(P, rng, wl0, wl1, ridged, n=4):
    """3 次元の fBm(方向ごとの正弦波の和)。波長 wl0 から wl1 まで 1 オクターブごとに半分、振幅は 0.55 倍。ridged=尖った稜線(1-|sin|)"""
    out, tot, amp, wl = np.zeros(len(P)), 0.0, 1.0, wl0
    while wl >= wl1:
        for _ in range(n):
            k = np.array([rng.gauss(0, 1) for _ in range(3)])
            k *= 2 * math.pi / wl / np.linalg.norm(k)
            s = np.sin(P @ k + rng.uniform(0, 6.28))
            out += amp * ((1 - np.abs(s)) if ridged else s)
        tot += amp * n
        amp *= 0.55
        wl /= 2
    return out / max(tot, 1e-9)


def hi_detail(P, nrm, rng, R, shape, sub):
    """hi(超高ポリ)の微細起伏: 岩種ごとの粗さの fBm を法線方向へ変位 + 割れ目の溝。最小波長は辺長の約 2.5 倍(これ以下はエイリアスになる)"""
    wl1 = max(R * 8 / 2 ** sub, 0.01)
    ridged = shape in ("angular", "slab", "karst")
    amp = {"round": 0.035, "soft": 0.05, "angular": 0.06, "slab": 0.05, "karst": 0.07}[shape] * R
    h = _fbm(P, rng, R * 0.7, wl1, ridged)
    P = P + nrm * ((h - h.mean()) * amp)[:, None]
    warp = _fbm(P, rng, R * 0.5, R * 0.1, False, 2)
    for _ in range(5 if shape in ("angular", "slab") else 2 if shape != "round" else 1):          # 割れ目: 平面状の細い溝
        n = np.array([rng.gauss(0, 1) for _ in range(3)])
        n /= np.linalg.norm(n)
        s = np.sin((P @ n + 0.12 * R * warp) * 2 * math.pi / (R * rng.uniform(0.35, 0.9)) + rng.uniform(0, 6.28))
        P = P - nrm * (0.02 * R * np.exp(-(s / 0.05) ** 2))[:, None]
    return P


def blob(m, R, rng, kind, st, lod, ctr=(0, 0, 0), sink=0.25, flat=None, sub_cap=4):
    """岩種の形の塊を追加し、切り落とし面のフラグ列を返す。lod: near=icosphere 2 分割(320 面) / far=1 分割(80 面) / hi=5〜6 分割(2 万〜8 万面)+微細起伏"""
    sp = KINDS[kind]
    sub = min((4 if R > 1.5 else 3 if R > 0.5 else 2), sub_cap) if lod == "near" else min(6 if R > 1.0 else 5, sub_cap) if lod == "hi" else 1
    if sub not in _ICO:
        _ICO[sub] = _ico(sub)
    V, F = _ICO[sub]
    nz = _noise_dir(rng)
    rough = sp["rough"] * (1 - 0.5 * st["weathering"] * (1 if sp["shape"] != "soft" else 0.3))      # 風化すると角が取れる
    d = V.copy()
    rad = R * (1 + rough * nz(d))
    if sp["shape"] == "karst":                                                                    # 溶食: 高周波の凹み
        hi = _noise_dir(rng, 9)(d * 2.3)
        rad = rad * (1 - 0.32 * np.clip(-hi - 0.1, 0, 1))
    P = d * rad[:, None]
    P[:, 2] *= flat if flat is not None else sp["flat"]
    P[:, 0] *= rng.uniform(0.85, 1.3)
    cut = np.zeros(len(P), bool)
    for _ in range(int(round(sp["cuts"] * (1 - 0.55 * st["weathering"])))):
        n = np.array([rng.gauss(0, 1) for _ in range(3)])
        n /= np.linalg.norm(n)
        ex = np.maximum(0, P @ n - R * rng.uniform(0.5, 0.82))
        cut |= ex > 1e-6
        P -= ex[:, None] * n
    if sp["shape"] == "slab":                                                                     # 層理: 水平な段(棚)
        step = max(R * 0.3, 0.05)
        t = P[:, 2] / step
        P[:, 2] = (np.floor(t) + _smoothstep((t - np.floor(t)) * 1.6 - 0.3)) * step * 0.5 + P[:, 2] * 0.5
    if lod == "hi":
        P = hi_detail(P, d, rng, R, sp["shape"], sub)
    P[:, 2] -= sink * R * sp["flat"]
    P += np.array(ctr)
    base = len(m.v)
    m.v.extend(map(tuple, P))
    cf = []
    for a, b, c in F:
        m.f.append((base + a, base + b, base + c))
        m.m.append(f"rk_{kind}")
        m.uv.append(None)
        cf.append(bool(cut[a] and cut[b] and cut[c]))
    return cf


def column_bundle(m, R, rng, kind, lod):
    """柱状節理(安山岩/玄武岩): 六角柱の束。上面はわずかに傾ける。far は柱数を減らす"""
    k = 3 if lod == "near" else 2
    cf = []
    for i in range(-k, k + 1):
        for j in range(-k, k + 1):
            x, y = (i + 0.5 * (j % 2)) * R * 0.62, j * R * 0.54
            if math.hypot(x, y) > R * 1.5 * (1 + 0.3 * rng.random()) or (lod == "far" and (i + j) % 2):
                continue
            h = R * rng.uniform(0.8, 2.4) * (1 - 0.25 * math.hypot(x, y) / (R * 1.6))
            r = R * 0.34
            tilt = (rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25))
            b = len(m.v)
            for z0, hh in ((-0.3 * R, 0.0), (h, 1.0)):
                for q in range(6):
                    a = math.pi / 3 * q
                    m.v.append((x + r * math.cos(a), y + r * math.sin(a), z0 + hh * (math.cos(a) * tilt[0] + math.sin(a) * tilt[1]) * r))
            for q in range(6):
                q2 = (q + 1) % 6
                m.f.append((b + q, b + q2, b + 6 + q2, b + 6 + q))
                m.m.append(f"rk_{kind}")
                m.uv.append(None)
                cf.append(False)
            m.f.append((b + 6, b + 7, b + 8, b + 9, b + 10, b + 11))
            m.m.append(f"rk_{kind}")
            m.uv.append(None)
            cf.append(True)
    return cf


def _rock_fn(kind, form, v, lod):
    st = STATES[v]

    def fn(m, W, H, rng):
        hi = lod == "hi"
        m.smooth = hi or KINDS[kind]["shape"] in ("round", "soft", "karst")
        if form == "column":
            cf = column_bundle(m, 1.0, rng, kind, lod)
        elif form == "outcrop":
            cf = []
            for _ in range(2 if lod == "far" else 3 + v):
                cf += blob(m, rng.uniform(1.3, 2.3), rng, kind, st, lod, ctr=(rng.uniform(-1.8, 1.8), rng.uniform(-1.4, 1.4), rng.uniform(0, 0.8)), sink=0.3, flat=KINDS[kind]["flat"] * 0.65, sub_cap=5 if hi else 3)
        else:
            cf = blob(m, {"s": 0.35, "m": 0.9, "l": 2.2}[form[-1]], rng, kind, st, lod, sub_cap=6 if hi else 4)
        apply_state(m, kind, rng, st, cf, grass=lod != "far" and form != "boulder_s")
    return fn


def _cliff_geo(kind, v, lod):
    st = STATES[v]

    def fn(m, W, H, rng):
        nx, nz = {"near": (28, 18), "far": (10, 7), "hi": (180, 120)}[lod]
        shape = KINDS[kind]["shape"]
        m.smooth = lod == "hi"
        xs, zs = np.linspace(-W / 2, W / 2, nx + 1), np.linspace(0, H, nz + 1)
        n_ = _noise_dir(rng, 8)
        lf, la = {"slab": (2.6, 0.5), "angular": (1.4, 0.25), "round": (0.9, 0.15), "karst": (1.8, 0.3), "soft": (1.2, 0.3)}[shape]
        P = np.zeros((nz + 1, nx + 1, 3))
        for j, z in enumerate(zs):
            ledge = la * math.sin(z * lf + v) + 0.3 * la * math.sin(z * 4.3)
            for k, x in enumerate(xs):
                d = np.array([x * 0.25, z * 0.35, v * 0.7])
                d = d / (np.linalg.norm(d) + 1e-9)
                joint = 0.5 * math.sin(x * 2.2 + 0.7 * v) if shape == "angular" else 0.0           # 縦の節理
                P[j, k] = (x, 1.6 - (1.0 + 1.2 * n_(d) + ledge + joint + 0.5 * math.sin(x * 1.3 + z * 0.7)), z - 0.6)
        if lod == "hi":                                                                         # 壁面の微細起伏(法線は -y 方向)
            Q = P.reshape(-1, 3)
            nrm = np.tile([0.0, -1.0, 0.0], (len(Q), 1))
            Q = hi_detail(Q, nrm, rng, 3.0, shape, 6)
            Q = Q.copy()
            P = Q.reshape(P.shape)
        base = len(m.v)
        m.v.extend(map(tuple, P.reshape(-1, 3)))
        for j in range(nz):
            for k in range(nx):
                a = base + j * (nx + 1) + k
                m.f.append((a, a + 1, a + nx + 2, a + nx + 1))
                m.m.append(f"rk_{kind}")
                m.uv.append(None)
        apply_state(m, kind, rng, st, None, grass=False)
    return fn


for _k in KINDS:
    for _v in range(len(STATES)):
        for _lod in ("near", "far", "hi"):
            _sfx = {"near": "", "far": "_far", "hi": "_hi"}[_lod]
            for _sz in ("s", "m", "l"):
                reg(f"rock_{_k}_boulder_{_sz}_{_v}{_sfx}", _rock_fn(_k, f"boulder_{_sz}", _v, _lod), W={"s": 0.8, "m": 2.0, "l": 5.0}[_sz], H={"s": 0.5, "m": 1.2, "l": 3.0}[_sz], lod=_lod, kind=_k)
            if _k != "river":
                reg(f"rock_{_k}_outcrop_{_v}{_sfx}", _rock_fn(_k, "outcrop", _v, _lod), W=6.0, H=3.0, lod=_lod, kind=_k)
                reg(f"rock_{_k}_cliff_{_v}{_sfx}", _cliff_geo(_k, _v, _lod), W=14.0, H=9.0, lod=_lod, kind=_k)
            if _k == "andesite" and _lod != "hi":
                reg(f"rock_{_k}_column_{_v}{_sfx}", _rock_fn(_k, "column", _v, _lod), W=4.0, H=3.0, lod=_lod, kind=_k)
