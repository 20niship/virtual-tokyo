"""高架の細部を見るためのカメラ(桁下・橋脚・非常階段・路面上)を、配置済みの細部Instから自動選定する。"""
import math

from shapely.geometry import Point

from .city_render import View


def _near(furn, name, c, r):
    return [i for i in furn if i.name == name and (i.x - c[0]) ** 2 + (i.y - c[1]) ** 2 < r * r]


def views(w, per=2):
    T, area, furn, info = w["T"], w["area"], w["furn"], w["info"]
    c = w["center"]
    out = []
    inner = area.buffer(-25)

    def add(name, cam, tgt, lens=22):
        if inner.contains(Point(cam[0], cam[1])):
            out.append(View(name, cam, tgt, lens, "ground"))
    plates = _near(furn, "ex_pier_plate", c, 400)
    for k, p in enumerate(plates[:per + 1]):
        nx, ny = -math.sin(p.rot), math.cos(p.rot)                       # 板の外向き(+y)
        d = 11.0
        cam = (p.x + nx * d, p.y + ny * d, T(p.x + nx * d, p.y + ny * d) + 1.65)
        add(f"x_pier_{k}", cam, (p.x, p.y, p.z + 3.5), 20)
    stairs = _near(furn, "ex_emerg_stair", c, 400)
    for k, s in enumerate(stairs[:per]):
        nx, ny = -math.sin(s.rot), math.cos(s.rot)
        for sg in (1, -1):
            cam = (s.x + nx * 13 * sg, s.y + ny * 13 * sg, T(s.x, s.y) + 1.65)
            if inner.contains(Point(cam[0], cam[1])):
                add(f"x_stair_{k}", cam, (s.x, s.y, s.z + 4.0), 22)
                break
    elev = info.get("elev", {}) if isinstance(info, dict) else {}
    eds = [e for e in w["edges"] if e.id in elev and e.line.intersects(area)]
    if eds:
        e = max(eds, key=lambda e: e.line.intersection(area).length)
        S, zs, prof = elev[e.id]
        L = e.line.length
        for k, f in enumerate((0.35, 0.6)):
            s = L * f
            p, q = e.line.interpolate(s), e.line.interpolate(min(L, s + 3))
            dx, dy = q.x - p.x, q.y - p.y
            n = math.hypot(dx, dy) or 1
            add(f"x_under_{k}", (p.x, p.y, T(p.x, p.y) + 1.65), (p.x + dx / n * 25, p.y + dy / n * 25, T(p.x, p.y) + 6.0), 18)
            zi = zs[min(len(zs) - 1, int(f * (len(zs) - 1)))]
            lane = (prof.lane_w * 0.6) if prof is not None else 2.0
            add(f"x_deck_{k}", (p.x - dy / n * lane, p.y + dx / n * lane, zi + 1.7), (p.x + dx / n * 40, p.y + dy / n * 40, zi + 3.0), 24)
    return out
