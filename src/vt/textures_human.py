"""人物用の手続きテクスチャ: 生地(グレースケール・タイル。材質の tint で着色)、プリント(架空ブランド)、ディテール(ボタン・ポケット)。
実在ブランドのロゴは使わない(名前・図形はすべて架空)。出力は assets/textures/ に小さい PNG で置く。"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

TEX = Path(__file__).resolve().parents[2] / "assets/textures"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FABRICS = ("jersey", "knit", "denim", "twill", "pin", "check", "border", "linen", "wool")
N = 256


def _noise(seed, sx=1, sy=1, amp=0.04):
    r = np.random.default_rng(seed)
    a = r.normal(0, 1, (N // sy + 1, N // sx + 1))
    a = np.kron(a, np.ones((sy, sx)))[:N, :N]
    return a * amp


def _save(name, a):
    TEX.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "L").save(TEX / name, optimize=True)


def make_fabrics():
    y, x = np.mgrid[0:N, 0:N].astype(float)
    out = {}
    out["jersey"] = 0.84 + 0.07 * np.sin(2 * math.pi * x / 4) * np.sin(2 * math.pi * y / 4) + _noise(1, 1, 1, 0.025)
    u, v = x % 16, y % 14
    out["knit"] = 0.55 + 0.45 * np.clip(1 - np.abs(u - 8) / 8 - 0.3 * (v / 14), 0, 1) + _noise(2, 1, 1, 0.02)
    tw = ((x + y) % 8 < 4).astype(float)
    out["denim"] = 0.70 + 0.16 * tw + _noise(3, 1, 24, 0.05) * (1 + (y % 3 == 0))
    out["twill"] = 0.76 + 0.12 * (((x + y) % 5) < 2) + _noise(4, 1, 1, 0.025)
    base = 0.58 + 0.10 * (((x + y) % 6) < 3) + _noise(5, 1, 1, 0.02)
    out["pin"] = np.where((x % 32) < 2, 1.0, base)
    gx, gy = (x // 16) % 2 == 0, (y // 16) % 2 == 0
    out["check"] = np.where(gx & gy, 0.62, np.where(gx | gy, 0.82, 1.0)) + _noise(6, 1, 1, 0.02)
    out["border"] = np.where((y % 48) < 24, 1.0, 0.42) + 0.06 * np.sin(2 * math.pi * x / 4) + _noise(7, 1, 1, 0.02)
    out["linen"] = 0.82 + _noise(8, 1, 6, 0.06) + _noise(9, 6, 1, 0.06)
    out["wool"] = 0.80 + _noise(10, 1, 1, 0.05) + 0.05 * np.sin(2 * math.pi * (x + y) / 5)
    for k, a in out.items():
        _save(f"fabric_{k}.png", a)
    return list(out)


def _font(sz):
    return ImageFont.truetype(FONT, sz)


def make_prints():
    """架空ブランドのプリント 8 種(128px x 8、アトラス 512x256)。白縁+黒縁でどの色の服にも読める"""
    A = Image.new("RGBA", (512, 256), (0, 0, 0, 0))
    cell = lambda i: (i % 4 * 128, i // 4 * 128)

    def text(d, xy, s, sz, fill, anchor="mm"):
        d.text(xy, s, font=_font(sz), fill=fill, anchor=anchor, stroke_width=2, stroke_fill=(20, 20, 24, 255))
    W, K, R, B, Y = (240, 240, 235, 255), (24, 24, 28, 255), (200, 60, 50, 255), (50, 100, 190, 255), (230, 190, 50, 255)
    for i in range(8):
        im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        if i == 0:      # 円と波線 + KAZEMI
            d.ellipse((24, 10, 104, 90), fill=B, outline=W, width=4)
            for k in range(3):
                d.arc((34, 30 + k * 14, 94, 70 + k * 14), 200, 340, fill=W, width=4)
            text(d, (64, 108), "KAZEMI", 20, W)
        elif i == 1:    # 山と太陽
            d.polygon([(10, 96), (50, 30), (74, 64), (92, 44), (118, 96)], fill=K, outline=W)
            d.ellipse((84, 14, 108, 38), fill=Y, outline=W, width=3)
            text(d, (64, 112), "NORD PEAK", 16, W)
        elif i == 2:    # 星
            pts = [(64 + 44 * math.cos(math.radians(-90 + 72 * k)), 52 + 44 * math.sin(math.radians(-90 + 72 * k))) for k in (0, 2, 4, 1, 3)]
            d.polygon(pts, fill=Y, outline=K)
            text(d, (64, 112), "STAR LAB", 18, W)
        elif i == 3:    # 太字ロゴ
            text(d, (64, 48), "SORA", 44, W)
            d.rectangle((16, 80, 112, 88), fill=R)
            text(d, (64, 108), "SINCE 1998", 14, W)
        elif i == 4:    # ネコ
            d.ellipse((24, 30, 104, 100), fill=W, outline=K, width=4)
            d.polygon([(28, 44), (30, 10), (56, 34)], fill=W, outline=K)
            d.polygon([(100, 44), (98, 10), (72, 34)], fill=W, outline=K)
            d.ellipse((44, 56, 54, 68), fill=K); d.ellipse((74, 56, 84, 68), fill=K)
            d.polygon([(60, 76), (68, 76), (64, 82)], fill=R)
            text(d, (64, 116), "NEKO CLUB", 16, W)
        elif i == 5:    # 背番号風
            text(d, (64, 56), "07", 72, W)
            d.rectangle((14, 100, 114, 106), fill=R)
        elif i == 6:    # 幾何
            for k in range(3):
                d.regular_polygon((64, 56, 46 - k * 14), 6, rotation=k * 15, outline=[W, Y, R][k], width=4)
        else:           # 小さな胸ロゴ
            d.ellipse((30, 30, 76, 76), outline=W, width=5); d.ellipse((52, 30, 98, 76), outline=Y, width=5)
            text(d, (64, 100), "HIBIKI", 18, W)
        A.paste(im, cell(i))
    A.save(TEX / "print_atlas.png", optimize=True)


def make_details():
    """ディテール 4 種(アトラス 512x128): 0=ボタン前立て(縦) 1=ジーンズ前ポケット 2=胸ポケット 3=シーム"""
    A = Image.new("RGBA", (512, 128), (0, 0, 0, 0))
    D = (30, 30, 34, 150)
    S = (255, 255, 255, 110)
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle((50, 0, 78, 127), fill=(255, 255, 255, 28), outline=D)
    for k in range(5):
        cy = 14 + k * 25
        d.ellipse((58, cy - 5, 70, cy + 7), fill=(235, 235, 230, 255), outline=(60, 60, 60, 255))
        d.point([(62, cy), (66, cy), (62, cy + 3), (66, cy + 3)], fill=(40, 40, 40, 255))
    A.paste(im, (0, 0))
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.arc((10, -40, 118, 90), 20, 160, fill=D, width=3)
    d.line((14, 40, 14, 110), fill=D, width=3); d.line((14, 110, 112, 110), fill=D, width=3)
    for dx in (4, -4):
        d.arc((10 + dx, -40 + abs(dx), 118 + dx, 90 + abs(dx)), 20, 160, fill=S, width=1)
    A.paste(im, (128, 0))
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle((24, 20, 104, 100), outline=D, width=3); d.line((24, 36, 104, 36), fill=D, width=3)
    d.rectangle((28, 24, 100, 96), outline=S, width=1)
    A.paste(im, (256, 0))
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.line((62, 0, 62, 127), fill=D, width=3); d.line((68, 0, 68, 127), fill=S, width=1)
    A.paste(im, (384, 0))
    A.save(TEX / "detail_atlas.png", optimize=True)


def make_all():
    f = make_fabrics()
    make_prints()
    make_details()
    return f


UV = dict(print=lambda i: ((i % 4) / 4, 1 - (i // 4 + 1) / 2, (i % 4 + 1) / 4, 1 - (i // 4) / 2), detail=lambda i: (i / 4, 0.0, (i + 1) / 4, 1.0))


# ---- 顔のデカール(目・眉・唇・血色・くま・そばかす・しわ)+ひげ ----
FACE_COLS, FACE_ROWS, TW, TH = 4, 5, 128, 64
FACE = dict(eye=(0, 0), brow=(0, 1), lips=(0, 2), blush=(0, 3), wrinkle=(0, 4))     # 各タイプの先頭(列, 行)


def face_uv(kind, i):
    c, r = FACE[kind]
    c += i
    return (c / FACE_COLS, 1 - (r + 1) / FACE_ROWS, (c + 1) / FACE_COLS, 1 - r / FACE_ROWS)


def _eye_tile(iris, ring):
    S = 4
    w, h = TW * S, TH * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    xs = np.linspace(0.04, 0.96, 60)
    top = [(x * w, h * (0.5 - 0.34 * (1 - (2 * x - 1) ** 2) ** 0.8)) for x in xs]
    bot = [(x * w, h * (0.5 + 0.22 * (1 - (2 * x - 1) ** 2) ** 0.9)) for x in xs[::-1]]
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon(top + bot, fill=255)
    base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(base)
    bd.rectangle((0, 0, w, h), fill=(238, 232, 226, 255))
    cx, cy, r = w * 0.5, h * 0.52, h * 0.30
    for k in range(18):
        t = k / 17
        col = tuple(int(ring[i] * (1 - t) + iris[i] * t) for i in range(3)) + (255,)
        rr = r * (1 - 0.55 * t)
        bd.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=col)
    bd.ellipse((cx - r * 0.42, cy - r * 0.42, cx + r * 0.42, cy + r * 0.42), fill=(8, 6, 6, 255))
    bd.ellipse((cx - r * 0.55, cy - r * 0.62, cx - r * 0.15, cy - r * 0.28), fill=(255, 255, 255, 235))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((0, 0, w, int(h * 0.42)), fill=(60, 40, 35, 120))
    base = Image.alpha_composite(base, sh)
    im.paste(base, (0, 0), mask)
    d = ImageDraw.Draw(im)
    d.line(top, fill=(25, 18, 16, 255), width=int(h * 0.075), joint="curve")
    for k in range(7):
        x = 0.58 + 0.055 * k
        px, py = x * w, h * (0.5 - 0.34 * (1 - (2 * x - 1) ** 2) ** 0.8)
        d.line((px, py, px + w * 0.02, py - h * 0.16), fill=(25, 18, 16, 235), width=int(h * 0.035))
    d.line(bot, fill=(110, 80, 70, 150), width=int(h * 0.03))
    return im.resize((TW, TH), Image.LANCZOS)


def _brow_tile(kind):
    S = 3
    w, h = TW * S, TH * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(kind)
    thick = (0.30, 0.20, 0.13, 0.24)[kind]
    arch = (0.10, 0.22, 0.12, 0.05)[kind]
    for k in range(420):
        t = rng.random()
        x = 0.05 + 0.9 * t
        yc = 0.62 - arch * math.sin(math.pi * t) - 0.12 * t
        y = yc + (rng.random() - 0.5) * thick * (1 - 0.5 * t)
        a = int(180 + 70 * rng.random())
        d.line((x * w, y * h, (x + 0.035) * w, (y - 0.07 + 0.14 * t * 0.5) * h), fill=(235, 235, 232, a), width=max(1, S))
    return im.resize((TW, TH), Image.LANCZOS)


def _soft(draw_fn, blur=0):
    from PIL import ImageFilter
    im = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(im))
    return im.filter(ImageFilter.GaussianBlur(blur)) if blur else im


def make_face():
    A = Image.new("RGBA", (FACE_COLS * TW, FACE_ROWS * TH), (0, 0, 0, 0))
    put = lambda im, c, r: A.paste(im, (c * TW, r * TH))
    for i, (iris, ring) in enumerate((((120, 80, 45), (50, 30, 15)), ((70, 45, 28), (25, 15, 8)), ((130, 105, 60), (60, 45, 25)), ((85, 95, 105), (35, 40, 48)))):
        put(_eye_tile(iris, ring), i, 0)
    for i in range(4):
        put(_brow_tile(i), i, 1)

    def lips(c1, c2, w1, open_=False, smile=False):
        def f(d):
            if open_:
                d.polygon([(10, 22), (64, 12), (118, 22), (110, 34), (64, 44), (18, 34)], fill=(110, 40, 42, 255))
                d.polygon([(22, 24), (64, 18), (106, 24), (100, 30), (64, 33), (28, 30)], fill=(238, 234, 226, 255))
            d.polygon([(8, 30), (40, 14), (64, 18), (88, 14), (120, 30), (64, 31)], fill=c1)
            d.polygon([(8, 30), (64, 31), (120, 30), (100, 46), (64, 52 if w1 else 48), (28, 46)], fill=c2)
            d.line((10, 30, 118, 30), fill=(90, 40, 40, 255), width=2)
        return _soft(f, 0.6)
    put(lips((178, 96, 92, 235), (196, 112, 106, 235), 0), 0, 2)
    put(lips((190, 100, 100, 240), (210, 118, 116, 240), 1), 1, 2)
    put(lips((170, 100, 96, 230), (182, 108, 104, 230), 0), 2, 2)
    put(lips((178, 96, 92, 240), (196, 112, 106, 240), 0, open_=True), 3, 2)
    put(_soft(lambda d: d.ellipse((14, 4, 114, 60), fill=(205, 85, 85, 90)), 9), 0, 3)
    put(_soft(lambda d: d.arc((14, -26, 114, 50), 25, 155, fill=(80, 55, 70, 120), width=9), 3), 1, 3)
    r = np.random.default_rng(5)
    put(_soft(lambda d: [d.ellipse((x - 1.4, y - 1.4, x + 1.4, y + 1.4), fill=(140, 95, 65, 150)) for x, y in zip(r.uniform(12, 116, 45), r.uniform(8, 56, 45))], 0.5), 2, 3)
    put(_soft(lambda d: d.ellipse((58, 26, 68, 36), fill=(70, 45, 35, 230)), 0.8), 3, 3)
    put(_soft(lambda d: [d.arc((8, 4 + k * 16 - 8, 120, 28 + k * 16 - 8), 200, 340, fill=(80, 55, 50, 85), width=2) for k in range(3)], 0.8), 0, 4)
    put(_soft(lambda d: [d.line((20, 32, 108, 32 + (k - 1) * 14), fill=(80, 55, 50, 85), width=2) for k in range(3)], 0.8), 1, 4)
    put(_soft(lambda d: d.arc((-30, 0, 100, 120), 275, 340, fill=(80, 55, 50, 100), width=3), 0.9), 2, 4)
    A.save(TEX / "face_atlas.png", optimize=True)
    r = np.random.default_rng(9)
    st = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    ds = ImageDraw.Draw(st)
    for x, y in zip(r.uniform(0, 128, 700), r.uniform(0, 128, 700)):
        a = int(90 + 110 * r.random())
        ds.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(230, 230, 230, a))
    st.save(TEX / "stubble.png", optimize=True)
