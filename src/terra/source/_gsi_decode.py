"""GSI 標高タイル(PNG)をモザイク npz にデコードする。取得データを読むので `python -I -m terra.source._gsi_decode` で隔離実行する。
引数: タイルルート layer(auto|dem10b) z x0 x1 y0 y1 出力.npz"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def read_tile(p):
    p = Path(p)
    if not p.exists() or p.stat().st_size < 100:
        return None
    a = np.asarray(Image.open(p).convert("RGB"), np.int64)
    x = a[..., 0] * 65536 + a[..., 1] * 256 + a[..., 2]
    h = np.where(x < 2 ** 23, x * 0.01, (x - 2 ** 24) * 0.01)
    return np.where(x == 2 ** 23, np.nan, h).astype(np.float32)


def main(root, layer, z, x0, x1, y0, y1, out):
    root = Path(root)
    mos = np.full(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), np.nan, np.float32)
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            t = read_tile(root / "dem5a_png" / str(z) / str(tx) / f"{ty}.png") if layer == "auto" and z == 15 else None
            if t is None:      # 10m タイル(z-1)を 2 倍に補間して使う
                par = read_tile(root / "dem_png" / str(z - 1) / str(tx // 2) / f"{ty // 2}.png")
                if par is not None:
                    from scipy.ndimage import zoom
                    qx, qy = (tx % 2) * 128, (ty % 2) * 128
                    t = zoom(par[qy:qy + 128, qx:qx + 128], 2, order=1)
            if t is not None:
                mos[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = t
    np.savez(out, dem=mos, z=z, x0=x0, y0=y0)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], *map(int, a[2:7]), a[7])
