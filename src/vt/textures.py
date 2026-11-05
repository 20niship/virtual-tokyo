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


def pavers(n, bw, bh, cols, seed, bond=0.5, gap=(1, 3), wobble=0.12, chip=0.10, stain=0.9):
    """歩道ブロック/平板: 目地の幅と列のずれが不規則、1枚ごとに明るさ・色味がばらつき、角が欠け、目地に汚れ/苔、全体に雨だれ状の汚れ"""
    r = np.random.default_rng(seed)
    img = np.zeros((n, n, 3)); img[:] = rgb("#55524c")                             # 目地(暗い)
    pal = [rgb(c) for c in cols]
    ny = int(round(n / bh))
    row_h = n / ny
    for j in range(ny):
        y0, y1 = int(j * row_h), int((j + 1) * row_h)
        off = (bw * bond if j % 2 else 0) + r.normal(0, bw * 0.03)
        x = -off
        while x < n:
            w = bw * (1 + r.uniform(-wobble, wobble))
            g0, g1 = r.integers(gap[0], gap[1] + 1), r.integers(gap[0], gap[1] + 1)
            xa, xb = int(x) + g0, int(x + w) - g1
            c = pal[r.integers(len(pal))] * (1 + r.normal(0, 0.06)) * (1 + r.normal(0, 0.008, 3))
            xs = np.arange(xa, xb) % n
            ya, yb = y0 + int(g0), y1 - int(g1)
            blk = np.broadcast_to(c, (yb - ya, len(xs), 3)).copy()
            blk *= (1 + 0.06 * r.standard_normal((yb - ya, len(xs), 1)))              # 表面の粒
            if r.random() < chip and blk.shape[0] > 6 and blk.shape[1] > 6:           # 角の欠け
                k = int(r.integers(2, 6)); cx = r.integers(0, 2); cy = r.integers(0, 2)
                sx = slice(0, k) if cx == 0 else slice(-k, None); sy = slice(0, k) if cy == 0 else slice(-k, None)
                blk[sy, sx] = rgb("#58554f")
            if r.random() < 0.03:                                                      # 割れた/色の違う補修ブロック
                blk *= 0.72
            img[ya:yb][:, xs] = blk
            x += w
    low = tnoise(n, 1.6, seed + 1)
    img *= (0.88 + 0.22 * low)[..., None]                                              # 色むら
    joint = (img.mean(-1) < 0.36).astype(float)
    moss = (tnoise(n, 0.9, seed + 2) > 0.62) * joint                                   # 目地の苔/土
    img = img * (1 - 0.4 * moss[..., None]) + rgb("#4a5a34") * 0.4 * moss[..., None]
    streak = tnoise(n, 0.5, seed + 3)                                                  # 縦方向の汚れ(雨だれ)
    k = np.exp(-np.arange(n) / 40.0)
    st = np.real(np.fft.ifft(np.fft.fft(streak, axis=0) * np.fft.fft(k)[:, None], axis=0)); st = (st - st.min()) / (st.max() - st.min())
    img *= (1 - stain * 0.22 * st)[..., None]
    return img


