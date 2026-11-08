"""前後比較画像: terra_compare.py before.png after.png out.jpg [ラベル前 ラベル後]。左=前、右=後。"""
import sys

from PIL import Image, ImageDraw, ImageFont

b, a, out = sys.argv[1:4]
lb, la = (sys.argv[4], sys.argv[5]) if len(sys.argv) > 5 else ("before", "after")
ib, ia = Image.open(b).convert("RGB"), Image.open(a).convert("RGB")
h = min(ib.height, ia.height)
ib, ia = ib.resize((int(ib.width * h / ib.height), h)), ia.resize((int(ia.width * h / ia.height), h))
im = Image.new("RGB", (ib.width + ia.width + 6, h), (255, 255, 255))
im.paste(ib, (0, 0))
im.paste(ia, (ib.width + 6, 0))
d = ImageDraw.Draw(im)
try:
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
except OSError:
    f = ImageFont.load_default()
for x, t in ((12, lb), (ib.width + 18, la)):
    d.text((x, 10), t, fill=(255, 255, 255), font=f, stroke_width=3, stroke_fill=(0, 0, 0))
for q in (88, 80, 70, 60):
    im.save(out, quality=q)
    import os
    if os.path.getsize(out) <= 500_000:
        break
print(out, os.path.getsize(out) // 1024, "KB")
