"""取得済みOSM(extra)のnatural=treeタグ分布を確認する。uv run python scripts/veg_osm_probe.py"""
from collections import Counter

from vt.layers import load_extra

X = load_extra()
c = Counter()
for f in X["pois"]:
    if f.tags.get("natural") == "tree":
        for k in ("genus", "species", "species:ja", "leaf_type", "leaf_cycle", "height", "name"):
            if k in f.tags:
                c[(k, f.tags[k])] += 1
print(sum(1 for f in X["pois"] if f.tags.get("natural") == "tree"), "trees", "hedges", len(X["hedges"]), "tree_rows", len(X["tree_rows"]), "vegareas", len(X["vegareas"]))
for k, v in c.most_common(30):
    print(k, v)
