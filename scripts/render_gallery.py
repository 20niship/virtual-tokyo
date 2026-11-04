"""モジュールをカテゴリ別にギャラリー画像へ。 uv run python scripts/render_gallery.py [cat ...]"""
import sys
from pathlib import Path

from vt import render
from vt.modules.library import REG

OUT = Path(__file__).resolve().parents[1] / "out/modules"
OUT.mkdir(parents=True, exist_ok=True)
cats = {}
for n, r in REG.items():
    cats.setdefault(r["cat"], []).append(n)
sel = sys.argv[1:] or list(cats)
for c in sel:
    names = [n for n in cats[c] if n != "light_highmast_25m"]
    big = c.startswith("標識(")
    step = 24 if big else 12
    for k in range(0, len(names), step):
        chunk = names[k:k + step]
        out = OUT / f"{c}_{k // step}.png"
        render.gallery(chunk, out, cols=6 if big else (4 if len(chunk) > 6 else 3), samples=int(__import__("os").environ.get("SPP", 48)))
        print("wrote", out)
