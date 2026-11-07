"""地質マスク(geology)・土種(soil_type)・苔/地衣類の付きやすさ(moss, lichen)。傾斜・標高・TWI・向き・土壌深から決める。
ゾーン分けは大域の低周波ノイズ(領域ワープ付き)で、既定の割合は目安(日本の山地の代表的な組み合わせ。地質図の実データではない)。"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from ..core.node import Node, node
from ..gen.noise import make_noise


def rock_zones(grid, rng, mix, wavelength=900.0):
    n = make_noise(grid, rng, "fbm", wavelength, 4, warp=0.5)
    cum = np.cumsum(np.array(mix, float) / sum(mix))
    q = np.quantile(n, cum[:-1])
    return np.searchsorted(q, n).astype(np.uint8)


def soil_types(geo, z, slope, twi, soil_depth, canopy):
    g = geo
    s = np.zeros(g.shape, np.uint8)
    s[g == 0] = 5                                    # 花崗岩 → マサ土
    s[g == 1] = 0                                    # 安山岩 → 黒ボク(火山灰土)
    s[(g == 1) & (z > 1250)] = 4                     # 標高が高い安山岩域は火山灰・スコリア
    s[g == 2] = 3                                    # 砂岩 → 砂質土
    s[(g == 2) & (twi > 8.0)] = 2                    # 砂岩・泥岩の湿った所は粘土
    s[g == 3] = 1                                    # 石灰岩 → 赤黄色土(テラロッサ)
    s[g == 4] = 2                                    # 凝灰岩 → 粘土
    s[(g == 4) & (slope < 22)] = 0                   # 凝灰岩の緩斜面は火山灰が載る
    s[(twi > 10.5) & (slope < 12)] = 7               # 谷底の平坦で湿った所はぬかるみ
    hum = (canopy > 0.65) & (slope < 30) & (soil_depth > 1.0) & (s != 7) & (s != 4)
    s[hum] = 6                                       # 森林の緩斜面は腐植・落葉層
    return s


def moss_lichen(slope, aspect, twi, canopy):
    north = 0.5 + 0.5 * np.cos(np.radians(aspect))        # 下り方向が北 = 北向き斜面(日陰・湿潤)
    wet = np.clip((twi - 6.0) / 5.0, 0, 1)
    moss = np.clip(0.2 + 0.5 * north + 0.5 * wet + 0.2 * canopy - 0.7, 0, 1) * 1.6
    lichen = np.clip((1 - north) * 0.8 + 0.2 * (1 - wet) - 0.2, 0, 1) * np.clip((slope - 20) / 20, 0, 1)
    return gaussian_filter(np.clip(moss, 0, 1).astype(np.float32), 1.0), gaussian_filter(lichen.astype(np.float32), 1.0)


@node("geology.zones")
class Zones(Node):
    """geology(岩種 ID)・soil_type(土種 ID)・moss/lichen(付着の強さ 0..1)を作る。要 masks.slope・hydro.flow・biome.jp_forest。mix は岩種の割合 [花崗岩, 安山岩, 砂岩, 石灰岩, 凝灰岩]"""
    inputs = ("height", "slope", "aspect", "twi", "canopy", "soil_depth")
    outputs = ("geology", "soil_type", "moss", "lichen")
    defaults = dict(mix=[0.25, 0.25, 0.30, 0.08, 0.12], wavelength_m=900.0)

    def run(self, doc, rng):
        L = doc.layers
        geo = rock_zones(doc.grid, rng, self.params["mix"], self.params["wavelength_m"])
        doc.set("geology", geo)
        doc.set("soil_type", soil_types(geo, L["height"], L["slope"], L["twi"], L["soil_depth"], L["canopy"]))
        m, li = moss_lichen(L["slope"], L["aspect"], L["twi"], L["canopy"])
        doc.set("moss", m)
        doc.set("lichen", li)
