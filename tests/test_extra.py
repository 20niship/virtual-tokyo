"""追加モジュール(田舎/ロードサイド/工業/高架細部)・屋根・様式・高架細部配置のテスト"""
import random

from shapely.geometry import Polygon

from vt import assemble, expwy, roofs
from vt.materials import MATERIALS
from vt.modules.library import REG, get
from vt.modules.xutil import shop_uv

NEW_CATS = {"日本家屋", "戸建", "アパート", "外構", "農業", "屋根部材", "農村", "ロードサイド", "店舗看板", "ガソリンスタンド", "駐車場", "工場", "プラント", "高架"}


def test_new_modules_build_with_known_materials():
    names = [n for n, r in REG.items() if r["cat"] in NEW_CATS]
    assert len(names) > 200
    for n in names:
        m = get(n)
        assert m.f, n
        assert {x for x in m.m} <= set(MATERIALS), (n, {x for x in m.m} - set(MATERIALS))


def test_styles_reference_existing_modules():
    assert assemble.validate_styles() == set()
    for k in ("house_jp_kawara", "house_maker_a", "apt_wood2", "rs_conv_a", "factory_tin_gray", "logistics"):
        assert k in assemble.STYLES


def test_shop_fascia_keys_exist_in_atlas():
    for n in REG:
        if n.startswith("rs_fascia_"):
            uv, _ = shop_uv(n[len("rs_fascia_"):])
            assert uv is not None, n


def test_roofs_all_kinds():
    poly = Polygon([(0, 0), (11, 0), (11, 7), (0, 7)])
    for kind in ("gable", "hip", "irimoya", "katanagare"):
        for mat in ("kawara", "tanshiki_blue", "slate_dark"):
            B = assemble.Built(1)
            assert roofs.build(B, poly, 3.0, random.Random(1), kind, mat)
            assert len(B.shell.f) > 8
            assert all(m in MATERIALS for m in B.shell.m)
    B = assemble.Built(2)
    assert not roofs.build(B, Polygon([(0, 0), (10, 0), (10, 2), (3, 2), (3, 8), (0, 8)]), 3.0, random.Random(1), "gable", "kawara")   # L字は不可


def test_house_with_new_style_builds():
    from vt.layers import Feature
    f = Feature(5, Polygon([(0, 0), (10, 0), (10, 7), (0, 7)]), dict(building="house", _top=6.5, _min=0.0, _style="house_jp_kawara"))
    b = assemble.build_building(f)
    assert b.meta["style"] == "house_jp_kawara" and b.meta["roof"][0] in ("gable", "hip", "irimoya", "katanagare")
    assert any(i.name.startswith("win_jp_") or i.name.startswith("wall_") for i in b.insts)


def test_pier_extras_placed():
    rng = random.Random(3)
    ins = []
    for _ in range(20):
        ins += expwy.pier_extras(0.0, 0.0, 0.3, 2.0, 12.0, 1.2, 5.0, "T", rng, True)
    names = {i.name for i in ins}
    assert {"ex_downpipe", "ex_pier_plate", "ex_fall_prevent"} <= names
    assert all(i.name in REG for i in ins)
