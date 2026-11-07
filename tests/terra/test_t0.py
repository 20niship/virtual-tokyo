import hashlib

from terra.cli import main
from terra.core import node_rng


def _h(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_empty_recipe_deterministic(tmp_path):
    outs = []
    for i in range(2):
        o = tmp_path / f"o{i}"
        main(["generate", "recipes/terra/empty.yaml", "--out", str(o), "--seed", "7", "--no-cache"])
        main(["export", str(o), "--geotiff", "--heightmap", "both"])
        outs.append(o)
    for f in ("height.tif", "height.r16", "height.png"):
        assert _h(outs[0] / f) == _h(outs[1] / f)


def test_rng_stable_and_independent():
    assert node_rng(1, "a").random() == node_rng(1, "a").random()
    assert node_rng(1, "a").random() != node_rng(1, "b").random()
