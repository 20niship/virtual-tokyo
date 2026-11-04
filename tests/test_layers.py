from vt.geo import to_local, to_lonlat
from vt.layers import building_height, load
import random


def test_geo_roundtrip():
    lon, lat = 139.7766, 35.6300
    assert max(abs(a - b) for a, b in zip(to_lonlat(*to_local(lon, lat)), (lon, lat))) < 1e-9


def test_height_priority():
    r = random.Random(0)
    assert building_height({"height": "12 m", "building:levels": "3"}, r)[0] == 12
    assert building_height({"building:levels": "3"}, r)[2] == "levels"
    assert building_height({}, r)[2] == "guess"


def test_layers_contain_target_lines():
    L = load()
    rail = {(f.tags.get("name"), f.tags["railway"]) for f in L["rail"]}
    assert ("ゆりかもめ", "light_rail") in rail
    assert ("東京モノレール", "monorail") in rail
    assert len(L["buildings"]) > 1000 and len(L["roads"]) > 1000
