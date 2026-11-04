import pytest

from vt import humans as H
from vt.materials import MATERIALS
from vt.modules import lib_anny

PK_OK = (H.PK / "shirts01").exists() and (H.PK / "hair01").exists()
pytestmark = pytest.mark.skipif(not PK_OK, reason="data/humans/pk(MakeHuman asset pack)が無い")


def test_age_param_monotonic():
    ys = [H.age_param(a) for a in (1, 6, 14, 25, 50, 80)]
    assert ys == sorted(ys) and ys[3] == pytest.approx(0.5)


def test_sample_height_matches_target():
    s = H.sample(1, "office", female=False)
    assert abs(H.height_of(s["p"]) - s["cm"]) < 2.5


def test_kid_shorter_than_adult():
    k, a = H.sample(3, "kid"), H.sample(3, "casual")
    assert H.height_of(k["p"]) < H.height_of(a["p"]) - 20


def test_cloth_licenses_allowed():
    for g in lib_anny.GROUPS:
        for k in range(lib_anny.GROUPS[g]):
            of = H.outfit(lib_anny.spec_of(g, k), __import__("random").Random(1))
            for pack, sub, key in (("shirts01", "clothes", "top"), ("pants01", "clothes", "bottom"), ("hair01", "hair", "hair")):
                assert H.load_mhclo(H._find(pack, sub, of[key]))["license"] in ("CC0", "CC BY 4.0"), of[key]


def test_module_mesh_and_materials():
    from vt.modules.library import get
    for n in (lib_anny.NAMES["office"][0], lib_anny.NAMES["kid"][0]):
        m = get(n)
        assert len(m.f) > 2000 and set(m.m) <= set(MATERIALS), n
        zs = [v[2] for v in m.v]
        assert -0.02 < min(zs) < 0.02 and 0.9 < max(zs) < 2.0


def test_hero_usd_has_skeleton(tmp_path):
    from pxr import Usd, UsdSkel
    from vt import humans_usd as U
    p = U.write_hero(H.sample(5, "casual"), tmp_path / "h.usdc")
    st = Usd.Stage.Open(str(p))
    skels = [UsdSkel.Skeleton(x) for x in st.Traverse() if x.IsA(UsdSkel.Skeleton)]
    assert len(skels) == 1 and len(skels[0].GetJointsAttr().Get()) == 53
    assert any(x.GetName() == "WalkAnim" for x in st.Traverse())
