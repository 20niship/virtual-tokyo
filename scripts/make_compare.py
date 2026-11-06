"""変更前後の比較画像: uv run python scripts/make_compare.py
out/render/humans/real_before と real_after のクローズアップ、街中(west_intersection round3 と round5)を左右に並べて out/render/humans/compare/ に出す。"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

R = Path(__file__).resolve().parents[1] / "out/render/humans"
OUT = R / "compare"
OUT.mkdir(exist_ok=True)
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)


def pair(a, b, name, h=720):
    ims = []
    for p, t in ((a, "BEFORE"), (b, "AFTER")):
        if not p.exists():
            return
        im = Image.open(p).convert("RGB")
        im = im.resize((int(im.width * h / im.height), h))
        ImageDraw.Draw(im).rectangle((0, 0, 150, 40), fill=(20, 24, 28))
        ImageDraw.Draw(im).text((8, 4), t, font=F, fill=(240, 240, 235))
        ims.append(im)
    W = ims[0].width + ims[1].width
    out = Image.new("RGB", (W, h))
    out.paste(ims[0], (0, 0)); out.paste(ims[1], (ims[0].width, 0))
    out.save(OUT / f"{name}.jpg", quality=86)


for g in ("casual3", "office1", "elder2"):
    for shot in ("face", "hair_side", "hair_back", "torso", "full"):
        pair(R / "real_before" / f"{g}_{shot}.png", R / "real_after" / f"{g}_{shot}.png", f"{g}_{shot}")
pair(R / "west_intersection/round3/g_roadway_1.png", R / "west_intersection/round5/g_roadway_1.png", "street_roadway_1", 540)
pair(R / "west_intersection/round3/g_roadway_0.png", R / "west_intersection/round5/g_roadway_0.png", "street_roadway_0", 540)
print(sorted(p.name for p in OUT.glob("*.jpg")))
pair(R / "var_e.png", R / "var_o.png", "crowd_gallery", 640)
