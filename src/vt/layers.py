"""OSM JSON -> 内部レイヤー(shapely, ローカルm座標)。"""
import random
import re
from collections import Counter
from dataclasses import dataclass

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import linemerge, polygonize, unary_union

from .geo import to_local
from .osm_fetch import fetch

LEVEL_H = 3.5

# highway種別 -> (車線数, 車道幅員m, 歩道幅m)。lanes/width タグが無い時のデフォルト
HIGHWAY_DEFAULT = {
    "motorway": (4, 14, 0), "motorway_link": (1, 5, 0), "trunk": (4, 14, 2.5), "trunk_link": (1, 5, 0),
    "primary": (4, 13, 3), "primary_link": (1, 5, 0), "secondary": (2, 9, 3), "secondary_link": (1, 5, 0),
    "tertiary": (2, 7, 2.5), "tertiary_link": (1, 5, 0), "unclassified": (2, 6, 2), "residential": (2, 6, 2),
    "service": (1, 4, 0), "living_street": (1, 5, 1.5),
    "footway": (0, 0, 2), "pedestrian": (0, 0, 4), "cycleway": (0, 0, 2.5), "steps": (0, 0, 2), "path": (0, 0, 1.5),
}


@dataclass
class Feature:
    id: int
    geom: object
    tags: dict


def _coords(g):
    return [to_local(p["lon"], p["lat"]) for p in g]


def _way_geom(el):
    c = _coords(el["geometry"])
    if len(c) >= 4 and c[0] == c[-1] and (el["tags"].get("area") == "yes" or not _is_line_tag(el["tags"])):
        return Polygon(c)
    return LineString(c) if len(c) >= 2 else None


def _is_line_tag(t):
    return "highway" in t or "railway" in t or "barrier" in t


def _rel_geom(el):
    outers, inners = [], []
    for m in el.get("members", []):
        if m["type"] != "way" or not m.get("geometry"):
            continue
        (inners if m["role"] == "inner" else outers).append(LineString(_coords(m["geometry"])))
    if not outers:
        return None
    polys = list(polygonize(linemerge(outers)))
    if not polys:
        return None
    out = unary_union(polys)
    if inners:
        holes = list(polygonize(linemerge(inners)))
        if holes:
            out = out.difference(unary_union(holes))
    return out


def _num(s):
    m = re.match(r"\s*([\d.]+)", s or "")
    return float(m.group(1)) if m else None


STOREY = {"apartments": 3.0, "residential": 3.0, "house": 3.0, "detached": 3.0, "dormitory": 3.0, "terrace": 3.0, "semidetached_house": 3.0,   # 階高[m](用途別。住宅は約3.0、事務所/商業は約3.9、工場は約4.5)
          "commercial": 3.9, "office": 3.9, "retail": 3.9, "hotel": 3.5, "supermarket": 4.2, "industrial": 4.5, "warehouse": 4.5, "factory": 4.5}


def building_height(tags, rng):
    """height -> levels*階高(用途別) -> 乱数推定(シード固定)。(top, min_height, source)を返す"""
    mh = _num(tags.get("min_height")) or 0.0
    if (h := _num(tags.get("height"))) is not None:
        return h, mh, "height"
    if (n := _num(tags.get("building:levels"))) is not None:
        return n * STOREY.get(tags.get("building", ""), LEVEL_H) + mh, mh, "levels"
    return rng.choice([6, 9, 12, 15, 20, 30]), mh, "guess"


def load(data=None):
    data = data or fetch()
    rng = random.Random(0)
    L = {k: [] for k in ("roads", "buildings", "building_parts", "rail", "water", "green", "stations", "coastline", "landuse")}
    for el in data["elements"]:
        t = el.get("tags", {})
        if el["type"] == "node":
            if t.get("railway") == "station":
                L["stations"].append(Feature(el["id"], Point(to_local(el["lon"], el["lat"])), t))
            continue
        if el["type"] == "way" and "geometry" in el:
            g = _way_geom(el)
        elif el["type"] == "relation":
            g = _rel_geom(el)
        else:
            continue
        if g is None or g.is_empty:
            continue
        f = Feature(el["id"], g, t)
        if "highway" in t and isinstance(g, LineString):
            L["roads"].append(f)
        elif "railway" in t and isinstance(g, LineString):
            L["rail"].append(f)
        elif t.get("natural") == "coastline":
            L["coastline"].append(f)
        elif isinstance(g, (Polygon, MultiPolygon)):
            if "building:part" in t:
                L["building_parts"].append(f)
            elif "building" in t:
                top, mh, src = building_height(t, rng)
                f.tags = {**t, "_top": top, "_min": mh, "_hsrc": src, "_n": int(_num(t.get("building:levels")) or 0)}
                L["buildings"].append(f)
            elif t.get("natural") in ("water", "bay") or "water" in t:
                L["water"].append(f)
            elif t.get("amenity") == "parking" or (t.get("landuse") and t["landuse"] not in ("grass", "forest", "recreation_ground", "village_green")) or t.get("natural") in ("sand", "beach", "bare_rock") or t.get("man_made") in ("pier", "breakwater") or t.get("leisure") in ("swimming_pool", "stadium", "track", "marina"):
                L["landuse"].append(f)
            elif t.get("landuse") in ("grass", "forest", "recreation_ground", "village_green") or t.get("leisure") in ("park", "garden", "pitch", "playground") or t.get("natural") in ("wood", "scrub"):
                L["green"].append(f)
    return L


def summary(L):
    lines = {k: len(v) for k, v in L.items()}
    rc = Counter(f.tags["highway"] for f in L["roads"])
    names = Counter((f.tags.get("name"), f.tags.get("railway")) for f in L["rail"])
    return lines, rc, names


if __name__ == "__main__":
    L = load()
    n, rc, names = summary(L)
    print(n)
    print(rc.most_common(10))
    print([x for x in names.most_common(15)])
    print(Counter(f.tags["_hsrc"] for f in L["buildings"]))


def load_extra(data=None):
    """道路ファニチャ用OSM(fetch_extra): 点(POI)・線(ガードレール/フェンス/電線)をローカルm座標で返す"""
    from .osm_fetch import fetch_extra
    data = data or fetch_extra()
    X = {"pois": [], "barriers": [], "powerlines": [], "adlines": [], "hedges": [], "tree_rows": [], "vegareas": []}
    for el in data["elements"]:
        t = el.get("tags", {})
        if el["type"] == "node":
            X["pois"].append(Feature(el["id"], Point(to_local(el["lon"], el["lat"])), t))
        elif el["type"] == "way" and el.get("geometry"):
            c = _coords(el["geometry"])
            g = LineString(c)
            if g.length < 0.5:
                continue
            f = Feature(el["id"], g, t)
            if t.get("barrier") == "hedge":
                X["hedges"].append(f)
            if t.get("natural") == "tree_row":
                X["tree_rows"].append(f)
            if (t.get("leisure") == "garden" or t.get("landuse") in ("flowerbed", "forest") or t.get("natural") in ("wood", "scrub", "shrub")) and len(c) >= 4 and c[0] == c[-1]:
                X["vegareas"].append(Feature(el["id"], Polygon(c), t))
            if "barrier" in t:
                X["barriers"].append(f)
            elif "power" in t:
                X["powerlines"].append(f)
            elif "advertising" in t:
                X["adlines"].append(f)
    return X
