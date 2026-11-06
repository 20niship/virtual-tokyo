"""人物モジュールの三角形数を数える: uv run python scripts/measure_humans.py [--rev <git rev>]
--rev を付けると、その時点でコミットされていた assets/modules/anny_*.usdc から数える(変更前との比較用)。"""
import subprocess
import sys
import tempfile
from pathlib import Path

from pxr import Usd, UsdGeom

ROOT = Path(__file__).resolve().parents[1]
rev = sys.argv[sys.argv.index("--rev") + 1] if "--rev" in sys.argv else None


def tris(path):
    st = Usd.Stage.Open(str(path))
    n = 0
    for p in st.Traverse():
        if p.IsA(UsdGeom.Mesh):
            c = UsdGeom.Mesh(p).GetFaceVertexCountsAttr().Get()
            n += sum(max(1, k - 2) for k in c)
    return n


if rev:
    names = subprocess.run(["git", "ls-tree", "--name-only", rev, "assets/modules/"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    names = [n for n in names if Path(n).name.startswith("anny_")]
else:
    names = [str(p.relative_to(ROOT)) for p in sorted((ROOT / "assets/modules").glob("anny_*.usdc"))]
tot, rows = 0, {}
with tempfile.TemporaryDirectory() as td:
    for n in names:
        if rev:
            data = subprocess.run(["git", "show", f"{rev}:{n}"], capture_output=True, cwd=ROOT).stdout
            f = Path(td) / Path(n).name
            f.write_bytes(data)
        else:
            f = ROOT / n
        t = tris(f)
        tot += t
        rows[Path(n).stem] = t
v = sorted(rows.values())
print(f"{'rev ' + rev if rev else 'working tree'}: {len(rows)} people, total {tot:,} tris, mean {tot // max(1, len(rows)):,}, median {v[len(v) // 2]:,}, min {v[0]:,}, max {v[-1]:,}")
for k in ("anny_casual_3", "anny_office_1", "anny_elder_2"):
    print(" ", k, rows.get(k))
