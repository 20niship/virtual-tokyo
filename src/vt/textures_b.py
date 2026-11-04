"""リアリズム強化(B): 服地/ナンバープレート/自販機/のぼり/提灯のテクスチャと、路面オーバーレイ(落ち葉/水たまり/タイヤ痕/油染み/補修帯/各種マンホール)を手続き生成(git管理)。
uv run python -m vt.textures_b   ナンバーの数字・店名・商品名はすべて架空。"""
import json
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .signs import font
from .textures import OUT, rgb, save, tnoise


def _save_img(name, im):
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / name, optimize=True)


# ---------------- 服地(タイル可能) ----------------
def cloth(name, kind, c1, c2="#ffffff", n=256, seed=1):
    y, x = np.mgrid[0:n, 0:n] / n
    r = tnoise(n, 0.6, seed)
    a, b = rgb(c1), rgb(c2)
    wv = 0.5 + 0.5 * np.sin(x * 2 * np.pi * (n / 3.0)) * np.sin(y * 2 * np.pi * (n / 3.0))      # 織り目
    if kind == "denim":
        m = (0.55 + 0.45 * np.sin((x + y) * 2 * np.pi * 48)) * 0.5 + 0.25 * wv
        img = a * (0.78 + 0.34 * m[..., None]) * (0.9 + 0.2 * r[..., None])
    elif kind == "stripe":
        t = (np.floor(y * 8) % 2)[..., None]
        img = a * (1 - t) + b * t
    elif kind == "pin":
        t = (np.sin(x * 2 * np.pi * 40) > 0.96)[..., None]
        img = a * (1 - 0.35 * t) + b * 0.35 * t
    elif kind == "plaid":
        tx = (np.floor(x * 6) % 2) * 0.5 + (np.floor(x * 24) % 2) * 0.25
        ty = (np.floor(y * 6) % 2) * 0.5 + (np.floor(y * 24) % 2) * 0.25
        t = np.clip(tx + ty, 0, 1)[..., None]
        img = a * (1 - t) + b * t
    elif kind == "knit":
        t = (0.5 + 0.5 * np.sin(x * 2 * np.pi * 36 + np.sin(y * 2 * np.pi * 18) * 1.4))[..., None]
        img = a * (0.7 + 0.45 * t)
    elif kind == "floral":
        img = np.ones((n, n, 3)) * a
        rg = np.random.default_rng(seed)
        for _ in range(14):
            cx, cy, rad = rg.random(), rg.random(), rg.uniform(0.02, 0.05)
            d = np.minimum(np.abs(x - cx), 1 - np.abs(x - cx)) ** 2 + np.minimum(np.abs(y - cy), 1 - np.abs(y - cy)) ** 2
            img = np.where((d < rad ** 2)[..., None], b * rg.uniform(0.8, 1.05), img)
    else:                                                    # plain
        img = a * (0.92 + 0.1 * wv[..., None]) * (0.94 + 0.12 * r[..., None])
    save(name, img * (0.96 + 0.06 * wv[..., None]))


CLOTHES = [("denim", "denim", "#3d5a85"), ("denim_dark", "denim", "#1f2d4a"), ("stripe_navy", "stripe", "#f0f0f0", "#1f2a52"),
           ("pin_gray", "pin", "#4a4d52", "#d8d8d8"), ("plaid_red", "plaid", "#a8262c", "#2a2a2a"), ("plaid_green", "plaid", "#2f5a3e", "#d8d8c8"),
           ("knit_beige", "knit", "#c7b79a"), ("knit_navy", "knit", "#2b3d63"), ("floral", "floral", "#e8e4d8", "#c85a78"), ("plain_pink", "plain", "#d98aa0"),
           ("plain_olive", "plain", "#6b6a40"), ("plain_mustard", "plain", "#c8a030")]


# ---------------- ナンバープレート ----------------
PLACES = ["品川", "練馬", "足立", "世田谷", "横浜", "川崎", "多摩", "大宮", "習志野", "湘南", "なにわ", "名古屋"]
PLATE_TYPES = [("white", (244, 246, 242), (22, 96, 56)), ("kei", (250, 214, 40), (20, 20, 20)),
               ("green", (22, 112, 62), (245, 245, 240)), ("keigreen", (20, 20, 20), (250, 214, 40))]
