"""散布ノード: scatter.trees / scatter.shrubs / scatter.rocks。結果は doc.scatter[name] = dict(pos(N,3), yaw, pitch, scale, kind(asset 添字), assets(名前配列))。"""
from __future__ import annotations

import numpy as np
from rasterio import features
from rasterio.transform import from_origin
from scipy.ndimage import distance_transform_edt, gaussian_filter

from ..biome.jp_forest import CONIFER, DECIDUOUS, DWARF_PINE, EVERGREEN, GRASS, RIPARIAN
from ..core.node import Node, node
from ..gen.noise import make_noise
from ..masks.terrain import slope_aspect
from .poisson import sample

# 種ごとの module 名(s/m/l)と代表樹高[m]。広葉樹は vt の植栽 module(veg_*)、針葉樹は terra_*(modules/lib_forest.py)
TREES = {
    "shii": dict(mods=["veg_shii_{z}_0_summer", "veg_shii_{z}_1_summer"], H=dict(s=5.0, m=9.0, l=14.0)),
    "kusunoki": dict(mods=["veg_kusunoki_{z}_0_summer"], H=dict(s=6.2, m=11.2, l=17.5)),
    "keyaki": dict(mods=["veg_keyaki_{z}_0_{se}", "veg_keyaki_{z}_1_summer"], H=dict(s=5.5, m=9.9, l=15.4), se="autumn_y"),
    "tokaikaede": dict(mods=["veg_tokaikaede_{z}_0_{se}"], H=dict(s=3.5, m=6.3, l=9.8), se="autumn_r"),
    "sakura": dict(mods=["veg_sakura_{z}_0_summer"], H=dict(s=4.2, m=7.6, l=11.9)),
    "kuromatsu": dict(mods=["veg_kuromatsu_{z}_0_summer", "veg_kuromatsu_{z}_1_summer"], H=dict(s=5.0, m=8.0, l=12.0)),
    "sugi": dict(mods=["terra_sugi_{z}"], H=dict(s=12.0, m=20.0, l=28.0)),
    "shirabiso": dict(mods=["terra_shirabiso_{z}"], H=dict(s=6.0, m=10.0, l=15.0)),
}
# バイオームごとの樹種の重み
MIX = {
    EVERGREEN: dict(shii=0.40, kusunoki=0.08, sugi=0.30, keyaki=0.10, sakura=0.04, kuromatsu=0.08),
    DECIDUOUS: dict(keyaki=0.32, tokaikaede=0.26, sakura=0.08, sugi=0.14, kuromatsu=0.06, shii=0.14),
    CONIFER: dict(shirabiso=0.78, kuromatsu=0.22),
    DWARF_PINE: dict(kuromatsu=1.0),
    RIPARIAN: dict(keyaki=0.45, tokaikaede=0.25, sakura=0.1, sugi=0.2),
    GRASS: dict(sakura=1.0),
}


def exclusion(doc, names, margin=2.0):
    """除外ラスタ(True=置けない)。river/lake/road/powerline などのベクタを幅+margin でバッファしてラスタ化。water_depth>0 も除外"""
    g = doc.grid
    tr = from_origin(g.x0, g.y0 + g.ny * g.res, g.res, g.res)
    ex = np.zeros(g.shape, bool)
    shapes = []
    for n in names:
        key = {"river": "rivers", "lake": "lakes", "road": "roads", "powerline": "powerlines"}.get(n, n)
        for geom, pr in doc.vectors.get(key, []):
            w = pr.get("width", {"roads": 10.0, "powerlines": 25.0}.get(key, 0.0))
            shapes.append((geom.buffer(w / 2 + margin), 1))
    if shapes:
        ex |= np.flipud(features.rasterize(shapes, out_shape=g.shape, transform=tr, fill=0, dtype="uint8")).astype(bool)
    if "water_depth" in doc.layers:
        ex |= doc.layers["water_depth"] > 0.05
    return ex


def _put(doc, name, xy, yaw, scale, kind, assets, pitch=None, zoff=-0.05):
    z = doc.heightfield().sample(xy[:, 0], xy[:, 1]) + zoff
    doc.scatter[name] = dict(pos=np.column_stack([xy, z]).astype(np.float32), yaw=yaw.astype(np.float32),
                             pitch=(np.zeros(len(xy)) if pitch is None else pitch).astype(np.float32), scale=scale.astype(np.float32),
                             kind=kind.astype(np.int16), assets=np.array(assets))


