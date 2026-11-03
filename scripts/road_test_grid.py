"""B-9: RoadProfile をタグで強制した合成道路網(十字/T字/五差路/ロータリー/分合流/街区途中横断/スクランブル)を俯瞰と低い視点でレンダする。
使い方: uv run python scripts/road_test_grid.py [--cases A,B] [--views top,low] [--fast]"""
import math
import os
import sys
from pathlib import Path

from shapely.geometry import LineString, Point

from vt import ground, render, roads
from vt.layers import Feature
from vt.world import Terrain

OUT = Path(__file__).resolve().parents[1] / "out/render"
SP = 260.0   # セル間隔


def arm_ways(c, ang_deg, length, tags, nid, start=0.0):
    a = math.radians(ang_deg)
    p0 = (c[0] + math.cos(a) * start, c[1] + math.sin(a) * start)
    return Feature(nid, LineString([p0, (c[0] + math.cos(a) * length, c[1] + math.sin(a) * length)]), dict(tags))


def T(hw="secondary", lanes=1, sw="both", bike="no", median=None, **kw):
    t = {"highway": hw, "vt_lanes": str(lanes), "vt_sw": sw, "vt_bike": bike}
    if median:
        t["vt_median"] = median
    t.update(kw)
    return t


def cross(c, nid, ta, tb, angs=(0, 90, 180, 270), tc=None, L=95.0):
    ways = []
    for i, a in enumerate(angs):
        ways.append(arm_ways(c, a, L, ta if i % 2 == 0 else (tb or ta), nid + i))
    return ways


def roundabout(c, nid, R=24.0):
    ways = []
    rt = T("primary", 2, "both", "no", None, vt_oneway="yes", junction="roundabout", oneway="yes")
    ang = [0, -90, -180, -270, -360]       # 時計回り(日本は左側通行)
    for i in range(4):
        pts = [(c[0] + R * math.cos(math.radians(a)), c[1] + R * math.sin(math.radians(a))) for a in [ang[i] + (ang[i + 1] - ang[i]) * k / 8 for k in range(9)]]
        ways.append(Feature(nid + i, LineString(pts), dict(rt)))
    for i, a in enumerate((0, 90, 180, 270)):
        ways.append(arm_ways(c, a, 95.0, T("primary", 2, "both", "no", "paint"), nid + 10 + i, start=R))
    return ways


def build_cases():
    cases = {}
    n = [1000]

    def nid():
        n[0] += 20
        return n[0]
    cx = lambda i, j: (i * SP, j * SP)
    # A: 十字 1車線/方向, 歩道あり, 自転車レーン無し(secondary)
    cases["A"] = cross(cx(0, 0), nid(), T("secondary", 1, "both", "no"), T("secondary", 1, "both", "no"))
    # B: 十字 2車線 + 植栽分離帯 + 自転車レーンあり (primary) × 1車線生活道路(歩道あり)
    cases["B"] = cross(cx(1, 0), nid(), T("primary", 2, "both", "yes", "planter"), T("tertiary", 1, "both", "no"))
    # C: 十字 3車線 + ガードレール型分離帯 + 歩道あり + 自転車なし (trunk)
    cases["C"] = cross(cx(2, 0), nid(), T("trunk", 3, "both", "no", "barrier"), T("trunk", 3, "both", "no", "paint"))
    # D: T字 2車線(paint)+自転車レーン × 1車線 住宅街(歩道あり)
    c = cx(0, 1)
    cases["D"] = [arm_ways(c, 0, 95, T("primary", 2, "both", "yes", "paint"), nid()), arm_ways(c, 180, 95, T("primary", 2, "both", "yes", "paint"), nid()),
                  arm_ways(c, 90, 95, T("residential", 1, "both", "no"), nid())]
    # E: T字 1車線 歩道は片側のみ、自転車なし
    c = cx(1, 1)
    cases["E"] = [arm_ways(c, 0, 95, T("secondary", 1, "left", "no"), nid()), arm_ways(c, 180, 95, T("secondary", 1, "left", "no"), nid()),
                  arm_ways(c, 270, 95, T("tertiary", 1, "right", "yes"), nid())]
    # F: 五差路(角度の異なる5本) 2車線+1車線の混在, 歩道あり/なし
    c = cx(2, 1)
    ts = [T("primary", 2, "both", "no", "paint"), T("secondary", 1, "both", "yes"), T("residential", 1, "no", "no"), T("tertiary", 1, "both", "no"), T("secondary", 2, "both", "no", "paint")]
    cases["F"] = [arm_ways(c, a, 95, t, nid()) for a, t in zip((0, 72, 150, 215, 290), ts)]
    # G: ロータリー
    cases["G"] = roundabout(cx(0, 2), nid())
    # H: 住宅街の十字(歩道なし, 路肩・駐車帯, 一方通行を含む)
    c = cx(1, 2)
    cases["H"] = [arm_ways(c, 0, 95, T("residential", 1, "no", "no", vt_shoulder="2.0"), nid()), arm_ways(c, 180, 95, T("residential", 1, "no", "no", vt_shoulder="2.0"), nid()),
                  arm_ways(c, 90, 95, T("residential", 1, "left", "no", vt_oneway="yes", oneway="yes"), nid()), arm_ways(c, 270, 95, T("residential", 1, "left", "no", vt_oneway="yes", oneway="-1"), nid())]
    # I: 一方通行(3車線)と二方向の十字
    c = cx(2, 2)
    cases["I"] = [arm_ways(c, 0, 95, T("primary", 3, "both", "no", vt_oneway="yes", oneway="yes"), nid()), arm_ways(c, 180, 95, T("primary", 3, "both", "no", vt_oneway="yes", oneway="yes"), nid()),
                  arm_ways(c, 90, 95, T("secondary", 1, "both", "no"), nid()), arm_ways(c, 270, 95, T("secondary", 1, "both", "no"), nid())]
    # J: 幹線に合流するランプ(primary_link) = 導流帯
    c = cx(0, 3)
    cases["J"] = [arm_ways(c, 0, 120, T("primary", 2, "both", "no", "paint"), nid()), arm_ways(c, 180, 120, T("primary", 2, "both", "no", "paint"), nid()),
                  arm_ways(c, 24, 120, T("primary_link", 1, "no", "no"), nid())]
    # K: 街区途中の横断歩道(OSM footway=crossing)
    c = cx(1, 3)
    cases["K"] = [Feature(nid(), LineString([(c[0] - 100, c[1]), (c[0] + 100, c[1])]), T("secondary", 2, "both", "yes", "paint")),
                  Feature(nid(), LineString([(c[0], c[1] - 14), (c[0], c[1] + 14)]), {"highway": "footway", "footway": "crossing"}),
                  Feature(nid(), LineString([(c[0] + 40, c[1] - 14), (c[0] + 40, c[1] + 14)]), {"highway": "footway", "footway": "crossing"})]
    # L: スクランブル(4方向の幹線)
    cases["L"] = cross(cx(2, 3), nid(), T("primary", 2, "both", "no", "paint"), T("primary", 2, "both", "no", "paint"))
    return cases