PLATE_CELL = (256, 128)


def plate_atlas(cols=6):
    rg = random.Random(7)
    hira = "あいうえかきくけこさすせそたちつてとなにぬねのはひふほまみむめもやゆよらりるろ"
    W, H = PLATE_CELL
    im = Image.new("RGB", (W * cols, H * len(PLATE_TYPES)))
    d = ImageDraw.Draw(im)
    uv = {}
    for r, (nm, bg, fg) in enumerate(PLATE_TYPES):
        for c in range(cols):
            x0, y0 = c * W, r * H
            d.rectangle([x0, y0, x0 + W - 1, y0 + H - 1], fill=bg)
            d.rounded_rectangle([x0 + 3, y0 + 3, x0 + W - 4, y0 + H - 4], 8, outline=fg, width=2)
            pl = rg.choice(PLACES)
            kana = rg.choice(hira) if nm in ("white", "kei") else rg.choice("あいうえおかきくけこを")
            cls = rg.choice(["300", "500", "330", "301", "580", "480"]) if nm in ("white", "green") else rg.choice(["580", "480", "583"])
            d.text((x0 + 24, y0 + 14), f"{pl} {cls}", font=font(30), fill=fg)
            d.text((x0 + 12, y0 + 52), kana, font=font(50), fill=fg)
            num = f"{rg.randint(1, 99)}-{rg.randint(0, 99):02d}"
            d.text((x0 + 70, y0 + 46), num, font=font(64), fill=fg)
            for sx in (x0 + 10, x0 + W - 14):
                d.ellipse([sx, y0 + 12, sx + 5, y0 + 17], fill=(120, 120, 120))
            uv[f"{nm}_{c}"] = [c / cols, 1 - (r + 1) / len(PLATE_TYPES), (c + 1) / cols, 1 - r / len(PLATE_TYPES)]
    _save_img("plate_atlas.png", im)
    json.dump(dict(cols=cols, types=[t[0] for t in PLATE_TYPES], uv=uv), open(OUT / "plate_atlas.json", "w"), indent=1)


# ---------------- 自販機の前面(架空の飲料ブランド) ----------------
VEND = [("#d8231f", "コーラ・ゼロ"), ("#1b6ab5", "ブルースカイ"), ("#2e8b57", "緑茶園"), ("#e0801c", "オレンジ堂"), ("#7a3f9c", "グレープ"), ("#202020", "BOSS珈琲"),
        ("#f0c020", "レモンスカッシュ"), ("#c02070", "ピーチ水")]
VCELL = (256, 512)


def vending_atlas():
    rg = random.Random(3)
    W, H = VCELL
    im = Image.new("RGB", (W * 4, H * 2), (30, 30, 30))
    d = ImageDraw.Draw(im)
    uv = []
    for i, (col, brand) in enumerate(VEND):
        c, r = i % 4, i // 4
        x0, y0 = c * W, r * H
        d.rectangle([x0, y0, x0 + W - 1, y0 + H - 1], fill=(26, 28, 32))
        d.rectangle([x0, y0, x0 + W - 1, y0 + 78], fill=col)                       # 上部の広告帯
        d.text((x0 + 12, y0 + 20), brand, font=font(34), fill=(255, 255, 255))
        d.rectangle([x0 + 8, y0 + 88, x0 + 170, y0 + 330], fill=(228, 232, 236))   # 商品窓
        for rr in range(3):
            for cc in range(6):
                xx, yy = x0 + 14 + cc * 26, y0 + 96 + rr * 78
                pc = rg.choice([col, "#f0f0f0", "#3a7a3a", "#d09020", "#2a5a9a", "#a02020", "#202020"])
                d.rounded_rectangle([xx, yy, xx + 18, yy + (46 if rr != 1 else 40)], 4, fill=pc)
                d.rectangle([xx + 4, yy + 12, xx + 14, yy + 24], fill=(255, 255, 255))
                d.rectangle([xx, yy + 56, xx + 18, yy + 66], fill=(255, 220, 40))
        d.rectangle([x0 + 180, y0 + 88, x0 + 246, y0 + 330], fill=(50, 52, 56))      # 操作パネル
        d.rectangle([x0 + 190, y0 + 98, x0 + 236, y0 + 120], fill=(200, 40, 30))
        d.rectangle([x0 + 192, y0 + 140, x0 + 234, y0 + 156], fill=(20, 20, 20))
        d.rectangle([x0 + 194, y0 + 200, x0 + 232, y0 + 212], fill=(90, 90, 90))
        d.rectangle([x0 + 8, y0 + 352, x0 + 246, y0 + 430], fill=(18, 18, 20))       # 取出口
        d.rectangle([x0 + 40, y0 + 370, x0 + 216, y0 + 416], fill=(8, 8, 10))
        uv.append([c / 4, 1 - (r + 1) / 2, (c + 1) / 4, 1 - r / 2])
    _save_img("vending_atlas.png", im)
    json.dump(dict(uv=uv, brands=[b for _, b in VEND]), open(OUT / "vending_atlas.json", "w"), indent=1)


