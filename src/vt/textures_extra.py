"""田舎・郊外・工業・ロードサイド用テクスチャを手続き生成(git管理)。屋根瓦/サイディング/波板/ブロック塀/コンクリート汚れ/店舗看板アトラス。
uv run python -m vt.textures_extra  (店舗名・社名はすべて架空)"""
import json
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .textures import OUT, rgb, save, tnoise

N = 1024


def _uv():
    y, x = np.mgrid[0:N, 0:N] / N
    return x, 1 - y          # 画像の上=v大


def _sm(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _tile_rows(nx, ny, seed, stagger=0.0):
    """セル分割: (セル内u, セル内v, セルID乱数)"""
    x, v = _uv()
    r = np.random.default_rng(seed)
    j = np.floor(v * ny).astype(int)
    off = (j % 2) * stagger / nx
    xx = (x + off) * nx
    i = np.floor(xx).astype(int)
    rnd = r.random((nx + 1, ny + 1))[i % nx, j % ny]
    return xx - i, v * ny - j, rnd


def kawara(name, col, nx=5, ny=6, seed=1, stagger=0.0):
    """桟瓦: 波打つ断面+上の瓦に覆われる下端の影。col=基調色。"""
    u, v, rnd = _tile_rows(nx, ny, seed, stagger)
    wave = 0.82 + 0.18 * np.cos(2 * np.pi * u)
    lip = 0.35 + 0.65 * _sm(0.0, 0.7, v)                  # v=0が軒側(下端)=厚い縁
    lip = np.where(v < 0.07, 1.08, lip)
    gap = 1 - 0.5 * (1 - _sm(0.0, 0.03, u)) - 0.5 * _sm(0.97, 1.0, u)
    shade = wave * lip * (0.35 + 0.65 * gap)
    g = shade * (0.9 + 0.2 * rnd) * (0.9 + 0.2 * tnoise(N, 1.4, seed + 2))
    img = g[..., None] * rgb(col)
    img *= (1 + 0.18 * (tnoise(N, 0.6, seed + 3) - 0.5))[..., None]
    save(name, img * 1.7)
    return g


def hon_gawara(name, col, seed=5):
    """本瓦葺き: 平瓦(凹)と丸瓦(凸)が縦に交互に並ぶ。"""
    x, v = _uv()
    nx = 4
    u = (x * nx) % 1.0
    round_ = (u > 0.38) & (u < 0.62)
    prof = np.where(round_, 0.9 + 0.1 * np.cos((u - 0.5) / 0.12 * np.pi), 0.62 + 0.14 * np.cos(2 * np.pi * u))
    seg = (v * 5) % 1.0
    joint = 1 - 0.45 * (1 - _sm(0.0, 0.04, seg))
    lip = 0.55 + 0.45 * _sm(0.0, 0.8, seg)
    g = prof * joint * lip * (0.88 + 0.2 * tnoise(N, 1.3, seed))
    img = g[..., None] * rgb(col) * (1 + 0.15 * (tnoise(N, 0.7, seed + 1) - 0.5))[..., None]
    save(name, img * 1.7)


def standing_seam(name, col, seed=7, seam=0.4, size=1.6):
    """瓦棒/立平葺き金属屋根: 縦のはぜ。"""
    x, v = _uv()
    nx = int(size / seam)
    u = (x * nx) % 1.0
    rib = np.exp(-((u - 0.5) / 0.06) ** 2)
    g = 0.85 - 0.25 * rib + 0.1 * (1 - np.abs(u - 0.5) * 2) * 0.3
    g = g + 0.06 * np.where(u < 0.06, 1, 0)
    rust = _sm(0.55, 0.9, tnoise(N, 1.8, seed))
    img = g[..., None] * rgb(col) * (1 + 0.06 * (tnoise(N, 0.5, seed + 1) - 0.5))[..., None]
    img = img * (1 - 0.45 * rust[..., None]) + 0.45 * rust[..., None] * rgb("#7a4a2a") * g[..., None]
    save(name, img)


def shingle(name, col, seed=9, nx=6, ny=8):
    """スレート/コロニアル: 平板の千鳥。"""
    u, v, rnd = _tile_rows(nx, ny, seed, stagger=0.5)
    lip = 0.5 + 0.5 * _sm(0.0, 0.6, v)
    edge = 1 - 0.4 * (1 - _sm(0.0, 0.04, u)) - 0.4 * _sm(0.96, 1.0, u)
    g = lip * edge * (0.85 + 0.3 * rnd) * (0.9 + 0.2 * tnoise(N, 1.2, seed + 1))
    img = g[..., None] * rgb(col)
    save(name, img * 1.6)


def shitami(name, col, n_boards=10, seed=11):
    """下見板張り(板が重なる)+木目。"""
    x, v = _uv()
    seg = (v * n_boards) % 1.0
    ov = 0.4 + 0.6 * _sm(0.0, 0.85, seg)
    ov = np.where(seg < 0.05, 0.2, ov)
    grain = tnoise(N, 0.2, seed) * 0.5 + 0.5 * np.sin((x * 6 + 0.9 * tnoise(N, 1.5, seed + 1)) * 2 * np.pi * 8) * 0.5
    g = ov * (0.72 + 0.28 * (0.6 * grain + 0.4 * tnoise(N, 1.0, seed + 2)))
    img = g[..., None] * rgb(col)
    img *= (1 + 0.25 * (tnoise(N, 1.2, seed + 3) - 0.5))[..., None]
    save(name, img)


def siding(name, col, rows=8, seed=13, brick=False):
    """窯業系サイディング: 横張りのパネル+目地、レンガ/石目エンボス。"""
    x, v = _uv()
    seg = (v * rows) % 1.0
    joint = 1 - 0.7 * (1 - _sm(0.0, 0.035, seg))
    j = (np.floor(v * rows)).astype(int)
    vj = ((x * 2 + (j % 2) * 0.37) % 1.0)
    vjoint = 1 - 0.5 * (1 - _sm(0.0, 0.012, vj)) * (1 if brick else 0.0)
    emb = tnoise(N, 0.35, seed) * 0.5 + 0.5 * tnoise(N, 1.2, seed + 1)
    if brick:
        bw, bh = 0.18, 0.06
        xi = x / bw; yi = v / bh
        bu = (xi + (np.floor(yi) % 2) * 0.5) % 1.0
        bv = yi % 1.0
        mort = (bu < 0.05) | (bv < 0.08)
        emb = np.where(mort, 0.3, 0.55 + 0.45 * emb)
    g = joint * vjoint * (0.8 + 0.2 * emb) * (0.95 + 0.1 * tnoise(N, 1.6, seed + 2))
    save(name, g[..., None] * rgb(col))


def corrugated(name, col_, seed=17, pitch=0.076, size=1.2, rust=0.45):
    """波板(トタン): 縦の波+錆と汚れ。"""
    x, v = _uv()
    nx = int(size / pitch)
    u = (x * nx) % 1.0
    prof = 0.5 + 0.5 * np.cos(2 * np.pi * u)
    light = 0.62 + 0.38 * prof
    r = _sm(1 - rust * 0.6, 1.0, 0.7 * tnoise(N, 0.9, seed) + 0.3 * tnoise(N, 0.3, seed + 1))              # 小さな錆斑
    col = tnoise(N, 1.4, seed + 2)[0:1, :]                                                                  # 縦の雨だれ筋(列ごとの濃淡)
    drip = (_sm(0.55, 1.0, col) * (1.0 - 0.7 * v))
    img = light[..., None] * rgb(col_)
    img = img * (1 - 0.55 * r[..., None]) + 0.55 * r[..., None] * rgb("#8a4a26") * light[..., None]
    img *= (1 - 0.22 * drip[..., None])
    img *= (0.94 + 0.12 * tnoise(N, 0.4, seed + 3))[..., None]
    save(name, np.clip(img, 0, 1))


def cmu_block(name, seed=19):
    """コンクリートブロック(390x190 + 目地)、わずかに汚れ。"""
    x, v = _uv()
    bw, bh = 0.39, 0.19
    xi = x * 1.17 / bw; yi = v * 1.14 / bh
    bu = (xi + (np.floor(yi) % 2) * 0.5) % 1.0
    bv = yi % 1.0
    mort = (bu < 0.035) | (bv < 0.06)
    g = np.where(mort, 0.5, 0.72 + 0.28 * tnoise(N, 0.4, seed))
    g = g * (0.86 + 0.2 * tnoise(N, 1.5, seed + 1))
    img = g[..., None] * rgb("#a8a7a2")
    save(name, img)


def concrete_stained(name, seed=23):
    """雨だれ・錆汁・カビの縦筋が出た経年コンクリート(高架橋脚・塀・擁壁用)。"""
    x, v = _uv()
    base = 0.62 + 0.14 * tnoise(N, 1.4, seed) + 0.05 * tnoise(N, 0.3, seed + 1)
    streak = _sm(0.5, 0.95, tnoise(N, 2.4, seed + 2)[:, :] * np.abs(np.sin(x * 2 * np.pi * 5 + 3 * tnoise(N, 2.0, seed + 3))))
    top = 1 - _sm(0.0, 0.7, 1 - v)
    mold = _sm(0.62, 0.9, tnoise(N, 1.9, seed + 4)) * (1 - v) * 0.8
    img = base[..., None] * rgb("#a6a49e")
    img *= (1 - 0.35 * (streak * (0.4 + 0.6 * top))[..., None])
    img = img * (1 - 0.5 * mold[..., None]) + 0.5 * mold[..., None] * rgb("#3a4a34") * base[..., None]
    pan = np.where(((v * 4) % 1.0) < 0.012, 0.6, 1.0) * np.where(((x * 3) % 1.0) < 0.01, 0.6, 1.0)   # 型枠の目地
    img *= pan[..., None]
    save(name, img)


def steel_painted(name, col, seed=29, rust=0.3):
    """塗装鋼板/鋼材の経年: 塗膜剥がれの錆と汚れ。"""
    x, v = _uv()
    base = 0.85 + 0.1 * tnoise(N, 1.2, seed)
    r = _sm(1 - rust, 1.0, tnoise(N, 2.0, seed + 1) * (0.6 + 0.6 * (1 - v)))
    img = base[..., None] * rgb(col)
    img = img * (1 - 0.8 * r[..., None]) + 0.8 * r[..., None] * rgb("#7a4020") * (0.6 + 0.5 * tnoise(N, 0.4, seed + 2))[..., None]
    save(name, img)


# ---------------- 店舗看板アトラス(架空の店名のみ) ----------------
SHOPS = [  # (キー, 表示, 背景, 文字, アクセント)
    ("conv_a", "ミニマート 24", "#0b6e4f", "#ffffff", "#f2b705"), ("conv_b", "ライフポート", "#1b4fa8", "#ffffff", "#e8321c"), ("conv_c", "コンビニ ここまち", "#e8561c", "#ffffff", "#ffe08a"),
    ("drug_a", "ドラッグ ひなた", "#1e8a4c", "#ffffff", "#f7e600"), ("drug_b", "くすりのマツノ", "#c2185b", "#ffffff", "#ffffff"),
    ("family_a", "ファミリーレストラン そら", "#b01c24", "#ffffff", "#ffd23f"), ("family_b", "Grill & Cafe ハナミズキ", "#3a2a1c", "#ffe9c7", "#c9302c"),
    ("super_a", "スーパー マルヨシ", "#e8a317", "#1a1a1a", "#c8201c"), ("super_b", "フードマーケット あおぞら", "#2a7ab8", "#ffffff", "#ffe066"),
    ("home_a", "ホームセンター ダイヤ", "#f28c00", "#1a1a1a", "#ffffff"), ("home_b", "DIYランド 山田屋", "#0a6a3a", "#ffffff", "#ffd700"),
    ("pachi_a", "パチンコ ゴールデン宮殿", "#b8860b", "#2a0a0a", "#ff2a2a"), ("pachi_b", "遊技場 ミラクル777", "#6a1b9a", "#fff1a8", "#ff4081"),
    ("car_a", "カーディーラー 東日本モーターズ", "#1c2a4a", "#ffffff", "#c0c0c0"), ("car_b", "中古車 オートプラザ", "#d8231f", "#ffffff", "#ffe600"),
    ("ramen_a", "らーめん 麺道", "#a4161a", "#ffe9a8", "#000000"), ("ramen_b", "ラーメン 一心", "#1a1a1a", "#ffd23f", "#c8201c"),
    ("shop100_a", "100円ショップ ワンコ屋", "#e8c200", "#c8201c", "#ffffff"), ("shop100_b", "均一ショップ ミライ", "#0e9aa7", "#ffffff", "#ffe600"),
    ("karaoke", "カラオケ ビッグボイス", "#7b1fa2", "#ffffff", "#ffee58"), ("bank", "信用金庫 みなと", "#00695c", "#ffffff", "#ffffff"),
    ("gs_a", "エナジー石油 24h", "#e8321c", "#ffffff", "#ffd23f"), ("gs_b", "セルフ給油 ブルーオイル", "#0a4a9a", "#ffffff", "#ff7a00"),
    ("udon", "手打ちうどん 讃岐", "#2d4a2a", "#f7f3e6", "#c8201c"),
    ("fac_a", "東洋化学工業株式会社", "#d9dedf", "#14345a", "#14345a"), ("fac_b", "日本鋳造 KOGYO", "#e6e0d0", "#8a1a1a", "#8a1a1a"),
    ("fac_c", "○○製作所 第二工場", "#cfd6d4", "#22302a", "#22302a"), ("fac_d", "関東物流センター", "#f3f3f0", "#1b4fa8", "#e8321c"),
    ("fac_e", "ミナト食品 工場", "#f1ecd8", "#b03a1c", "#b03a1c"), ("fac_f", "株式会社 大和製鋼", "#c8cdd0", "#1a1a1a", "#c8201c"),
    ("park_a", "コインパーキング 24h", "#1b4fa8", "#ffffff", "#ffe600"), ("park_b", "月極駐車場 空有", "#ffffff", "#1b4fa8", "#1b4fa8"),
    ("cl_a", "ブティック こころ", "#2a2a2a", "#ffffff", "#ffb7c5"), ("cl_b", "洋服の青海", "#1b4fa8", "#ffffff", "#ffe600"),
    ("shoe", "くつの専門店 あゆみ", "#c0392b", "#ffffff", "#ffffff"), ("bk", "古書 ブックフォレスト", "#4e342e", "#ffe9c7", "#ffe9c7"),
    ("rent", "レンタルビデオ ビデオ館", "#0277bd", "#ffee58", "#ffffff"), ("hosp", "あおぞら内科クリニック", "#e8f5e9", "#1b5e20", "#1b5e20"),
    ("dental", "さくら歯科医院", "#fce4ec", "#ad1457", "#ad1457"), ("wash", "コインランドリー ピカピカ", "#26c6da", "#ffffff", "#ffffff"),
    ("sushi", "回転寿司 海鮮丸", "#b71c1c", "#ffffff", "#ffe082"), ("bake", "ベーカリー こむぎ", "#ffcc80", "#4e342e", "#4e342e"),
    ("izaka", "居酒屋 酔いどれ", "#212121", "#ff5252", "#ffd54f"), ("gym", "フィットネス ジムパーク", "#37474f", "#ffffff", "#76ff03"),
    ("nursery", "ひまわり保育園", "#fff59d", "#e65100", "#e65100"), ("tire", "タイヤ館 ロードランナー", "#212121", "#ffd600", "#ffffff"),
    ("used", "リサイクルショップ もったいない", "#4caf50", "#ffffff", "#ffeb3b"), ("agri", "JA みどり農協", "#2e7d32", "#ffffff", "#ffeb3b"),
    ("sos", "非常電話", "#e8741a", "#ffffff", "#ffffff"), ("estair", "非常階段", "#1b7a3a", "#ffffff", "#ffffff"), ("pier_no", "P-1234", "#e6e6e0", "#14345a", "#14345a"),
    ("etc", "ETC 専用", "#5a2a9a", "#ffffff", "#ffe600"), ("nostop", "停車禁止 高速道路", "#d8231f", "#ffffff", "#ffffff"),
]
CELL = (512, 160)
COLS = 6


def _font(size):
    fp = None
    for line in subprocess.run(["fc-list", ":lang=ja", "file"], capture_output=True, text=True).stdout.splitlines():
        if "NotoSansCJK-Bold" in line or "NotoSansCJKjp-Bold" in line:
            fp = line.split(":")[0].strip()
            break
    return ImageFont.truetype(fp, size, index=0) if fp else ImageFont.load_default()


def shop_atlas():
    rows = (len(SHOPS) + COLS - 1) // COLS
    W, H = CELL[0] * COLS, CELL[1] * rows
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    meta = {"size": [W, H], "panels": {}}
    for i, (key, txt, bg, fg, ac) in enumerate(SHOPS):
        x, y = (i % COLS) * CELL[0], (i // COLS) * CELL[1]
        d.rectangle((x, y, x + CELL[0] - 1, y + CELL[1] - 1), fill=bg)
        d.rectangle((x, y, x + CELL[0] - 1, y + 14), fill=ac)
        d.rectangle((x, y + CELL[1] - 14, x + CELL[0] - 1, y + CELL[1] - 1), fill=ac)
        size = 72 if len(txt) <= 6 else 56 if len(txt) <= 9 else 44 if len(txt) <= 13 else 34
        f = _font(size)
        while d.textlength(txt, font=f) > CELL[0] - 28 and size > 16:
            size -= 2
            f = _font(size)
        d.text((x + CELL[0] / 2 + 2, y + CELL[1] / 2 + 3), txt, font=f, fill="#00000060", anchor="mm")
        d.text((x + CELL[0] / 2, y + CELL[1] / 2), txt, font=f, fill=fg, anchor="mm")
        meta["panels"][key] = dict(name=txt, uv=[x / W, 1 - (y + CELL[1]) / H, (x + CELL[0]) / W, 1 - y / H], aspect=CELL[0] / CELL[1])
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / "shop_atlas.png", optimize=True)
    (OUT / "shop_atlas.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))


def main():
    kawara("roof_kawara.png", "#555a60", seed=1, stagger=0.0)
    kawara("roof_kawara_brown.png", "#7a4a36", seed=2, stagger=0.0)
    hon_gawara("roof_kawara_hon.png", "#4b4f52")
    kawara("roof_cement_red.png", "#9a4a34", nx=4, ny=5, seed=3)
    kawara("roof_cement_blue.png", "#3c4f6a", nx=4, ny=5, seed=4)
    standing_seam("roof_tanshiki_blue.png", "#34506e")
    standing_seam("roof_tanshiki_green.png", "#3c5e48", seed=8)
    standing_seam("roof_tanshiki_red.png", "#8a3a2c", seed=9)
    standing_seam("roof_tanshiki_gray.png", "#6a7074", seed=10)
    shingle("roof_slate_dark.png", "#3a3d42", seed=9)
    shingle("roof_slate_brown.png", "#5a4034", seed=10)
    shitami("siding_shitami.png", "#4a3426")
    shitami("siding_shitami_light.png", "#8a6a48", seed=12)
    siding("siding_ceramic_cream.png", "#c4b896", seed=13)
    siding("siding_ceramic_gray.png", "#8c8f8e", seed=14)
    siding("siding_ceramic_brick.png", "#6a3426", seed=15, brick=True)
    corrugated("corrugated_gray.png", "#868e92", seed=17, rust=0.28)
    corrugated("corrugated_blue.png", "#476a8a", seed=18, rust=0.1)
    corrugated("corrugated_green.png", "#547a62", seed=19, rust=0.1)
    corrugated("corrugated_cream.png", "#b8b08c", seed=20, rust=0.2)
    cmu_block("cmu_block.png")
    concrete_stained("concrete_stained.png")
    steel_painted("steel_rusty_gray.png", "#8a9094", rust=0.35)
    shop_atlas()
    print("ok")


if __name__ == "__main__":
    main()
