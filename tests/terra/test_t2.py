import numpy as np

from terra.core import node_rng
from terra.erosion.hydraulic import hydraulic
from terra.erosion.thermal import thermal
from terra.gen.noise import make_noise
from terra.core.grid import Grid
from terra.hydro.flow import flow
from terra.hydro.rivers import lakes, river_lines


def _terrain(n=160, res=5.0, seed=3):
    g = Grid.from_size(n * res, res)
    z = 300 * make_noise(g, node_rng(seed, "t"), "fbm", 400, 5) + 0.15 * np.arange(n)[None, :] * res
    return g, z.astype(np.float64)


def test_flow_conservation_and_monotone():
    g, z = _terrain()
    filled, rcv, area = flow(z, g.res)
    assert (filled >= z - 1e-9).all()
    r = rcv.ravel()
    f = filled.ravel()
    ok = r >= 0
    assert (f[ok] > f[r[ok]]).all()                     # 全セルが厳密に下流へ下る
    outlets = ~ok
    assert abs(area.ravel()[outlets].sum() - z.size * g.res ** 2) < 1e-6   # 出口の流量の合計 = 全面積(保存)
    assert area.min() >= g.res ** 2
    # どのセルからも出口(境界)へ到達する
    c = np.arange(z.size)
    for _ in range(z.size):
        n = np.where(r[c] >= 0, r[c], c)
        if (n == c).all():
            break
        c = n
    assert outlets[c].all()


def test_rivers_descend_and_connect():
    g, z = _terrain()
    filled, rcv, area = flow(z, g.res)
    lines, wmap = river_lines(area, rcv, g, filled, min_area_m2=2e4)
    assert len(lines) > 3
    for ln, p in lines:
        assert p["z_top"] >= p["z_bot"]                  # 折れ線の始点から終点へ標高が下る
    # 川の最下流の終点は領域の境界か別の川の中
    ends = [np.asarray(ln.coords)[-1] for ln, _ in lines]
    x1, y1 = g.nx * g.res, g.ny * g.res
    from shapely.geometry import MultiLineString, Point
    net = MultiLineString([ln for ln, _ in lines])
    for e in ends:
        on_edge = e[0] < g.res * 1.6 or e[1] < g.res * 1.6 or e[0] > x1 - g.res * 1.6 or e[1] > y1 - g.res * 1.6
        assert on_edge or net.distance(Point(e)) < 1e-6 or net.distance(Point(e)) < g.res


def test_lakes_fill_depressions():
    z = np.full((40, 40), 10.0)
    z[15:25, 15:25] = 5.0                                  # 深さ 5m の窪地
    filled, rcv, area = flow(z, 1.0)
    lab, wd, info = lakes(z, filled, 1.0, min_depth=2, min_area_m2=50)
    assert lab.max() == 1 and abs(wd.max() - 5) < 1e-3 and (lab > 0).sum() == 100


def test_erosion_stable_and_deterministic():
    g, z = _terrain(96, 4.0)
    a, dz = hydraulic(z, g.res, iterations=30)
    b, _ = hydraulic(z, g.res, iterations=30)
    assert np.array_equal(a, b) and np.isfinite(a).all()
    assert np.abs(dz).max() < 5 and dz.min() < 0
    t = thermal(z, g.res, talus_deg=20, iterations=20)
    assert abs(t.sum() - z.sum()) / z.sum() < 1e-6          # 質量保存
    gy, gx = np.gradient(t, g.res)
    gy0, gx0 = np.gradient(z, g.res)
    assert np.hypot(gx, gy).max() <= np.hypot(gx0, gy0).max()