# ---------------- のぼり旗/提灯(架空の店名) ----------------
NOBORI = [("#d8231f", "#ffffff", "ラーメン"), ("#ffffff", "#c01818", "営業中"), ("#f0c020", "#202020", "大安売り"), ("#1b6ab5", "#ffffff", "新装開店"),
          ("#2e8b57", "#ffffff", "お弁当"), ("#ffffff", "#1b3a8a", "つけ麺"), ("#e07820", "#ffffff", "焼きたて"), ("#c02070", "#ffffff", "SALE")]
NCELL = (160, 480)


def nobori_atlas():
    W, H = NCELL
    im = Image.new("RGB", (W * 4, H * 2))
    d = ImageDraw.Draw(im)
    uv = []
    for i, (bg, fg, tx) in enumerate(NOBORI):
        c, r = i % 4, i // 4
        x0, y0 = c * W, r * H
        d.rectangle([x0, y0, x0 + W - 1, y0 + H - 1], fill=bg)
        d.rectangle([x0 + 6, y0 + 6, x0 + W - 7, y0 + H - 7], outline=fg, width=3)
        sz = min(100, int(380 / max(1, len(tx))))
        f = font(sz)
        for k, ch in enumerate(tx):                             # 縦書き
            d.text((x0 + (W - f.getlength(ch)) / 2, y0 + 30 + k * sz * 1.05), ch, font=f, fill=fg)
        uv.append([c / 4, 1 - (r + 1) / 2, (c + 1) / 4, 1 - r / 2])
    _save_img("nobori_atlas.png", im)
    json.dump(dict(uv=uv), open(OUT / "nobori_atlas.json", "w"), indent=1)


def lantern_atlas():
    LT = [("居酒屋", (200, 32, 28), (255, 240, 208)), ("ら〜めん", (200, 32, 28), (255, 240, 208)), ("酒", (240, 232, 208), (32, 32, 32)), ("焼鳥", (200, 32, 28), (255, 240, 208))]
    im = Image.new("RGB", (256 * 4, 256))
    d = ImageDraw.Draw(im)
    uv = []
    for i, (tx, bg, fg) in enumerate(LT):
        x0 = i * 256
        d.rectangle([x0, 0, x0 + 255, 255], fill=bg)
        for k in range(1, 8):
            d.line([x0, k * 30, x0 + 255, k * 30], fill=tuple(int(c * 0.82) for c in bg), width=2)
        d.rectangle([x0, 0, x0 + 255, 18], fill=(24, 24, 24))
        d.rectangle([x0, 238, x0 + 255, 255], fill=(24, 24, 24))
        f = font(120 if len(tx) == 1 else 62)
        d.text((x0 + 128 - f.getlength(tx) / 2, 70), tx, font=f, fill=fg)
        uv.append([i / 4, 0, (i + 1) / 4, 1])
    _save_img("lantern_atlas.png", im)
    json.dump(dict(uv=uv), open(OUT / "lantern_atlas.json", "w"), indent=1)


# ---------------- 路面オーバーレイ(RGBA) ----------------
def _rgba(name, alpha, col):
    a = np.clip(alpha, 0, 1)
    img = np.zeros(a.shape + (4,))
    img[..., :3] = col
    img[..., 3] = a
    save(name, img, "RGBA")


