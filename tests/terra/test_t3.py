import numpy as np
from pxr import Usd, UsdGeom
from scipy.spatial import cKDTree

from terra import modules as tm
from terra.biome.jp_forest import CONIFER, DECIDUOUS, EVERGREEN, classify
from terra.core import node_rng, run_recipe
from terra.core.grid import Grid
from terra.export.usd import export_usd
from terra.scatter.nodes import exclusion
from terra.scatter.poisson import bridson

RECIPE = {"grid": {"size_m": 400, "res_m": 4}, "climate": {"lat": 36.0, "sea_level_temp_c": 15},
          "steps": [{"gen.noise": {"base_height": 900, "wavelength_m": 500, "offset": 500}}, {"erosion.fluvial": {"iterations": 4, "k": 0.01}},
                    {"masks.slope": {}}, {"hydro.flow": {}}, {"hydro.rivers": {"min_area_km2": 0.004}},
                    {"biome.jp_forest": {}}, {"scatter.trees": {"r_m": 5}}, {"scatter.shrubs": {}}, {"scatter.rocks": {}}]}


def test_poisson_min_distance_and_determinism():
    a = bridson(200.0, 150.0, 4.0, 24, 1)
    assert np.array_equal(a, bridson(200.0, 150.0, 4.0, 24, 1))
    d, _ = cKDTree(a).query(a, k=2)
    assert d[:, 1].min() >= 4.0 - 1e-9 and len(a) > 1000


def test_biome_zones_ordered_by_altitude():
    z = np.tile(np.linspace(0, 3200, 200)[None, :], (4, 1))
    s, t, asp = np.full(z.shape, 20.0), np.full(z.shape, 6.0), np.full(z.shape, 180.0)
    cls, lim = classify(z, s, asp, t, {"lat": 36, "sea_level_temp_c": 15}, node_rng(0, "b"), Grid(200, 4, 10.0))
    row = cls[0]
    assert row[0] == EVERGREEN and row[np.argmin(abs(z[0] - 1000))] == DECIDUOUS and row[np.argmin(abs(z[0] - 2000))] == CONIFER
    warm = classify(z, s, asp, t, {"lat": 36, "sea_level_temp_c": 20}, node_rng(0, "b"), Grid(200, 4, 10.0))[1]
    assert (warm > lim).all()                                   # 温暖なほど植生帯は高い所へ


def test_scatter_respects_exclusion_and_is_deterministic(tmp_path):
    a = run_recipe(RECIPE, seed=5, out=tmp_path, log=lambda s: None)
    b = run_recipe(RECIPE, seed=5, out=tmp_path, cache=False, log=lambda s: None)
    t = a.scatter["trees"]
    assert len(t["pos"]) > 100 and np.array_equal(t["pos"], b.scatter["trees"]["pos"])
    ex = exclusion(a, ["river", "lake"])
    g = a.grid
    ii = np.clip(((t["pos"][:, 0] - g.x0) / g.res).astype(int), 0, g.nx - 1)
    jj = np.clip(((t["pos"][:, 1] - g.y0) / g.res).astype(int), 0, g.ny - 1)
    assert not ex[jj, ii].any()                                 # 川・湖の上に木が無い
    hz = a.heightfield().sample(t["pos"][:, 0], t["pos"][:, 1])
    assert np.abs(t["pos"][:, 2] - hz).max() < 0.1              # 地面に接地


def test_rock_modules_and_usd_export(tmp_path):
    for n in ("rock_boulder_m_0", "rock_cliff_1", "rock_outcrop_0", "rock_scree_0", "rock_pebble_0"):
        m = tm.build(n)
        assert len(m.f) > 100 and set(m.m) <= {"rock_granite", "rock_dark", "rock_warm", "rock_pebble"}
    doc = run_recipe(RECIPE, seed=5, out=tmp_path, log=lambda s: None)
    p = export_usd(doc, tmp_path)[0]
    st = Usd.Stage.Open(str(p))
    n = sum(len(UsdGeom.PointInstancer(pr).GetProtoIndicesAttr().Get()) for pr in st.Traverse() if pr.IsA(UsdGeom.PointInstancer))
    assert n == sum(len(s["pos"]) for s in doc.scatter.values())
    assert any(pr.GetName().startswith("tile_") for pr in st.Traverse())
