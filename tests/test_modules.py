from vt.materials import MATERIALS
from vt.modules.geom import Mesh, _newell
from vt.modules.library import REG, get


def test_all_modules_build_and_use_known_materials():
    assert len(REG) >= 90
    for n in REG:
        m = get(n)
        assert m.f, n
        assert set(m.m) <= set(MATERIALS), (n, set(m.m) - set(MATERIALS))


def test_bbox_normals_outward():
    m = Mesh(); m.bbox(0, 0, 0, 1, 1, 1, "x", 0.1)
    c = (0.5, 0.5, 0.5)
    for f in m.f:
        p = [m.v[i] for i in f]
        n = _newell(p); cen = [sum(q[i] for q in p) / len(p) for i in range(3)]
        assert sum(n[i] * (cen[i] - c[i]) for i in range(3)) > 0


def test_ring_front_faces_plus_y():
    m = Mesh(); m.ring((0, 4, 0, 3), (1, 3, 1, 2), -0.25, 0.0, "x", 0.01, 0.01)
    fronts = [f for f in m.f if all(abs(m.v[i][1]) < 1e-9 for i in f)]
    assert fronts and all(_newell([m.v[i] for i in f])[1] > 0 for f in fronts)


def test_assemble_and_usd(tmp_path):
    from vt.assemble import build_building
    from vt.layers import Feature, load
    from shapely.geometry import Polygon
    f = Feature(1, Polygon([(0, 0), (20, 0), (20, 12), (0, 12)]), {"building": "apartments", "_top": 25.0, "_min": 0.0})
    b = build_building(f)
    assert b and len(b.insts) > 100 and {i.name for i in b.insts} <= set(REG)
    from vt import usd_out
    p = usd_out.write_buildings([b], tmp_path / "b.usda")
    from pxr import Usd
    assert Usd.Stage.Open(str(p)).GetPrimAtPath(f"/City/Buildings/b1/Modules")
