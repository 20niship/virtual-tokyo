"""T0〜T4 残課題の修正(キャッシュのコードハッシュ・最小曲線半径・切土法尻・側溝/集落 ほか)のテスト"""
import numpy as np

from terra.core import node_rng, pipeline, run_recipe
from terra.infra.road import chaikin, curvature_stats, limit_curvature

from test_t4 import make_doc, run


def test_cache_invalidated_by_code_hash(tmp_path, monkeypatch):
    r = {"grid": {"size_m": 200, "res_m": 4}, "steps": [{"gen.noise": {"base_height": 100}}]}
    logs = []
    run_recipe(r, seed=1, out=tmp_path, log=logs.append)
    run_recipe(r, seed=1, out=tmp_path, log=logs.append)
    assert " run " in logs[0] and "cache" in logs[1]
    monkeypatch.setattr(pipeline, "code_hash", lambda cls: "changed")       # ノード実装のコードが変わった
    run_recipe(r, seed=1, out=tmp_path, log=logs.append)
    assert " run " in logs[2]


def test_limit_curvature_opens_hairpin():
    c = chaikin(np.array([[0, 0], [40, 0], [40, 6], [0, 6], [0, 12], [40, 12]], float), 4)
    assert 1 / curvature_stats(c).max() < 8
    q = limit_curvature(c, 15.0)
    assert 1 / curvature_stats(q).max() >= 14.0
    assert np.allclose(q[0], c[0]) and np.allclose(q[-1], c[-1])


def test_road_min_radius_param():
    for R in (15.0, 25.0):
        doc = run(make_doc("side"), min_radius=R)
        st = doc.vectors["road_stats"][0][1]
        assert st["min_radius_m"] >= R * 0.9, st


def _toe_roughness(doc):
    z = doc.height.astype(np.float64)
    return float(np.abs(np.diff(z, 2, axis=1)).sum() + np.abs(np.diff(z, 2, axis=0)).sum())


def test_toe_rounding_smooths_slope(monkeypatch):
    from terra.infra import earthwork
    a = _toe_roughness(run(make_doc("side")))
    monkeypatch.setattr(earthwork, "_round_toe", lambda new, *r: new)
    b = _toe_roughness(run(make_doc("side")))
    assert a < b                                  # 丸めた方が法尻・法肩の折れ(2 階差分の総和)が小さい


def test_tunnel_interior_and_portals():
    from terra import modules as tm
    from terra.infra.furniture import Furniture
    doc = run(make_doc("ridge"))
    Furniture().run(doc, node_rng(1, "f"))
    s = doc.scatter["road_furniture"]
    names = [str(n) for n in s["assets"]]
    kinds = [names[k] for k in s["kind"]]
    ln, pr = doc.vectors["tunnels"][0]
    n_in = kinds.count("tunnel_inner_8m")
    assert n_in >= int((pr["length"] - 2 * 16.0) / 8.0) - 1               # 坑口の間を 8m ごとに埋める
    assert kinds.count("tunnel_portal_0") + kinds.count("tunnel_portal_1") + kinds.count("tunnel_portal_2") == 2
    P = np.asarray(ln.coords)                                                # 坑口はトンネル端から切り通しの分だけ奥に立つ
    pp = s["pos"][[i for i, k in enumerate(kinds) if k.startswith("tunnel_portal")]][:, :2]
    assert all(np.hypot(*(q - P[0])).item() > 10 or np.hypot(*(q - P[-1])).item() > 10 for q in pp)
    assert len(tm.build("tunnel_inner_8m").f) > 5 * len(tm.build("tunnel_inner_8m_far").f)        # near は内部を作り、far は省略


def test_ditch_on_cut_side_only():
    from terra.infra.furniture import Furniture
    doc = run(make_doc("side"))
    Furniture().run(doc, node_rng(1, "f"))
    s = doc.scatter["road_furniture"]
    names = [str(n) for n in s["assets"]]
    hf = doc.heightfield()
    ditch = [i for i, k in enumerate(s["kind"]) if names[k].startswith("road_ditch")]
    assert ditch                                                                  # 山腹の道路には側溝がある
    for i in ditch:
        x, y, z = s["pos"][i]
        yaw = float(s["yaw"][i])
        out = np.array([np.cos(yaw), np.sin(yaw)])                                  # module の +x(外側)
        assert hf.sample(np.array([x + out[0] * 4.0]), np.array([y + out[1] * 4.0]))[0] > z - 0.5     # 外側の地面は路面より高い(切土側)


def test_village_placement_and_exclusion():
    from shapely.geometry import MultiLineString
    from terra.infra.village import VillageNode
    from terra.scatter.nodes import exclusion
    doc = run(make_doc("slope"))
    VillageNode(houses=6, fields=2).run(doc, node_rng(1, "v"))
    v = doc.scatter["village"]
    assert len(v["yaw"]) >= 2
    roads = MultiLineString([ln for ln, _ in doc.vectors["roads"] + doc.vectors["tunnels"]])
    from shapely.geometry import Point
    for x, y, z in v["pos"]:
        assert roads.distance(Point(x, y)) >= 8.0                                   # 道路の上に建たない
    h = doc.heightfield()
    for (x, y, z), a in zip(v["pos"], v["kind"]):
        assert abs(h.sample(np.array([x]), np.array([y]))[0] - z) < 0.5              # 整地した地面に接地
    assert doc.vectors["lanes"] and all(pr["width"] > 2 for _, pr in doc.vectors["lanes"])
    ex = exclusion(doc, ["village_pads"], 0.0)
    g = doc.grid
    x, y, _ = v["pos"][0]
    assert ex[int((y - g.y0) / g.res), int((x - g.x0) / g.res)]                       # 敷地は散布の除外領域


def test_conifer_atlas():
    from terra import modules as tm
    for sp in ("sugi", "hinoki", "shirabiso", "karamatsu"):
        mats = set(tm.build(f"terra_{sp}_s").m)
        assert "conifer_atlas" in mats and "leaf_atlas" not in mats                   # 広葉の葉アトラスを使わない
    from PIL import Image
    a = np.asarray(Image.open("assets/terra/textures/conifer_atlas.png"))
    import json
    for nm, c in json.load(open("assets/terra/textures/conifer_atlas.json"))["cards"].items():
        x, y, w, h = c["rect"]
        assert (a[y:y + h, x:x + w, 3] > 128).mean() > 0.1, nm                         # 各カードに葉がある
