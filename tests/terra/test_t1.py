import numpy as np
from PIL import Image

from terra.core import Document, run_recipe
from terra.core.grid import Grid
from terra.gen.noise import make_noise
from terra.gen.stamp import paste
from terra.masks.terrain import band, slope_aspect
from terra.source._gsi_decode import read_tile
from terra.source.gsi_dem import lonlat_grid, tile_xy


def test_noise_deterministic_and_normalized():
    from terra.core import node_rng
    g = Grid.from_size(1000, 10)
    for kind in ("fbm", "ridged", "billow", "worley"):
        a = make_noise(g, node_rng(1, "n"), kind, 300, warp=0.3)
        b = make_noise(g, node_rng(1, "n"), kind, 300, warp=0.3)
        assert np.array_equal(a, b) and a.min() == 0 and abs(a.max() - 1) < 1e-6
        assert not np.array_equal(a, make_noise(g, node_rng(2, "n"), kind, 300, warp=0.3))


def test_recipe_same_seed_same_height_and_cache(tmp_path):
    r = {"grid": {"size_m": 400, "res_m": 4}, "steps": [{"gen.noise": {"base_height": 100}}, {"gen.shape": {"kind": "volcano", "radius_m": 150}}]}
    a = run_recipe(r, seed=3, out=tmp_path, log=lambda s: None)
    b = run_recipe(r, seed=3, out=tmp_path, log=lambda s: None)      # キャッシュ経由
    c = run_recipe(r, seed=4, out=tmp_path, log=lambda s: None)
    assert np.array_equal(a.height, b.height) and not np.array_equal(a.height, c.height)


def test_slope_aspect_plane():
    x = np.arange(50) * 2.0
    z = np.tile(x[None, :] * 0.5, (50, 1))       # 東へ上る 26.6 度の斜面
    s, asp = slope_aspect(z, 2.0)
    assert abs(s[25, 25] - np.degrees(np.arctan(0.5))) < 1e-3
    assert abs(asp[25, 25] - 270) < 1e-3          # 下りは西(270 度)


def test_band_and_stamp():
    assert band(np.array([0, 5, 10.0]), 4, 6)[1] == 1
    doc = Document(Grid.from_size(100, 1), 0)
    doc.set("height", np.zeros(doc.grid.shape))
    out = paste(doc, np.full((10, 10), 50.0), 40, (0.5, 0.5), blend_m=10)
    assert out[50, 50] == 50 and out[5, 5] == 0


def test_gsi_decode_and_projection(tmp_path):
    # 標高 123.45m = 12345 -> R=0,G=48,B=57 / 無効値 2^23 -> NaN
    a = np.zeros((256, 256, 3), np.uint8)
    a[..., 1], a[..., 2] = 48, 57
    a[0, 0] = (128, 0, 0)
    Image.fromarray(a).save(tmp_path / "t.png")
    h = read_tile(tmp_path / "t.png")
    assert abs(h[5, 5] - 123.45) < 1e-3 and np.isnan(h[0, 0])
    g = lonlat_grid((138.775, 35.385), 1000, 5)
    assert g.crs == "EPSG:32654" and g.nx == 200
    x, y = tile_xy(138.775, 35.385, 15)
    assert int(x) == 29015
