import json
from pathlib import Path

import pytest

from vt.materials import MATERIALS
from vt.modules import library as lib

TEX = Path(__file__).resolve().parents[1] / "assets/textures"
NEW = [n for n in lib.all_names() if n.startswith(("lf_", "pedx_", "cyclist_", "scooter_", "car_wagon_", "car_van_", "car_keivan_", "truck_kei_", "truck_dump", "bus_coach", "bus_mini", "bus_city_", "motorbike"))]


def test_new_module_count():
    assert len(NEW) >= 150


@pytest.mark.parametrize("name", NEW)
def test_module_builds_with_known_materials(name):
    m = lib.get(name)
    assert len(m.f) > 0
    assert set(m.m) <= set(MATERIALS), set(m.m) - set(MATERIALS)
    for f in m.f:
        assert all(0 <= i < len(m.v) for i in f)


def test_textures_exist_for_materials():
    for k, d in MATERIALS.items():
        if k.startswith(("car_paint_", "ped_tex_", "decal_overlay_", "vending_atlas", "nobori_atlas", "lantern_atlas", "car_plate_atlas")):
            assert (TEX / d["tex"]).exists(), (k, d["tex"])


def test_plate_atlas_has_all_kinds():
    j = json.load(open(TEX / "plate_atlas.json"))
    assert {"white", "kei", "green", "keigreen"} <= set(j["types"])
    assert all(len(v) == 4 and 0 <= v[0] < v[2] <= 1 for v in j["uv"].values())


def test_atlas_uvs_in_unit_square():
    for fn in ("vending_atlas.json", "nobori_atlas.json", "lantern_atlas.json"):
        for u in json.load(open(TEX / fn))["uv"]:
            assert 0 <= u[0] < u[2] <= 1 and 0 <= u[1] < u[3] <= 1


def test_pedestrian_variety():
    from vt.modules.lib_city2 import PEDX
    assert sum(len(v) for v in PEDX.values()) >= 35 and {"office", "elder", "kid", "parasol"} <= set(PEDX)


def test_city_props_names_exist():
    import random
    from vt import city_props
    rng = random.Random(1)
    for _ in range(400):
        assert city_props._vehicle(rng, rng.choice([1, 3, 4])) in lib.REG
        assert city_props._ped(rng, rng.choice([0, 1, 2, 3])) in lib.REG
