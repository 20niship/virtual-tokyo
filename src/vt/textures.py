"""道路・地面・線路用テクスチャを手続き生成して assets/textures/*.png に保存(git管理)。
uv run python -m vt.textures"""
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[2] / "assets/textures"


def tnoise(n, beta, seed):
    """タイル可能な 1/f^beta ノイズ(0..1)"""
    r = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)
    k = np.sqrt(f[:, None] ** 2 + f[None, :] ** 2)
    k[0, 0] = 1
    spec = (r.normal(size=(n, n)) + 1j * r.normal(size=(n, n))) / k ** beta
    spec[0, 0] = 0
    a = np.real(np.fft.ifft2(spec))
    a = (a - a.min()) / (a.max() - a.min())
    return a


def save(name, arr, mode=None):
    OUT.mkdir(parents=True, exist_ok=True)
    arr = np.clip(arr, 0, 1)
    im = Image.fromarray((arr * 255).astype(np.uint8), mode)
    im.save(OUT / name, optimize=True)


def rgb(c):
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def tint(gray, c0, c1):
    return gray[..., None] * rgb(c1) + (1 - gray[..., None]) * rgb(c0)


def asphalt(n=1024):
    low, mid, fine = tnoise(n, 1.6, 1), tnoise(n, 1.0, 2), tnoise(n, 0.2, 3)
    agg = (fine > 0.78).astype(float) * 0.5 + fine * 0.5          # 骨材の粒
    g = 0.16 + 0.07 * low + 0.05 * mid + 0.09 * agg
    img = np.stack([g, g, g * 1.02], -1)
    save("asphalt.png", img)
    # 補修パッチ・ひび(タイル内の低周波)入り劣化版
    crack = np.abs(tnoise(n, 1.3, 7) - 0.5) < 0.004
    patch = tnoise(n, 2.2, 9) > 0.8
    img2 = img * (1 - 0.12 * patch[..., None]) * (1 - 0.8 * crack[..., None])
    save("asphalt_worn.png", img2)


def bricks(n, bw, bh, gap, cols, seed, jitter=0.07, bond=True):
    r = np.random.default_rng(seed)
    img = np.zeros((n, n, 3)); img[:] = rgb("#6b6862")
    ny, nx = int(n / bh), int(n / bw)
    pal = [rgb(c) for c in cols]
    for j in range(ny):
        for i in range(nx):
            x0 = int(i * bw + (bw / 2 if (bond and j % 2) else 0)) % n
            y0 = int(j * bh)
            c = pal[r.integers(len(pal))] * (1 + r.normal(0, jitter))
            xs = [(x0 + k) % n for k in range(gap, int(bw) - gap)]
            img[y0 + gap:y0 + int(bh) - gap][:, xs] = c
    return img


def sidewalk(n=1024):
    img = bricks(n, 64, 32, 2, ["#b0a79a", "#a89b8b", "#98908a", "#b8aea0"], 4)   # インターロッキング(長手)
    img *= (0.9 + 0.2 * tnoise(n, 1.2, 5))[..., None]
    save("sidewalk_paver.png", img)
    # コンクリート平板 60x60
    g = np.zeros((n, n, 3)); g[:] = rgb("#a4a29c")
    g *= (0.88 + 0.2 * tnoise(n, 1.5, 6))[..., None]
    s = n // 4
    for k in range(4):
        g[k * s:k * s + 3, :] *= 0.55; g[:, k * s:k * s + 3] *= 0.55
    save("sidewalk_tile.png", g)
    # カラーアスファルト(歩道)
    a = tint(0.35 + 0.35 * tnoise(n, 0.8, 8) * 0.6 + 0.3 * tnoise(n, 0.2, 10) * 0.4, "#6f635a", "#a09283")
    save("sidewalk_asphalt.png", a)
    # 御影石の平板 300x600
    st = bricks(n, 128, 256, 3, ["#8a8985", "#9a9791", "#7a7a78", "#a6a39b"], 11, 0.06, False)
    st *= (0.9 + 0.2 * tnoise(n, 1.0, 12))[..., None]
    save("sidewalk_granite.png", st)