def sidewalk(n=1024):
    img = pavers(n, 64, 32, ["#b0a79a", "#a89b8b", "#98908a", "#b8aea0", "#a39d98"], 4, 0.5, (1, 3), 0.12, 0.12)   # インターロッキング(長手)
    save("sidewalk_paver.png", img)
    # コンクリート平板 60x60(目地が不規則、欠け・汚れ)
    g = pavers(n, n // 4, n // 4, ["#a4a29c", "#9c9a94", "#aeaca5"], 6, 0.0, (2, 4), 0.02, 0.2, 1.2)
    save("sidewalk_tile.png", g)
    # カラーアスファルト(歩道)
    a = tint(0.35 + 0.35 * tnoise(n, 0.8, 8) * 0.6 + 0.3 * tnoise(n, 0.2, 10) * 0.4, "#6f635a", "#a09283")
    save("sidewalk_asphalt.png", a)
    # 御影石の平板 300x600
    st = pavers(n, 256, 128, ["#8a8985", "#9a9791", "#7a7a78", "#a6a39b"], 11, 0.0, (2, 3), 0.03, 0.1)
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
        elif kind in ("left", "right"):
            # 右左折専用: 縦の軸が上で斜めに曲がり、矢じりが進行方向の斜め前を向く(日本の路面標示の形)
            sgn = 1 if kind == "right" else -1
            cx = 60 - sgn * 22
            pts = [(cx, 500), (cx, 280), (cx + sgn * 34, 170)]
            d.line(pts, fill=W, width=34, joint="curve")
            dx, dy = sgn * 34, -110.0
            L = math.hypot(dx, dy); dx, dy = dx / L, dy / L
            ex, ey = pts[-1]
            ax, ay = ex + dx * 70, ey + dy * 70
            px_, py_ = -dy, dx
            d.polygon([(ax, ay), (ex + px_ * 46, ey + py_ * 46), (ex - px_ * 46, ey - py_ * 46)], fill=W)
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


def road_decals():
    """路面の劣化デカール(ひび割れ/補修パッチ/わだち)と、排水設備(グレーチング/集水桝/側溝)"""
    r = np.random.default_rng(90)

    def walk_cracks(n, count, seed, branch=0.35):
        im = Image.new("L", (n, n), 0); d = ImageDraw.Draw(im)
        g = np.random.default_rng(seed)

        def crack(x, y, ang, w, depth):
            pts = [(x, y)]
            for _ in range(int(g.integers(12, 28))):
                ang += g.normal(0, 0.35); x += math.cos(ang) * g.uniform(8, 18); y += math.sin(ang) * g.uniform(8, 18)
                pts.append((x, y))
                if depth < 2 and g.random() < branch * 0.25:
                    crack(x, y, ang + g.choice([-1, 1]) * g.uniform(0.5, 1.2), max(1, w - 1), depth + 1)
            d.line(pts, fill=255, width=w)
        for _ in range(count):
            crack(g.uniform(0.15, 0.85) * n, g.uniform(0.15, 0.85) * n, g.uniform(0, 6.28), 3, 0)
        return im
    from PIL import ImageFilter
    for k, (cnt, seed) in enumerate(((2, 1), (3, 2), (1, 3)), 1):
        a = np.array(walk_cracks(512, cnt, seed).filter(ImageFilter.GaussianBlur(0.8))) / 255.0
        rgba = np.zeros((512, 512, 4)); rgba[..., :3] = rgb("#101012"); rgba[..., 3] = np.clip(a * 0.85, 0, 1)
        save(f"asphalt_crack_{k}.png", rgba, "RGBA")
    # 補修パッチ(埋設工事の復旧跡: 切り口の線+やや黒い新しいアスファルト) 3m x 1m
    for k, (w, h) in enumerate(((600, 200), (400, 400)), 1):
        base = 0.10 + 0.05 * tnoise(512, 0.8, 100 + k)[:h, :w] if False else 0.1 + 0.05 * np.random.default_rng(100 + k).random((h, w))
        rgba = np.zeros((h, w, 4)); rgba[..., :3] = base[..., None] * np.array([1, 1, 1.03]); rgba[..., 3] = 0.45
        im = Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA"); dd = ImageDraw.Draw(im)
        dd.rectangle((1, 1, w - 2, h - 2), outline=(40, 36, 34, 255), width=4)
        dd.rectangle((8, 8, w - 9, h - 9), outline=(20, 20, 22, 160), width=2)
        OUT.mkdir(parents=True, exist_ok=True); im.save(OUT / f"asphalt_patch_{k}.png", optimize=True)
    # わだち(タイヤ通過帯の黒ずみ・磨き): u=進行方向 4m タイル, v=幅0.7m
    n = 512
    rut = np.zeros((n // 4, n, 4)); yy = np.linspace(-1, 1, n // 4)[:, None]
    band = np.exp(-(yy * 1.6) ** 2)
    streak = 0.6 + 0.4 * tnoise(n, 1.4, 120)[:n // 4]
    rut[..., :3] = rgb("#0c0c0e"); rut[..., 3] = np.clip(band * streak * 0.16, 0, 1)
    save("asphalt_rut.png", rut, "RGBA")
    # グレーチング 0.3 x 0.6 m(横格子)
    im = Image.new("RGBA", (200, 400), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
    dd.rectangle((0, 0, 199, 399), fill=(58, 58, 60, 255), outline=(34, 34, 36, 255), width=6)
    for i in range(12):
        y = 22 + i * 30
        dd.rectangle((16, y, 183, y + 16), fill=(14, 14, 16, 255))
    im.save(OUT / "grating.png", optimize=True)
    # 集水桝の蓋(円) 0.6m
    im = Image.new("RGBA", (256, 256), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
    dd.ellipse((4, 4, 251, 251), fill=(64, 64, 66, 255), outline=(30, 30, 32, 255), width=6)
    for i in range(9):
        y = 48 + i * 20
        dd.line([(70, y), (186, y)], fill=(16, 16, 18, 255), width=7)
    im.save(OUT / "drain_inlet.png", optimize=True)
    # 側溝(U字溝の蓋): 1.0m x 0.3m タイル, 細いスリット
    n1, n2 = 1000, 300
    g = np.zeros((n2, n1, 3)); g[:] = rgb("#7c7b76") * (0.92 + 0.12 * np.random.default_rng(130).random((n2, n1)))[..., None]
    gi = Image.fromarray((g * 255).astype(np.uint8)); dd = ImageDraw.Draw(gi)
    dd.rectangle((0, 0, n1 - 1, 5), fill=(70, 70, 68)); dd.rectangle((0, n2 - 6, n1 - 1, n2 - 1), fill=(70, 70, 68))
    for x in (0, 500):
        dd.rectangle((x, 0, x + 3, n2), fill=(50, 50, 50))
    for x in range(40, 480, 70):
        dd.rectangle((x, 90, x + 40, 210), fill=(24, 24, 26)); dd.rectangle((x + 500, 90, x + 540, 210), fill=(24, 24, 26)) if x + 540 < n1 else None
    gi.save(OUT / "gutter.png", optimize=True)


def main():
    asphalt(); sidewalk(); concrete(); ballast(); ground(); paint_wear(); markings(); road_decals(); ads()
    print(sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()


# ---------- 広告アトラス(野立て看板・サイネージ・バス停広告用。架空のブランド名のみ) ----------
AD_PANELS = [
    ("SALE", "#d8231f", "#ffffff"), ("OPEN", "#1b4fa8", "#ffffff"), ("海辺の街で、あそぼう。", "#0b7a8a", "#ffffff"), ("DAIBA", "#222b3a", "#ffd23f"),
    ("ご当地グルメ", "#e8a317", "#2a1d0a"), ("新生活応援", "#6b4aa8", "#ffffff"), ("SUMMER FES", "#ff5b7f", "#ffffff"), ("ゆったり温泉", "#2e7d4f", "#f7f3e6"),
    ("BAYSIDE", "#0a2342", "#8fd3ff"), ("ショッピング", "#c2185b", "#fff1f6"), ("EV CHARGE", "#00a86b", "#ffffff"), ("駐車場 P", "#1b4fa8", "#ffffff"),
    ("Cafe & Dining", "#4e342e", "#ffe9c7"), ("Tokyo Night View", "#101820", "#ffb703"), ("安全第一", "#f2c500", "#111111"), ("お台場マップ", "#eef2f5", "#1b4fa8"),
]
AD_CELL = (512, 256)


def ads():
    import json
    cols = 4
    rows = (len(AD_PANELS) + cols - 1) // cols
    W, H = AD_CELL[0] * cols, AD_CELL[1] * rows
    im = Image.new("RGB", (W, H))
    meta = {"size": [W, H], "panels": []}
    fp = None
    for line in subprocess.run(["fc-list", ":lang=ja", "file"], capture_output=True, text=True).stdout.splitlines():
        if "NotoSansCJK-Bold" in line:
            fp = line.split(":")[0].strip()
            break
    for i, (txt, bg, fg) in enumerate(AD_PANELS):
        x, y = (i % cols) * AD_CELL[0], (i // cols) * AD_CELL[1]
        d = ImageDraw.Draw(im)
        d.rectangle((x, y, x + AD_CELL[0] - 1, y + AD_CELL[1] - 1), fill=bg)
        # 帯・グラデ風の装飾
        for k in range(6):
            d.polygon([(x + 320 + k * 30, y), (x + 360 + k * 30, y), (x + 200 + k * 30, y + AD_CELL[1]), (x + 160 + k * 30, y + AD_CELL[1])], fill=tuple(min(255, int(int(bg[j:j + 2], 16) * (1.0 + 0.04 * k))) for j in (1, 3, 5)))
        d.rectangle((x + 8, y + 8, x + AD_CELL[0] - 9, y + AD_CELL[1] - 9), outline=fg, width=4)
        f = ImageFont.truetype(fp, 64 if len(txt) < 8 else 44, index=0) if fp else ImageFont.load_default()
        d.text((x + AD_CELL[0] / 2, y + AD_CELL[1] / 2), txt, font=f, fill=fg, anchor="mm")
        meta["panels"].append(dict(name=txt, uv=[x / W, 1 - (y + AD_CELL[1]) / H, (x + AD_CELL[0]) / W, 1 - y / H]))
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / "ad_atlas.png", optimize=True)
    (OUT / "ad_atlas.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
