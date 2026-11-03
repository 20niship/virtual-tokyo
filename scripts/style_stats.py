"""建物スタイルの分布・生成時間・欠落モジュールを確認する: uv run python scripts/style_stats.py [件数]"""
import collections
import sys
import time

from vt.assemble import build_building, validate_styles
from vt.layers import load

print("missing:", validate_styles())
L = load()
n = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
t = time.time()
st, used = collections.Counter(), collections.Counter()
ok = err = ni = 0
for f in L["buildings"][:n]:
    try:
        b = build_building(f)
    except Exception as e:
        err += 1
        if err < 4:
            print("ERR", f.id, repr(e)[:160])
        continue
    if b:
        ok += 1
        ni += len(b.insts)
        st[b.meta["style"]] += 1
        used.update(i.name for i in b.insts)
print(ok, "buildings", ni, "insts", err, "errors", round(time.time() - t, 1), "s")
print(dict(st))
print(len(used), "distinct modules used")