def concrete(n=1024):
    low, fine = tnoise(n, 1.8, 20), tnoise(n, 0.3, 21)
    pores = (tnoise(n, 0.1, 22) > 0.985).astype(float)
    g = 0.55 + 0.12 * low + 0.05 * fine - 0.25 * pores
    img = np.stack([g, g * 0.99, g * 0.96], -1)
    save("concrete.png", img)
    # 型枠割り(1.8m x 0.9m)入り: 高架橋・護岸
    v = img.copy()
    sy, sx = n // 2, n // 2
    for k in range(2):
        v[k * sy:k * sy + 3, :] *= 0.6; v[:, k * sx:k * sx + 3] *= 0.6
    for yy in (n // 4, 3 * n // 4):
        for xx in (n // 4, 3 * n // 4):
            v[yy - 3:yy + 3, xx - 3:xx + 3] *= 0.5
    save("concrete_formed.png", v)
    # 石積み護岸
    r = np.random.default_rng(30)
    st = np.zeros((n, n, 3)); st[:] = rgb("#55524d")
    y = 0
    while y < n:
        h = int(r.choice([96, 128, 160])); x = int(r.integers(0, 200))
        while x < n + 200:
            w = int(r.choice([160, 224, 288]))
            c = rgb("#8a867e") * (0.8 + 0.4 * r.random())
            xs = [(x + k) % n for k in range(3, w - 3)]
            st[y + 3:min(y + h - 3, n)][:, xs] = c
            x += w
        y += h
    st *= (0.85 + 0.3 * tnoise(n, 1.2, 31))[..., None]
    save("riprap_stone.png", st)


def ballast(n=1024):
    """砕石 + 横向きの枕木(u方向=線路に沿って4本/タイル、タイル=2.4m x 3.2m)"""
    f1, f2 = tnoise(n, 0.15, 40), tnoise(n, 0.6, 41)
    g = 0.32 + 0.28 * f1 + 0.1 * f2
    img = np.stack([g, g, g * 0.97], -1)
    sl = n // 4
    for k in range(4):
        x0 = k * sl + int(sl * 0.35)
        img[:, x0:x0 + int(sl * 0.3)] = rgb("#8d8a84") * (0.8 + 0.3 * tnoise(n, 0.4, 42 + k)[:, :1])[..., None] * 0 + rgb("#8a867f")
    # レール位置(横方向 v)の黒い汚れ
    for yy in (int(n * 0.31), int(n * 0.69)):
        img[yy - 40:yy + 40] *= 0.78
    save("track_bed.png", img)


def ground(n=1024):
    g1, g2 = tnoise(n, 0.5, 50), tnoise(n, 1.4, 51)
    grass = np.stack([0.20 + 0.08 * g1 + 0.05 * g2, 0.36 + 0.14 * g1 + 0.08 * g2, 0.12 + 0.04 * g1], -1)
    save("grass.png", grass)
    save("soil.png", tint(0.4 + 0.4 * g1 * 0.5 + 0.3 * g2 * 0.5, "#4a3b2c", "#8a7660"))
    save("gravel.png", tint(0.3 + 0.7 * tnoise(n, 0.05, 52), "#6e6a64", "#b7b2a8"))
    pl = tint(0.45 + 0.4 * g2, "#9b988f", "#b8b5ac")                 # 広場の舗装(大判)
    s = n // 4
    for k in range(4):
        pl[k * s:k * s + 2, :] *= 0.6; pl[:, k * s:k * s + 2] *= 0.6
    save("plaza.png", pl)


def paint_wear(n=1024):
    a = 0.55 * tnoise(n, 1.5, 60) + 0.45 * tnoise(n, 0.3, 61)
    a = np.clip((a - 0.28) * 3.0, 0, 1)
    a = 0.55 + 0.45 * a            # 0.55..1 = かすれ
    save("paint_wear.png", a, "L")


def rgba(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def sym(name, im):
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / name, optimize=True)


def markings():
    W = (240, 240, 235, 255)
    # 矢印(1.2m x 5m = 120x500)
    def arrow(kind):
        im = rgba(120, 500); d = ImageDraw.Draw(im)
        if kind == "straight":
            d.polygon([(60, 0), (115, 150), (80, 150), (80, 500), (40, 500), (40, 150), (5, 150)], fill=W)
        elif kind == "left":
            d.polygon([(0, 120), (60, 20), (60, 90), (95, 90), (95, 500), (55, 500), (55, 130), (0, 120)][:0] or
                      [(5, 110), (62, 10), (62, 70), (80, 70), (80, 500), (45, 500), (45, 110)], fill=W)
        elif kind == "right":
            d.polygon([(115, 110), (58, 10), (58, 70), (40, 70), (40, 500), (75, 500), (75, 110)], fill=W)
        elif kind in ("straight_left", "straight_right"):
            d.polygon([(60, 0), (110, 120), (78, 120), (78, 500), (42, 500), (42, 120), (10, 120)], fill=W)
            if kind == "straight_left":
                d.polygon([(0, 250), (40, 200), (40, 232), (60, 232), (60, 300), (40, 300), (40, 280)], fill=W)
            else:
                d.polygon([(120, 250), (80, 200), (80, 232), (60, 232), (60, 300), (80, 300), (80, 280)], fill=W)
        sym(f"arrow_{kind}.png", im)
    for k in ("straight", "left", "right", "straight_left", "straight_right"):
        arrow(k)
    # 文字(日本の路面文字は縦に約2.5倍)
    path = subprocess.run(["fc-list", ":lang=ja", "file", "family"], capture_output=True, text=True).stdout
    font = None
    for line in path.splitlines():
        if "Noto Sans CJK JP" in line or "NotoSansCJK" in line:
            fp = line.split(":")[0]
            try:
                font = ImageFont.truetype(fp, 200, index=0)
                break
            except Exception:
                continue
    def text(name, s, size=(500, 500), sx=1.0, sy=2.6):
        base = rgba(*size); d = ImageDraw.Draw(base)
        f = font or ImageFont.load_default()
        bb = d.textbbox((0, 0), s, font=f)
        d.text(((size[0] - (bb[2] - bb[0])) / 2 - bb[0], (size[1] - (bb[3] - bb[1])) / 2 - bb[1]), s, font=f, fill=W)
        bb2 = base.getbbox()
        base = base.crop(bb2)
        base = base.resize((int(base.width * sx), int(base.height * sy)), Image.LANCZOS)
        sym(name, base)
    text("text_tomare.png", "止まれ", (900, 300), 1.0, 2.6)
    text("text_bus.png", "バス", (600, 300), 1.0, 2.6)
    text("text_徐行.png".replace("徐行", "jokou"), "徐行", (600, 300), 1.0, 2.6)
    for v in (30, 40, 50, 60):
        text(f"speed_{v}.png", str(v), (500, 300), 1.0, 2.6)
    # ひし形(横断歩道あり) 1.0 x 2.0m
    im = rgba(100, 200); d = ImageDraw.Draw(im)
    d.polygon([(50, 0), (100, 100), (50, 200), (0, 100)], outline=W, width=9)
    sym("diamond.png", im)
    # 逆三角(優先道路/停止予告) 1.2 x 1.6m
    im = rgba(120, 160); d = ImageDraw.Draw(im)
    d.polygon([(4, 4), (116, 4), (60, 156)], outline=W, width=9)
    sym("triangle.png", im)
    # 自転車ピクト 0.9 x 1.4m
    im = rgba(90, 140); d = ImageDraw.Draw(im)
    for cx in (20, 70):
        d.ellipse((cx - 18, 90, cx + 18, 126), outline=W, width=6)
    d.line([(20, 108), (40, 70), (70, 108)], fill=W, width=6); d.line([(40, 70), (62, 70), (70, 108)], fill=W, width=6)
    d.line([(60, 70), (56, 52)], fill=W, width=6); d.line([(50, 52), (64, 52)], fill=W, width=6)
    d.ellipse((34, 14, 52, 32), fill=W); d.line([(42, 32), (46, 56), (62, 70)], fill=W, width=7)
    sym("bike_symbol.png", im)
    # 自転車レーンの青路面(RGBA、ざらつき)
    n = 256
    blue = np.zeros((n, n, 4)); blue[..., :3] = rgb("#2f6fb5") * (0.85 + 0.25 * tnoise(n, 0.3, 70))[..., None]; blue[..., 3] = 1
    save("bikelane_blue.png", blue, "RGBA")
    # 誘導ブロック(線状: 0.3m角を4本線 / 点状: 5x5ドット)
    n = 300
    t = np.zeros((n, n, 4)); t[..., :3] = rgb("#d8b400"); t[..., 3] = 1
    img = Image.fromarray((t * 255).astype(np.uint8), "RGBA"); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, n - 1, n - 1), outline=(150, 120, 0, 255), width=5)
    for i in range(4):
        x = 45 + i * 70
        d.rounded_rectangle((x - 12, 12, x + 12, n - 12), 10, fill=(240, 205, 20, 255), outline=(150, 120, 0, 255), width=2)
    img.save(OUT / "tbs_line.png", optimize=True)
    img = Image.fromarray((t * 255).astype(np.uint8), "RGBA"); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, n - 1, n - 1), outline=(150, 120, 0, 255), width=5)
    for i in range(5):
        for j in range(5):
            cx, cy = 30 + i * 60, 30 + j * 60
            d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=(240, 205, 20, 255), outline=(150, 120, 0, 255), width=2)
    img.save(OUT / "tbs_dot.png", optimize=True)
    # マンホール蓋(直径0.65m)
    n = 256
    im = rgba(n, n); d = ImageDraw.Draw(im)
    d.ellipse((4, 4, n - 4, n - 4), fill=(70, 68, 66, 255), outline=(35, 34, 33, 255), width=6)
    for r in (100, 60):
        d.ellipse((n / 2 - r, n / 2 - r, n / 2 + r, n / 2 + r), outline=(100, 98, 94, 255), width=5)
    for k in range(12):
        a = k * math.pi / 6
        d.line([(n / 2 + 60 * math.cos(a), n / 2 + 60 * math.sin(a)), (n / 2 + 100 * math.cos(a), n / 2 + 100 * math.sin(a))], fill=(100, 98, 94, 255), width=5)
    sym("manhole.png", im)


def main():
    asphalt(); sidewalk(); concrete(); ballast(); ground(); paint_wear(); markings()
    print(sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
