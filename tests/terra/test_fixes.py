"""T0〜T4 残課題の修正(キャッシュのコードハッシュ・最小曲線半径・切土法尻・側溝/集落 ほか)のテスト"""
import numpy as np

from terra.core import pipeline, run_recipe
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
