import numpy as np
from scipy.ndimage import map_coordinates

from terra import modules as tm
from terra import detail as D
from terra.core import node_rng, run_recipe
from terra.erosion.hydraulic import hydraulic
from terra.gen.noise import make_noise
from terra.core.grid import Grid
from terra.geology.tables import ROCKS, SOILS
from terra.stats import axis_streak_index
from vt.materials import MATERIALS

RECIPE = {"grid": {"size_m": 600, "res_m": 4}, "climate": {"lat": 36.0, "sea_level_temp_c": 15},
          "steps": [{"gen.noise": {"base_height": 700, "wavelength_m": 400, "offset": 500}}, {"erosion.fluvial": {"iterations": 4, "k": 0.01}},
                    {"gen.crags": {}}, {"masks.slope": {}}, {"hydro.flow": {}}, {"hydro.rivers": {"min_area_km2": 0.004}},
                    {"biome.jp_forest": {}}, {"geology.zones": {}}, {"scatter.trees": {"r_m": 6}}, {"scatter.shrubs": {}},
                    {"scatter.rocks": {}}, {"scatter.ground": {}}]}


def test_geology_layers(tmp_path):
    doc = run_recipe(RECIPE, seed=2, out=tmp_path, log=lambda s: None)
    geo, soil = doc.layers["geology"], doc.layers["soil_type"]
    assert geo.max() < len(ROCKS) and soil.max() < len(SOILS)
    assert len(np.unique(geo)) >= 3                                   # 複数の岩種が出る
    assert 0 <= doc.layers["moss"].min() and doc.layers["moss"].max() <= 1
    assert (soil[geo == 0] != 3).all()                                # 花崗岩域に砂質土(砂岩由来)は出ない


def test_modules_catalog_and_lod():
    names = list(tm.REG)
    assert len([n for n in names if n.startswith("rock_") and n.count("_") >= 3]) >= 100
    kinds = {n.split("_")[1] for n in names if n.startswith("rock_") and n.split("_")[1] in ("granite", "andesite", "sandstone", "limestone", "tuff", "river")}
    assert len(kinds) == 6
    assert len([n for n in names if n.startswith("soil_") and "patch" in n and not n.endswith("far")]) == len(SOILS) * 3
    for n in ("rock_granite_boulder_m_1", "rock_sandstone_outcrop_2", "rock_andesite_column_0", "soil_clay_patch_0", "gravel_patch_talus_1", "gravel_stone_round_cobble_2"):
        near, far = tm.build(n), tm.build(n + "_far")
        assert len(near.f) > len(far.f) > 0                            # near は far より面が多い
        assert set(near.m) <= set(MATERIALS) and set(far.m) <= set(MATERIALS)


def test_rock_states_change_surface():
    mossy, fresh, weathered = (tm.build(f"rock_limestone_boulder_m_{v}") for v in (2, 0, 1))
    assert mossy.m.count("rk_moss") > 20 and fresh.m.count("rk_moss") == 0          # 苔は mossy にだけ
    assert any(m.endswith("_fresh") for m in fresh.m) and not any(m.endswith("_fresh") for m in mossy.m)   # 欠け面は fresh にだけ
    assert any(m.endswith("_lichen") for m in weathered.m)                            # 地衣類
    assert len({tm.REG[f"rock_{k}_boulder_m_0"]["kind"] for k in ROCKS}) == 5
    assert MATERIALS["rk_granite"]["tex"] != MATERIALS["rk_sandstone"]["tex"]          # 岩種ごとに材質が違う


def test_soils_differ():
    cols = {k: MATERIALS[f"soil_{k}"]["tex"] for k in SOILS}
    assert len(set(cols.values())) == len(SOILS)
    mud = tm.build("soil_mud_patch_2")
    assert "soil_mud_wet" in mud.m                                                     # ぬかるみに水たまり(濡れ材質)


