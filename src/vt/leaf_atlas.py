"""葉スキャン(灰色背景JPG)→葉スプライト抽出→枝/葉塊/針葉/椰子/花カード合成→1枚のRGBAアトラス+JSON。ZIPは展開せずメモリ上で画像のみ読む。"""
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
from scipy.spatial import ConvexHull

OUT = Path(__file__).resolve().parents[2] / "assets/textures"
AW, AH = 4096, 4096
MIN_AREA = 500          # px。これ未満の欠片は捨てる
MAX_LONG = 150          # スプライトの長辺の上限(px)


# ---------------------------------------------------------------- 1. 抽出
def read_images(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        for name in sorted(zf.namelist()):
            if name.startswith("__MACOSX") or "/." in name or not name.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            im = Image.open(io.BytesIO(zf.read(name)))
            if im.width * im.height > 40_000_000:
                continue
            yield Path(name).stem, im.convert("RGB")


def extract_sprites(name, im):
    """背景(灰色)をキーにして葉を1枚ずつRGBAスプライトに。縁は灰色を内側の色で置換(デフリンジ)し、アルファは滑らかに。"""
    a = np.asarray(im).astype(np.float32)
    chroma = a.max(2) - a.min(2)
    bg = np.median(a[chroma < 9], axis=0)
    d = np.sqrt(((a - bg) ** 2).sum(2))
    m = d > 24
    m = ndi.binary_opening(m, iterations=1)
    m = ndi.binary_closing(m, iterations=2)
    m = ndi.binary_fill_holes(m)
    lab, n = ndi.label(m)
    areas = ndi.sum(m, lab, range(1, n + 1))
    good = areas[areas > MIN_AREA]
    med = float(np.median(good)) if len(good) else 1.0
    sprites = []
    H, W = m.shape
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        if sl is None:
            continue
        ys, xs = sl
        area = areas[i - 1]
        if area < MIN_AREA or area > 4.2 * med:                  # 欠片 / 複数枚がくっついた塊
            continue
        if ys.start <= 1 or xs.start <= 1 or ys.stop >= H - 1 or xs.stop >= W - 1:
            continue
        y0, y1, x0, x1 = max(ys.start - 5, 0), min(ys.stop + 5, H), max(xs.start - 5, 0), min(xs.stop + 5, W)
        comp = lab[y0:y1, x0:x1] == i
        reg = ndi.binary_dilation(comp, iterations=2)
        dd = d[y0:y1, x0:x1]
        alpha = np.clip((dd - 12) / 18.0, 0, 1) * reg
        core = ndi.binary_erosion(comp, iterations=2)
        alpha = np.maximum(alpha, core.astype(np.float32))
        alpha = ndi.gaussian_filter(alpha, 0.6)
        alpha[~reg] = 0
        rgb = a[y0:y1, x0:x1].copy()
        solid = alpha > 0.97
        if solid.sum() < 50:
            continue
        idx = ndi.distance_transform_edt(~solid, return_distances=False, return_indices=True)
        rgb = rgb[idx[0], idx[1]]                                  # 灰色の縁を内側の色で上書き
        yy, xx = np.nonzero(comp)
        pts = np.stack([xx, yy], 1).astype(np.float32)
        try:
            hull = ConvexHull(pts)
            solidity = float(comp.sum() / hull.volume)
        except Exception:
            continue
        c = pts - pts.mean(0)
        ev, evec = np.linalg.eigh(np.cov(c.T))
        aspect = float(math.sqrt(ev[1] / max(ev[0], 1e-6)))
        spr = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8), "RGBA")
        spr = spr.crop(spr.getbbox())
        sprites.append(dict(img=spr, src=name, solidity=solidity, aspect=aspect, axis=evec[:, 1]))
    return sprites


def classify(sp):
    s, a, src = sp["solidity"], sp["aspect"], sp["src"]
    if "ivy" in src or s < 0.86:
        return "ivy" if s < 0.93 else "round"
    if a > 3.2:
        return "narrow"
    if a > 1.3:
        return "oval"
    return "round"


