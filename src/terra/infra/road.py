"""道路: 経路 → 中心線(平滑化・2m 間隔)→ 縦断線形(勾配上限を満たす)→ 橋・トンネル区間の判定 → 切土盛土(earthwork)→ ベクタ出力。
既定値(車道幅 5.5m・路肩 0.5m x2・縦断勾配 10% など)は設計上の既定値で、道路構造令の原文で確認したものではない(docs/terra/infra_defaults.md)。"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter1d
from shapely.geometry import LineString, Point

from ..core.node import Node, node
from ..masks.terrain import slope_aspect
from . import bridge, earthwork, tunnel
from .route import BRIDGE, NORMAL, TUNNEL, find_route

DS = 2.0     # 中心線の間隔[m]


def chaikin(pts, it=2):
    for _ in range(it):
        if len(pts) < 3:
            break
        a, b = pts[:-1], pts[1:]
        q = np.stack([0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b], 1).reshape(-1, 2)
        pts = np.concatenate([pts[:1], q[1:-1], pts[-1:]])
    return pts


def centerline(route, ds=DS):
    """route: [(x, y, kind_in, z)]。通常の手が続く区間を Chaikin で平滑化し(橋・トンネルの弦は直線のまま)、ds 間隔に再標本化。
    路面高は探索で使った頂点の標高を弧長で線形補間する(隣り合う頂点間の勾配は探索で上限以内なので、縦断勾配が必ず守られる)。
    返り値: xy(N,2), kind(N,) = その点から次の点への区間の種類, z(N,)"""
    pts = np.array([[r[0], r[1]] for r in route], float)
    zv = np.array([r[3] for r in route], float)
    kin = [r[2] for r in route]
    xy, kd, zz = [], [], []
    i = 0
    n = len(pts)
    while i < n - 1:
        k = kin[i + 1]
        j = i + 1
        while j < n - 1 and kin[j + 1] == k and k == NORMAL:
            j += 1
        seg = pts[i:j + 1]
        d0 = np.r_[0, np.cumsum(np.hypot(*np.diff(seg, axis=0).T))]
        frac = d0 / max(d0[-1], 1e-9)
        if k == NORMAL:
            seg = chaikin(seg, 4)
        d = np.r_[0, np.cumsum(np.hypot(*np.diff(seg, axis=0).T))]
        m = max(int(round(d[-1] / ds)), 1)
        t = np.linspace(0, d[-1], m + 1)[:-1]
        xy.append(np.stack([np.interp(t, d, seg[:, 0]), np.interp(t, d, seg[:, 1])], 1))
        zz.append(np.interp(t / max(d[-1], 1e-9), frac, zv[i:j + 1]))
        kd += [k] * m
        i = j
    xy.append(pts[-1:])
    zz.append(zv[-1:])
    kd.append(kd[-1])
    return np.concatenate(xy), np.array(kd, np.int8), np.concatenate(zz)


def design_profile(zanchor, kind, xy, gmax=0.10, iters=30):
    """縦断線形: 探索の頂点高を補間した線(勾配は上限以内)を少し平滑化し(平滑化は勾配を増やさない)、念のため勾配上限で押さえる。橋・トンネル区間は固定"""
    n = len(zanchor)
    pinned = np.zeros(n, bool)
    i = 0
    while i < n:
        if kind[i] != NORMAL:
            j = i
            while j < n - 1 and kind[j] == kind[i]:
                j += 1
            pinned[i:j + 1] = True
            i = j + 1
        else:
            i += 1
    z = zanchor.astype(float).copy()
    sm = gaussian_filter1d(z, 4.0, mode="nearest")
    z = np.where(pinned, z, sm)
    g = gmax * np.hypot(*np.diff(xy, axis=0).T) * 0.999                # 実際の点間隔ごとの許容標高差(再標本化で 1.2〜2.1m と不均一)
    for _ in range(iters):
        for i in range(1, n):
            if not pinned[i]:
                z[i] = min(max(z[i], z[i - 1] - g[i - 1]), z[i - 1] + g[i - 1])
        for i in range(n - 2, -1, -1):
            if not pinned[i]:
                z[i] = min(max(z[i], z[i + 1] - g[i]), z[i + 1] + g[i])
    return z, pinned


def curvature_stats(xy, ds=DS):
    d = np.diff(xy, axis=0)
    ang = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    w = 5                                         # 10m の窓で曲率(1/半径)を測る
    return np.abs(ang[w:] - ang[:-w]) / (w * ds)


def _segments(xy, z, kind, width, clear):
    """同じ種類の連続区間ごとに (LineString, props) を作る。props の z は 2m 間隔の路面高"""
    out = []
    i, n = 0, len(xy)
    while i < n - 1:
        j = i
        while j < n - 2 and kind[j + 1] == kind[i]:
            j += 1
        k = int(kind[i])
        sl = slice(i, j + 2)
        name = {NORMAL: "road", BRIDGE: "bridge", TUNNEL: "tunnel"}[k]
        out.append((LineString(xy[sl]), dict(kind=name, width=width, clear_width=clear if k != TUNNEL else 0.0, z=[round(float(v), 2) for v in z[sl]],
                                              length=float(LineString(xy[sl]).length))))
        i = j + 1
    return out


@node("infra.road")
class RoadNode(Node):
    """connect の地名を順に結ぶ道路を引き、地形を切土・盛土し、橋・トンネル区間を判定する。地名は レシピの places: {名前: [格子比 x, y]}。
    要 hydro.rivers(橋の判定)。出力: height(切土盛土後)・road(路盤マスク)・cutfill[m]、ベクタ roads/tunnels/portals/road_stats"""
    inputs = ("height", "slope", "river", "water_depth")
    outputs = ("height", "road", "cutfill")
    vec_outputs = ("roads", "tunnels", "portals", "road_stats")
    defaults = dict(connect=["village_a", "village_b"], max_grade=0.10, allow_tunnel=True, allow_bridge=True, width=6.5, clear_width=22.0,
                    min_cover=10.0, tunnel_cost=22.0, bridge_cost=10.0, factor=4, cut_ratio=0.8, fill_ratio=1.5)

    def run(self, doc, rng):
        import time
        t0 = time.time()
        p, g = self.params, doc.grid
        places = doc.meta.get("places") or {}
        sx, sy = g.size
        pt = lambda nm: (g.x0 + places[nm][0] * sx, g.y0 + places[nm][1] * sy)
        z0 = doc.height.copy()
        river = doc.layers.get("river", np.zeros(g.shape, np.float32))
        water = doc.layers.get("water_depth", np.zeros(g.shape, np.float32))
        road_mask = np.zeros(g.shape, np.float32)
        segs, tun, por, stats = [], [], [], dict(length_m=0.0, bridges=0, bridge_m=0.0, tunnels=0, tunnel_m=0.0, max_grade=0.0, cut_m3=0.0, fill_m3=0.0, hairpins=0, min_radius_m=1e9, roads=0)
        for a, b in zip(p["connect"][:-1], p["connect"][1:]):
            z = doc.height
            slope, _ = slope_aspect(z, g.res)
            route = find_route(z, g.res, slope, water, river, pt(a), pt(b), g, p["max_grade"], p["factor"], p["allow_tunnel"], p["allow_bridge"],
                               exist=(road_mask > 0), min_cover=p["min_cover"], tunnel_cost=p["tunnel_cost"], bridge_cost=p["bridge_cost"])
            if not route:
                raise RuntimeError(f"経路が見つからない: {a} -> {b}(max_grade={p['max_grade']} を上げるか橋・トンネルを許可する)")
            xy, kind, za = centerline(route)
            zr, pinned = design_profile(za, kind, xy, p["max_grade"])
            res = earthwork.carve(doc, xy, zr, kind, p["width"], p["cut_ratio"], p["fill_ratio"], river, road_mask)
            segs += _segments(xy, zr, kind, p["width"], p["clear_width"])
            for ln, pr in _segments(xy, zr, kind, p["width"], p["clear_width"]):
                if pr["kind"] == "tunnel":
                    tun.append((ln, pr))
                    for end, sgn in ((0, 1), (-1, -1)):
                        c = ln.coords[end]
                        por.append((Point(c), dict(width=30.0, z=pr["z"][end])))
            stats["length_m"] += float(np.sum(np.hypot(*np.diff(xy, axis=0).T)))
            grade = np.abs(np.diff(zr)) / np.hypot(*np.diff(xy, axis=0).T)
            stats["max_grade"] = max(stats["max_grade"], float(grade.max()))
            k = curvature_stats(xy)
            if len(k):
                stats["min_radius_m"] = min(stats["min_radius_m"], float(1.0 / max(k.max(), 1e-6)))
                stats["hairpins"] += int(np.sum(np.convolve((1.0 / np.maximum(k, 1e-6) < 25.0).astype(int), np.ones(10, int), "valid") >= 8) > 0)
            for s_ in bridge.find_bridges(xy, zr, kind, doc):
                stats["bridges"] += 1
                stats["bridge_m"] += s_["length"]
            for s_ in tunnel.find_tunnels(xy, zr, kind, doc):
                stats["tunnels"] += 1
                stats["tunnel_m"] += s_["length"]
            stats["cut_m3"] += res["cut_m3"]
            stats["fill_m3"] += res["fill_m3"]
            stats["roads"] += 1
        stats["secs"] = round(time.time() - t0, 2)
        doc.set("road", road_mask)
        doc.set("cutfill", doc.height - z0)
        doc.vectors["roads"] = [s for s in segs if s[1]["kind"] != "tunnel"]
        doc.vectors["tunnels"] = tun
        doc.vectors["portals"] = por
        doc.vectors["road_stats"] = [(Point(0, 0), {k: (round(v, 3) if isinstance(v, float) else v) for k, v in stats.items()})]
