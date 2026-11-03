"""駅名標アトラス(3.2m x 1.0m, 1024x320px/枚)を assets/textures/station_signs.{png,json} に生成: uv run python -m vt.station_signs"""
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[2] / "assets/textures"
BW, BH = 1024, 320
COLS = 2

# OSM駅名 → (路線, 記号, かな, ローマ字)
STATIONS = {
    "新橋": ("yurikamome", "U01", "しんばし", "Shimbashi"),
    "汐留": ("yurikamome", "U02", "しおどめ", "Shiodome"),
    "竹芝": ("yurikamome", "U03", "たけしば", "Takeshiba"),
    "日の出": ("yurikamome", "U04", "ひので", "Hinode"),
    "芝浦ふ頭": ("yurikamome", "U05", "しばうらふとう", "Shibaurafuto"),
    "お台場海浜公園": ("yurikamome", "U06", "おだいばかいひんこうえん", "Odaiba-kaihinkoen"),
    "台場": ("yurikamome", "U07", "だいば", "Daiba"),
    "東京国際クルーズターミナル": ("yurikamome", "U08", "とうきょうこくさいくるーずたーみなる", "Tokyo International Cruise Terminal"),
    "テレコムセンター": ("yurikamome", "U09", "てれこむせんたー", "Telecom Center"),
    "青海": ("yurikamome", "U10", "あおみ", "Aomi"),
    "東京ビッグサイト": ("yurikamome", "U11", "こくさいてんじじょうせいもん", "Kokusai-Tenjijo-Seimon"),
    "有明": ("yurikamome", "U12", "ありあけ", "Ariake"),
    "有明テニスの森": ("yurikamome", "U13", "ありあけてにすのもり", "Ariake-Tennis-no-Mori"),
    "市場前": ("yurikamome", "U14", "しじょうまえ", "Shijomae"),
    "モノレール浜松町": ("monorail", "MO-01", "はままつちょう", "Hamamatsucho"),
    "天王洲アイル": ("monorail", "MO-03", "てんのうずあいる", "Tennozu Isle"),
}
LINE_COLOR = {"yurikamome": (0, 110, 190), "monorail": (232, 110, 20)}


def _font_path():
    for line in subprocess.run(["fc-list", ":lang=ja", "file"], capture_output=True, text=True).stdout.splitlines():
        if "NotoSansCJK-Bold" in line:
            return line.split(":")[0].strip()
    for line in subprocess.run(["fc-list", ":lang=ja", "file"], capture_output=True, text=True).stdout.splitlines():
        if "NotoSansCJK" in line:
            return line.split(":")[0].strip()


def _fit(d, text, fp, max_w, size):
    while size > 12:
        f = ImageFont.truetype(fp, size, index=0)
        if d.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return ImageFont.truetype(fp, 12, index=0)


def board(name, line, code, kana, romaji, fp):
    col = LINE_COLOR[line]
    im = Image.new("RGB", (BW, BH), (250, 250, 248))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, BW - 1, BH - 1), outline=col, width=14)
    d.rectangle((14, 14, BW - 15, 62), fill=col)
    d.text((40, 38), "ゆりかもめ  Yurikamome" if line == "yurikamome" else "東京モノレール  Tokyo Monorail", font=ImageFont.truetype(fp, 34, index=0), fill=(255, 255, 255), anchor="lm")
    d.ellipse((50, 90, 270, 310), fill=col)
    d.ellipse((66, 106, 254, 294), outline=(255, 255, 255), width=6)
    d.text((160, 200), code, font=_fit(d, code, fp, 160, 76), fill=(255, 255, 255), anchor="mm")
    x0, x1 = 300, BW - 40
    cx = (x0 + x1) / 2
    d.text((cx, 128), name, font=_fit(d, name, fp, x1 - x0, 104), fill=(20, 20, 20), anchor="mm")
    d.text((cx, 208), kana, font=_fit(d, kana, fp, x1 - x0, 44), fill=(60, 60, 60), anchor="mm")
    d.text((cx, 266), romaji, font=_fit(d, romaji, fp, x1 - x0, 50), fill=(20, 20, 20), anchor="mm")
    return im


def main():
    fp = _font_path()
    names = list(STATIONS)
    rows = (len(names) + COLS - 1) // COLS
    W, H = BW * COLS, BH * rows
    atlas = Image.new("RGB", (W, H), (255, 255, 255))
    meta = {"size": [W, H], "board": [3.2, 1.0], "stations": {}}
    for i, n in enumerate(names):
        line, code, kana, rom = STATIONS[n]
        r, c = divmod(i, COLS)
        atlas.paste(board(n, line, code, kana, rom, fp), (c * BW, r * BH))
        meta["stations"][n] = dict(line=line, code=code, uv=[c * BW / W, 1 - (r + 1) * BH / H, (c + 1) * BW / W, 1 - r * BH / H])
    OUT.mkdir(parents=True, exist_ok=True)
    atlas.save(OUT / "station_signs.png", optimize=True)
    (OUT / "station_signs.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(len(names), "station boards ->", OUT / "station_signs.png")


def load_meta():
    return json.loads((OUT / "station_signs.json").read_text())


if __name__ == "__main__":
    main()