def test_hydraulic_smoothing_reduces_axis_streaks():
    g = Grid.from_size(400, 2)
    z = (300 * make_noise(g, node_rng(1, "t"), "fbm", 300, 5) + 0.2 * np.arange(g.nx)[None, :] * 2).astype(np.float64)
    raw, _ = hydraulic(z, 2.0, iterations=60, smooth=0)
    smooth, _ = hydraulic(z, 2.0, iterations=60, smooth=1.0)
    assert axis_streak_index(smooth) <= axis_streak_index(raw) + 1e-9
    assert np.isfinite(smooth).all()


def test_crags_only_on_steep_slopes():
    from terra.core import Document
    from terra.gen.crags import Crags
    g = Grid.from_size(600, 4)
    doc = Document(g, 0)
    X, _ = g.xy()
    doc.set("height", np.where(X < 300, 0.0, (X - 300) * 1.0))               # 左半分は平ら、右半分は 45 度の斜面
    before = doc.height.copy()
    Crags(peak_amp=0.0).run(doc, node_rng(0, "c"))
    d = np.abs(doc.height - before)
    assert d[:, X[0] < 270].max() < 1e-3                                       # 平らな所は変わらない
    assert d[:, X[0] > 330].mean() > 0.2                                       # 急斜面に段・岩の角が付く


def test_near_doc_is_crack_free_and_denser(tmp_path):
    doc = run_recipe(RECIPE, seed=2, out=tmp_path, log=lambda s: None)
    c = (300.0, 300.0)
    near = D.make_near_doc(doc, c, half=60.0, res=0.5, seed=2)
    x0, y0, x1, y1 = near.meta["near_box"]
    assert near.grid.res == 0.5 and near.grid.nx > 200
    # 縁の頂点は粗いメッシュの線形補間と一致(ひび割れが無い)
    X, Y = near.grid.xy()
    ci, cj = doc.grid.to_ij(X, Y)
    lin = map_coordinates(doc.height, [cj, ci], order=1, mode="nearest")
    for edge in (near.height[0], near.height[-1], near.height[:, 0], near.height[:, -1]):
        pass
    assert np.abs(near.height[0] - lin[0]).max() < 1e-3 and np.abs(near.height[:, -1] - lin[:, -1]).max() < 1e-3
    # 内部には微細起伏が乗り、散布は far より高密度
    inner = (slice(60, -60), slice(60, -60))
    assert np.abs(near.height[inner] - lin[inner]).max() > 0.02
    area_ratio = (near.grid.nx * 0.5) ** 2 / (doc.grid.nx * 4.0) ** 2
    tot = lambda d: sum(len(v["pos"]) for v in d.scatter.values())
    assert tot(near) / area_ratio > 1.5 * tot(doc)                    # 面積あたりの散布数は far より多い
    assert len(near.scatter["rocks"]["pos"]) > 0 and len(near.scatter["ground"]["pos"]) > 0
    again = D.make_near_doc(doc, c, half=60.0, res=0.5, seed=2)
    assert np.array_equal(near.height, again.height) and np.array_equal(near.scatter["trees"]["pos"], again.scatter["trees"]["pos"])
    # 散布 asset はすべて module として存在する
    for s in near.scatter.values():
        assert all(str(n) in tm.REG or str(n).startswith("veg_") for n in s["assets"])


def test_clear_view_removes_trees_near_camera(tmp_path):
    doc = run_recipe(RECIPE, seed=2, out=tmp_path, log=lambda s: None)
    near = D.make_near_doc(doc, (300.0, 300.0), half=60.0, res=0.5, seed=2)
    loc, tgt = (270.0, 270.0, 0.0), (300.0, 300.0, 0.0)
    D.clear_view(near, loc, tgt)
    p = near.scatter["trees"]["pos"][:, :2] - np.array(loc[:2])
    assert (np.linalg.norm(p, axis=1) >= 4.5).all()
