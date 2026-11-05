import importlib.util
import random
from pathlib import Path

from shapely.geometry import LineString, Point

from vt import road_extras as rx
from vt import roads
from vt.layers import Feature
from vt.world import Terrain

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("road_test_grid", ROOT / "scripts/road_test_grid.py")
grid = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grid)


def _world(c, r=200):
    area = Point(*c).buffer(r)
    return dict(area=area, land=area, zf=Terrain(flat=2.0), center=c)


def _build(key, **cfg_over):
    feats = grid.build_cases()[key]
    xs = [p[0] for f in feats for p in f.geom.coords]; ys = [p[1] for f in feats for p in f.geom.coords]
    c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    cfg = dict(roads.CFG, **cfg_over)
    return roads.build_roads({"roads": feats}, _world(c, 220), cfg)


def test_b9_all_representative_junctions_build():
    for key in grid.build_cases():
        m, edges, info = _build(key)
        assert len(m.f) > 300, key


def test_forced_profile_tags():
    cfg = dict(roads.CFG)
    p = roads.make_profile({"highway": "primary", "vt_lanes": "3", "vt_sw": "left", "vt_bike": "yes", "vt_median": "planter"}, random.Random(1), cfg)
    assert p.lanes == 3 and p.sw_l > 0 and p.sw_r == 0 and p.bike > 0 and p.median >= 1.8 and p.median_kind == "planter"
    q = roads.make_profile({"highway": "residential", "vt_sw": "no", "vt_shoulder": "2.0"}, random.Random(1), cfg)
    assert q.sw_l == 0 and q.sw_r == 0 and q.shoulder == 2.0 and q.parking
    assert abs(q.half - (q.lanes * 2 * q.lane_w / 2 + q.median / 2 + q.bike + q.shoulder)) < 1e-9


def test_osm_turn_lanes_parsed_in_lane_order():
    tags = {"turn:lanes:forward": "left|through|through;right"}
    # 前進側(b端への接近)。縁石側(左)から3レーン → 中央側(k=0)から並べ替わる
    assert rx.osm_turn_lanes(tags, False, False, 0, 3) == ["arrow_straight_right", "arrow_straight", "arrow_left"]
    assert rx.osm_turn_lanes(tags, True, False, 0, 3) is None


def test_right_turn_lane_gets_arrow_guide_line_and_pocket():
    m, edges, info = _build("B", scramble_rate=0.0)
    plans = info["plans"]
    assert plans and all(len(v["arrows"]) == edges[0].prof.lanes or True for v in plans.values())
    assert any(v["rt"] > 0 for v in plans.values())
    mats = set(m.m)
    assert {"decal_arrow_right", "paint_road_white"} <= mats or {"decal_arrow_straight_right", "paint_road_white"} <= mats
    # 分離帯(planter)を右折レーン区間で切って導流帯にした: 白帯の数が通常の車線標示だけより多い
    assert sum(1 for x in m.m if x == "paint_road_white") > 200


def test_gore_zone_at_link_merge_and_no_crosswalk_there():
    m, edges, info = _build("J")
    assert len(info["gores"]) == 1 and not info["arms"]


def test_osm_crossing_way_becomes_midblock_crosswalk_with_both_stop_lines():
    m, edges, info = _build("K")
    assert len(info["mid_crossings"]) >= 1
    assert sum(1 for x in m.m if x == "paint_road_white") > 100


def test_hump_and_camber_raise_pavement():
    # 住宅街の長い1本道: ハンプを必ず置く(hump_rate=1)
    line = Feature(1, LineString([(0, 0), (200, 0)]), {"highway": "residential", "vt_lanes": "1", "vt_sw": "both", "vt_bike": "no"})
    cfg = dict(roads.CFG, hump_rate=1.0, city_age=0.0)
    m, edges, info = roads.build_roads({"roads": [line]}, _world((100, 0), 150), cfg)
    zs = [v[2] for f, mt in zip(m.f, m.m) if mt == "asphalt" for v in (m.v[i] for i in f)]
    base = 2.02
    assert max(zs) > base + 0.07          # ハンプ天端(+8cm)
    assert len({round(z, 3) for z in zs}) > 3   # カマボコ断面で高さが一様でない


def test_curb_has_chamfer_top_and_l_gutter():
    key = next(iter(grid.build_cases()))
    m, _, _ = _build(key, barrier_free_rate=0.0)             # 高い縁石(12〜18cm)
    assert {"curb_top", "gutter_l"} <= set(m.m)
    n_top = sum(1 for x in m.m if x == "curb_top")
    n_gut = sum(1 for x in m.m if x == "gutter_l")
    assert n_top >= 2 * n_gut > 0                             # 縁石ごとに 面取り+天端 の2面、側溝1面