def _blob_mask(n, seed, sc=0.42, soft=0.07, thr=0.5):
    f = tnoise(n, 2.4, seed)
    y, x = np.mgrid[0:n, 0:n] / n
    rad = np.hypot(x - 0.5, y - 0.5) / sc
    v = (1 - rad) * 1.2 + (f - 0.5) * 1.0
    return np.clip((v - thr + soft) / (2 * soft), 0, 1) * np.clip(1.4 - rad, 0, 1)


def overlays(n=512):
    for i in (1, 2):                                                   # 落ち葉(銀杏/桜/ケヤキの色)
        rg = random.Random(i)
        im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for _ in range(rg.randint(26, 40)):
            cx, cy = rg.randint(30, n - 30), rg.randint(30, n - 30)
            col = rg.choice([(214, 168, 30), (190, 120, 30), (150, 80, 30), (200, 190, 60), (110, 70, 30), (230, 190, 60)])
            a, rad = rg.uniform(0, 6.28), rg.randint(9, 16)
            pts = [(cx + math.cos(a + t) * rad * (1 + 0.35 * math.cos(2 * t)), cy + math.sin(a + t) * rad * 0.62 * (1 + 0.3 * math.cos(2 * t))) for t in np.linspace(0, 6.28, 9)]
            d.polygon(pts, fill=col + (235,))
        _save_img(f"overlay_leaf_litter_{i}.png", im.filter(ImageFilter.GaussianBlur(0.8)))
    m = _blob_mask(n, 4, 0.44, 0.1, 0.35)                                 # 水たまり(暗い鏡面+縁の濡れ)
    edge = np.clip(1 - np.abs(m - 0.5) * 2, 0, 1) * 0.25
    _rgba("overlay_puddle.png", m * 0.85 + edge * 0.3, np.array([0.05, 0.07, 0.09]))
    m = _blob_mask(n, 11, 0.4, 0.14, 0.45)                                # 油染み(暗い茶黒)
    _rgba("overlay_oil.png", m * 0.55 * (0.7 + 0.3 * tnoise(n, 0.8, 12)), np.array([0.03, 0.03, 0.035]))
    y, x = np.mgrid[0:n, 0:n] / n                                          # タイヤ痕: 緩いカーブの2本の黒い筋
    a = np.zeros((n, n))
    for off in (-0.1, 0.1):
        cx = 0.5 + off + 0.12 * np.sin(y * 2.4 + off * 6)
        a = np.maximum(a, np.clip(1 - np.abs(x - cx) / 0.035, 0, 1) * np.clip(1.2 - np.abs(y - 0.5) * 2.2, 0, 1))
    a *= 0.4 + 0.6 * tnoise(n, 0.5, 21)
    _rgba("overlay_tire_marks.png", a * 0.5, np.array([0.02, 0.02, 0.02]))
    band = np.abs(x - 0.5) < 0.22                                          # 掘削復旧帯: 新しいアスファルト+縁の目地シール
    img = np.zeros((n, n, 4))
    img[..., :3] = (0.07 + 0.03 * tnoise(n, 0.6, 31))[..., None]
    img[..., 3] = np.where(band, 0.82, 0.0)
    edge = np.abs(np.abs(x - 0.5) - 0.22) < 0.012
    img[edge, :3] = 0.02
    img[edge, 3] = 0.95
    save("overlay_trench.png", img, "RGBA")


