"""樹皮テクスチャ(タイル可能・手続き生成)を assets/textures/bark_*.png へ。uv run python -m vt.veg_textures"""
import numpy as np
from PIL import Image

from .textures import OUT, tnoise

N = 512


def _rgb(c):
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def _ramp(g, stops):
    """g(0..1) → stopsの色ランプ [(pos, '#rrggbb'), ...]"""
    pos = np.array([p for p, _ in stops])
    cols = np.array([_rgb(c) for _, c in stops])
    return np.stack([np.interp(g, pos, cols[:, k]) for k in range(3)], -1)


def _stretch(seed, beta, ax, k):
    """一方向に伸ばした(縦裂け/横皮目の)タイル可能ノイズ"""
    a = tnoise(N, beta, seed)
    sm = np.fft.fft2(a)
    f = np.fft.fftfreq(N)
    ky = f[:, None] if ax == 0 else f[None, :]
    sm = sm * np.exp(-(ky * k) ** 2 * 40)
    b = np.real(np.fft.ifft2(sm))
    return (b - b.min()) / (b.max() - b.min())


def furrow(name, stops, seed, depth=1.0):
    ridge = _stretch(seed, 1.1, 1, 1.0)            # x方向に細かく=縦裂け
    base = _stretch(seed + 1, 1.8, 1, 0.5)
    h = 0.6 * ridge + 0.4 * base
    shade = np.clip(h + 0.25 * (tnoise(N, 0.7, seed + 2) - 0.5), 0, 1)
    img = _ramp(shade, stops)
    crack = np.clip((0.35 - h) * 5, 0, 1) * depth
    img *= (1 - 0.55 * crack[..., None])
    lichen = tnoise(N, 2.0, seed + 3) > 0.74
    img = np.where(lichen[..., None], img * 0.7 + _rgb("#8fa58a") * 0.3, img)
    save(name, img)


def smooth(name, seed):
    g = tnoise(N, 1.4, seed)
    img = _ramp(g, [(0, "#2c2328"), (0.5, "#4a3b3a"), (1, "#6e5d57")])
    stripe = _stretch(seed + 5, 0.4, 0, 0.9)           # 横に伸びた皮目
    lenti = (stripe > 0.74) & (tnoise(N, 0.2, seed + 6) > 0.52)
    img = np.where(lenti[..., None], _rgb("#b9a79a") * 0.9, img)
    save(name, img)


def plane(name, seed):
    g = tnoise(N, 2.2, seed)
    patch = (g > 0.52).astype(float)
    img = _ramp(tnoise(N, 1.0, seed + 1), [(0, "#6b6a55"), (1, "#a8a384")]) * (1 - patch[..., None]) + _ramp(tnoise(N, 1.0, seed + 2), [(0, "#d9d4bb"), (1, "#efe9d0")]) * patch[..., None]
    edge = np.abs(g - 0.52) < 0.012
    img = np.where(edge[..., None], img * 0.55, img)
    save(name, img)


def pine(name, seed):
    from scipy import ndimage as ndi
    r = np.random.default_rng(seed)
    pts = r.random((70, 2)) * N
    yy, xx = np.mgrid[0:N, 0:N]
    best = np.full((N, N), 1e9)
    second = np.full((N, N), 1e9)
    for (px, py) in pts:
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                d = np.hypot((xx - px - ox) * 0.8, (yy - py - oy) * 1.5)
                m = d < best
                second = np.where(m, best, np.minimum(second, d))
                best = np.where(m, d, best)
    edge = np.clip((second - best) / 7.0, 0, 1)
    tone = tnoise(N, 1.2, seed + 1)
    img = _ramp(tone, [(0, "#4a3326"), (0.5, "#8a5a3c"), (1, "#c58a5a")])
    img *= (0.45 + 0.55 * edge[..., None])
    save(name, img)


def palm(name, seed):
    yy = np.arange(N)[:, None] * np.ones((1, N))
    ring = np.abs(np.sin(yy / N * 2 * np.pi * 14)) ** 0.3
    n = tnoise(N, 1.3, seed)
    img = _ramp(0.5 * n + 0.5 * ring, [(0, "#4c4234"), (0.6, "#8a7a62"), (1, "#b5a58a")])
    fiber = _stretch(seed + 2, 0.5, 1, 1.0)
    img *= (0.8 + 0.3 * fiber[..., None])
    save(name, img)


def shuro(name, seed):
    f = _stretch(seed, 0.6, 1, 1.4)
    img = _ramp(0.7 * f + 0.3 * tnoise(N, 1.2, seed + 1), [(0, "#2a1d12"), (0.6, "#5a3d24"), (1, "#8a6a42")])
    save(name, img)


def save(name, img):
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB").save(OUT / name, optimize=True)


def main():
    furrow("bark_furrow.png", [(0, "#2b2622"), (0.5, "#6e655c"), (1, "#a79d90")], 10)
    furrow("bark_furrow_dark.png", [(0, "#1d1814"), (0.5, "#4a3d33"), (1, "#7a6a58")], 20, 1.2)
    smooth("bark_smooth.png", 30)
    plane("bark_plane.png", 40)
    pine("bark_pine.png", 50)
    palm("bark_palm.png", 60)
    shuro("bark_shuro.png", 70)


if __name__ == "__main__":
    main()
