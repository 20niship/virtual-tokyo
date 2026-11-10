"""針葉樹の葉アトラス(スギ・ヒノキ・シラビソ・カラマツ・マツの小枝カード各 3 枚)を手続き生成する。外部データなし。
出力: assets/terra/textures/conifer_atlas.png(1024px RGBA, 256px のカード 4x4)と conifer_atlas.json(カード名 → uv / rect)。"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "assets/terra/textures"
C, SS = 256, 2                        # カード 1 枚の画素数・スーパーサンプル
KINDS = {                             # 種: (基本色, 明色, 暗色)
    "sugi": ((74, 112, 58), (112, 150, 78), (46, 76, 44)),
    "fir": ((46, 82, 62), (150, 176, 160), (30, 58, 46)),
    "hinoki": ((92, 128, 62), (132, 164, 84), (62, 92, 46)),
    "larch": ((132, 164, 76), (176, 202, 108), (92, 124, 58)),
    "pine": ((66, 98, 48), (104, 138, 70), (40, 66, 36)),
}


def _col(rng, base, light, dark):
    t = rng.random()
    a, b = (dark, base) if t < 0.5 else (base, light)
    u = (t % 0.5) * 2
    return tuple(int(a[i] * (1 - u) + b[i] * u) for i in range(3)) + (255,)


def _needle(d, p, ang, ln, w, col):
    """先の尖った針(三角形): 根元 p から角度 ang に長さ ln、根元の幅 w"""
    dx, dy = math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    d.polygon([(p[0] + nx * w / 2, p[1] + ny * w / 2), (p[0] - nx * w / 2, p[1] - ny * w / 2), (p[0] + dx * ln, p[1] + dy * ln)], fill=col)


def _twig(rng, kind, S):
    """1 枚のカード(S x S, RGBA)。枝は下から上へ伸び、側枝に針を付ける"""
    base, light, dark = KINDS[kind]
    im = Image.new("RGBA", (S, S), base + (0,))
    d = ImageDraw.Draw(im)
    brown = (88, 70, 50, 255)
    cx, y0 = S * 0.5, S * 0.97
    main_len = S * 0.9
    sway = rng.uniform(-0.25, 0.25)

    def pt(t, off=0.0):
        a = math.pi / 2 + sway * math.sin(t * 3.0)
        x = cx + sway * S * 0.25 * math.sin(t * 3.0) * t
        y = y0 - main_len * t
        return x, y, a

    d.line([(pt(t)[0], pt(t)[1]) for t in np.linspace(0, 1, 12)], fill=brown, width=max(3, S // 60))
    n_side = {"sugi": 14, "fir": 13, "hinoki": 11, "larch": 12, "pine": 8}[kind]
    for i in range(n_side):
        t = 0.12 + 0.86 * i / n_side
        x, y, _ = pt(t)
        for sd in (-1, 1):
            ln = S * (0.34 * (1 - t) ** 0.6 + 0.1) * rng.uniform(0.75, 1.15)
            if kind == "pine":
                ln = S * 0.2 * rng.uniform(0.7, 1.0)
            ang = -math.pi / 2 + sd * rng.uniform(0.45, 0.8) if kind == "pine" else -math.pi / 2 + sd * rng.uniform(0.7, 1.15)                        # 枝先が上向き(カードの上が先端)
            ex, ey = x + math.cos(ang - sd * 0.0) * ln, y + math.sin(ang) * ln
            d.line([(x, y), (ex, ey)], fill=brown, width=max(2, S // 110))
            if kind == "sugi":                                                         # 錐状の針が枝を取り巻く(ボトルブラシ)
                for k in range(16):
                    f = 0.15 + 0.85 * k / 16
                    px, py = x + (ex - x) * f, y + (ey - y) * f
                    for q in (-1, 1):
                        _needle(d, (px, py), ang + q * rng.uniform(0.35, 0.8), S * rng.uniform(0.05, 0.075), S * 0.022, _col(rng, base, light, dark))
            elif kind == "fir":                                                        # 平らに 2 列に並ぶ針
                for k in range(18):
                    f = 0.1 + 0.9 * k / 18
                    px, py = x + (ex - x) * f, y + (ey - y) * f
                    for q in (-1, 1):
                        _needle(d, (px, py), ang + q * 1.25, S * rng.uniform(0.05, 0.07), S * 0.02, _col(rng, base, dark, dark))
            elif kind == "hinoki":                                                     # 鱗状の葉が平たい扇状の小枝になる
                for k in range(10):
                    f = 0.1 + 0.9 * k / 10
                    px, py = x + (ex - x) * f, y + (ey - y) * f
                    wd = S * 0.05 * (1 - 0.5 * f)
                    d.ellipse([px - wd, py - wd * 1.5, px + wd, py + wd * 1.5], fill=_col(rng, base, light, dark))
                    for q in (-1, 1):
                        d.ellipse([px + q * wd * 1.5 - wd * 0.8, py - wd, px + q * wd * 1.5 + wd * 0.8, py + wd], fill=_col(rng, base, light, dark))
            elif kind == "larch":                                                      # 短枝から放射状に出る柔らかい針の束
                for k in range(5):
                    f = 0.25 + 0.75 * k / 5
                    px, py = x + (ex - x) * f, y + (ey - y) * f
                    for j in range(14):
                        _needle(d, (px, py), -math.pi / 2 + rng.uniform(-1.6, 1.6), S * rng.uniform(0.06, 0.1), S * 0.014, _col(rng, base, light, dark))
            else:                                                                      # マツ: 長い 2 本針の束が枝先に
                for j in range(9):
                    a2 = ang + rng.uniform(-0.55, 0.55)
                    _needle(d, (ex, ey), a2, S * rng.uniform(0.16, 0.23), S * 0.012, _col(rng, base, light, dark))
    return im


def build():
    rng = np.random.default_rng(11)
    atlas = Image.new("RGBA", (C * 4, C * 4), (0, 0, 0, 0))
    cards = {}
    for ki, kind in enumerate(KINDS):
        for v in range(3):
            card = _twig(rng, kind, C * SS).resize((C, C), Image.LANCZOS)
            x, y = (ki * 3 + v) % 4 * C, (ki * 3 + v) // 4 * C
            atlas.paste(card, (x, y))
            cards[f"conifer_{kind}_{v}"] = dict(kind="cluster", rect=[x, y, C, C], uv=[x / (C * 4), 1 - (y + C) / (C * 4), (x + C) / (C * 4), 1 - y / (C * 4)])
    OUT.mkdir(parents=True, exist_ok=True)
    atlas.save(OUT / "conifer_atlas.png", optimize=True)
    (OUT / "conifer_atlas.json").write_text(json.dumps(dict(size=[C * 4, C * 4], cards=cards), indent=1))
    print("wrote", OUT / "conifer_atlas.png", (OUT / "conifer_atlas.png").stat().st_size // 1024, "KB cards", len(cards))


if __name__ == "__main__":
    build()