def _cover(name, kind, n=256):
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fg, mid, dk = (88, 86, 82, 255), (112, 108, 100, 255), (50, 48, 46, 255)
    if kind == "round_sewer":                                               # 丸型の下水蓋: 同心円+格子目+文字
        d.ellipse([6, 6, n - 6, n - 6], fill=dk)
        d.ellipse([14, 14, n - 14, n - 14], fill=mid)
        d.ellipse([36, 36, n - 36, n - 36], outline=fg, width=6)
        for k in range(-5, 6):
            d.line([30, n // 2 + k * 18, n - 30, n // 2 + k * 18], fill=fg, width=3)
            d.line([n // 2 + k * 18, 30, n // 2 + k * 18, n - 30], fill=fg, width=3)
        d.rounded_rectangle([n // 2 - 46, n // 2 - 22, n // 2 + 46, n // 2 + 22], 6, fill=dk)
        d.text((n // 2 - 36, n // 2 - 18), "下水", font=font(38), fill=(190, 188, 180, 255))
    elif kind == "square_water":                                            # 角形の水道制水弁室
        d.rectangle([10, 10, n - 10, n - 10], fill=dk)
        d.rectangle([22, 22, n - 22, n - 22], fill=mid)
        d.rectangle([30, 30, n - 30, n - 30], outline=fg, width=6)
        for k in range(1, 7):
            d.line([30, 30 + k * 28, n - 30, 30 + k * 28], fill=fg, width=4)
        d.text((n // 2 - 18, n // 2 - 22), "水", font=font(52), fill=(190, 188, 180, 255))
    elif kind == "round_water":
        d.ellipse([20, 20, n - 20, n - 20], fill=dk)
        d.ellipse([30, 30, n - 30, n - 30], fill=mid)
        for k in range(8):
            a = k * math.pi / 4
            d.line([n // 2, n // 2, n // 2 + math.cos(a) * 88, n // 2 + math.sin(a) * 88], fill=fg, width=5)
        d.ellipse([n // 2 - 18, n // 2 - 18, n // 2 + 18, n // 2 + 18], fill=dk)
    elif kind == "gas":
        d.rectangle([40, 20, n - 40, n - 20], fill=dk)
        d.rectangle([50, 30, n - 50, n - 30], fill=(150, 130, 60, 255))
        d.text((n // 2 - 30, n // 2 - 30), "ガス", font=font(46), fill=(40, 30, 10, 255))
    else:                                                                   # 電気ハンドホール(長方形・ストライプ)
        d.rectangle([4, 40, n - 4, n - 40], fill=dk)
        d.rectangle([14, 50, n - 14, n - 50], fill=mid)
        for k in range(14):
            d.line([20 + k * 16, 56, 6 + k * 16, n - 56], fill=fg, width=4)
        d.text((n // 2 - 14, n // 2 - 24), "電", font=font(40), fill=(220, 220, 200, 255))
    _save_img(name, im.filter(ImageFilter.GaussianBlur(0.5)))


# ---------------- 車の塗装(下回りの汚れ+雨だれ入り。UVはボックス投影[m]: 側面 v=z) ----------------
CAR_PAINT = dict(white="#e8e8e4", black="#16171a", silver="#aeb2b6", gray="#5a5f64", red="#a3161c", blue="#1c3f7a", beige="#bba98a", green="#2f5a40", taxi="#1a1a1c",
                 pearl="#efeee8", navy="#14224a", wine="#5a1424", sky="#7ea6c8", yellow="#e8b818", bus="#2f7d4a")


def carpaints(n=256):
    y, x = np.mgrid[0:n, 0:n] / n
    v = 1 - y                                                      # 画像の下=v小=車体の下部
    streak = tnoise(n, 0.9, 5)
    col_n = np.mean(tnoise(n, 1.6, 8), axis=0, keepdims=True) * np.ones((n, 1))        # 縦筋(列ごとの濃淡)
    for nm, c in CAR_PAINT.items():
        low = np.clip(1 - v / 0.06, 0, 1) ** 1.4                    # 下端(~0.4m)の泥跳ね
        rain = np.clip(col_n - 0.45, 0, 1) * np.clip(1 - v / 0.22, 0, 1) * 0.5     # 縦の雨だれ
        dirt = np.clip(0.5 * low + rain + 0.07 * streak, 0, 0.6)
        img = rgb(c)[None, None, :] * (1 - dirt[..., None]) + np.array([0.18, 0.15, 0.11]) * dirt[..., None]
        save(f"carpaint_{nm}.png", img)


def main():
    for c in CLOTHES:
        cloth("cloth_" + c[0] + ".png", c[1], c[2], *(c[3:4] or ["#ffffff"]))
    plate_atlas()
    vending_atlas()
    nobori_atlas()
    lantern_atlas()
    overlays()
    carpaints()
    for k in ("round_sewer", "square_water", "round_water", "gas", "hand"):
        _cover(f"overlay_cover_{k}.png", k)
    print("ok")


if __name__ == "__main__":
    main()
