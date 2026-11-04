import numpy as np
import pytest
from PIL import Image

bpy = pytest.importorskip("bpy")

from vt import render  # noqa: E402
from vt.materials import MATERIALS  # noqa: E402


def test_grime_texture():
    from vt.textures import OUT
    a = np.asarray(Image.open(OUT / "wall_grime.png"))
    assert a.shape == (1024, 1024, 3) and a.std() > 20


@pytest.mark.parametrize("time", ["day", "dusk", "night"])
def test_realism_materials_build(time):
    render.init_scene((64, 36), 1, time=time, realism=True)
    for mid in ("glass_main", "interior", "water", "tile_main", "brick_main", "stone_main", "alc", "paint_main", "led_white"):
        assert render.get_material(mid).use_nodes
    assert bpy.context.scene.compositing_node_group is not None


def test_estimate_exposure_range():
    render.init_scene((64, 36), 4, realism=True)
    render.add_plane(200, 0.0, "ground")
    render.add_camera((0, -30, 10), (0, 0, 0), 35)
    ev = render.estimate_exposure()
    assert -3.6 <= ev <= 1.2


def test_joint_materials_have_size():
    for mid, d in MATERIALS.items():
        if "joint" in d:
            assert d["joint"]["w"] > 0 and d["joint"]["h"] > 0
