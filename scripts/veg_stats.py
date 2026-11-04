"""植栽モジュールの生成時間・三角形数を一覧する。uv run python scripts/veg_stats.py"""
import time

from vt import tree_gen as tg
from vt.modules.library import REG, get

names = [n for n, r in REG.items() if r["cat"] == "植栽"]
t = time.time()
rows, bad = [], []
for n in names:
    try:
        rows.append((tg.tris(get(n)), n))
    except Exception as e:  # noqa: BLE001
        bad.append((n, repr(e)[:120]))
rows.sort()
print(len(names), "modules", round(time.time() - t, 1), "s", "errors", bad[:6])
print("min", rows[:3])
print("max", rows[-8:])
tree = [r for r in rows if r[1].startswith("veg_") and any(s in r[1] for s in ("_m_", "_l_"))]
print("tree median tris", sorted(r[0] for r in tree)[len(tree) // 2] if tree else None)
