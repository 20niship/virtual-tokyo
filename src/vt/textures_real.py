"""リアリズム用の壁面汚れマスクを手続き生成(git管理)。
wall_grime.png (1024², RGB, 全チャンネル 0=きれい/1=汚れ):
  R=雨だれ(縦の筋) / G=室外機・手すり下の垂れ染み(縦長の斑) / B=錆・カビの斑(低周波+細かい点)
uv run python -m vt.textures_real"""
import numpy as np

from .textures import save, tnoise

N = 1024


def _aniso(seed, sx, sy, beta=1.6):
    """タイル可能な異方性ノイズ(sx>sy で横方向に潰れ=縦長の筋)"""
    r = np.random.default_rng(seed)
    fx, fy = np.fft.fftfreq(N)[None, :], np.fft.fftfreq(N)[:, None]
    k = np.sqrt((fx * sx) ** 2 + (fy * sy) ** 2)
    k[0, 0] = 1
    spec = (r.normal(size=(N, N)) + 1j * r.normal(size=(N, N))) / k ** beta
    spec[0, 0] = 0
    a = np.real(np.fft.ifft2(spec))
    return (a - a.min()) / (a.max() - a.min())


def _sm(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def wall_grime():
    streak = _sm(0.52, 0.80, _aniso(1, 9.0, 0.35))              # 細く長い雨だれ
    streak *= 0.45 + 0.55 * _aniso(2, 1.0, 1.0, 1.2)             # 全体の濃淡
    drip = _sm(0.62, 0.86, _aniso(3, 3.5, 0.5)) * _sm(0.45, 0.8, tnoise(N, 1.3, 4))   # 太めの垂れ染み
    low = tnoise(N, 2.2, 5)
    speck = _sm(0.70, 0.9, tnoise(N, 0.4, 6))
    rust = np.clip(_sm(0.55, 0.85, low) * 0.7 + speck * 0.5, 0, 1)
    save("wall_grime.png", np.dstack([streak, drip, rust]))


def main():
    wall_grime()


if __name__ == "__main__":
    main()
