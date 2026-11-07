"""Terra 地形・岩用の小さなタイル可能テクスチャ(スペクトル合成, 512px)を assets/terra/textures/ に作る。外部データなし。"""
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parents[1] / "assets/terra/textures"
N = 512


def fbm(seed, beta, n=N):
    """周期境界のスペクトル合成ノイズ(0..1)。beta が大きいほど滑らか"""
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)
    k = np.hypot(*np.meshgrid(f, f))
    k[0, 0] = 1
    spec = (rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))) / k ** (beta / 2)
    spec[0, 0] = 0
    a = np.fft.ifft2(spec).real
    return (a - a.min()) / (a.max() - a.min())


def mix(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


def save(name, c):
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(c, 0, 1) * 255 + 0.5).astype(np.uint8)).save(OUT / name, optimize=True)


def rock():
    h = fbm(1, 2.4)
    y = np.arange(N)[:, None] / N
    strata = 0.5 + 0.5 * np.sin(2 * np.pi * (6 * y + 1.5 * fbm(2, 3.0)))        # 水平な層理(周期=6 本)
    crack = np.abs(fbm(3, 2.0) - 0.5)
    crack = np.clip(1 - crack / 0.018, 0, 1)                                     # 細い割れ目
    base = mix(np.array([0.30, 0.28, 0.26]), np.array([0.58, 0.55, 0.50]), np.clip(0.55 * h + 0.3 * strata + 0.15 * fbm(4, 1.2), 0, 1))
    lich = np.clip((fbm(5, 2.8) - 0.62) * 6, 0, 1) * (fbm(6, 1.0) > 0.45)
    c = mix(base, np.array([0.45, 0.50, 0.30]), lich * 0.5)
    c = c * (1 - 0.55 * crack[..., None])
    save("rock_cliff.png", c)


def litter():
    f1, f2 = fbm(11, 1.0), fbm(12, 2.2)
    base = mix(np.array([0.12, 0.08, 0.04]), np.array([0.30, 0.20, 0.10]), np.clip(0.6 * f1 + 0.4 * f2, 0, 1))
    leaf = (fbm(13, 0.5) > 0.78)[..., None] * np.array([0.52, 0.36, 0.16])
    moss = np.clip((fbm(14, 2.6) - 0.6) * 5, 0, 1)
    c = np.where(leaf > 0, leaf * (0.7 + 0.3 * f1[..., None]), base)
    c = mix(c, np.array([0.14, 0.22, 0.08]), moss * 0.5)
    save("forest_litter.png", c)


def turf():
    f1, f2 = fbm(21, 1.2), fbm(22, 2.6)
    base = mix(np.array([0.22, 0.28, 0.10]), np.array([0.46, 0.45, 0.20]), np.clip(0.6 * f1 + 0.4 * f2, 0, 1))
    dry = np.clip((fbm(23, 2.4) - 0.58) * 5, 0, 1)
    c = mix(base, np.array([0.40, 0.30, 0.18]), dry * 0.6)
    save("alpine_turf.png", c)


if __name__ == "__main__":
    rock()
    litter()
    turf()
    for p in sorted(OUT.glob("*.png")):
        print(p.name, p.stat().st_size // 1024, "KB")
