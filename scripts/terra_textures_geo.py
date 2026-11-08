"""岩・土・砂利・苔の手続きテクスチャ(256px タイル可能)を assets/terra/textures/ に作る。外部データなし(すべてスペクトル合成と周期ボロノイ)。"""
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import terra_textures as T  # noqa: E402

N = 256
C = lambda *a: np.array(a, float)
f = lambda seed, beta: T.fbm(seed, beta, N)


def voronoi(seed, count, n=N):
    """周期境界のボロノイ: (最近点の ID, 最近点までの距離/二番目までの距離の比 = セル縁で 1 に近づく, セル内座標)"""
    rng = np.random.default_rng(seed)
    p = rng.random((count, 2))
    off = np.array([(i, j) for i in (-1, 0, 1) for j in (-1, 0, 1)], float)
    P = (p[None] + off[:, None]).reshape(-1, 2)
    ids = np.tile(np.arange(count), 9)
    g = (np.indices((n, n)).reshape(2, -1).T[:, ::-1] + 0.5) / n
    d, i = cKDTree(P).query(g, k=2)
    return ids[i[:, 0]].reshape(n, n), (d[:, 0] / np.maximum(d[:, 1], 1e-9)).reshape(n, n), d[:, 0].reshape(n, n)


def save(name, c):
    T.OUT.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    Image.fromarray((np.clip(c, 0, 1) * 255 + 0.5).astype(np.uint8)).save(T.OUT / name, optimize=True)


def rock_tex():
    h = f(31, 2.2)
    # 花崗岩: 明灰の粒状(白・黒・ピンクの鉱物粒)
    g = f(32, 0.4)
    c = T.mix(C(0.55, 0.54, 0.52), C(0.78, 0.77, 0.74), np.clip(0.5 * h + 0.5 * f(33, 1.0), 0, 1))
    c = np.where((g > 0.8)[..., None], C(0.12, 0.12, 0.13), c)
    c = np.where(((g < 0.12))[..., None], C(0.78, 0.6, 0.55), c)
    save("rock_granite.png", c)
    # 玄武岩・安山岩: 暗灰+気孔
    v = f(34, 0.5) > 0.86
    c = T.mix(C(0.13, 0.13, 0.14), C(0.30, 0.29, 0.29), f(35, 2.0))
    c = np.where(v[..., None], C(0.03, 0.03, 0.03), c)
    save("rock_basalt.png", c)
    # 砂岩・泥岩: 層理(横縞)ベージュ〜茶
    y = np.arange(N)[:, None] / N
    band = 0.5 + 0.5 * np.sin(2 * np.pi * (9 * y + 2.0 * f(36, 3.0)))
    c = T.mix(C(0.55, 0.43, 0.30), C(0.80, 0.68, 0.50), np.clip(0.55 * band + 0.3 * f(37, 1.2) + 0.15, 0, 1))
    c = c * (0.85 + 0.15 * f(38, 0.6))[..., None]
    save("rock_sandstone.png", c)
    # 石灰岩: 白灰、溶食(孔と筋)
    pit = np.clip((f(39, 2.6) - 0.68) * 6, 0, 1)
    c = T.mix(C(0.72, 0.71, 0.67), C(0.88, 0.87, 0.83), f(40, 1.6))
    c = c * (1 - 0.5 * pit[..., None]) * (0.92 + 0.08 * f(41, 0.5))[..., None]
    save("rock_limestone.png", c)
    # 凝灰岩: 淡い黄灰の多孔質
    c = T.mix(C(0.60, 0.57, 0.48), C(0.80, 0.77, 0.66), f(42, 1.4))
    c = np.where((f(43, 0.5) > 0.9)[..., None], C(0.35, 0.33, 0.28), c)
    save("rock_tuff.png", c)
    # 川原の丸石: 灰・茶・緑の斑
    ids, _, _ = voronoi(44, 18)
    pal = np.array([C(0.45, 0.44, 0.42), C(0.58, 0.52, 0.44), C(0.38, 0.40, 0.38), C(0.66, 0.64, 0.60), C(0.42, 0.36, 0.32)])
    c = pal[ids % 5] * (0.8 + 0.4 * f(45, 1.0))[..., None]
    save("rock_river.png", c)
    # 苔(緑のふさふさ)
    m = f(46, 0.9)
    c = T.mix(C(0.17, 0.25, 0.08), C(0.46, 0.56, 0.22), np.clip(m * 1.2, 0, 1))
    c = c * (0.7 + 0.5 * f(47, 0.3))[..., None]
    save("moss.png", c)


