"""超高ポリ(`_hi`)の岩・地面 module を usdc に書き出す。近影(数 m 先)のスーパーリアル用で、near より 1〜2 桁面が多い(転石 2〜8 万面、崖 2.2 万面、土パッチ 1.7 万面)。
例: terra_modules_hi.py            # 代表セット(岩種 5 × 形 4 + 土 4 種)
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
KS = ["granite", "andesite", "sandstone", "limestone", "tuff"]
if a.all:
    names = [n for n in M.REG if n.endswith("_hi")]
elif a.names:
    names = a.names
else:
    names = [f"rock_{k}_{f}_hi" for i, k in enumerate(KS) for f in (f"boulder_m_{1 + i % 2}", f"boulder_l_{i % 4}", f"outcrop_{1 + i % 2}", f"cliff_{i % 4}")]
    names += [f"soil_{k}_patch_0_hi" for k in ("kuroboku", "clay", "scoria", "masa", "sandy", "humus", "mud", "redyellow")]
for n in names:
    m = M.build(n)
    p = M.write_module(n)
    print(f"{n}: {len(m.f)} faces, {p.stat().st_size // 1024} KB")
