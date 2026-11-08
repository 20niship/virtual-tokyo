"""道路の付属物と構造物の module 配置(scatter グループ "road_furniture"): ガードレール(盛土側)・擁壁(深い切土側)・落石防止網(高い切土)・
カーブミラー(急カーブの外側)・橋の桁(8m ごと)と橋脚・沈下橋・トンネル坑口(ポータル)。向きは module の長手 +y を道路方向へ、勾配は pitch(X 軸回り)で付ける。"""
from __future__ import annotations

import math

import numpy as np

from ..core.node import Node, node
from . import bridge

HW = 3.25         # 路盤の半幅(幅 6.5m)


def _frame(P, z, i, j):
    d = P[j] - P[i]
    L = float(np.hypot(*d))
    d = d / max(L, 1e-9)
    return d, L, math.atan2(-d[0], d[1]), math.atan((z[j] - z[i]) / max(L, 1e-9))


@node("infra.furniture")
class Furniture(Node):
    """要 infra.road。guard_drop: 盛土側がこの高さ以上落ちる所にガードレール / wall_cut: 切土がこの高さ以上で擁壁 / net_cut: 落石防止網 / mirror_radius: カーブミラーの半径しきい値"""
    inputs = ("height",)
    scatter_outputs = ("road_furniture",)
    defaults = dict(guard_drop=1.5, wall_cut=3.0, net_cut=6.0, mirror_radius=35.0)

    def run(self, doc, rng):
        p = self.params
        hf = doc.heightfield()
        rows = []        # (x, y, z, yaw, pitch, name)
        for ln, pr in doc.vectors.get("roads", []):
            P = np.asarray(ln.coords)
            z = np.asarray(pr["z"])
            if pr["kind"] == "road":
                self._road(P, z, hf, p, rows)
            else:
                self._bridge(P, z, hf, rows)
        for ln, pr in doc.vectors.get("tunnels", []):
            P = np.asarray(ln.coords)
            z = np.asarray(pr["z"])
            v = int(rng.integers(3))
            d, _, yaw, pit = _frame(P, z, 0, min(4, len(P) - 1))
            rows.append((P[0, 0], P[0, 1], z[0], yaw, pit, f"tunnel_portal_{v}"))
            d, _, yaw, pit = _frame(P, z, len(P) - 1, max(len(P) - 5, 0))
            rows.append((P[-1, 0], P[-1, 1], z[-1], yaw, pit, f"tunnel_portal_{v}"))
        names = sorted({r[5] for r in rows})
        ix = {n: i for i, n in enumerate(names)}
        a = np.array([[r[0], r[1], r[2]] for r in rows], np.float32).reshape(-1, 3)
        doc.scatter["road_furniture"] = dict(pos=a, yaw=np.array([r[3] for r in rows], np.float32), pitch=np.array([r[4] for r in rows], np.float32),
                                             scale=np.ones(len(rows), np.float32), kind=np.array([ix[r[5]] for r in rows], np.int16), assets=np.array(names or ["road_guardrail_4m"]))

    def _road(self, P, z, hf, p, rows):
        n = len(P)
        for i in range(0, n - 2, 2):
            d, L, yaw, pit = _frame(P, z, i, i + 2)
            c = (P[i] + P[i + 2]) / 2
            zc = (z[i] + z[i + 2]) / 2
            right = np.array([d[1], -d[0]])
            for side in (1, -1):
                sd = right * side
                h_out = float(hf.sample(np.array([c[0] + sd[0] * 5.5]), np.array([c[1] + sd[1] * 5.5]))[0])
                h_in = float(hf.sample(np.array([c[0] + sd[0] * 5.0]), np.array([c[1] + sd[1] * 5.0]))[0])
                yaw_s = yaw if side > 0 else yaw + math.pi
                if zc - h_out > p["guard_drop"]:
                    q = c + sd * (HW - 0.2)
                    rows.append((q[0], q[1], zc, yaw_s, pit, "road_guardrail_4m"))
                cut = h_in - zc
                if cut > p["wall_cut"]:
                    q = c + sd * (HW + 0.45)
                    rows.append((q[0], q[1], zc - 0.1, yaw_s, pit, "road_retwall_4m"))
                if cut > p["net_cut"] and i % 4 == 0:
                    q = c + sd * (HW + 2.2)
                    hz = float(hf.sample(np.array([q[0]]), np.array([q[1]]))[0])
                    rows.append((q[0], q[1], max(zc + 2.4, hz - 0.3), yaw_s, 0.0, "road_rocknet_8m"))
        # カーブミラー: 方位変化から半径を推定し、急カーブの外側に 1 本
        last = -99
        for i in range(5, n - 5):
            a1 = math.atan2(*(P[i] - P[i - 5])[::-1])
            a2 = math.atan2(*(P[i + 5] - P[i])[::-1])
            da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
            R = 10.0 / max(abs(da), 1e-6)
            if R < p["mirror_radius"] and i - last > 14:
                d, _, yaw, pit = _frame(P, z, i - 1, i + 1)
                right = np.array([d[1], -d[0]])
                side = 1 if da > 0 else -1                  # 左へ曲がる(da>0)なら外側 = 右
                q = P[i] + right * side * (HW + 0.6)
                rows.append((q[0], q[1], z[i], yaw, 0.0, "road_curve_mirror"))
                last = i

    def _bridge(self, P, z, hf, rows):
        s = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
        L = float(s[-1])
        info = bridge.classify(P, z, hf)
        name = "bridge_chinka_8m" if info["kind"] == "chinka" else "bridge_deck_8m"
        n = max(int(math.ceil(L / 8.0)), 1)
        for q in range(n):
            sc = (q + 0.5) * L / n
            i = int(np.searchsorted(s, sc))
            i0, i1 = max(i - 1, 0), min(i + 1, len(P) - 1)
            d, _, yaw, pit = _frame(P, z, i0, i1)
            x, y = np.interp(sc, s, P[:, 0]), np.interp(sc, s, P[:, 1])
            rows.append((x, y, float(np.interp(sc, s, z)), yaw, pit, name))
        d, _, yaw, _ = _frame(P, z, 0, len(P) - 1)
        for sq, zg, zb in info["piers"]:
            H, nm = bridge.pier_module(zb - zg)
            x, y = np.interp(sq, s, P[:, 0]), np.interp(sq, s, P[:, 1])
            rows.append((x, y, zb - H, yaw, 0.0, nm))
