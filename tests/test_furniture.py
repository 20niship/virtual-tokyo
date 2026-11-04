import json
from pathlib import Path

from shapely.geometry import Point

from vt import furniture, roads
from vt.modules.library import REG
from tests.test_world import _cross, _world

TEX = Path(__file__).resolve().parents[1] / "assets/textures"


def test_sign_atlas_covers_japanese_signs():
    meta = json.loads((TEX / "sign_atlas.json").read_text())
    s = meta["signs"]
    assert len(s) >= 120
    cats = {v["cat"] for v in s.values()}
    assert {"規制", "警戒", "指示", "補助", "案内"} <= cats
    for need in ("reg_stop", "reg_no_entry", "reg_speed_40", "ins_crosswalk", "warn_signal", "gd_odaiba_left", "route_kokudo_357", "route_shuto_C1"):
        assert need in s
    W, H = meta["size"]
    for v in s.values():
        x, y, w, h = v["rect"]
        assert 0 <= x and x + w <= W and 0 <= y and y + h <= H


def test_signal_variants_and_lights_registered():
    for era in ("old", "led", "slim"):
        assert f"sigv_h3_{era}_g" in REG and f"sigp_{era}_r" in REG
    assert "sigv_v3_led_g" in REG and "sigv_h3_led_g_arrow" in REG and "sigp_led_countdown_g" in REG
    lit = [n for n, r in REG.items() if n.startswith(("light_", "sigv_h3_led_g"))]
    from vt.modules.library import get
    assert any(get(n).lights for n in lit)


def test_furniture_placement_on_crossing():
    w = _world()
    m, edges, info = roads.build_roads(_cross(), w, dict(roads.CFG))
    ins = furniture.build_furniture(_cross(), w, edges, info, roads.CFG)
    names = {i.name for i in ins}
    assert any(n.startswith("sigv_") for n in names) and any(n.startswith("sigp_") for n in names)
    assert any(n.startswith("sign_") for n in names) and any(n.startswith("light_") for n in names)
    assert names <= set(REG)
    cw = info["cw"]
    poles = [i for i in ins if i.name.startswith(("pole_", "light_"))]
    assert poles and not any(cw.buffer(-0.05).contains(Point(i.x, i.y)) for i in poles)
