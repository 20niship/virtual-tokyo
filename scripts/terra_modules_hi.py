"""超高ポリ(`_hi`)の岩・地面 module を usdc に書き出す。近影(数 m 先)のスーパーリアル用で、near より 1〜2 桁面が多い(転石 20〜35 万面、露頭 13〜57 万面、崖 25〜50 万面。SDF 彫刻、lib_rock_sdf)。
例: terra_modules_hi.py            # 代表セット(花崗岩・安山岩・海辺の岩 × 転石 3 状態 + 露頭)
    terra_modules_hi.py --all      # 全 _hi(数百 MB)
    terra_modules_hi.py rock_granite_boulder_l_0_hi ...   # 名前指定"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from terra import modules as M  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("names", nargs="*")
ap.add_argument("--all", action="store_true")
a = ap.parse_args()
if a.all:
    names = [n for n in M.REG if n.endswith("_hi")]
elif a.names:
    names = a.names
else:
    names = [f"rock_{k}_{f}_hi" for k in ("granite", "andesite", "seashore") for f in ("boulder_l_0", "boulder_l_2", "boulder_l_4", "outcrop_2")]
for n in names:
    m = M.build(n)
    p = M.write_module(n)
    print(f"{n}: {len(m.f)} faces, {p.stat().st_size // 1024} KB")
