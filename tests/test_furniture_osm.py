from shapely.geometry import LineString, Point

from tests.test_world import _cross, _world
from vt import furniture, roads
from vt.layers import Feature
from vt.modules.library import REG, get


def test_safety_street_furniture_modules_build():
    cats = {"安全施設", "電柱", "街具", "看板"}
    names = [n for n, r in REG.items() if r["cat"] in cats]
    assert len(names) >= 40
    for n in names:
        assert get(n).f, n
    assert get("guardrail_beam_4m").lights == [] and get("utility_pole_12m_trans").f


def test_osm_driven_placement():
    w = _world()
    L = _cross()
    m, edges, info = roads.build_roads(L, w, dict(roads.CFG))
    X = {"pois": [Feature(1, Point(20, 8), {"amenity": "bench"}), Feature(2, Point(-20, -8), {"highway": "bus_stop", "shelter": "yes"}),
                  Feature(3, Point(30, 8), {"highway": "street_lamp"}), Feature(4, Point(35, -8), {"amenity": "vending_machine"}),
                  Feature(5, Point(40, 8), {"amenity": "post_box"})],
         "barriers": [Feature(10, LineString([(50, 10), (90, 10)]), {"barrier": "guard_rail"})],
         "powerlines": [Feature(20, LineString([(10, 40), (70, 40)]), {"power": "minor_line"})], "adlines": []}
    ins = furniture.build_furniture(L, w, edges, info, roads.CFG, X=X)
    names = [i.name for i in ins]
    assert {"bench_wood_back", "bench_metal", "bench_backless", "bench_arc"} & set(names)
    assert "bus_stop_post" in names and "post_box_red" in names
    assert names.count("guardrail_beam_4m") >= 9 and "guardrail_terminal" in names
    assert furniture.build_furniture.wires is not None and furniture.build_furniture.wires.f
    assert any(n.startswith("utility_pole") for n in names)
    assert set(names) <= set(REG)
