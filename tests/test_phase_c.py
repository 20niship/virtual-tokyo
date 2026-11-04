import random
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import LineString, Point

from vt import bridges, rails_c, roads
from vt.layers import Feature
from vt.modules.geom import Mesh
from vt.modules.geom import _newell
from vt.modules.geom3 import beam, frustum
from vt.modules.library import REG, get
from vt.world import Terrain

ROOT = Path(__file__).resolve().parents[1]


def _world(r=400):
    area = Point(0, 0).buffer(r)
    return dict(area=area, land=area, zf=Terrain(flat=2.0), center=(0, 0))


def _outward(m, c):
    for f in m.f:
        p = [m.v[i] for i in f]
        n = _newell(p)
        fc = [sum(q[k] for q in p) / len(p) for k in range(3)]
        assert sum(n[k] * (fc[k] - c[k]) for k in range(3)) > -1e-9


def test_beam_and_frustum_normals_outward():
    m = Mesh(); beam(m, (0, 0, 0), (10, 3, 4), 1.0, 2.0, "x")
    _outward(m, (5, 1.5, 2))
    m = Mesh(); frustum(m, 0, 0, 0, 10, 4, 4, 2, 2, 0.7, "x")
    _outward(m, (0, 0, 5))


def test_modules_registered():
    for n in ("hanger_clamp", "platform_door_unit", "station_roof_bay", "station_sign_U07", "station_sign_MO_03"):
        assert n in REG and get(n).f, n


def test_elevated_road_has_girder_barrier_joint_and_piers():
    f = Feature(1, LineString([(-150, 0), (150, 0)]), {"highway": "motorway", "bridge": "yes", "layer": "2", "lanes": "2", "oneway": "yes", "name": "x"})
    W = _world()
    edges = roads.build_edges([f], W["area"], roads.CFG)
    m = bridges.elevated_roads(edges, W, roads.CFG, random.Random(1))
    mats = set(m.m)
    assert {"asphalt", "concrete_formed", "steel_gray", "paint_road_white"} <= mats
    assert len(m.f) > 3000
    zmax = max(v[2] for v in m.v)
    assert zmax > 10          # 桁・パラペット・橋脚が立ち上がっている


def test_station_has_platform_doors_roof_and_sign():
    ln = LineString([(-200, 0), (200, 0)])
    n = 134
    S = [400 * i / n for i in range(n + 1)]
    zs = [12.0] * (n + 1)
    rails_c._XY["台場"] = (0.0, 0.0)
    m, insts = Mesh(), []
    rails_c.build_station(m, insts, ln, S, zs, Terrain(flat=2.0), "台場", "yurikamome", _world()["land"], random.Random(1))
    names = {i.name for i in insts}
    assert {"platform_door_unit", "station_roof_bay", "station_sign_U07"} <= names
    assert len(m.f) > 500


def test_rainbow_found_in_osm():
    if not list((ROOT / "data/osm").glob("*.json")):
        pytest.skip("OSM cache なし")
    from vt.layers import load
    rb = bridges.find_rainbow(load())
    assert rb is not None and 850 < rb.Lc < 1000
    mid = rb.at(rb.Lc / 2)
    assert rb.w(mid[0], mid[1]) > 0.95 and rb.w(mid[0] + 500, mid[1] + 500) < 0.05
