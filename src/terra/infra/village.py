"""集落: 道路沿いの平らな所に家屋・畑・取り付け道(lane)を置き敷地を整地する(出力は層 height/village、ベクタ village_pads/lanes/villages、散布 village)。"""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point, Polygon

from ..core.node import Node, node

HOUSES = ["house_jp_a", "house_jp_b", "house_jp_c"]
FIELDS = ["field_rows_green", "field_rows_soil"]
HOUSE_HALF = (6.0, 4.5)        # 敷地(家屋+庭)の半分 (x: 棟方向, y: 玄関方向)
FIELD_HALF = (10.0, 7.0)


def _rect(cx, cy, hx, hy, yaw):
    """yaw 回り(module の +y を前方とする)の長方形の頂点"""
    c, s = math.cos(yaw), math.sin(yaw)
    return [(cx + c * x - s * y, cy + s * x + c * y) for x, y in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]


def level_pad(doc, poly, blend=6.0, z=None):
    """多角形の内側を水平(z=内側の平均標高)にし、外側 blend[m] で地形へ滑らかにすり付ける。返り値: z"""
    from scipy.ndimage import distance_transform_edt
    from shapely import contains_xy
    g = doc.grid
    x0, y0, x1, y1 = poly.buffer(blend + 2 * g.res).bounds
    i0, i1 = max(int((x0 - g.x0) / g.res), 0), min(int((x1 - g.x0) / g.res) + 1, g.nx)
    j0, j1 = max(int((y0 - g.y0) / g.res), 0), min(int((y1 - g.y0) / g.res) + 1, g.ny)
    X, Y = g.xy()
    sl = (slice(j0, j1), slice(i0, i1))
    inside = contains_xy(poly, X[sl], Y[sl])
    h = doc.layers["height"].astype(np.float64)
    if z is None:
        z = float(h[sl][inside].mean()) if inside.any() else float(h[sl].mean())
    d = distance_transform_edt(~inside) * g.res
    w = np.clip(1.0 - d / blend, 0.0, 1.0)
    w = w * w * (3 - 2 * w)
    h[sl] = h[sl] * (1 - w) + z * w
    doc.layers["height"] = h.astype(np.float32)
    return z, inside


