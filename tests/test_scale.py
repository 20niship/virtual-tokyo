import numpy as np
import pytest

from vt.modules import library as lib


def size(name):
    v = np.array(lib.get(name).v)
    return v.max(0) - v.min(0), v.min(0)


# 日本の実寸基準[m]: (長さ x幅 x高さ) の許容範囲
DIMS = {
    "car_sedan_white": ((4.2, 5.0), (1.6, 2.1), (1.35, 1.6)),
    "car_hatch_white": ((3.7, 4.3), (1.6, 2.0), (1.4, 1.7)),
    "car_suv_white": ((4.2, 4.9), (1.7, 2.1), (1.55, 1.9)),
    "car_minivan_white": ((4.4, 5.1), (1.6, 2.0), (1.7, 2.05)),
    "car_kei_white": ((3.2, 3.7), (1.45, 1.8), (1.45, 1.85)),
    "car_wagon_white": ((4.3, 5.0), (1.6, 2.1), (1.4, 2.0)),
    "car_van_white": ((4.4, 5.1), (1.6, 2.0), (1.8, 2.1)),
    "truck_kei_white": ((3.2, 3.7), (1.45, 1.8), (1.4, 1.8)),
    "truck_box_white": ((5.5, 7.0), (2.0, 2.6), (3.0, 3.7)),
    "bus_city": ((10.0, 12.0), (2.4, 2.9), (3.0, 3.6)),
    "bus_coach": ((11.0, 13.0), (2.4, 2.9), (3.2, 3.8)),
    "bicycle_mama": ((1.6, 1.9), (0.5, 0.75), (0.95, 1.2)),
    "motorbike": ((1.7, 2.2), (0.5, 0.9), (0.9, 1.3)),
    "pedx_office_0": ((0.3, 0.9), (0.3, 0.9), (1.5, 1.95)),
    "pedx_kid_0": ((0.2, 0.9), (0.2, 0.9), (0.95, 1.5)),
    "utility_pole_12m": ((1.0, 2.2), (0.2, 1.0), (11.5, 12.5)),
    "traffic_cone": ((0.3, 0.45), (0.3, 0.45), (0.6, 0.78)),
    "lf_vend_0": ((1.0, 1.3), (0.6, 0.95), (1.8, 2.0)),   # 自治体の設置仕様書: 幅1.2m前後×奥行0.7〜0.95m×高さ1.9〜2.0m以内
    "lf_ac_0": ((0.6, 0.9), (0.2, 0.5), (0.4, 1.3)),
    "lf_scaf_bay": ((1.5, 1.9), (0.7, 1.1), (1.8, 3.0)),
    "lf_down_gray_3m": ((0.04, 0.2), (0.04, 0.2), (2.9, 3.1)),
    "lf_hoard_gray": ((2.9, 3.4), (0.2, 0.8), (3.0, 3.3)),
    "lf_stand_a": ((0.4, 0.9), (0.4, 0.9), (0.8, 1.1)),
    "lf_hyd_box": ((0.5, 0.8), (0.2, 0.5), (0.9, 1.2)),
}


@pytest.mark.parametrize("name", list(DIMS))
def test_module_dimensions(name):
    s, mn = size(name)
    for ax, (lo, hi), lab in zip(range(3), DIMS[name], "LWH"):
        assert lo <= s[ax] <= hi, f"{name} {lab}={s[ax]:.2f} not in [{lo},{hi}]"
    assert mn[2] >= -0.02, f"{name} が地面より下に出ている z0={mn[2]:.3f}"


def test_vehicles_wheels_on_ground():
    for n in ("car_sedan_black", "car_suv_gray", "bus_city", "truck_dump", "scooter_white", "bicycle_mama"):
        assert size(n)[1][2] >= -0.02, n


def test_road_profile_defaults():
    from vt.roads import BASE
    for hw, (lane_w, sw, n) in BASE.items():
        assert 2.4 <= lane_w <= 3.6, hw
        assert sw == 0.0 or 1.5 <= sw <= 6.0, hw


def test_storey_heights_by_use():
    from vt.layers import STOREY, building_height
    import random
    top, _, src = building_height({"building": "apartments", "building:levels": "5"}, random.Random(0))
    assert src == "levels" and abs(top / 5 - 3.0) < 1e-6                        # 住宅の階高≈3.0m
    top, _, _ = building_height({"building": "office", "building:levels": "10"}, random.Random(0))
    assert 3.6 <= top / 10 <= 4.2                                               # 事務所の階高≈3.9m
    assert all(2.6 <= v <= 5.0 for v in STOREY.values())
    top, _, src = building_height({"building": "yes", "height": "42"}, random.Random(0))
    assert (top, src) == (42.0, "height")


def test_building_floor_split_follows_levels():
    from shapely.geometry import box
    from vt.assemble import build_building
    from vt.layers import Feature
    f = Feature(1, box(0, 0, 20, 14), {"building": "apartments", "building:levels": "6", "_top": 18.0, "_min": 0.0, "_hsrc": "levels", "_n": 6})
    b = build_building(f)
    assert b.meta["floors"] == 6
    f2 = Feature(2, box(0, 0, 20, 14), {"building": "yes", "_top": 18.0, "_min": 0.0, "_hsrc": "guess", "_n": 0})
    assert build_building(f2).meta["floors"] == 5                              # 階数不明は3.6mで割る