def orient(sp, cls):
    """楕円葉は長軸を縦にし、細い方(先端)を上へ"""
    im = sp["img"]
    if cls in ("oval", "narrow"):
        ax = sp["axis"]
        ang = math.degrees(math.atan2(ax[0], -ax[1]))
        im = im.rotate(ang, resample=Image.BICUBIC, expand=True)
        im = im.crop(im.getbbox())
        al = np.asarray(im)[..., 3] > 128
        h = al.shape[0]
        top = al[: h // 4].sum()
        bot = al[-h // 4:].sum()
        if top > bot:
            im = im.rotate(180)
    long = max(im.size)
    if long > MAX_LONG:
        k = MAX_LONG / long
        im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    return im


def avg_color(im):
    a = np.asarray(im).astype(np.float32)
    w = a[..., 3:4] / 255.0
    return [int(x) for x in (a[..., :3] * w).sum((0, 1)) / max(w.sum(), 1e-6)]


# ---------------------------------------------------------------- 2. 色変換(季節)
SEASONS = {
    "spring": dict(dh=+0.045, ds=-0.05, dv=+0.10),
    "summer": dict(dh=0.0, ds=0.0, dv=0.0),
    "autumn_y": dict(target=0.14, mix=0.85, ds=+0.25, dv=+0.18),
    "autumn_r": dict(target=0.02, mix=0.8, ds=+0.2, dv=-0.02),
}


def recolor(im, season, jitter=0.0):
    if season == "summer" and abs(jitter) < 1e-6:
        return im
    p = SEASONS[season]
    hsv = np.asarray(im.convert("RGB").convert("HSV")).astype(np.float32) / 255.0
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    if "target" in p:
        t = p["target"] + jitter * 0.04
        dh = ((t - h + 0.5) % 1.0) - 0.5
        h = (h + dh * p["mix"]) % 1.0
    else:
        h = (h + p["dh"] + jitter * 0.02) % 1.0
    s = np.clip(s + p["ds"], 0, 1)
    v = np.clip(v + p["dv"], 0, 1)
    out = Image.fromarray((np.dstack([h, s, v]) * 255).astype(np.uint8), "HSV").convert("RGB")
    out.putalpha(im.getchannel("A"))
    return out


def shade(im, k):
    a = np.asarray(im).astype(np.float32)
    a[..., :3] *= k
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


# ---------------------------------------------------------------- 3. カード合成
class Cards:
    def __init__(self, spr):
        self.spr = spr          # cls -> [RGBA Image]

    def pick(self, rng, cls):
        pool = self.spr.get(cls) or self.spr["oval"]
        return pool[int(rng.integers(len(pool)))]

    @staticmethod
    def paste(card, leaf, cx, cy, ang, length, season, rng, k=1.0, stretch=1.0):
        im = leaf
        sc = length / max(im.height, 1)
        im = im.resize((max(1, int(im.width * sc * stretch)), max(1, int(im.height * sc))), Image.BICUBIC)
        im = recolor(im, season, rng.normal(0, 0.5))
        if k != 1.0:
            im = shade(im, k)
        im = im.rotate(ang, resample=Image.BICUBIC, expand=True)
        card.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

    def cluster(self, w, h, cls, season, seed, leaf_px, dense=1.0, shape="blob"):
        """葉塊カード: 中心ほど暗く外周ほど明るい(焼き込みAO)。広い面に使い回して樹冠を作る。"""
        rng = np.random.default_rng(seed)
        card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        cx, cy = w / 2, h / 2
        n = int(w * h / (leaf_px * leaf_px) * 3.4 * dense)
        P = []
        for _ in range(n):
            if shape == "blob":
                r = (rng.random() ** 0.72) * 0.5 * (0.92 + 0.1 * math.sin(rng.random() * 9))
                t = rng.random() * 2 * math.pi
                x, y = cx + r * w * math.cos(t) * 0.97, cy + r * h * math.sin(t) * 0.97
            else:
                x, y = rng.random() * w, rng.random() * h
                r = math.hypot((x - cx) / w, (y - cy) / h)
            P.append((r, x, y))
        P.sort(key=lambda p: p[0])
        for r, x, y in P:
            leaf = self.pick(rng, cls)
            k = 0.55 + 0.6 * min(r * 2, 1.0) + rng.normal(0, 0.05)
            ang = rng.uniform(0, 360) if cls != "oval" or rng.random() < 0.5 else rng.normal(0, 70)
            self.paste(card, leaf, x, y, ang, leaf_px * rng.uniform(0.8, 1.25), season, rng, k=float(np.clip(k, 0.4, 1.15)))
        return card

    def twig(self, w, h, cls, season, seed, leaf_px, n_leaf=9, stretch=1.0):
        rng = np.random.default_rng(seed)
        card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        bx, by = w / 2, h - 4
        pts = []
        for i in range(21):
            t = i / 20
            pts.append((bx + math.sin(t * 2.6 + seed) * w * 0.07 * t, by - t * (h - 20)))
        col = (86, 62, 42, 255)
        d.line(pts, fill=col, width=max(2, w // 90))
        for i in range(1, n_leaf + 1):
            t = i / (n_leaf + 1)
            x, y = pts[int(t * 20)]
            side = 1 if i % 2 else -1
            ang = side * rng.uniform(35, 70)
            L = leaf_px * (1.15 - 0.45 * t) * rng.uniform(0.85, 1.15)
            ex, ey = x + side * L * 0.55, y - L * 0.35
            d.line([(x, y), (ex, ey)], fill=col, width=max(1, w // 180))
            self.paste(card, self.pick(rng, cls), ex, ey - L * 0.35, -ang * 0.7, L, season, rng, k=rng.uniform(0.8, 1.05), stretch=stretch)
        self.paste(card, self.pick(rng, cls), pts[-1][0], pts[-1][1] - leaf_px * 0.4, rng.normal(0, 10), leaf_px * 0.85, season, rng, stretch=stretch)
        return card

    def ginkgo(self, w, h, season, seed, leaf_px):
        """イチョウ: 扇形マスク(中央に浅い切れ込み)+実葉の質感。短枝に放射状に7枚"""
        rng = np.random.default_rng(seed)
        card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        S = 160
        fan = Image.new("L", (S * 2, S * 2), 0)
        fd = ImageDraw.Draw(fan)
        pts = [(S, S * 1.9)]
        for k in range(41):
            a = math.radians(-70 + 140 * k / 40)
            rr = S * 1.7 * (1 - 0.18 * math.exp(-((k - 20) / 3.0) ** 2)) * (0.97 + 0.03 * math.sin(k * 1.7))
            pts.append((S + rr * math.sin(a), S * 1.9 - rr * math.cos(a)))
        fd.polygon(pts, fill=255)
        fan = fan.filter(ImageFilter.GaussianBlur(1.2))
        for i in range(7):
            base = self.pick(rng, "round").resize((S * 2, S * 2), Image.BICUBIC).convert("RGB")
            tex = np.asarray(base).astype(np.float32) * 0.6 + np.array([140, 150, 40]) * 0.4
            leaf = Image.fromarray(np.clip(tex, 0, 255).astype(np.uint8), "RGB")
            leaf.putalpha(fan)
            leaf = leaf.crop(leaf.getbbox())
            ang = -60 + 120 * i / 6 + rng.normal(0, 8)
            r = leaf_px * rng.uniform(0.9, 1.1)
            cx, cy = w / 2 + math.sin(math.radians(ang)) * r * 0.55, h * 0.6 - math.cos(math.radians(ang)) * r * 0.2
            self.paste(card, leaf, cx, cy, -ang * 0.8, r * 1.15, season, rng, k=rng.uniform(0.8, 1.05))
        return card

    def pine(self, w, h, seed, leaf_px):
        """クロマツ: 暗緑の針(2本束)が放射する針葉の房。手続き生成のみ"""
        rng = np.random.default_rng(seed)
        S2 = 2
        card = Image.new("RGBA", (w * S2, h * S2), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        cx, cy = w * S2 * 0.5, h * S2 * 0.62
        d.line([(w * S2 / 2, h * S2 - 2), (cx, cy)], fill=(70, 50, 36, 255), width=5)
        for _ in range(14):
            ta = rng.uniform(-80, 80)
            tcx = cx + math.sin(math.radians(ta)) * w * S2 * 0.32 * rng.random()
            tcy = cy - abs(math.cos(math.radians(ta))) * h * S2 * 0.28 * rng.random()
            for _k in range(46):
                a = math.radians(rng.uniform(-75, 75) + ta * 0.4)
                L = leaf_px * S2 * rng.uniform(0.7, 1.15)
                x1, y1 = tcx + math.sin(a) * L, tcy - math.cos(a) * L * 0.9
                g = int(rng.uniform(55, 100))
                d.line([(tcx, tcy), (tcx + (x1 - tcx) * 0.5 + rng.normal(0, 1), tcy + (y1 - tcy) * 0.5), (x1, y1)], fill=(int(g * 0.5), g, int(g * 0.38), 255), width=2)
        return card.resize((w, h), Image.LANCZOS)

    def palm(self, w, h, seed, kind="frond"):
        """ヤシ/シュロの葉: 羽状(カナリーヤシ)=中心軸+細い小葉、掌状(シュロ)=中心から放射する裂片"""
        rng = np.random.default_rng(seed)
        S2 = 2
        card = Image.new("RGBA", (w * S2, h * S2), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        if kind == "frond":
            n = 34
            x0, y0 = w * S2 * 0.06, h * S2 * 0.5
            x1, y1 = w * S2 * 0.97, h * S2 * 0.34
            d.line([(x0, y0), ((x0 + x1) / 2, h * S2 * 0.36), (x1, y1)], fill=(108, 120, 56, 255), width=7)
            for i in range(n):
                t = (i + 0.5) / n
                x = x0 + (x1 - x0) * t
                y = y0 + (y1 - y0) * t - math.sin(t * math.pi) * h * S2 * 0.12
                L = h * S2 * 0.42 * (math.sin(t * math.pi) ** 0.6) * rng.uniform(0.85, 1.05) + 6
                for side in (-1, 1):
                    a = math.radians(side * rng.uniform(58, 78) + 10)
                    g = rng.uniform(0.75, 1.1)
                    ex, ey = x + math.sin(a) * L * 0.35, y - math.cos(a) * L * 0.1 + side * L * 0.72
                    d.polygon([(x, y), ((x + ex) / 2 + 2, (y + ey) / 2 - 2), (ex, ey), ((x + ex) / 2 - 2, (y + ey) / 2 + 2)], fill=(int(58 * g), int(120 * g), int(44 * g), 255))
        else:
            cx, cy = w * S2 / 2, h * S2 * 0.92
            n = 26
            for i in range(n):
                a = math.radians(-100 + 200 * i / (n - 1))
                L = h * S2 * 0.9 * (0.9 + 0.1 * rng.random()) * (1 - 0.12 * abs(a) / 1.7)
                g = rng.uniform(0.8, 1.1)
                ex, ey = cx + math.sin(a) * L, cy - math.cos(a) * L
                nx, ny = math.cos(a) * 9, math.sin(a) * 9
                d.polygon([(cx, cy), (cx + (ex - cx) * 0.5 + nx, cy + (ey - cy) * 0.5 + ny), (ex, ey), (cx + (ex - cx) * 0.5 - nx, cy + (ey - cy) * 0.5 - ny)],
                          fill=(int(60 * g), int(118 * g), int(50 * g), 255))
            d.line([(cx, h * S2), (cx, cy)], fill=(110, 120, 60, 255), width=8)
        return card.resize((w, h), Image.LANCZOS)

    def flowers(self, w, h, season, seed, leaf_px, palette, kind="bed"):
        """花付きカード: 葉の塊の上に花(5弁)や小花の房"""
        rng = np.random.default_rng(seed)
        base = self.cluster(w, h, "oval", season, seed, leaf_px, dense=0.9, shape="blob")
        d = ImageDraw.Draw(base)
        n = {"bed": 26, "azalea": 40, "hydrangea": 16}[kind]
        for _ in range(n):
            r = math.sqrt(rng.random()) * 0.42
            t = rng.random() * 2 * math.pi
            x, y = w / 2 + r * w * math.cos(t), h / 2 + r * h * math.sin(t) * (0.9 if kind != "bed" else 1.0)
            col = palette[int(rng.integers(len(palette)))]
            if kind == "hydrangea":
                R = leaf_px * 0.95
                for _k in range(26):
                    px, py = x + rng.normal(0, R * 0.45), y + rng.normal(0, R * 0.4)
                    c2 = tuple(int(min(255, c * rng.uniform(0.85, 1.05))) for c in col)
                    for q in range(4):
                        a = q * math.pi / 2 + 0.4
                        d.ellipse([px + math.cos(a) * 4 - 4, py + math.sin(a) * 4 - 4, px + math.cos(a) * 4 + 4, py + math.sin(a) * 4 + 4], fill=c2 + (255,))
            else:
                R = leaf_px * 0.32 * rng.uniform(0.8, 1.2)
                for q in range(5):
                    a = q * 2 * math.pi / 5 + rng.random()
                    d.ellipse([x + math.cos(a) * R * 0.55 - R * 0.5, y + math.sin(a) * R * 0.55 - R * 0.5, x + math.cos(a) * R * 0.55 + R * 0.5, y + math.sin(a) * R * 0.55 + R * 0.5], fill=col + (255,))
                d.ellipse([x - R * 0.2, y - R * 0.2, x + R * 0.2, y + R * 0.2], fill=(240, 200, 60, 255))
        return base

    def grass(self, w, h, seed, kind="tuft"):
        """観賞用イネ科(パンパス/ススキ風): 弧を描く細い葉の房。kind=plume は穂付き"""
        rng = np.random.default_rng(seed)
        S2 = 2
        card = Image.new("RGBA", (w * S2, h * S2), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        for _ in range(70):
            x0 = w * S2 * (0.5 + rng.normal(0, 0.06))
            ang = rng.normal(0, 0.55)
            L = h * S2 * rng.uniform(0.55, 0.97)
            bend = rng.normal(0, 0.45)
            g = rng.uniform(0.7, 1.15)
            pts = []
            for i in range(11):
                t = i / 10
                a = ang + bend * t * t
                pts.append((x0 + math.sin(a) * L * t * 0.8 + 0, h * S2 - 2 - math.cos(a) * L * t))
            wd = max(2, int(5 * (1 - 0.0)))
            for i in range(10):
                d.line([pts[i], pts[i + 1]], fill=(int(70 * g), int(125 * g), int(45 * g), 255), width=max(1, wd - i // 2))
        if kind == "plume":
            for _ in range(5):
                x0 = w * S2 * (0.5 + rng.normal(0, 0.12))
                top = h * S2 * rng.uniform(0.04, 0.22)
                d.line([(x0, h * S2 * 0.5), (x0 + rng.normal(0, 14), top)], fill=(150, 150, 110, 255), width=3)
                for _k in range(60):
                    d.line([(x0 + rng.normal(0, 4), top + rng.random() * 70), (x0 + rng.normal(0, 22), top - rng.random() * 26 + 40)], fill=(236, 228, 205, 255), width=2)
        return card.resize((w, h), Image.LANCZOS)

    def sakura(self, w, h, seed, leaf_px, bloom=1.0):
        """桜(満開): 淡桃の5弁花が枝を覆う。葉はほぼ無い"""
        rng = np.random.default_rng(seed)
        card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        for _ in range(int(w * h / (leaf_px * leaf_px) * 3 * bloom)):
            r = (rng.random() ** 0.72) * 0.5
            t = rng.random() * 2 * math.pi
            x, y = w / 2 + r * w * math.cos(t), h / 2 + r * h * math.sin(t)
            R = leaf_px * rng.uniform(0.3, 0.45)
            col = (int(rng.uniform(243, 255)), int(rng.uniform(196, 222)), int(rng.uniform(205, 228)), 255)
            for q in range(5):
                a = q * 2 * math.pi / 5 + rng.random() * 0.3
                d.ellipse([x + math.cos(a) * R * 0.55 - R * 0.5, y + math.sin(a) * R * 0.55 - R * 0.5, x + math.cos(a) * R * 0.55 + R * 0.5, y + math.sin(a) * R * 0.55 + R * 0.5], fill=col)
            d.ellipse([x - R * 0.18, y - R * 0.18, x + R * 0.18, y + R * 0.18], fill=(215, 110, 130, 255))
        return card


# ---------------------------------------------------------------- 4. パック
def shelf_pack(items, W, H, gap=2):
    """items: [(key, w, h)] → ({key: (x,y)}, 使用高さ)。高さ順のシェルフ詰め"""
    items = sorted(items, key=lambda t: -t[2])
    pos = {}
    x = y = rowh = 0
    for key, w, h in items:
        if x + w + gap > W:
            x, y, rowh = 0, y + rowh + gap, 0
        pos[key] = (x, y)
        x += w + gap
        rowh = max(rowh, h)
    return pos, y + rowh


def build_cards(by):
    C = Cards(by)
    cards = []     # (name, kind, season, species, Image)
    seasons = ("spring", "summer", "autumn_y", "autumn_r")
    for ss in seasons:
        for v in range(3):
            cards.append((f"oval_cluster_{ss}_{v}", "cluster", ss, "broadleaf", C.cluster(384, 384, "oval", ss, 100 + v, 40)))
            cards.append((f"oval_twig_{ss}_{v}", "twig", ss, "broadleaf", C.twig(256, 320, "oval", ss, 200 + v, 56, 9)))
        for v in range(2):
            cards.append((f"lobed_cluster_{ss}_{v}", "cluster", ss, "lobed", C.cluster(384, 384, "ivy", ss, 300 + v, 62)))
            cards.append((f"ginkgo_{ss}_{v}", "twig", ss, "ginkgo", C.ginkgo(320, 256, ss, 400 + v, 120)))
        cards.append((f"round_cluster_{ss}_0", "cluster", ss, "broadleaf", C.cluster(384, 384, "round", ss, 500, 48)))
    for v in range(3):
        cards.append((f"willow_twig_{v}", "hang", "summer", "willow", C.twig(160, 448, "narrow", "summer", 600 + v, 80, 14, stretch=0.55)))
        cards.append((f"evergreen_cluster_{v}", "cluster", "summer", "evergreen", C.cluster(384, 384, "oval", "summer", 700 + v, 36, dense=1.3)))
        cards.append((f"shrub_cluster_{v}", "cluster", "summer", "shrub", C.cluster(256, 256, "oval", "summer", 800 + v, 28, dense=1.4)))
        cards.append((f"hedge_fill_{v}", "fill", "summer", "hedge", C.cluster(256, 256, "oval", "summer", 900 + v, 26, dense=1.6, shape="rect")))
        cards.append((f"ivy_wall_{v}", "fill", "summer", "ivy", C.cluster(256, 256, "ivy", "summer", 1000 + v, 44, dense=1.5, shape="rect")))
        cards.append((f"ivy_vine_{v}", "twig", "summer", "ivy", C.twig(192, 320, "ivy", "summer", 1100 + v, 52, 8)))
        cards.append((f"pine_tuft_{v}", "tuft", "summer", "pine", C.pine(320, 256, 1200 + v, 80)))
    for v in range(2):
        cards.append((f"grass_tuft_{v}", "tuft", "summer", "grass", C.grass(256, 256, 1800 + v, "tuft")))
        cards.append((f"grass_plume_{v}", "tuft", "summer", "grass", C.grass(256, 320, 1810 + v, "plume")))
    cards.append(("palm_frond_0", "frond", "summer", "palm", C.palm(512, 192, 1300, "frond")))
    cards.append(("palm_frond_1", "frond", "summer", "palm", C.palm(512, 192, 1301, "frond")))
    cards.append(("palm_fan_0", "fan", "summer", "palm", C.palm(256, 256, 1310, "fan")))
    cards.append(("palm_fan_1", "fan", "summer", "palm", C.palm(256, 256, 1311, "fan")))
    pal_az = [(222, 70, 110), (240, 120, 160), (246, 246, 246), (206, 40, 70)]
    pal_bed = [(250, 210, 40), (230, 70, 120), (150, 90, 200), (250, 250, 250), (250, 140, 40)]
    for i, pal in enumerate(([pal_az[0], pal_az[1]], [pal_az[2]], [pal_az[3], pal_az[0]])):
        cards.append((f"azalea_bloom_{i}", "cluster", "spring", "azalea", C.flowers(256, 256, "summer", 1400 + i, 28, pal, "azalea")))
    for i in range(3):
        cards.append((f"flowerbed_{i}", "fill", "summer", "flowerbed", C.flowers(256, 256, "summer", 1500 + i, 28, pal_bed, "bed")))
    for i, pal in enumerate(([(110, 140, 230), (150, 170, 240)], [(230, 120, 170), (240, 160, 200)])):
        cards.append((f"hydrangea_{i}", "cluster", "summer", "hydrangea", C.flowers(256, 256, "summer", 1600 + i, 40, pal, "hydrangea")))
    for i in range(3):
        cards.append((f"sakura_bloom_{i}", "cluster", "spring", "sakura", C.sakura(384, 384, 1700 + i, 40)))
        cards.append((f"sakura_mixed_{i}", "cluster", "spring", "sakura", C.sakura(384, 384, 1710 + i, 40, 0.8)))
    return cards


def build(zip_path):
    spr_all = []
    for name, im in read_images(zip_path):
        for sp in extract_sprites(name, im):
            sp["cls"] = classify(sp)
            sp["img"] = orient(sp, sp["cls"])
            spr_all.append(sp)
    by = {k: [] for k in ("oval", "round", "ivy", "narrow")}
    for sp in spr_all:
        by[sp["cls"]].append(sp["img"])
    if not by["narrow"]:
        by["narrow"] = [im for im in by["oval"] if im.height > 2.2 * im.width] or by["oval"]
    if len(by["ivy"]) < 4:
        by["ivy"] = by["round"] or by["oval"]
    if not by["round"]:
        by["round"] = by["oval"]
    cards = build_cards(by)
    raws = []
    for cls in ("oval", "round", "ivy", "narrow"):
        for j, im in enumerate(by[cls][:150]):
            raws.append((f"leaf_{cls}_{j}", cls, im))

    def pack(raws):
        items = [(("card", c[0]), c[4].width, c[4].height) for c in cards] + [(("raw", r[0]), r[2].width, r[2].height) for r in raws]
        return shelf_pack(items, AW, AH)
    pos, used = pack(raws)
    while used > AH and raws:
        raws = raws[: int(len(raws) * 0.9)]
        pos, used = pack(raws)
    atlas = Image.new("RGBA", (AW, AH), (0, 0, 0, 0))
    meta = dict(size=[AW, AH], source_sprites=len(spr_all), used_height=used, cards={}, leaves={})

    def uv(x, y, w, h):
        return [x / AW, 1 - (y + h) / AH, (x + w) / AW, 1 - y / AH]
    for name, kind, season, species, im in cards:
        x, y = pos[("card", name)]
        atlas.alpha_composite(im, (x, y))
        meta["cards"][name] = dict(kind=kind, season=season, species=species, rect=[x, y, im.width, im.height], uv=uv(x, y, im.width, im.height), avg=avg_color(im))
    for name, cls, im in raws:
        x, y = pos[("raw", name)]
        atlas.alpha_composite(im, (x, y))
        meta["leaves"][name] = dict(cls=cls, rect=[x, y, im.width, im.height], uv=uv(x, y, im.width, im.height), avg=avg_color(im))
    # 透明部の色を最寄りの不透明色で埋める(ミップ/バイリニアでの黒・灰色フリンジ防止)
    arr = np.asarray(atlas).astype(np.float32)
    solid = arr[..., 3] > 8
    idx = ndi.distance_transform_edt(~solid, return_distances=False, return_indices=True)
    out = np.dstack([arr[..., :3][idx[0], idx[1]], arr[..., 3]]).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(OUT / "leaves_atlas.png", optimize=True)
    meta["classes"] = {k: len(v) for k, v in by.items()}
    (OUT / "leaves_atlas.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return meta


def load_meta():
    return json.loads((OUT / "leaves_atlas.json").read_text())
