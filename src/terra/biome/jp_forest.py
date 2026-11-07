"""日本の植生帯(標高・緯度・傾斜・向き・TWI): 照葉樹林 → 落葉広葉樹林 → 亜高山針葉樹林 → ハイマツ → 高山荒原。
境界高度は本州中部(北緯36度、海面平均気温15度)の目安値で、気候(気温差・緯度)で上下にずらす。目安値は設計上の既定で、植生学の原典で確認したものではない。"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from ..core.node import Node, node
from ..gen.noise import make_noise

ROCK, EVERGREEN, DECIDUOUS, CONIFER, DWARF_PINE, ALPINE, SNOW, GRASS, RIPARIAN = range(9)
NAMES = ["rock", "evergreen_broadleaf", "deciduous_broadleaf", "subalpine_conifer", "dwarf_pine", "alpine_barren", "snow", "grassland", "riparian"]
SPLAT = ["grass", "litter", "rock", "scree", "soil", "alpine"]


def zone_limits(climate, base=(700.0, 1600.0, 2400.0, 2900.0)):
    """気候による境界高度[m]。海面気温が 1度高いと約 180m 上がり(気温減率 5.5度/km)、緯度が 1度低いと約 150m 上がる"""
    c = climate or {}
    dz = (c.get("sea_level_temp_c", 15.0) - 15.0) / 0.0055 + (36.0 - c.get("lat", 36.0)) * 150.0
    return np.array(base) + dz


def classify(z, slope, aspect, twi, climate, rng, grid, rock_slope=58.0):
    lim = zone_limits(climate)
    g = z.shape
    # 境界のゆらぎ(±80m)と日当たり(南向き斜面は +80m)
    jitter = (make_noise(grid, rng, "fbm", 120.0, 3) - 0.5) * 160.0
    sun = np.cos(np.radians(aspect - 180.0)) * np.clip(slope / 25.0, 0, 1) * 80.0
    zz = z - jitter - sun
    cls = np.full(g, ALPINE, np.uint8)
    cls[zz < lim[3]] = DWARF_PINE
    cls[zz < lim[2]] = CONIFER
    cls[zz < lim[1]] = DECIDUOUS
    cls[zz < lim[0]] = EVERGREEN
    wet = (twi > 11.5) & (slope < 14) & (z < lim[1])
    cls[wet] = RIPARIAN
    cls[(slope < 6) & (twi > 9.5) & (z < lim[0] * 0.6) & ~wet] = GRASS      # 低地の平坦で湿った所は草地(農地跡・河原)
    cls[slope >= rock_slope] = ROCK
    return cls, lim


def soil_depth(slope, twi):
    s = 2.5 * np.clip(1 - slope / 50.0, 0, 1) ** 1.5 + 0.8 * np.clip((twi - 8) / 4, 0, 1)
    return np.clip(s, 0.0, 3.0).astype(np.float32)


def canopy(cls, slope, z, lim, rng, grid):
    d = np.clip(1.0 - np.clip(slope - 36, 0, 24) / 24.0 * 0.8, 0.0, 1.0)             # 36度までは密、60度で 20%
    d = np.where(slope >= 62, 0, d)
    near = np.clip((lim[2] + 200 - z) / 300.0, 0.35, 1.0)                               # 森林限界付近は疎ら
    forest = np.isin(cls, (EVERGREEN, DECIDUOUS, CONIFER, RIPARIAN))
    d = np.where(forest, d * np.where(cls == CONIFER, near, 1.0), 0.0)
    d = np.where(cls == DWARF_PINE, 0.55 * np.clip(1 - np.clip(slope - 30, 0, 20) / 25.0, 0, 1), d)
    patch = make_noise(grid, rng, "fbm", 90.0, 3)
    return (d * (0.75 + 0.35 * patch)).clip(0, 1).astype(np.float32)


def splat_weights(cls, slope, canopy_, z, lim):
    f = lambda a: gaussian_filter(a.astype(np.float32), 1.0)
    forest = canopy_ > 0.15
    rock = np.clip((slope - 46) / 14, 0, 1) + (cls == ROCK)
    scree = np.clip((slope - 30) / 8, 0, 1) * np.clip((56 - slope) / 8, 0, 1) * (~forest | (canopy_ < 0.5))
    alpine = np.clip((z - lim[2] + 150) / 250, 0, 1) * (cls >= DWARF_PINE) * (cls != ROCK)
    litter = forest * np.clip(canopy_ * 1.3, 0, 1) * np.clip((40 - slope) / 14, 0, 1)
    grass = np.isin(cls, (GRASS, RIPARIAN)) * 1.0 + 0.35 * (~forest) * np.clip((34 - slope) / 12, 0, 1) * (cls < DWARF_PINE)
    soil = 0.25 + 0.5 * (~forest) * np.clip((30 - slope) / 20, 0, 1)
    w = np.stack([f(grass), f(litter), f(rock), f(scree), f(soil), f(alpine)], 0) + 1e-4
    return w / w.sum(0, keepdims=True)


@node("biome.jp_forest")
class JpForest(Node):
    """要 masks.slope と hydro.flow(twi)。biome(クラス ID)・canopy(樹冠密度 0..1)・soil_depth[m]・splat_*(6 層の重み)を作る"""
    inputs = ("height", "slope", "aspect", "twi")
    outputs = ("biome", "canopy", "soil_depth", "bedrock") + tuple("splat_" + n for n in SPLAT)
    defaults = dict(rock_slope=58.0)

    def run(self, doc, rng):
        z, s, a, t = (doc.layers[k] for k in ("height", "slope", "aspect", "twi"))
        cls, lim = classify(z, s, a, t, doc.meta.get("climate"), rng, doc.grid, self.params["rock_slope"])
        sd = soil_depth(s, t)
        can = canopy(cls, s, z, lim, rng, doc.grid)
        doc.set("biome", cls)
        doc.set("canopy", can)
        doc.set("soil_depth", sd)
        doc.set("bedrock", z - sd)
        w = splat_weights(cls, s, can, z, lim)
        for n, wi in zip(SPLAT, w):
            doc.set("splat_" + n, wi)
