import hashlib
import json
from pathlib import Path

from shapely.geometry import Point, Polygon

from tests.test_world import _cross, _world
from vt import roads, tree_gen as tg, vegetation
from vt.layers import Feature
from vt.materials import MATERIALS
from vt.modules.library import REG, get

TEX = Path(__file__).resolve().parents[1] / "assets/textures"


def test_leaf_atlas_consistent():
    m = json.loads((TEX / "leaves_atlas.json").read_text())
    W, H = m["size"]
    assert W <= 4096 and H <= 4096 and m["source_sprites"] > 500
    assert len(m["cards"]) >= 60 and len(m["leaves"]) >= 100
    for v in list(m["cards"].values()) + list(m["leaves"].values()):
        x, y, w, h = v["rect"]
        assert 0 <= x and x + w <= W and 0 <= y and y + h <= H
        u0, v0, u1, v1 = v["uv"]
        assert abs(u0 - x / W) < 1e-6 and abs(v1 - (1 - y / H)) < 1e-6
    from PIL import Image
    im = Image.open(TEX / "leaves_atlas.png")
    assert im.mode == "RGBA" and im.size == (W, H)
    kinds = {c["species"] for c in m["cards"].values()}
    assert {"broadleaf", "ginkgo", "pine", "palm", "ivy", "azalea", "hedge", "sakura", "grass"} <= kinds


def test_all_vegetation_modules_build_with_low_poly_count():
    names = [n for n, r in REG.items() if r["cat"] == "植栽"]
    assert len(names) >= 120
    for n in names:
        mesh = get(n)
        assert mesh.f, n
        assert set(mesh.m) <= set(MATERIALS), n
        assert tg.tris(mesh) <= 20000, (n, tg.tris(mesh))
    big = [get(n) for n in names if "_m_0_summer" in n]
    assert all(tg.tris(m) >= 300 for m in big)


def test_tree_generation_is_deterministic_and_varies_with_seed():
    h = lambda m: hashlib.md5(repr(m.v[:200]).encode()).hexdigest()
    a, _ = tg.build_tree("keyaki", 9.0, 0, "summer")
    b, _ = tg.build_tree("keyaki", 9.0, 0, "summer")
    c, _ = tg.build_tree("keyaki", 9.0, 1, "summer")
    assert h(a) == h(b) and h(a) != h(c)


def test_seasons_change_leaf_cards_and_winter_is_bare():
    s, _ = tg.build_tree("ichou", 9.0, 0, "summer")
    w, _ = tg.build_tree("ichou", 9.0, 0, "winter")
    assert "leaf_atlas" in s.m and "leaf_atlas" not in w.m


def test_placement_avoids_carriageway_and_is_deterministic():
    w = _world(250)
    cfg = dict(roads.CFG)
    m, edges, info = roads.build_roads(_cross(), w, cfg)
    sw = info["sw"]
    walk = sw.buffer(0).representative_point() if not sw.is_empty else Point(20, 5)
    L = dict(roads=[], green=[Feature(1, Polygon([(60, 60), (140, 60), (140, 140), (60, 140)]), {"leisure": "park"})], landuse=[], buildings=[])
    X = dict(pois=[Feature(2, Point(walk.x, walk.y), {"natural": "tree"})], hedges=[], tree_rows=[], vegareas=[])
    a = vegetation.build_vegetation(L, X, w, edges, info, cfg, seed=5)
    b = vegetation.build_vegetation(L, X, w, edges, info, cfg, seed=5)
    assert [(i.name, round(i.x, 3), round(i.y, 3)) for i in a] == [(i.name, round(i.x, 3), round(i.y, 3)) for i in b]
    assert len(a) > 20
    cw = info["cw"]
    for i in a:
        assert i.name in REG
        if i.name.startswith(("veg_tree", "veg_keyaki", "veg_ichou", "veg_platanus", "veg_sakura", "veg_kusunoki", "veg_shii")):
            assert not cw.contains(Point(i.x, i.y)), i.name


def test_realistic_trees_small_leaf_cards_litter_and_bark_height():
    import numpy as np
    mesh, _ = tg.build_tree("keyaki", 9.0, 0, "summer")
    assert 5000 <= tg.tris(mesh) <= 12000
    assert {"veg_litter_y", "veg_litter_r", "veg_litter_b", "veg_litter_g"} <= set(REG)
    for k in "yrbg":
        assert (TEX / f"overlay_litter_{k}.png").exists()
    for b in ("furrow", "furrow_dark", "smooth", "plane", "pine", "palm", "shuro"):
        assert (TEX / f"bark_{b}_h.png").exists()
    v = np.array(mesh.v, float).reshape(-1, 3)
    leaf = [f for f, mt in zip(mesh.f, mesh.m) if mt == "leaf_atlas"]
    ext = max(np.ptp(v[list(f)], axis=0).max() for f in leaf)
    assert ext < 1.3, ext                     # 葉クラスターカードは実寸(旧実装は2〜3.5m)
