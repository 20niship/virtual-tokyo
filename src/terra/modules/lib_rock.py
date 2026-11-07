"""岩・崖・転石・礫(手続き生成、PBR 材質 rock_*)。原点=接地点(岩は下部を地面へ少し埋める前提で底が z=0 より下に入る)、z 上。
boulder_{s,m,l}_{0..3}: 角張った巨礫 / outcrop_{0..2}: 板状の露頭 / scree_{0..2}: 小石の塊 / pebble_{0..2}: 丸い川礫 / cliff_{0..2}: 幅 14m の崖面パネル(面は -y 向き)"""
import math

import numpy as np

from .registry import reg


def _ico(sub=2):
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6),
         (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    v = [np.array(p, float) / np.linalg.norm(p) for p in v]
    for _ in range(sub):
        cache, nf = {}, []

        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                m = v[a] + v[b]
                v.append(m / np.linalg.norm(m))
                cache[k] = len(v) - 1
            return cache[k]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    return np.array(v), f


_ICO = {}


def _noise_dir(rng, n=6):
    """球面上の滑らかな乱数場(方向ベクトル → 値): 方向ごとの正弦波の和"""
    ks = [np.array([rng.gauss(0, 1) for _ in range(3)]) * (1.4 + i * 0.7) for i in range(n)]
    ph = [rng.uniform(0, 6.28) for _ in range(n)]
    amp = [1 / (1 + i * 0.9) for i in range(n)]
    return lambda d: sum(a * np.sin(d @ k + p) for a, k, p in zip(amp, ks, ph)) / sum(amp)


def rock_mesh(m, R, rng, flat=0.75, cuts=7, rough=0.22, mat="rock_granite", ctr=(0, 0, 0), sink=0.25, sub=2):
    """角張った岩: 球を乱数場で歪め、ランダムな平面で切り落として面を作る。底を sink*R だけ地面に埋める"""
    if sub not in _ICO:
        _ICO[sub] = _ico(sub)
    V, F = _ICO[sub]
    d = V.copy()
    nz = _noise_dir(rng)
    P = d * (R * (1 + rough * nz(d)))[:, None]
    P[:, 2] *= flat
    P[:, 0] *= rng.uniform(0.85, 1.25)
    for _ in range(cuts):
        n = np.array([rng.gauss(0, 1) for _ in range(3)])
        n /= np.linalg.norm(n)
        off = R * rng.uniform(0.55, 0.85)
        P -= np.maximum(0, P @ n - off)[:, None] * n
    P[:, 2] -= sink * R * flat
    P += np.array(ctr)
    base = len(m.v)
    m.v.extend(map(tuple, P))
    for a, b, c in F:
        m.f.append((base + a, base + b, base + c))
        m.m.append(mat)
        m.uv.append(None)


def _boulder(R, seed_off):
    def fn(m, W, H, rng):
        rock_mesh(m, R, rng, flat=0.7 + 0.1 * (seed_off % 3), cuts=6 + seed_off % 3, rough=0.2 + 0.03 * (seed_off % 4), mat=("rock_granite", "rock_dark", "rock_warm", "rock_granite")[seed_off % 4])
    return fn


for _sz, _R in (("s", 0.35), ("m", 0.9), ("l", 2.2)):
    for _i in range(4):
        reg(f"rock_boulder_{_sz}_{_i}", _boulder(_R, _i), W=_R * 2.4, H=_R * 1.4)


def _outcrop(i):
    def fn(m, W, H, rng):
        for k in range(3 + i):                       # 重なった板状の岩
            rock_mesh(m, rng.uniform(1.4, 2.4), rng, flat=0.45, cuts=8, rough=0.18, mat="rock_dark" if k % 2 else "rock_granite",
                      ctr=(rng.uniform(-1.8, 1.8), rng.uniform(-1.4, 1.4), rng.uniform(0, 0.8)), sink=0.3)
    return fn


for _i in range(3):
    reg(f"rock_outcrop_{_i}", _outcrop(_i), W=6.0, H=3.0)


def _scree(i):
    def fn(m, W, H, rng):
        for _ in range(16):
            rock_mesh(m, rng.uniform(0.08, 0.3), rng, flat=0.6, cuts=5, rough=0.25, mat="rock_warm" if rng.random() < 0.5 else "rock_granite",
                      ctr=(rng.uniform(-1.2, 1.2), rng.uniform(-1.2, 1.2), 0), sink=0.3, sub=1)
    return fn


def _pebble(i):
    def fn(m, W, H, rng):
        for _ in range(10):
            rock_mesh(m, rng.uniform(0.1, 0.28), rng, flat=0.55, cuts=0, rough=0.08, mat="rock_pebble", ctr=(rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9), 0), sink=0.3, sub=1)
    return fn


for _i in range(3):
    reg(f"rock_scree_{_i}", _scree(_i), W=3.0, H=0.4)
    reg(f"rock_pebble_{_i}", _pebble(_i), W=2.0, H=0.25)


def _cliff(i):
    """幅 14m・高さ 9m・奥行き最大 ~3m の崖面。層理の段(水平な棚)と縦の割れ目で凹凸を付けた格子面。底中央が原点、面の外向きは -y"""
    def fn(m, W, H, rng):
        nx, nz = 28, 18
        xs, zs = np.linspace(-W / 2, W / 2, nx + 1), np.linspace(0, H, nz + 1)
        nz_ = _noise_dir(rng, 8)
        P = np.zeros((nz + 1, nx + 1, 3))
        for j, z in enumerate(zs):
            ledge = 0.35 * math.sin(z * 1.9 + i) + 0.2 * math.sin(z * 4.3)              # 棚(層理)
            for k, x in enumerate(xs):
                d = np.array([x * 0.25, z * 0.35, i * 0.7])
                d = d / (np.linalg.norm(d) + 1e-9)
                y = 1.6 - (1.0 + 1.2 * nz_(d) + ledge + 0.5 * math.sin(x * 1.3 + z * 0.7))   # 斜面に半分埋め込み、出っ張りだけが見える
                P[j, k] = (x, y, z - 0.6)
        base = len(m.v)
        m.v.extend(map(tuple, P.reshape(-1, 3)))
        for j in range(nz):
            for k in range(nx):
                a = base + j * (nx + 1) + k
                mat = "rock_dark" if (k // 4 + j // 3) % 3 == 0 else "rock_granite"
                m.f.append((a, a + 1, a + nx + 2, a + nx + 1))      # 外向き(-y)が表
                m.m.append(mat)
                m.uv.append(None)
    return fn


for _i in range(3):
    reg(f"rock_cliff_{_i}", _cliff(_i), W=14.0, H=9.0)
