import numpy as np
import pytest
from shapely.geometry import LineString, MultiLineString, Point

from terra import modules as tm
from terra.core import Document, node_rng, run_recipe
from terra.core.grid import Grid
from terra.infra.earthwork import REACH
from terra.infra.furniture import Furniture
from terra.infra.road import RoadNode
from terra.masks.terrain import slope_aspect
from terra.scatter.nodes import exclusion


def make_doc(kind):
    """500m 角・4m 格子の合成地形。a=西(x=0.1)、b=東(x=0.9)。valley=中央に深さ 22m の谷+川 / ridge=中央に高さ 160m の尾根(全幅)で迂回不可 / slope=緩い斜面のみ"""
    g = Grid.from_size(500, 4)
    X, Y = g.xy()
    z = 600 + 0.06 * (X - 250) + 4 * np.sin(Y / 60.0) + (0.45 * (Y - 250) if kind == "side" else 0.0)      # side = 横断勾配 24 度の山腹
    river = np.zeros(g.shape, np.float32)
    if kind == "valley":
        z = z - 22 * np.exp(-(((X - 250) / 14.0) ** 2))
        river[(np.abs(X - 250) < 3)] = 4.0
    if kind == "ridge":
        z = z + 160 * np.exp(-(((X - 250) / 55.0) ** 2))
    d = Document(g, 1, dict(places={"a": [0.1, 0.5], "b": [0.9, 0.5]}, climate={}))
    d.set("height", z)
    d.set("slope", slope_aspect(d.height, 4.0)[0])
    d.set("river", river)
    d.set("water_depth", np.zeros(g.shape, np.float32))
    return d


def run(doc, **kw):
    RoadNode(connect=["a", "b"], **kw).run(doc, node_rng(1, "r"))
    return doc


def kinds(doc):
    return [pr["kind"] for _, pr in doc.vectors["roads"] + doc.vectors["tunnels"]]


@pytest.mark.parametrize("kind", ["slope", "valley"])
@pytest.mark.parametrize("gmax", [0.08, 0.10])
def test_grade_limit(kind, gmax):
    doc = run(make_doc(kind), max_grade=gmax)
    for ln, pr in doc.vectors["roads"] + doc.vectors["tunnels"]:
        P, z = np.asarray(ln.coords), np.asarray(pr["z"])
        g = np.abs(np.diff(z)) / np.hypot(*np.diff(P, axis=0).T)
        assert g.max() <= gmax * 1.02


def test_river_crossed_by_bridge():
    doc = run(make_doc("valley"))
    br = [ln for ln, pr in doc.vectors["roads"] if pr["kind"] == "bridge"]
    assert br, kinds(doc)
    river_x = 250.0
    assert any(min(np.asarray(b.coords)[:, 0]) < river_x < max(np.asarray(b.coords)[:, 0]) for b in br)      # 川を跨ぐ区間が橋
    z = np.asarray([pr for _, pr in doc.vectors["roads"] if pr["kind"] == "bridge"][0]["z"])
    assert z.max() > 0


def test_ridge_needs_tunnel_with_cover():
    doc = run(make_doc("ridge"))
    assert doc.vectors["tunnels"], kinds(doc)
    ln, pr = doc.vectors["tunnels"][0]
    P, zr = np.asarray(ln.coords), np.asarray(pr["z"])
    zt = (doc.height - doc.layers["cutfill"])
    from terra.core.grid import Heightfield
    cover = Heightfield(doc.grid, zt).sample(P[:, 0], P[:, 1]) - zr
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    assert cover[(s > 25) & (s < s[-1] - 25)].min() >= 9.5                    # 坑口付近を除き土被り >= 10m
    assert len(doc.vectors["portals"]) == 2
    with pytest.raises(RuntimeError):
        run(make_doc("ridge"), allow_tunnel=False)                              # トンネル無しでは越えられない


