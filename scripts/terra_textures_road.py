"""山間部の道路の路面テクスチャ(使い込んだ明るめのアスファルト, 512px タイル可能)を assets/textures/road_asphalt.png に作る。外部データなし。"""
from pathlib import Path

import numpy as np
from PIL import Image

N = 512
OUT = Path(__file__).resolve().parents[1] / "assets/textures/road_asphalt.png"


def fbm(seed, beta, n=N):
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)
    k = np.hypot(*np.meshgrid(f, f))
    k[0, 0] = 1
    a = np.fft.ifft2((rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))) / k ** (beta / 2)).real
    return (a - a.min()) / (a.max() - a.min())


rng = np.random.default_rng(5)
base = 0.40 + 0.10 * (fbm(1, 1.6) - 0.5) * 2 + 0.06 * (fbm(2, 3.0) - 0.5) * 2                   # 明るい灰色(骨材が出た古い舗装)
grain = rng.normal(0, 0.035, (N, N))                                                            # 骨材の粒
speck = (rng.random((N, N)) > 0.985) * rng.uniform(0.1, 0.25, (N, N))                          # 明るい砂利の粒
dark = (fbm(3, 2.4) > 0.72) * 0.06                                                              # 油染み・タイヤ跡の暗部
crack = np.clip(1 - np.abs(fbm(4, 2.2) - 0.5) / 0.006, 0, 1) * 0.18                              # 細いひび
g = np.clip(base + grain + speck - dark - crack, 0, 1)
c = np.stack([g * 1.0, g * 1.0, g * 1.02], -1)
Image.fromarray((c * 255 + 0.5).astype(np.uint8)).save(OUT, optimize=True)
print("wrote", OUT, OUT.stat().st_size // 1024, "KB mean", round(float(c.mean() * 255)))
