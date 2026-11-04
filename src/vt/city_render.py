"""全シーンの検証レンダ: 地面視点(目線高1.65m)と空中視点を自動選定し、カメラ周辺だけをBlenderへ読み込んで描画する。"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw
from shapely.geometry import Point
from shapely.ops import unary_union

from . import ground, render
from .city import split_insts, split_mesh

OUT = Path(__file__).resolve().parents[2] / "out/render/final"
EYE = 1.65


class View:
    def __init__(self, name, cam, tgt, lens, kind):
        self.name, self.cam, self.tgt, self.lens, self.kind = name, cam, tgt, lens, kind


def _look(x, y, dx, dy, z, dist=20.0, dz=0.0):
    n = math.hypot(dx, dy) or 1
    return (x + dx / n * dist, y + dy / n * dist, z + dz)


def pick_ground_views(w, seed=5, per=2):
    """歩道/車道/交差点/公園/広場/水辺/高架下/駐車場/路地/建物裏/駅前 から自動選定"""
    rng = random.Random(seed)
    T, area, edges, info = w["T"], w["area"], w["edges"], w["info"]
    inner = area.buffer(-150)
    views = []

    from shapely.strtree import STRtree
    foots = [b.meta["foot"] for b in w["builts"] if "foot" in b.meta]
    ftree = STRtree(foots) if foots else None

    def add(kind, x, y, dx, dy, zoff=0.0, lens=22):
        if not inner.contains(Point(x, y)):
            return
        if ftree is not None and any(foots[i].buffer(1.5).contains(Point(x, y)) for i in ftree.query(Point(x, y).buffer(2))):
            return                                     # 建物の中/直近は選ばない(真っ黒になる)
        z = T(x, y) + EYE + zoff
        views.append(View(f"g_{kind}_{len([v for v in views if v.kind == kind])}", (x, y, z), _look(x, y, dx, dy, z, 25, -0.05 * 25), lens, kind))

    drive = [e for e in edges if e.kind == "drive" and e.level == 0 and e.line.length > 60 and inner.intersects(e.line)]
    major = [e for e in drive if e.tags["highway"] in ("trunk", "primary", "secondary", "tertiary")]
    minor = [e for e in drive if e.tags["highway"] in ("residential", "service", "unclassified", "living_street")]
    for e in rng.sample(major, min(per, len(major))):          # 車道中央(車線上)
        s = e.line.length * rng.uniform(0.3, 0.7)
        p, q = e.line.interpolate(s), e.line.interpolate(s + 2)
        dx, dy = q.x - p.x, q.y - p.y
        n = math.hypot(dx, dy) or 1
        t = (0 if e.prof.oneway else e.prof.median / 2) + e.prof.lane_w * (0.5 if e.prof.oneway else 0.7)   # 中央分離帯の上ではなく車線上
        add("roadway", p.x - dy / n * t, p.y + dx / n * t, dx, dy)
    for e in rng.sample(major, min(per, len(major))):          # 歩道
        s = e.line.length * rng.uniform(0.2, 0.8)
        p, q = e.line.interpolate(s), e.line.interpolate(s + 2)
        dx, dy = q.x - p.x, q.y - p.y
        n = math.hypot(dx, dy) or 1
        off = e.prof.half + 1.2
        add("sidewalk", p.x - dy / n * off, p.y + dx / n * off, dx, dy, 0.14)
    for e in rng.sample(minor, min(per, len(minor))):          # 路地
        s = e.line.length * rng.uniform(0.3, 0.7)
        p, q = e.line.interpolate(s), e.line.interpolate(s + 2)
        add("alley", p.x, p.y, q.x - p.x, q.y - p.y, 0, 20)
    # 交差点
    from collections import defaultdict
    deg = defaultdict(list)
    for a in info["arms"]:
        deg[a[1]].append(a)
    nodes = [(k, v) for k, v in deg.items() if inner.contains(Point(k))]
    for k, v in rng.sample(nodes, min(per + 1, len(nodes))):
        a = v[0]
        px, py, tx, ty = a[6][0], a[6][1], a[6][2], a[6][3]
        add("intersection", px + tx * 22, py + ty * 22, -tx, -ty, 0, 24)
    # 公園/広場/駐車場
    for f in rng.sample([f for f in w["L"]["green"] if f.geom.area > 1500 and inner.contains(f.geom.centroid)], min(per, 4)) if w["L"]["green"] else []:
        c = f.geom.representative_point()
        add("park", c.x, c.y, rng.uniform(-1, 1), rng.uniform(-1, 1))
    park = [f for f in w["L"].get("landuse", []) if f.tags.get("amenity") == "parking" and f.geom.area > 800 and inner.contains(f.geom.centroid)]
    for f in rng.sample(park, min(per, len(park))):
        c = f.geom.representative_point()
        add("parking", c.x, c.y, rng.uniform(-1, 1), rng.uniform(-1, 1))
    plaza = [f for f in w["L"].get("landuse", []) if f.tags.get("landuse") in ("commercial", "retail", "industrial") and f.geom.area > 4000 and inner.contains(f.geom.centroid)]
    for f in rng.sample(plaza, min(per, len(plaza))):
        c = f.geom.representative_point()
        add("plaza", c.x, c.y, rng.uniform(-1, 1), rng.uniform(-1, 1))
    # 水辺(護岸の内側から水へ向かって)
    land = w["land"]
    polys = [land] if land.geom_type == "Polygon" else list(land.geoms)
    ring = max(polys, key=lambda p: p.area).exterior
    cnt = 0
    for _ in range(40):
        if cnt >= per:
            break
        s = rng.uniform(0, ring.length)
        p, q = ring.interpolate(s), ring.interpolate(min(ring.length, s + 2))
        dx, dy = q.x - p.x, q.y - p.y
        n = math.hypot(dx, dy) or 1
        ox, oy = dy / n, -dx / n            # 水側(右)
        x, y = p.x - ox * 4, p.y - oy * 4
        if inner.contains(Point(x, y)) and land.contains(Point(x, y)):
            add("waterfront", x, y, ox, oy)
            cnt += 1
    # 高架下
    for k, (e, (S, zs, p)) in enumerate([(e, info["elev"][e.id]) for e in edges if e.id in info["elev"] and e.line.length > 80][:60]):
        if k % 5 == 0 and len([v for v in views if v.kind == "underdeck"]) < per:
            s = e.line.length * 0.5
            pt, q = e.line.interpolate(s), e.line.interpolate(s + 2)
            add("underdeck", pt.x + 6, pt.y + 6, q.x - pt.x, q.y - pt.y)
    # 建物裏: 建物の重心から道路と反対側
    bl = [b for b in w["builts"] if inner.contains(Point(b.insts[0].x, b.insts[0].y)) and b.meta["height"] > 15]
    for b in rng.sample(bl, min(per, len(bl))):
        x0, y0 = b.insts[0].x, b.insts[0].y
        add("behind", x0 + rng.uniform(-8, 8), y0 + rng.uniform(-8, 8), rng.uniform(-1, 1), rng.uniform(-1, 1), 0, 20)
    # 駅前
    for st in w["L"].get("stations", []):
        if inner.contains(st.geom) and len([v for v in views if v.kind == "station"]) < per:
            add("station", st.geom.x + 8, st.geom.y + 8, -1, -1, 0, 20)
    return views


def pick_aerial_views(w):
    c = w["center"]
    T = w["T"]
    h = w["area"].bounds[2] - c[0]
    z0 = T(*c)
    vs = []
    for k, (ax, ay) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        vs.append(View(f"a_oblique_{k}", (c[0] + ax * h * 0.55, c[1] + ay * h * 0.55, z0 + 160), (c[0], c[1], z0 + 10), 30, "aerial"))
    vs.append(View("a_top", (c[0], c[1], z0 + 520), (c[0], c[1], z0), 30, "aerial"))
    vs.append(View("a_low_0", (c[0] - h * 0.4, c[1] - h * 0.5, z0 + 45), (c[0] + h * 0.2, c[1] + h * 0.1, z0 + 12), 28, "aerial"))
    vs.append(View("a_low_1", (c[0] + h * 0.5, c[1] + h * 0.3, z0 + 60), (c[0] - h * 0.2, c[1] - h * 0.1, z0 + 15), 28, "aerial"))
    return vs


def render_view(w, tiles, v, radius, samples=24, res=(1280, 720), extra=None):
    """tiles=dict(kind→dict(tile→メッシュ/インスタンス)); カメラ周辺radius[m]のタイル/インスタンスのみ"""
    cx, cy = v.cam[0], v.cam[1]
    render.init_scene(res, samples, sun_dir=(0.5, -0.45, 0.65))
    for name in ("g", "r", "t"):
        for (i, j), m in tiles[name].items():
            if w["tiler"].box(i, j).distance(Point(cx, cy)) < radius:
                render.add_mesh_object(f"{name}{i}_{j}", m)
    render.add_plane(80000, 0.0, "water", loc=w["center"])          # 水平線までつながる広い水面
    dmin = 6.0 if v.kind != "aerial" else 0.0           # カメラに重なる人/車を除く(視界が潰れるため)
    near = lambda i: dmin < (i.x - cx) ** 2 + (i.y - cy) ** 2 < radius * radius
    sel = []
    for key in ("furn", "veg", "props"):
        for ij, lst in tiles[key].items():
            if w["tiler"].box(*ij).distance(Point(cx, cy)) < radius:
                sel += [i for i in lst if near(i)]
    render.add_instances_gn(sel)
    bl = [b for b in w["builts"] if (b.insts[0].x - cx) ** 2 + (b.insts[0].y - cy) ** 2 < (radius + 60) ** 2]
    render.add_buildings_gn(bl)
    render.add_camera(v.cam, v.tgt, v.lens)
    OUT.mkdir(parents=True, exist_ok=True)
    render.render(OUT / f"{v.name}.png")


def make_tiles(w):
    t = w["tiler"]
    return dict(g=split_mesh(w["g"], t), r=split_mesh(w["r"], t), t=split_mesh(w["t"], t), furn=split_insts(w["furn"], t),
                veg=split_insts(w["veg"], t), props=split_insts(w["props"], t))


def contact_sheet(names, out, cols=3, size=(640, 360)):
    ims = []
    for n in names:
        p = OUT / f"{n}.png"
        if p.exists():
            im = Image.open(p).convert("RGB").resize(size)
            ImageDraw.Draw(im).text((6, 4), n, fill=(255, 255, 0))
            ims.append(im)
    if not ims:
        return
    rows = (len(ims) + cols - 1) // cols
    sh = Image.new("RGB", (size[0] * cols, size[1] * rows))
    for k, im in enumerate(ims):
        sh.paste(im, ((k % cols) * size[0], (k // cols) * size[1]))
    sh.save(OUT / out, quality=85)
