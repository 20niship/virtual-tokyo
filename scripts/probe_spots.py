"""地点プリセットの座標探索: レインボーブリッジ(東京港連絡橋)の線上の点を lon,lat で出す"""
from vt.geo import to_lonlat
from vt.layers import load

L = load()
fs = [f for f in L["roads"] if "東京港連絡橋" in (f.tags.get("name") or "")]
fs.sort(key=lambda f: -f.geom.length)
for f in fs[:2]:
    g = f.geom
    print("len", round(g.length), g.geom_type)
    for t in (0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0):
        p = g.interpolate(t, normalized=True)
        print(t, ["%.5f" % v for v in to_lonlat(p.x, p.y)])