@node("scatter.trees")
class Trees(Node):
    """樹冠密度(canopy)とバイオームから木を散布。間隔 r_m のポアソンディスク → 密度で間引き → 種を斑状に選ぶ。exclude の領域には置かない。要 biome.jp_forest"""
    inputs = ("canopy", "biome")
    scatter_outputs = ("trees",)
    defaults = dict(r_m=4.2, exclude=["river", "lake", "road", "powerline"], season="summer", max_slope=62.0, size_mix=[0.35, 0.45, 0.2])

    def run(self, doc, rng):
        p, g = self.params, doc.grid
        slope, _ = slope_aspect(doc.height, g.res)
        allowed = ~exclusion(doc, p["exclude"]) & (slope < p["max_slope"])
        xy, jj, ii = sample(g, p["r_m"], int(rng.integers(1 << 30)), doc.layers["canopy"], allowed, rng)
        biome = doc.layers["biome"][jj, ii]
        patch = make_noise(g, rng, "fbm", 140.0, 3)[jj, ii]
        u = np.clip(0.7 * (patch - 0.5) * 2.2 + 0.5 + 0.3 * (rng.random(len(xy)) - 0.5), 0, 0.999)
        names, kind, scale = [], np.zeros(len(xy), np.int16), np.ones(len(xy))
        idx = {}
        zr = doc.height[jj, ii]
        for b, mix in MIX.items():
            sel = np.flatnonzero(biome == b)
            if not len(sel):
                continue
            sp = list(mix)
            cum = np.cumsum([mix[s] for s in sp]) / sum(mix.values())
            ch = np.minimum(np.searchsorted(cum, u[sel], side="right"), len(sp) - 1)
            for s_i, sn in enumerate(sp):
                ss = sel[ch == s_i]
                if not len(ss):
                    continue
                spec = TREES[sn]
                szi = rng.choice(3, len(ss), p=np.array(p["size_mix"]) / sum(p["size_mix"]))
                var = rng.integers(len(spec["mods"]), size=len(ss))
                for z_i, z in enumerate("sml"):
                    for v_i, mod in enumerate(spec["mods"]):
                        m = (szi == z_i) & (var == v_i)
                        if not m.any():
                            continue
                        se = spec.get("se", "summer") if p["season"] == "autumn" else "summer"
                        nm = mod.format(z=z, se=se)
                        if nm not in idx:
                            idx[nm] = len(names)
                            names.append(nm)
                        kind[ss[m]] = idx[nm]
                        scale[ss[m]] = rng.uniform(0.85, 1.2, m.sum())
        dwarf = biome == DWARF_PINE
        scale[dwarf] *= rng.uniform(0.25, 0.5, dwarf.sum())
        stunt = np.clip((doc.meta.get("climate", {}).get("treeline", 2400.0) - zr) / 400.0, 0.5, 1.0)
        scale *= np.where(biome == CONIFER, stunt, 1.0)
        _put(doc, "trees", xy, rng.uniform(0, 2 * np.pi, len(xy)), scale, kind, names)


@node("scatter.shrubs")
class Shrubs(Node):
    """林床の低木(ツツジ・ツゲ)・湿地のアジサイ・開けた所の草を散布。要 biome.jp_forest"""
    inputs = ("canopy", "biome")
    scatter_outputs = ("shrubs",)
    defaults = dict(r_m=2.6, exclude=["river", "lake", "road", "powerline"], shrub_density=0.5, grass_density=0.6)

    def run(self, doc, rng):
        p, g = self.params, doc.grid
        slope, _ = slope_aspect(doc.height, g.res)
        biome, can = doc.layers["biome"], doc.layers["canopy"]
        forest = can > 0.15
        dens = np.where(forest, p["shrub_density"] * np.clip(can, 0, 1), 0.0)
        dens = np.where(np.isin(biome, (GRASS, RIPARIAN)), np.maximum(dens, p["grass_density"]), dens)
        dens = np.where((~forest) & (biome != 0) & (slope < 38), p["grass_density"] * 0.5, dens)
        dens = np.where(slope > 45, 0, dens)
        allowed = ~exclusion(doc, p["exclude"], 1.0)
        xy, jj, ii = sample(g, p["r_m"], int(rng.integers(1 << 30)), dens.astype(np.float32), allowed, rng)
        b, f = biome[jj, ii], forest[jj, ii]
        names = ["veg_azalea_0_r8", "veg_azalea_1_r8", "veg_azalea_green_r8", "veg_tsuge_dome_r8", "veg_hydrangea_0_r75", "veg_grass_tuft_0", "veg_grass_tuft_1", "veg_grass_plume_0"]
        kind = np.where(f, rng.integers(0, 4, len(xy)), rng.integers(5, 8, len(xy)))
        kind = np.where(b == RIPARIAN, np.where(rng.random(len(xy)) < 0.5, 4, kind), kind)
        scale = np.where(f, rng.uniform(0.7, 1.5, len(xy)), rng.uniform(0.8, 1.6, len(xy)))
        _put(doc, "shrubs", xy, rng.uniform(0, 2 * np.pi, len(xy)), scale, kind, names, zoff=-0.03)


