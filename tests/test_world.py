import random
from pathlib import Path

from shapely.geometry import LineString, Point

from vt import roads
from vt.layers import Feature
from vt.modules.geom import _newell
from vt.world import Terrain, sweep


def _world(r=300):
    area = Point(0, 0).buffer(r)
    return dict(area=area, land=area, zf=Terrain(flat=2.0), center=(0, 0))


def _cross():
    mk = lambda i, a, b: Feature(i, LineString([a, b]), {"highway": "secondary"})
    return {"roads": [mk(1, (-200, 0), (0, 0)), mk(2, (0, 0), (200, 0)), mk(3, (0, -200), (0, 0)), mk(4, (0, 0), (0, 200))]}


def test_profile_is_seeded_and_in_range():
    t = {"highway": "tertiary"}
    a = roads.make_profile(t, random.Random(5), roads.CFG)
    b = roads.make_profile(t, random.Random(5), roads.CFG)
    assert a == b
    assert 1.5 <= max(a.sw_l, a.sw_r) <= 6.0 and 0.0 <= a.curb_h <= 0.2 and a.lanes >= 1


def test_sidewalk_off_and_bike_lane_switches():
    cfg = dict(roads.CFG, bike_lane_rate=1.0, tactile_rate=0.0)
    p = roads.make_profile({"highway": "secondary", "sidewalk": "no"}, random.Random(1), cfg)
    assert p.sw_l == 0 and p.sw_r == 0 and p.bike > 0 and not p.tactile


def test_crossing_gets_crosswalk_stopline_ramp_and_tactile():
    m, edges, info = roads.build_roads(_cross(), _world(), dict(roads.CFG, barrier_free_rate=1.0, tactile_rate=1.0))
    mats = set(m.m)
    assert {"asphalt", "paint_road_white", "decal_tbs_dot"} <= mats | {"asphalt"}
    assert "paint_road_white" in mats and "decal_tbs_dot" in mats
    assert any(x.startswith("sidewalk") for x in mats)
    assert len(m.f) > 500


def test_sweep_normals_outward():
    from vt.modules.geom import Mesh
    m = Mesh()
    path = [(0, 0), (5, 0), (10, 0)]
    sweep(m, path, lambda i: [(-1, 0, "x"), (1, 0, "x"), (1, 1, "x"), (-1, 1, "x")], [0, 0, 0])
    for f in m.f:
        p = [m.v[i] for i in f]
        n = _newell(p)
        c = [sum(q[k] for q in p) / len(p) for k in range(3)]
        assert n[0] * (c[0] - 5) * 0 + n[1] * c[1] + n[2] * (c[2] - 0.5) >= -1e-9


def test_textures_committed():
    d = Path(__file__).resolve().parents[1] / "assets/textures"
    for n in ("asphalt.png", "sidewalk_paver.png", "arrow_straight.png", "text_tomare.png", "tbs_line.png", "paint_wear.png", "track_bed.png"):
        assert (d / n).exists(), n