def test_earthwork_continuity_and_platform():
    doc = make_doc("side")
    z0 = doc.height.copy()
    run(doc)
    cf = doc.layers["cutfill"]
    assert abs(cf).max() > 1.0 and doc.layers["road"].sum() > 20
    # 路盤は路面高に一致し、影響範囲の外は不変
    for ln, pr in doc.vectors["roads"]:
        if pr["kind"] != "road":
            continue
        P, z = np.asarray(ln.coords), np.asarray(pr["z"])
        from terra.core.grid import Heightfield
        h = Heightfield(doc.grid, doc.height).sample(P[:, 0], P[:, 1])
        assert np.abs(h - z).max() < 0.35
    X, Y = doc.grid.xy()
    line = MultiLineString([ln for ln, pr in doc.vectors["roads"] + doc.vectors["tunnels"]])
    far = np.array([line.distance(Point(x, y)) > REACH + 6 for x, y in zip(X[::6, ::6].ravel(), Y[::6, ::6].ravel())]).reshape(X[::6, ::6].shape)
    assert np.abs(cf[::6, ::6][far]).max() == 0
    # 隣接セルの高さ差は急な法面でも有限(連続)
    assert np.abs(np.diff(doc.height, axis=1)).max() < 12.0 and np.abs(np.diff(z0, axis=1)).max() < 12.0


RECIPE = {"grid": {"size_m": 600, "res_m": 4}, "climate": {"lat": 36.0, "sea_level_temp_c": 15}, "places": {"a": [0.15, 0.2], "b": [0.85, 0.8]},
          "steps": [{"gen.noise": {"base_height": 120, "wavelength_m": 400, "offset": 700}}, {"erosion.fluvial": {"iterations": 4, "k": 0.01}},
                    {"masks.slope": {}}, {"hydro.flow": {}}, {"hydro.rivers": {"min_area_km2": 0.004}},
                    {"infra.road": {"connect": ["a", "b"]}}, {"masks.slope": {}}, {"hydro.flow": {}}, {"biome.jp_forest": {}}, {"geology.zones": {}},
                    {"scatter.trees": {"r_m": 5}}, {"scatter.shrubs": {}}, {"scatter.rocks": {}}, {"scatter.ground": {}}, {"infra.furniture": {}}]}


def test_scatter_excludes_road_and_is_deterministic(tmp_path):
    a = run_recipe(RECIPE, seed=3, out=tmp_path, log=lambda s: None)
    b = run_recipe(RECIPE, seed=3, cache=False, log=lambda s: None)
    assert np.array_equal(a.height, b.height) and [ln.wkt for ln, _ in a.vectors["roads"]] == [ln.wkt for ln, _ in b.vectors["roads"]]
    assert np.array_equal(a.scatter["trees"]["pos"], b.scatter["trees"]["pos"])
    roads = MultiLineString([ln for ln, pr in a.vectors["roads"]])
    for k in ("trees", "shrubs", "rocks", "ground"):
        pos = a.scatter[k]["pos"]
        d = np.array([roads.distance(Point(x, y)) for x, y, _ in pos[::7]])
        assert d.min() > 8.0, (k, d.min())                                       # 伐採帯(clear_width 22m の半分 = 11m から外)ほぼ守られる
    ex = exclusion(a, ["road"])
    ii = np.clip(((a.scatter["trees"]["pos"][:, 0] - a.grid.x0) / 4).astype(int), 0, a.grid.nx - 1)
    jj = np.clip(((a.scatter["trees"]["pos"][:, 1] - a.grid.y0) / 4).astype(int), 0, a.grid.ny - 1)
    assert not ex[jj, ii].any()
    fu = a.scatter["road_furniture"]
    assert all(str(n) in tm.REG for n in fu["assets"])


def test_road_modules_near_far():
    for n in ("road_guardrail_4m", "road_retwall_4m", "road_rocknet_8m", "road_curve_mirror", "tunnel_portal_0", "bridge_deck_8m", "bridge_pier_16"):
        assert len(tm.build(n).f) >= len(tm.build(n + "_far").f) > 0
    assert len(tm.build("bridge_deck_8m").f) > len(tm.build("bridge_deck_8m_far").f)
    _ = (LineString, Furniture)
