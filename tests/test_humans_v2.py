import random

import numpy as np
import pytest

from vt import humans as H
from vt import humans_motion as HM
from vt import humans_wear as W
from vt.modules import lib_anny

PK_OK = (H.PK / "shirts01").exists() and (H.PK / "skirts01").exists()
needs_pk = pytest.mark.skipif(not PK_OK, reason="data/humans/pk(MakeHuman asset pack)が無い")


def test_population_size_and_groups():
    assert len(lib_anny.ALL) >= 100
    assert set(lib_anny.GROUPS) >= {"office", "casual", "elder", "student", "kid", "heavy", "worker"}


def test_clips_committed():
    need = {"walk", "walk_slow", "run", "idle", "idle_hands", "idle_phone", "sit", "bike", "talk", "wave", "carry"}
    assert need <= set(HM.names())
    Q, T = HM.load("walk")
    assert Q.shape[1:] == (53, 4) and len(Q) >= 20 and np.allclose(np.linalg.norm(Q, axis=-1), 1, atol=1e-2)


def test_walk_moves_legs_and_idle_does_not():
    L = HM.H.model("anny").bone_labels
    i = L.index("thigh_l")
    from scipy.spatial.transform import Rotation as R
    ang = lambda name: np.ptp(R.from_quat(HM.load(name)[0][:, i]).as_euler("xyz", degrees=True)[:, 0])
    assert ang("walk") > 20 and ang("idle") < 8


def test_phase_offsets_differ():
    ps = {lib_anny.pose_of("casual", k)[1] for k in range(20)}
    assert len(ps) == 20


def test_roles_cover_city_uses():
    for role in ("walk", "wait", "park"):
        assert len(lib_anny.by_role(role)) >= 15, role


@needs_pk
def test_wardrobe_variety_and_licenses():
    seen, lic = set(), set()
    for g, n in lib_anny.GROUPS.items():
        for k in range(n):
            sp = lib_anny.spec_of(g, k)
            of = H.outfit(sp, random.Random(sp["seed"] * 31 + 5))
            for kind, slot, arg, color, margin in of["pieces"]:
                seen.add(slot)
                if kind == "mh":
                    lic.add(H.load_mhclo(H._find(*arg))["license"])
    assert {"skirt" if False else "bottom", "dress", "suit", "jacket", "coat", "blazer", "coverall", "hat", "mask", "backpack", "umbrella", "bag", "helmet"} <= seen
    assert lic <= {"CC0", "CC BY 4.0"}


@needs_pk
def test_garment_covers_torso_and_arms():
    sp = H.sample(3, "casual", female=False)
    r = H.run(sp["p"], "anny")
    g = W.garment(r, "jacket", 0.52, "long", margin=0.03)
    z = g["Vrest"][:, 2]
    zf = (z - r["rest_vertices"][:, 2].min()) / (r["rest_vertices"][:, 2].max() - r["rest_vertices"][:, 2].min())
    assert len(g["cl"]["faces"]) > 800 and zf.min() > 0.45 and zf.max() > 0.8


def test_decimate_reduces_and_keeps_triangles():
    g = np.mgrid[0:20, 0:20].reshape(2, -1).T * 0.004
    V = np.c_[g, np.zeros(len(g))]
    F = [[i * 20 + j, i * 20 + j + 1, (i + 1) * 20 + j + 1, (i + 1) * 20 + j] for i in range(19) for j in range(19)]
    V2, T = H.decimate(V, F, 0.012)
    assert len(V2) < len(V) / 4 and all(len(set(t)) == 3 for t in T)


@needs_pk
def test_module_has_face_decals_and_no_holes_material():
    from vt.modules.library import get
    from vt.materials import MATERIALS
    m = get(lib_anny.NAMES["casual"][2])
    mats = set(m.m)
    assert "anny_face" in mats and any(x.startswith("anny_brow_") for x in mats) and mats <= set(MATERIALS)
    assert len(m.f) < 30000


def test_fabric_and_decal_assets_exist():
    from vt import textures_human as TX
    from vt.materials import MATERIALS
    for f in TX.FABRICS:
        assert (TX.TEX / f"fabric_{f}.png").exists() and "anny_cl_navy_" + f in MATERIALS
    for n in ("print_atlas.png", "detail_atlas.png", "face_atlas.png", "stubble.png"):
        assert (TX.TEX / n).exists()
    assert (TX.TEX / "face_atlas.png").stat().st_size < 400_000


def test_face_uv_inside_atlas_and_distinct():
    from vt import textures_human as TX
    seen = set()
    for kind, n in (("eye", 4), ("brow", 4), ("lips", 4), ("blush", 4), ("wrinkle", 3)):
        for i in range(n):
            u0, v0, u1, v1 = TX.face_uv(kind, i)
            assert 0 <= u0 < u1 <= 1 and 0 <= v0 < v1 <= 1
            seen.add((u0, v0))
    assert len(seen) == 19


@needs_pk
def test_hair_and_beard_variety():
    kinds, beards, colors, shoes = set(), set(), set(), set()
    for g, n in lib_anny.GROUPS.items():
        for k in range(n):
            sp = lib_anny.spec_of(g, k)
            of = H.outfit(sp, random.Random(sp["seed"] * 31 + 5))
            kinds.add(of["hair_kind"]); beards.add(of["beard"]); colors.add(of["hair_color"]); shoes.add(of["shoe_type"])
    assert {"card", "buzz", "pony"} <= kinds and {"stubble", "beard"} & beards and len(colors) >= 6 and len(shoes) >= 3


@needs_pk
def test_decals_and_shoes_in_module():
    from vt.modules.library import get
    from collections import Counter
    c = Counter()
    for n in lib_anny.NAMES["casual"][:14] + lib_anny.NAMES["student"][:4]:
        c.update(get(n).m)
    assert c["anny_print"] > 0 and c["anny_detail"] > 0
    assert any(k.startswith("anny_sole_") for k in c) and any(k.startswith("anny_lace_") for k in c)
