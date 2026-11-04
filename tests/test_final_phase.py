import random

from shapely.geometry import Point, Polygon, box

from tests.test_world import _cross
from vt import blocks, city, roads
from vt.modules.library import REG, get
from vt.world import Terrain


def test_tiler_covers_without_overlap():
    area = box(-900, -900, 900, 900)
    t = city.Tiler(area.bounds, 450)
    boxes = [t.box(i, j) for i, j in t.all()]
    assert abs(sum(b.area for b in boxes) - area.area) < 1e-6
    for k, b in enumerate(boxes):
        for c in boxes[k + 1:]:
            assert b.intersection(c).area < 1e-6
    assert t.idx(-900, -900) == (0, 0) and t.idx(899.9, 899.9) == (t.nx - 1, t.ny - 1)


def test_split_lot_conserves_area():
    rng = random.Random(1)
    poly = Polygon([(0, 0), (120, 0), (120, 80), (0, 80)])
    lots = blocks.split_lot(poly, rng, 600, 40)
    assert len(lots) >= 6
    assert abs(sum(p.area for p in lots) - poly.area) < 1.0


def _world():
    area = box(-300, -300, 300, 300)
    w = dict(area=area, land=area, zf=Terrain(flat=2.0), center=(0, 0))
    L = _cross()
    L.update(buildings=[], green=[], water=[], rail=[], landuse=[], stations=[], coastline=[])
    m, edges, info = roads.build_roads(L, w, dict(roads.CFG))
    w.update(T=w["zf"], L=L, info=info, edges=edges)
    return w


def test_infill_fills_blocks_without_touching_roads_and_is_deterministic():
    w = _world()
    a = blocks.infill(w, "infill", seed=3, log=lambda s: None)
    b = blocks.infill(w, "infill", seed=3, log=lambda s: None)
    assert len(a["features"]) >= 12
    assert [f.geom.wkt for f in a["features"]] == [f.geom.wkt for f in b["features"]]
    cw = w["info"]["cw"]
    for f in a["features"]:
        assert f.geom.intersection(cw).area < 0.5, f.id
    top = max(f.tags["_top"] for f in a["features"])
    assert top > 15


def test_vehicle_and_person_modules_build():
    names = [n for n, r in REG.items() if r["cat"] in ("車両", "人")]
    assert len(names) >= 40
    for n in names:
        assert get(n).f, n
