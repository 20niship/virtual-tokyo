"""超高ポリ岩の Bump 用高さ画像 rockh_<形>.png(512px、周期タイル。1 枚 0.8m 相当)を assets/terra/textures/ に作る。外部データなし。
細かい皺・粒・割れ目(ボロノイの縁)・穴を重ね、形ごとに配合を変える。"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

OUT = Path(__file__).resolve().parents[1] / "assets/terra/textures"
N = 512


def fbm(seed, beta):
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(N)
    k = np.hypot(*np.meshgrid(f, f))
    k[0, 0] = 1
    a = np.fft.ifft2((rng.normal(size=(N, N)) + 1j * rng.normal(size=(N, N))) / k ** (beta / 2)).real
    return (a - a.min()) / (a.max() - a.min())


def cells(seed, count):
    """周期ボロノイ: セル縁までの距離(0=縁)"""
    rng = np.random.default_rng(seed)
    p = rng.random((count, 2))
    off = np.array([(i, j) for i in (-1, 0, 1) for j in (-1, 0, 1)], float)
    P = (p[None] + off[:, None]).reshape(-1, 2)
    g = (np.indices((N, N)).reshape(2, -1).T[:, ::-1] + 0.5) / N
    d, _ = cKDTree(P).query(g, k=2)
    return (d[:, 1] - d[:, 0]).reshape(N, N)


def ridged(seed, beta):
    return 1 - np.abs(2 * fbm(seed, beta) - 1)


def make(name, w):
    h = w["grain"] * fbm(1, 1.6) + w["wrinkle"] * ridged(2, 2.4) + w["mid"] * fbm(3, 2.6)
    if w["crack"]:
        e = cells(4, w["crack"])
        h -= w["crack_depth"] * np.clip(1 - e / 0.012, 0, 1) ** 1.5                   # 細い割れ目(ネットワーク)
        h += 0.15 * np.clip(e / 0.08, 0, 1)                                           # セル中央を盛る(角ばった小片)
    if w["pits"]:
        v = fbm(5, 1.2)
        h -= w["pits"] * np.clip((v - 0.72) / 0.1, 0, 1)                              # 小さな穴
    if w["layers"]:
        y = np.arange(N)[:, None] / N
        h += w["layers"] * np.abs(np.sin(np.pi * (w["nl"] * y + 1.2 * fbm(6, 3.0)))) # 層理
    h = (h - h.min()) / (h.max() - h.min())
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray((h * 255 + 0.5).astype(np.uint8)).save(OUT / f"rockh_{name}.png", optimize=True)


W = dict(crack=0, crack_depth=0, pits=0, layers=0, nl=0)
PRESETS = {
    "round": dict(W, grain=0.5, wrinkle=0.35, mid=0.5, crack=40, crack_depth=0.25, pits=0.1),
    "angular": dict(W, grain=0.3, wrinkle=0.7, mid=0.4, crack=70, crack_depth=0.55, pits=0.3),
    "slab": dict(W, grain=0.3, wrinkle=0.5, mid=0.3, crack=30, crack_depth=0.4, layers=0.7, nl=14),
    "karst": dict(W, grain=0.3, wrinkle=0.8, mid=0.5, crack=25, crack_depth=0.4, pits=0.5),
    "soft": dict(W, grain=0.6, wrinkle=0.4, mid=0.5, crack=20, crack_depth=0.2, pits=0.4),
}
if __name__ == "__main__":
    for k, w in PRESETS.items():
        make(k, w)
    print("wrote", ", ".join(f"rockh_{k}.png" for k in PRESETS), "->", OUT, file=sys.stderr)
