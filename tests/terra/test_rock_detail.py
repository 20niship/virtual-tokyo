import numpy as np

from terra import modules as tm
from terra.core import run_recipe
from vt.materials import MATERIALS

COAST = {"grid": {"size_m": 400, "res_m": 2}, "climate": {"lat": 33.0, "sea_level_temp_c": 17},
         "steps": [{"gen.noise": {"base_height": 30, "wavelength_m": 200, "offset": 10}},
                   {"gen.sea_cliff": {"sea_dir_deg": 180, "cliff_height": 22}}, {"masks.slope": {}}, {"hydro.flow": {}},
                   {"biome.jp_forest": {}}, {"geology.zones": {}}, {"scatter.trees": {"r_m": 6}}, {"scatter.rocks": {}}]}


def _normals_z(m):
    V, F = np.array(m.v, float), np.array([f[:3] for f in m.f])
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    vol = (V[F].mean(1) * n).sum()                                      # 閉曲面の符号付き体積(発散定理)で巻き方向を判定し外向きに揃える
    return (n[:, 2] if vol > 0 else -n[:, 2]), V


def test_crag_modules_lod_and_determinism():
    for n in ("rock_seacliff_seacliff_1", "rock_peakrock_spire_1", "rock_granite_spire_2"):
        far, near = tm.build(n + "_far"), tm.build(n)
        assert 0 < len(far.f) < len(near.f)
        assert np.isfinite(np.array(near.v)).all() and set(near.m) <= set(MATERIALS) and set(far.m) <= set(MATERIALS)
        assert len(set(near.m)) >= 5                                    # 層ごとの濃淡・雨筋・地衣類などで材質が分かれる
    a, b = tm.build("rock_seacliff_seacliff_0_far"), tm.build("rock_seacliff_seacliff_0_far")
    assert np.array_equal(np.array(a.v), np.array(b.v)) and a.m == b.m


def test_seacliff_has_ledges_and_sheer_walls():
    """層理の棚(水平に近い面)と垂直に近い壁が両方ある。滑らかな塊より垂直面の割合が大きい"""
    nz, V = _normals_z(tm.build("rock_seacliff_seacliff_1"))
    assert (np.abs(nz) > 0.85).mean() > 0.04                            # 棚・頂部
    assert (np.abs(nz) < 0.35).mean() > 0.25                            # 壁
    blob = _normals_z(tm.build("rock_granite_boulder_m_1"))[0]
    assert (np.abs(nz) < 0.35).mean() > (np.abs(blob) < 0.35).mean()
    assert V[:, 2].max() > 8 and V[:, 2].min() < 0                      # 高さ 10m 前後・水面下まで


def test_spire_has_lichen_on_top():
    m = tm.build("rock_peakrock_spire_1")
    nz, _ = _normals_z(m)
    lich = np.array([("lich" in x) for x in m.m])
    assert lich[nz > 0.5].mean() > 1.5 * lich[nz < -0.2].mean() > 0     # 地衣類は上向きの面に優先して付く


def test_crags_strata_and_joints():
    def run(p):
        r = {"grid": {"size_m": 600, "res_m": 4}, "steps": [{"gen.noise": {"base_height": 700, "wavelength_m": 400, "offset": 500}}, {"gen.crags": p}]}
        return run_recipe(r, seed=2, out=None, log=lambda s: None).height
    z0, z1, z2 = run({"hardness_var": 0, "joint_m": 0}), run({"hardness_var": 0.8, "joint_m": 0}), run({"hardness_var": 0.8, "joint_m": 12, "joint_amp": 1.5})
    assert np.array_equal(z1, run({"hardness_var": 0.8, "joint_m": 0}))   # 決定性
    assert np.abs(z1 - z0).max() > 0.2 and np.abs(z2 - z1).max() > 0.3
    lap = lambda z: np.abs(z[1:-1, 1:-1] * 4 - z[:-2, 1:-1] - z[2:, 1:-1] - z[1:-1, :-2] - z[1:-1, 2:]).mean()
    assert lap(z2) > lap(z1)                                            # 節理のブロックで細かい凹凸が増える


def test_sea_cliff_coast(tmp_path):
    doc = run_recipe(COAST, seed=3, out=tmp_path, log=lambda s: None)
    z, sl = doc.height, doc.meta["sea_level"]
    sea, cliff, plat = doc.layers["sea"] > 0, doc.layers["coast_cliff"] > 0, doc.layers["wave_platform"] > 0
    assert sea.mean() > 0.1 and cliff.any() and plat.any()
    assert z[~sea & ~plat & ~cliff].min() > sl and z.max() > sl + 15      # 内陸は海面より上の台地
    assert doc.layers["slope"][cliff].mean() > 30                       # 崖は急
    assert np.median(z[plat]) < sl + 1.6 and np.percentile(z[plat], 95) < sl + 4.0   # 波食棚は海面近くの平らな岩盤
    if len(doc.scatter["trees"]["pos"]):
        assert (doc.scatter["trees"]["pos"][:, 2] > sl + 1).all()         # 木は海・波食棚に立たない
    names = {str(a) for a in doc.scatter["rocks"]["assets"]}
    assert any("seacliff" in n for n in names) and any("seashore_boulder" in n for n in names)