def main():
    args = sys.argv[1:]
    sel = args[args.index("--cases") + 1].split(",") if "--cases" in args else None
    views = args[args.index("--views") + 1].split(",") if "--views" in args else ["top", "low"]
    fast = "--fast" in args
    cases = build_cases()
    cfg = dict(roads.CFG, scramble_rate=1.0, barrier_free_rate=1.0, tactile_rate=1.0, escort_rate=0.5, hump_rate=1.0 if "--hump" in args else 0.0)
    for key in (sel or cases):
        feats = cases[key]
        L = {"roads": feats}
        xs = [p[0] for f in feats for p in f.geom.coords]; ys = [p[1] for f in feats for p in f.geom.coords]
        c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        ends = {}
        for f in feats:
            for q in (f.geom.coords[0], f.geom.coords[-1]):
                ends[(round(q[0], 1), round(q[1], 1))] = ends.get((round(q[0], 1), round(q[1], 1)), 0) + 1
        top = max(ends.items(), key=lambda kv: kv[1])
        if top[1] >= 3 and not any(f.tags.get("junction") for f in feats):
            c = top[0]          # 3本以上が集まる点 = 交差点中心
        area = Point(c).buffer(170)
        W = dict(area=area, land=area, zf=Terrain(flat=2.0), center=c)
        m, edges, info = roads.build_roads(L, W, cfg)
        print(key, "faces", len(m.f), "edges", len(edges), "crossings", len(info["arms"]), "mid", len(info["mid_crossings"]), "gores", len(info["gores"]))
        for view in views:
            render.init_scene((1600, 1000), 24 if fast else 64, sun_dir=(0.5, -0.45, 0.7))
            render.add_plane(1200, 1.96, "ground", loc=c)
            render.add_mesh_object("roads", m)
            if view == "top":
                render.add_camera((c[0], c[1] - 4, 95), (c[0], c[1], 2), 50)
            else:   # 低い視点: 1本の腕の80m先の路面から交差点を見る
                f0 = max(feats, key=lambda f: f.geom.length)
                lc = list(f0.geom.coords)
                far = lc[-1] if Point(lc[0]).distance(Point(c)) < Point(lc[-1]).distance(Point(c)) else lc[0]
                dx, dy = far[0] - c[0], far[1] - c[1]
                d = math.hypot(dx, dy) or 1
                render.add_camera((c[0] + dx / d * 46 + dy / d * 3.5, c[1] + dy / d * 46 - dx / d * 3.5, 4.8), (c[0], c[1], 2.2), 32)
            render.render(OUT / f"road_grid_{key}_{view}.png")


if __name__ == "__main__":
    main()
