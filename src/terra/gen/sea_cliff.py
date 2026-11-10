"""岩石海岸: 既存の高さを内陸の台地として残し、海側へ 海食崖(層理の棚・節理・波食ノッチ)→ 波食棚(平らな岩盤)→ 沖の海 を作る。
海面は doc.meta["sea_level"](render がまとめて水面を張る)。崖の面・崖下の転石帯・波食棚はマスク(coast_cliff / shore_talus / wave_platform)で後段の散布に渡す。"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from ..core.node import Node, node
from .crags import Crags, _smooth
from .noise import make_noise


@node("gen.sea_cliff")
class SeaCliff(Node):
    """sea_dir_deg: 海の方位(北=0 時計回り)、coast_offset: 格子中心から海岸線までの距離[m](海側が正)、cliff_height: 崖の高さ[m]、cliff_run_m: 崖の水平幅、
    platform_m: 波食棚の幅、strata_m: 層理の間隔、notch_m: 崖脚のノッチ(えぐれ)の深さ[m]、wobble_m: 海岸線の出入り、inland_relief: 内陸台地の起伏の倍率"""
    outputs = ("height", "coast_cliff", "shore_talus", "wave_platform", "sea", "no_veg", "water_depth")
    defaults = dict(sea_dir_deg=180.0, coast_offset=0.0, cliff_height=22.0, cliff_run_m=7.0, platform_m=26.0, strata_m=1.6, notch_m=2.0,
                    wobble_m=60.0, inland_relief=0.25, sea_level=0.0)

    def run(self, doc, rng):
        p, g = self.params, doc.grid
        X, Y = g.xy()
        a = np.radians(p["sea_dir_deg"])
        n = np.array([np.sin(a), np.cos(a)])                                   # 海へ向かう単位ベクトル(x=東, y=北)
        wob = (make_noise(g, rng, "fbm", 180.0, 3) - 0.5) * 2 * p["wobble_m"] + (make_noise(g, rng, "ridged", 40.0, 3, 2.0, 0.5, 0.3) - 0.5) * 14.0
        s = (X - X.mean()) * n[0] + (Y - Y.mean()) * n[1] - p["coast_offset"] - wob      # 崖の肩からの海側距離(<0 は内陸)
        z0 = doc.height.astype(np.float64)
        H, run, wp, sl = p["cliff_height"], p["cliff_run_m"], p["platform_m"], p["sea_level"]
        top = sl + H + p["inland_relief"] * (gaussian_filter(z0, 3.0) - float(z0.mean()))            # 内陸の台地(頂部は崖の高さ付近)
        top = top + 0.6 * (make_noise(g, rng, "fbm", 30.0, 3) - 0.5) * H * 0.2
        # 崖の面: 肩 s=0 で頂部、s=run で棚の高さ。上部はやや張り出す(丸み)
        u = np.clip(s / run, 0, 1)
        face = (1 - u ** 1.6)                                                  # 1(頂部)→0(崖脚)
        zp = sl + 0.9                                                          # 波食棚(干潮時に出る岩盤)の高さ
        zc = zp + (top - zp) * face
        # 層理: 層ごとに硬さが違い、硬い層は棚、軟らかい層は凹む。節理でブロック状に割れる
        crag = Crags(strata_m=p["strata_m"], hardness_var=1.0, dip_deg=1.5, joint_m=4.5, joint_amp=0.9)
        stair = crag._stair(zc, crag.params, rng)
        joint = crag._joints(X, Y, zc, crag.params, rng)
        cliff_face = (s > 0) & (s < run)
        mid = _smooth(face * 4) * _smooth((1 - face) * 4)                      # 面の中間だけに強く効かせる(肩・崖脚は滑らか)
        zc = zc + mid * (0.55 * stair + 0.5 * joint)
        zc = zc - p["notch_m"] * np.exp(-(((face - 0.07) / 0.06) ** 2))        # 崖脚のえぐれ(波食ノッチ: 高さ場では溝として表す。張り出しは module 側)
        # 波食棚 → 沖: ごく緩い傾斜の岩盤に潮だまりの凹凸、その先で急に深くなる
        dd = np.clip(s - run, 0, None)
        plat = zp - 0.012 * dd + 0.35 * (make_noise(g, rng, "ridged", 9.0, 3, 2.0, 0.5, 0.3) - 0.45) * np.clip(1 - dd / wp, 0, 1) + 0.5 * stair * np.clip(1 - dd / (wp * 0.5), 0, 1) * 0.5
        drop = sl - 12.0 * _smooth((dd - wp) / 40.0)
        shelf = np.minimum(plat, plat * (1 - _smooth((dd - wp) / 40.0)) + drop * _smooth((dd - wp) / 40.0))
        z = np.where(s < 0, top, np.where(s < run, zc, shelf))
        z = gaussian_filter(z, 0.5)
        doc.set("height", z)
        doc.set("coast_cliff", (cliff_face & (face > 0.12)).astype(np.float32))
        doc.set("wave_platform", ((s >= run) & (s < run + wp) & (z > sl - 0.5)).astype(np.float32))
        talus = (s > run * 0.6) & (s < run + 22.0) & (z > sl - 1.5) & (z < sl + 5)
        doc.set("shore_talus", gaussian_filter(talus.astype(np.float32), 1.0))
        doc.set("sea", (z < sl).astype(np.float32))
        doc.set("water_depth", np.clip(sl - z, 0, None))
        doc.set("no_veg", ((s > -3.0) | (z < sl + 1.2)).astype(np.float32))                 # 崖の縁 3m 手前から海側は植生なし
        doc.meta["sea_level"] = float(sl)
        doc.meta["sea_dir"] = [float(n[0]), float(n[1])]

