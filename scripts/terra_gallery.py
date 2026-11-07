"""画像を 500KB 以下の JPG にして out/terra/gallery/ へコピーする: terra_gallery.py a.png b.png ..."""
import io
import sys
from pathlib import Path

from PIL import Image

dst = Path(__file__).resolve().parents[1] / "out/terra/gallery"
dst.mkdir(parents=True, exist_ok=True)
for p in map(Path, sys.argv[1:]):
    im = Image.open(p).convert("RGB")
    for q in (92, 85, 78, 70, 60, 50):
        b = io.BytesIO()
        im.save(b, "JPEG", quality=q, optimize=True)
        if b.tell() <= 500_000:
            break
    out = dst / f"{p.parent.name}_{p.stem}.jpg"
    out.write_bytes(b.getvalue())
    print(out, b.tell() // 1024, "KB")