@node("infra.village")
class VillageNode(Node):
    """places の各地点の周りに集落を作る。要 infra.road。houses: 1 集落あたりの家屋数の上限 / fields: 畑の数の上限 / radius: 集落の半径 /
    min_gap: 家屋どうしの最小間隔 / offset: 道路中心から家屋の中心までの距離の範囲 / max_slope: 置ける最大傾斜[度] / max_pad: 整地で許す最大の切盛り[m]"""
    inputs = ("height", "slope", "river", "water_depth")
    outputs = ("height", "village")
    vec_outputs = ("village_pads", "lanes", "villages")
    scatter_outputs = ("village",)
    defaults = dict(places=None, houses=8, fields=4, radius=170.0, min_gap=19.0, offset=(11.5, 19.0), max_slope=13.0, max_pad=2.2, road_gap=9.0)

    def run(self, doc, rng):
        p, g = self.params, doc.grid
        pl = doc.meta.get("places") or {}
        names = p["places"] or list(pl)
        sx, sy = g.size
        roads = [(np.asarray(ln.coords), np.asarray(pr["z"])) for ln, pr in doc.vectors.get("roads", []) if pr["kind"] == "road"]
        allp = [np.asarray(ln.coords) for ln, _ in doc.vectors.get("roads", []) + doc.vectors.get("tunnels", [])]
        tree = cKDTree(np.concatenate(allp)) if allp else None
        slope = doc.layers["slope"]
        river = doc.layers.get("river", np.zeros(g.shape, np.float32))
        water = doc.layers.get("water_depth", np.zeros(g.shape, np.float32))
        hf = doc.heightfield
        ij = lambda x, y: (int(np.clip((y - g.y0) / g.res, 0, g.ny - 1)), int(np.clip((x - g.x0) / g.res, 0, g.nx - 1)))
        wet = lambda x, y, r: bool((river[tuple(slice(max(a - int(r / g.res), 0), a + int(r / g.res) + 1) for a in ij(x, y))] > 0).any() or
                                   (water[tuple(slice(max(a - int(r / g.res), 0), a + int(r / g.res) + 1) for a in ij(x, y))] > 0.05).any())
        pads, lanes, vill, rows = [], [], [], []
        placed = []             # (x, y, 半径)
        mask = np.zeros(g.shape, np.float32)

        def ok_site(x, y, hx, hy, yaw, gap):
            poly = Polygon(_rect(x, y, hx, hy, yaw))
            if tree is not None and tree.query(np.array(poly.centroid.coords[0]))[0] < p["road_gap"] + max(hx, hy):
                return None
            if tree is not None:
                dd, _ = tree.query(np.array(poly.exterior.coords)[:-1])
                if dd.min() < p["road_gap"] - 3.0:
                    return None
            if wet(x, y, max(hx, hy) + 4.0) or any(math.hypot(x - a, y - b) < gap + r for a, b, r in placed):
                return None
            j, i = ij(x, y)
            if slope[j, i] > p["max_slope"]:
                return None
            ss = [hf().sample(np.array([q[0]]), np.array([q[1]]))[0] for q in list(poly.exterior.coords)[:-1]]
            if max(ss) - min(ss) > 2 * p["max_pad"]:
                return None
            return poly

        for nm in names:
            if nm not in pl:
                continue
            c = np.array([g.x0 + pl[nm][0] * sx, g.y0 + pl[nm][1] * sy])
            cand = []
            for P, z in roads:
                for k in range(2, len(P) - 2, 3):
                    if np.hypot(*(P[k] - c)) < p["radius"]:
                        d = P[k + 1] - P[k - 1]
                        d = d / max(np.hypot(*d), 1e-9)
                        cand.append((P[k], d, int(k)))
            order = rng.permutation(len(cand)) if cand else []
            nh = nf = 0
            for ci in order:
                if nh >= p["houses"]:
                    break
                P0, d, _ = cand[ci]
                side = 1 if rng.random() < 0.5 else -1
                nrm = np.array([d[1], -d[0]]) * side
                off = rng.uniform(*p["offset"])
                ctr = P0 + nrm * off
                front = -nrm                                              # 玄関が向く方向(道路側)
                yaw = math.atan2(-front[0], front[1])
                kind = rng.choice(len(HOUSES) + 1, p=[0.3, 0.2, 0.3, 0.2])
                poly = ok_site(ctr[0], ctr[1], *HOUSE_HALF, yaw, p["min_gap"])
                if poly is None:
                    continue
                zc, inside = level_pad(doc, poly, blend=5.0)
                if abs(doc.heightfield().sample(np.array([ctr[0]]), np.array([ctr[1]]))[0] - zc) > p["max_pad"]:
                    continue
                name = (HOUSES + ["barn_jp"])[kind]
                rows.append((ctr[0], ctr[1], zc, yaw, name, 1.0))
                placed.append((ctr[0], ctr[1], 8.0))
                pads.append((poly, dict(width=0.0, clear_width=0.0)))
                nh += 1
                # 取り付け道: 玄関前 → 道路の肩(中心から 4m)
                a = ctr + front * (HOUSE_HALF[1] + 0.5)
                b = P0 + nrm * 4.0
                n_ = max(int(np.hypot(*(b - a)) / 2.0), 2)
                t = np.linspace(0, 1, n_ + 1)
                line = np.stack([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t], 1)
                zl = hf().sample(line[:, 0], line[:, 1])
                zl[0] = zc
                lanes.append((LineString(line), dict(width=3.2, z=[round(float(v), 2) for v in zl], kind="lane")))
                pads.append((LineString(line).buffer(2.0), dict(width=0.0, clear_width=0.0)))
                # 畑: 家屋の横(道路と平行にずらす)
                if nf < p["fields"] and rng.random() < 0.7:
                    for sgn in rng.permutation([1, -1]):
                        fc = ctr + d * sgn * (HOUSE_HALF[0] + FIELD_HALF[0] + 3.0)
                        fyaw = yaw
                        fpoly = ok_site(fc[0], fc[1], *FIELD_HALF, fyaw, 2.0)
                        if fpoly is None:
                            continue
                        fz, _ = level_pad(doc, fpoly, blend=4.0)
                        rows.append((fc[0], fc[1], fz, fyaw, FIELDS[int(rng.integers(2))], 1.0))
                        placed.append((fc[0], fc[1], 10.0))
                        pads.append((fpoly, dict(width=0.0, clear_width=0.0)))
                        nf += 1
                        break
            vill.append((Point(*c), dict(name=nm, radius=p["radius"], houses=nh, fields=nf)))
        # 敷地マスク
        from rasterio import features
        from rasterio.transform import from_origin
        if pads:
            tr = from_origin(g.x0, g.y0 + g.ny * g.res, g.res, g.res)
            mask = np.flipud(features.rasterize([(q.buffer(1.0), 1) for q, _ in pads], out_shape=g.shape, transform=tr, fill=0, dtype="uint8")).astype(np.float32)
        doc.set("village", mask)
        doc.vectors["village_pads"] = pads
        doc.vectors["lanes"] = lanes
        doc.vectors["villages"] = vill
        # 家屋・畑は整地後の標高に接地
        assets = sorted({r[4] for r in rows}) or HOUSES[:1]
        ix = {n: i for i, n in enumerate(assets)}
        a = np.array([[r[0], r[1], r[2]] for r in rows], np.float32).reshape(-1, 3)
        doc.scatter["village"] = dict(pos=a, yaw=np.array([r[3] for r in rows], np.float32), pitch=np.zeros(len(rows), np.float32),
                                      scale=np.ones(len(rows), np.float32), kind=np.array([ix[r[4]] for r in rows], np.int16), assets=np.array(assets))