@node("scatter.rocks")
class Rocks(Node):
    """崖(急斜面に崖パネル)・崖下の転石(扇状)・露頭・巨礫・川沿いの丸い礫を散布。where: 崖とみなす傾斜[度]"""
    inputs = ("slope", "aspect")
    scatter_outputs = ("rocks",)
    defaults = dict(cliff_deg=54.0, boulder_density=0.04, exclude=["river", "lake"])

    def run(self, doc, rng):
        p, g = self.params, doc.grid
        slope, aspect = doc.layers["slope"], doc.layers["aspect"]
        ex = exclusion(doc, p["exclude"], 0.5)
        names = [f"rock_cliff_{i}" for i in range(3)] + [f"rock_outcrop_{i}" for i in range(3)] + [f"rock_boulder_{z}_{i}" for z in "sml" for i in range(4)] \
            + [f"rock_scree_{i}" for i in range(3)] + [f"rock_pebble_{i}" for i in range(3)]
        ix = {n: i for i, n in enumerate(names)}
        parts = []   # (xy, kind, scale, pitch, yaw)
        # 1) 崖パネル: 急斜面に疎ら(間隔 ~12m)。面は下り方向、斜面に沿って傾ける
        cl = (slope >= p["cliff_deg"]) & ~ex
        xy, jj, ii = sample(g, 12.0, int(rng.integers(1 << 30)), cl.astype(np.float32) * 0.25, None, rng)
        a = np.radians(aspect[jj, ii])
        al = np.radians(slope[jj, ii])
        parts.append((xy, np.array([ix[f"rock_cliff_{k}"] for k in rng.integers(0, 3, len(xy))], np.int16) if len(xy) else np.zeros(0, np.int16), rng.uniform(0.8, 1.5, len(xy)),
                      al - np.pi / 2, np.pi - a))
        # 2) 崖下の転石: 崖マスクをぼかして下流側へ広げた密度(傾斜 22〜42度)
        fan = gaussian_filter(cl.astype(np.float32), 14.0 / g.res * 2) * 3.0
        d2 = np.clip(fan, 0, 1) * 0.5 * np.clip((slope - 18) / 6, 0, 1) * np.clip((44 - slope) / 6, 0, 1) * (~ex)
        xy, jj, ii = sample(g, 3.0, int(rng.integers(1 << 30)), d2.astype(np.float32), None, rng)
        zi = rng.choice(3, len(xy), p=[0.75, 0.2, 0.05])
        k = np.array([ix[f"rock_boulder_{'sml'[z]}_{rng.integers(4)}"] for z in zi], np.int16) if len(xy) else np.zeros(0, np.int16)
        parts.append((xy, k, rng.uniform(0.4, 1.8, len(xy)), np.zeros(len(xy)), rng.uniform(0, 6.28, len(xy))))
        # 3) 一般の巨礫・露頭(土が薄い所ほど多い)
        sd = doc.layers.get("soil_depth", np.full(g.shape, 1.0, np.float32))
        d3 = p["boulder_density"] * np.clip(1.2 - sd, 0.1, 1.2) * np.clip(slope / 30, 0.3, 1) * (~ex) * (slope < p["cliff_deg"])
        xy, jj, ii = sample(g, 5.0, int(rng.integers(1 << 30)), d3.astype(np.float32), None, rng)
        isout = rng.random(len(xy)) < 0.12
        k = np.where(isout, rng.integers(0, 3, len(xy)) + 3, [ix[f"rock_boulder_{'sml'[z]}_{rng.integers(4)}"] for z in rng.choice(3, len(xy), p=[0.55, 0.35, 0.1])])
        parts.append((xy, k.astype(np.int16), np.where(isout, rng.uniform(0.7, 1.5, len(xy)), rng.uniform(0.6, 1.5, len(xy))), np.zeros(len(xy)), rng.uniform(0, 6.28, len(xy))))
        # 4) 川沿いの礫・小石(川から 12m 以内)
        riv = doc.layers.get("river", np.zeros(g.shape, np.float32)) > 0
        if riv.any():
            dist = distance_transform_edt(~riv) * g.res
            d4 = np.clip(1 - dist / 12.0, 0, 1) * 0.9 * (~ex)
            xy, jj, ii = sample(g, 2.2, int(rng.integers(1 << 30)), d4.astype(np.float32), None, rng)
            k = np.where(rng.random(len(xy)) < 0.5, rng.integers(0, 3, len(xy)) + ix["rock_pebble_0"], rng.integers(0, 3, len(xy)) + ix["rock_scree_0"])
            parts.append((xy, k.astype(np.int16), rng.uniform(0.7, 1.4, len(xy)), np.zeros(len(xy)), rng.uniform(0, 6.28, len(xy))))
        xy = np.concatenate([q[0] for q in parts])
        xy = xy + rng.uniform(-1.3, 1.3, xy.shape)            # 高密度域のポアソンディスクが六方格子状に見えないよう位置を崩す
        _put(doc, "rocks", xy, np.concatenate([q[4] for q in parts]), np.concatenate([q[2] for q in parts]), np.concatenate([q[1] for q in parts]), names,
             pitch=np.concatenate([q[3] for q in parts]), zoff=-0.1)
