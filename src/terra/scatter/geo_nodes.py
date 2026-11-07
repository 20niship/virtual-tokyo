"""地質を使う散布: scatter.rocks(岩種・状態を geology/moss/lichen/TWI から選ぶ)と scatter.ground(土パッチ・砂利パッチ)。"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

from ..core.node import Node, node
from ..geology.tables import ROCKS, SOILS
from .nodes import _put, exclusion
from .poisson import sample


class Assets:
    """asset 名 → 添字(散布 1 グループ内で共有)"""

    def __init__(self):
        self.names, self.idx = [], {}

    def __call__(self, n):
        if n not in self.idx:
            self.idx[n] = len(self.names)
            self.names.append(n)
        return self.idx[n]


def _kind(doc, jj, ii, rng, main=0.8):
    geo = doc.layers.get("geology")
    g = geo[jj, ii] if geo is not None else np.zeros(len(jj), int)
    other = rng.integers(0, len(ROCKS), len(jj))
    return np.where(rng.random(len(jj)) < main, g, other)


def _state(doc, jj, ii, rng, steep=None):
    """状態 v: 0 新鮮・欠け / 1 風化・地衣類 / 2 苔むし・草 / 3 水染み・汚れ"""
    z = np.zeros(doc.grid.shape, np.float32)
    moss = doc.layers.get("moss", z)[jj, ii]
    lichen = doc.layers.get("lichen", z)[jj, ii]
    twi = doc.layers.get("twi", z + 6)[jj, ii]
    v = np.ones(len(jj), int)
    v[(rng.random(len(jj)) < moss * 1.1)] = 2
    v[(twi > 9) & (rng.random(len(jj)) < 0.5) & (v == 1)] = 3
    v[(lichen < 0.1) & (v == 1) & (rng.random(len(jj)) < 0.3)] = 0
    if steep is not None:
        v[steep & (rng.random(len(jj)) < 0.5)] = 0
    return v


@node("scatter.rocks")
class Rocks(Node):
    """崖パネル(急斜面)・崖下の転石(扇状)・露頭・巨礫・ガレ(単体礫)・川沿いの丸石を、地質(岩種)と苔・地衣類の付きやすさに応じた module で散布。
    density は全体の倍率(near プロファイルは 3〜4)"""
    inputs = ("slope", "aspect")
    scatter_outputs = ("rocks",)
    defaults = dict(cliff_deg=54.0, boulder_density=0.04, exclude=["river", "lake"], density=1.0)

    def run(self, doc, rng):
        p, g = self.params, doc.grid
        D = p["density"]
        slope, aspect = doc.layers["slope"], doc.layers["aspect"]
        ex = exclusion(doc, p["exclude"], 0.5)
        A = Assets()
        xs, ks, scs, pits, yaws = [], [], [], [], []

        def add(xy, names, sc, pitch, yaw):
            xs.append(xy)
            ks.append(np.array([A(n) for n in names], np.int16))
            scs.append(sc)
            pits.append(pitch)
            yaws.append(yaw)
        # 1) 崖パネル
        cl = (slope >= p["cliff_deg"]) & ~ex
        xy, jj, ii = sample(g, 12.0 / np.sqrt(D), int(rng.integers(1 << 30)), cl.astype(np.float32) * 0.25, None, rng)
        kd, st = _kind(doc, jj, ii, rng, 0.9), _state(doc, jj, ii, rng, np.ones(len(jj), bool))
        col = rng.random(len(kd)) < 0.3
        names = [f"rock_{ROCKS[k]}_{'column' if (ROCKS[k] == 'andesite' and c) else 'cliff'}_{v}" for k, v, c in zip(kd, st, col)]
        add(xy, names, rng.uniform(0.8, 1.5, len(xy)), np.radians(slope[jj, ii]) - np.pi / 2, np.pi - np.radians(aspect[jj, ii]))
        # 2) 崖下の転石(扇状)
        fan = gaussian_filter(cl.astype(np.float32), 14.0 / g.res * 2) * 3.0
        d2 = np.clip(fan, 0, 1) * 0.5 * np.clip((slope - 18) / 6, 0, 1) * np.clip((44 - slope) / 6, 0, 1) * (~ex)
        xy, jj, ii = sample(g, 3.0 / np.sqrt(D), int(rng.integers(1 << 30)), d2.astype(np.float32), None, rng)
        kd, st = _kind(doc, jj, ii, rng), _state(doc, jj, ii, rng)
        sz = rng.choice(3, len(xy), p=[0.75, 0.2, 0.05])
        add(xy, [f"rock_{ROCKS[k]}_boulder_{'sml'[z]}_{v}" for k, z, v in zip(kd, sz, st)], rng.uniform(0.4, 1.8, len(xy)), np.zeros(len(xy)), rng.uniform(0, 6.28, len(xy)))
        # 3) 一般の巨礫・露頭(土が薄い所ほど多い)
        sd = doc.layers.get("soil_depth", np.full(g.shape, 1.0, np.float32))
        d3 = p["boulder_density"] * np.clip(1.2 - sd, 0.1, 1.2) * np.clip(slope / 30, 0.3, 1) * (~ex) * (slope < p["cliff_deg"])
        xy, jj, ii = sample(g, 5.0 / np.sqrt(D), int(rng.integers(1 << 30)), d3.astype(np.float32), None, rng)
        kd, st = _kind(doc, jj, ii, rng), _state(doc, jj, ii, rng)
        out = rng.random(len(xy)) < 0.12
        sz = rng.choice(3, len(xy), p=[0.55, 0.35, 0.1])
        add(xy, [f"rock_{ROCKS[k]}_{'outcrop' if o else 'boulder_' + 'sml'[z]}_{v}" for k, o, z, v in zip(kd, out, sz, st)], rng.uniform(0.6, 1.5, len(xy)), np.zeros(len(xy)), rng.uniform(0, 6.28, len(xy)))
        # 4) ガレ・礫(単体礫): 崖下と土の薄い所に角礫、川沿いに丸石
        d4 = np.clip(fan, 0, 1) * 0.3 * (slope < 45) * (~ex)
        xy, jj, ii = sample(g, 1.8 / np.sqrt(D), int(rng.integers(1 << 30)), d4.astype(np.float32), None, rng)
        sh, zz, vv = rng.choice(["angular", "flat"], len(xy), p=[0.6, 0.4]), rng.choice(["medium", "cobble"], len(xy), p=[0.7, 0.3]), rng.integers(4, size=len(xy))
        add(xy, [f"gravel_stone_{a}_{b}_{c}" for a, b, c in zip(sh, zz, vv)], rng.uniform(0.7, 1.6, len(xy)), np.zeros(len(xy)), rng.uniform(0, 6.28, len(xy)))
        riv = doc.layers.get("river", np.zeros(g.shape, np.float32)) > 0
        if riv.any():
            dist = distance_transform_edt(~riv) * g.res
            d5 = np.clip(1 - dist / 12.0, 0, 1) * 0.9 * (~ex)
            xy, jj, ii = sample(g, 1.6 / np.sqrt(D), int(rng.integers(1 << 30)), d5.astype(np.float32), None, rng)
            r = rng.random(len(xy))
            vv, cc = rng.integers(4, size=len(r)), rng.integers(2, size=len(r))
            names = [f"rock_river_boulder_{'sm'[int(q > 0.55)]}_{v}" if q < 0.7 else f"gravel_stone_round_{['medium', 'cobble'][c]}_{v}" for q, v, c in zip(r, vv, cc)]
            add(xy, names, rng.uniform(0.7, 1.5, len(xy)), np.zeros(len(xy)), rng.uniform(0, 6.28, len(xy)))
        xy = np.concatenate(xs)
        xy = xy + rng.uniform(-1.3, 1.3, xy.shape)            # 高密度域のポアソンディスクが六方格子状に見えないよう位置を崩す
        _put(doc, "rocks", xy, np.concatenate(yaws), np.concatenate(scs), np.concatenate(ks), A.names, pitch=np.concatenate(pits), zoff=-0.1)


@node("scatter.ground")
class Ground(Node):
    """地面の質感 module を散布: 土パッチ(土種は soil_type)・河原の砂利/砂パッチ・ガレ場の礫パッチ。パッチは斜面に沿って傾ける。要 geology.zones"""
    inputs = ("soil_type", "slope", "aspect")
    scatter_outputs = ("ground",)
    defaults = dict(soil_r_m=4.5, soil_prob=0.3, exclude=["river", "lake"], density=1.0)

    def run(self, doc, rng):
        p, g = self.params, doc.grid
        D = p["density"]
        from ..masks.terrain import slope_aspect
        hs = gaussian_filter(doc.height.astype(np.float64), 1.5 / g.res)         # パッチ(2〜4m)の傾きは 1.5m 平滑化した面から(微細な凹凸に引きずられない)
        slope, aspect = slope_aspect(hs, g.res)
        ex = exclusion(doc, p["exclude"], 0.3)
        can = doc.layers.get("canopy", np.zeros(g.shape, np.float32))
        A = Assets()
        xs, ks, scs, pits, yaws = [], [], [], [], []

        def add(xy, jj, ii, names, sc):
            a = np.radians(aspect[jj, ii])
            xs.append(xy)
            ks.append(np.array([A(n) for n in names], np.int16))
            scs.append(sc)
            pits.append(np.radians(np.minimum(slope[jj, ii], 40)))
            yaws.append(np.pi - a)
        d = p["soil_prob"] * (1 - 0.6 * can) * (slope < 42) * (~ex)
        xy, jj, ii = sample(g, p["soil_r_m"] / np.sqrt(D), int(rng.integers(1 << 30)), d.astype(np.float32), None, rng)
        st = doc.layers["soil_type"][jj, ii]
        add(xy, jj, ii, [f"soil_{SOILS[s]}_patch_{v}" for s, v in zip(st, rng.integers(3, size=len(st)))], rng.uniform(1.0, 1.6, len(xy)))
        riv = doc.layers.get("river", np.zeros(g.shape, np.float32)) > 0
        if riv.any():
            dist = distance_transform_edt(~riv) * g.res
            d2 = np.clip(1 - dist / 9.0, 0, 1) * 0.9 * (~ex)
            xy, jj, ii = sample(g, 2.6 / np.sqrt(D), int(rng.integers(1 << 30)), d2.astype(np.float32), None, rng)
            kinds = rng.choice(["river", "cobble", "medium", "sand"], len(xy), p=[0.45, 0.2, 0.2, 0.15])
            add(xy, jj, ii, [f"gravel_patch_{k}_{v}" for k, v in zip(kinds, rng.integers(3, size=len(kinds)))], rng.uniform(1.0, 1.5, len(xy)))
        cl = (slope >= 54) & ~ex
        fan = gaussian_filter(cl.astype(np.float32), 14.0 / g.res * 2) * 3.0
        d3 = np.clip(fan, 0, 1) * 0.7 * np.clip((slope - 20) / 6, 0, 1) * np.clip((42 - slope) / 6, 0, 1) * (~ex)
        xy, jj, ii = sample(g, 5.0 / np.sqrt(D), int(rng.integers(1 << 30)), d3.astype(np.float32), None, rng)
        add(xy, jj, ii, [f"gravel_patch_talus_{v}" for v in rng.integers(3, size=len(xy))], rng.uniform(0.9, 1.4, len(xy)))
        xy = np.concatenate(xs)
        _put(doc, "ground", xy, np.concatenate(yaws), np.concatenate(scs), np.concatenate(ks), A.names, pitch=np.concatenate(pits), zoff=0.02)
