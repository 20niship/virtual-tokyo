"""葉スキャンZIP → assets/textures/leaves_atlas.png + leaves_atlas.json
uv run python scripts/convert_leaves.py ~/Downloads/leaves.zip"""
import sys

from vt import leaf_atlas

if __name__ == "__main__":
    m = leaf_atlas.build(sys.argv[1])
    print("source sprites", m["source_sprites"], "classes", m["classes"], "cards", len(m["cards"]), "raw leaves", len(m["leaves"]))