SOILS = {   # 基色(暗, 明), 粒の荒さ(beta 小さいほど粗い)
    "kuroboku": (C(0.08, 0.06, 0.05), C(0.24, 0.19, 0.15), 1.0),      # 黒ボク土
    "redyellow": (C(0.42, 0.20, 0.10), C(0.68, 0.40, 0.18), 1.4),      # 赤黄色土
    "clay": (C(0.50, 0.46, 0.34), C(0.72, 0.68, 0.52), 2.2),          # 粘土(灰黄)
    "sandy": (C(0.60, 0.52, 0.38), C(0.82, 0.74, 0.56), 0.5),         # 砂質土
    "scoria": (C(0.07, 0.05, 0.05), C(0.40, 0.14, 0.08), 0.6),         # 火山灰・スコリア(黒〜赤)
    "masa": (C(0.55, 0.47, 0.38), C(0.82, 0.74, 0.64), 0.4),          # 花崗岩風化砂(マサ土)
    "humus": (C(0.10, 0.065, 0.035), C(0.32, 0.21, 0.10), 0.8),       # 腐植・落葉層
    "mud": (C(0.14, 0.11, 0.08), C(0.30, 0.24, 0.17), 2.6),           # ぬかるみ
}


def soil_tex():
    for i, (k, (a, b, beta)) in enumerate(SOILS.items()):
        t = np.clip(0.45 * f(50 + i, beta) + 0.55 * f(70 + i, 0.3), 0, 1)
        t = np.clip((t - 0.5) * 1.7 + 0.5, 0, 1)                                       # 粒のコントラストを強める
        c = T.mix(a, b, t)
        ids, edge, _ = voronoi(200 + i, 70)                                            # 土塊(クロッド)の縁を暗く
        c = c * (1 - 0.32 * np.clip((edge - 0.6) * 3, 0, 1))[..., None]
        if k == "clay":                                       # 乾いた亀裂
            ids, edge, _ = voronoi(90, 40)
            c = c * (1 - 0.6 * np.clip((edge - 0.78) * 6, 0, 1))[..., None]
        if k == "humus":                                      # 落ち葉片
            c = np.where((f(95, 0.5) > 0.82)[..., None], C(0.40, 0.26, 0.10) * (0.7 + 0.5 * f(96, 1.0))[..., None], c)
        if k == "scoria":
            c = np.where((f(97, 0.4) > 0.88)[..., None], C(0.55, 0.12, 0.06), c)
        if k == "mud":                                        # 濡れて暗く光る
            c = c * 0.8
        save(f"soil_{k}.png", c)


GRAVELS = {  # 名前: (石の数, 石色パレット, 縁の暗さ)
    "sand": (700, [C(0.62, 0.55, 0.42), C(0.72, 0.65, 0.50), C(0.52, 0.46, 0.36)], 0.15),
    "fine": (260, [C(0.50, 0.47, 0.42), C(0.62, 0.58, 0.50), C(0.38, 0.36, 0.33), C(0.70, 0.64, 0.55)], 0.35),
    "medium": (90, [C(0.48, 0.45, 0.42), C(0.60, 0.55, 0.48), C(0.36, 0.35, 0.34), C(0.68, 0.62, 0.52), C(0.42, 0.38, 0.33)], 0.5),
    "cobble": (30, [C(0.46, 0.44, 0.42), C(0.58, 0.52, 0.44), C(0.38, 0.40, 0.38), C(0.64, 0.62, 0.58), C(0.42, 0.36, 0.32)], 0.65),
    "crushed": (110, [C(0.40, 0.40, 0.42), C(0.52, 0.52, 0.52), C(0.30, 0.30, 0.31), C(0.60, 0.58, 0.55)], 0.45),
    "river": (60, [C(0.52, 0.50, 0.46), C(0.62, 0.58, 0.50), C(0.40, 0.42, 0.40), C(0.70, 0.68, 0.62), C(0.44, 0.40, 0.36)], 0.55),
}


def gravel_tex():
    for i, (k, (cnt, pal, dark)) in enumerate(GRAVELS.items()):
        ids, edge, _ = voronoi(120 + i, cnt)
        pal = np.array(pal)
        c = pal[ids % len(pal)] * (0.75 + 0.5 * f(130 + i, 0.8))[..., None]
        c = c * (1 - dark * np.clip((edge - 0.55) * 2.5, 0, 1))[..., None]
        save(f"gravel_{k}.png", c)


if __name__ == "__main__":
    rock_tex()
    soil_tex()
    gravel_tex()
    tot = 0
    for p in sorted(T.OUT.glob("*.png")):
        tot += p.stat().st_size
    print("terra textures total KB", tot // 1024)
