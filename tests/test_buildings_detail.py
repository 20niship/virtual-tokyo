from shapely.geometry import Polygon

from vt.assemble import STYLES, build_building, validate_styles
from vt.layers import Feature
from vt.modules.library import REG


def _feat(i, w, d, tags, top=20.0):
    return Feature(i, Polygon([(0, 0), (w, 0), (w, d), (0, d)]), {"_top": top, "_min": 0.0, **tags})


def test_styles_reference_existing_modules():
    assert validate_styles() == set()
    assert len(STYLES) >= 16 and len(REG) >= 220


def test_each_tag_builds_a_distinct_style_family():
    cases = {
        "house": _feat(1, 9, 8, {"building": "house"}, 7.0), "parking": _feat(2, 40, 20, {"building": "parking"}, 14.0),
        "warehouse": _feat(3, 60, 30, {"building": "warehouse"}, 12.0), "shrine": _feat(4, 12, 8, {"building": "shrine"}, 6.0),
        "school": _feat(5, 50, 14, {"building": "school"}, 12.0), "tower_mansion": _feat(6, 30, 30, {"building": "apartments"}, 90.0),
    }
    got = {}
    for key, f in cases.items():
        b = build_building(f)
        assert b and len(b.insts) > 20, key
        got[key] = b.meta["style"]
    assert got["house"] == "house" and got["parking"] == "parking" and got["warehouse"] == "warehouse"
    assert got["shrine"] == "shrine" and got["school"] == "school" and got["tower_mansion"] == "tower_mansion"


def test_house_gets_pitched_roof_and_micro_gets_prefab():
    h = build_building(_feat(10, 9, 8, {"building": "house"}, 7.0))
    assert "roof_tile" in set(h.shell.m) or "roof_metal" in set(h.shell.m)
    mi = build_building(_feat(11, 5, 2, {"building": "yes", "amenity": "bicycle_parking"}, 3.0))
    assert mi.meta["style"] == "micro" and mi.insts[0].name == "bldg_bike_shed"


def test_deterministic_and_variety():
    f = _feat(20, 24, 14, {"building": "yes"}, 30.0)
    a, b = build_building(f), build_building(f)
    assert [(i.name, round(i.x, 3), round(i.z, 3)) for i in a.insts] == [(i.name, round(i.x, 3), round(i.z, 3)) for i in b.insts]
    names = {tuple(sorted({i.name for i in build_building(_feat(100 + k, 24, 14, {"building": "yes"}, 30.0)).insts})) for k in range(12)}
    assert len(names) >= 6
