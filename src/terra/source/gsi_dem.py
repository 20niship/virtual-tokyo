"""国土地理院 標高タイル(DEM5A z15 / DEM10B z14)の取得とグリッドへの再サンプル。
利用条件・出典は data/terra/SOURCES.md。取得データは data/terra/ に置き(gitignore)、デコードは python -I の別プロセスで行う。"""
from __future__ import annotations

import hashlib
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from pyproj import Transformer
from scipy.ndimage import distance_transform_edt, map_coordinates

from ..core.grid import Grid
from ..core.node import Node, node

URL = "https://cyberjapandata.gsi.go.jp/xyz/{layer}/{z}/{x}/{y}.png"
ROOT = Path(__file__).resolve().parents[3] / "data" / "terra" / "gsi_dem"
UA = {"User-Agent": "virtual-tokyo-terra/0.1 (research; contact via github 20niship/virtual-tokyo)"}


def utm_epsg(lon, lat):
    return (32600 if lat >= 0 else 32700) + int((lon + 180) // 6) + 1


def tile_xy(lon, lat, z):
    n = 2 ** z
    return (lon + 180) / 360 * n, (1 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2 * n


def lonlat_grid(center, size_m, res_m):
    """中心(lon,lat)から UTM の正方 Grid を作る(原点は 1m に丸める)"""
    ep = utm_epsg(*center)
    cx, cy = Transformer.from_crs(4326, ep, always_xy=True).transform(*center)
    return Grid.from_size(size_m, res_m, f"EPSG:{ep}", round(cx - size_m / 2), round(cy - size_m / 2))


def _get(layer, z, x, y, root):
    import requests
    p = Path(root) / layer / str(z) / str(x) / f"{y}.png"
    if p.exists():
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(URL.format(layer=layer, z=z, x=x, y=y), headers=UA, timeout=30)
    if r.status_code == 200 and r.content[:8] == b"\x89PNG\r\n\x1a\n" and len(r.content) < 2_000_000:
        p.write_bytes(r.content)
    else:
        p.write_bytes(b"")          # 欠測(範囲外 404 等)は空ファイルで記録し再取得しない
    time.sleep(0.05)
    return p


def fetch_tiles(bbox, root=ROOT, z=15):
    """bbox=(lon0,lat0,lon1,lat1)。z15 は dem5a、足りない所用に z-1 の dem_png も取る。タイル範囲を返す"""
    fx0, fy1 = tile_xy(bbox[0], bbox[1], z)
    fx1, fy0 = tile_xy(bbox[2], bbox[3], z)
    x0, x1, y0, y1 = int(fx0), int(fx1), int(fy0), int(fy1)
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            _get("dem5a_png", z, tx, ty, root)
            _get("dem_png", z - 1, tx // 2, ty // 2, root)
    return x0, x1, y0, y1


def fetch_dem(bbox, out=ROOT.parent, zoom=15):
    fetch_tiles(bbox, Path(out) / "gsi_dem", 15)
    return Path(out) / "gsi_dem"


def dem_array(center, size_m, res_m, layer="auto", root=ROOT):
    """center=(lon,lat) 中心・一辺 size_m の正方領域を res_m 格子に再サンプルした標高[m](行0=南)。海は 0。"""
    g = lonlat_grid(center, size_m, res_m)
    return sample_grid(g, layer, root)


def sample_grid(g: Grid, layer="auto", root=ROOT):
    ep = int(g.crs.split(":")[1])
    to_ll = Transformer.from_crs(ep, 4326, always_xy=True)
    X, Y = g.xy()
    lon, lat = to_ll.transform(X, Y)
    z = 15     # 5m(DEM5A)。範囲外は 10m(DEM10B z14)を補間
    box = (lon.min() - 1e-4, lat.min() - 1e-4, lon.max() + 1e-4, lat.max() + 1e-4)
    x0, x1, y0, y1 = fetch_tiles(box, root, z)
    tag = hashlib.sha1(f"{layer}{z}{x0}{x1}{y0}{y1}".encode()).hexdigest()[:10]
    mp = Path(root) / f"mosaic_{tag}.npz"
    if not mp.exists():
        subprocess.run([sys.executable, "-I", "-m", "terra.source._gsi_decode", str(root), layer, str(z), str(x0), str(x1), str(y0), str(y1), str(mp)], check=True)
    with np.load(mp, allow_pickle=False) as f:
        mos = f["dem"]
    px, py = tile_xy(lon, lat, z)
    fi, fj = (px - x0) * 256 - 0.5, (py - y0) * 256 - 0.5
    bad = np.isnan(mos)
    if bad.any():                       # 欠測は最近傍で埋め、全欠測なら 0
        if bad.all():
            return np.zeros(g.shape, np.float32)
        idx = distance_transform_edt(bad, return_distances=False, return_indices=True)
        mos = mos[tuple(idx)]
    h = map_coordinates(mos, [fj, fi], order=1, mode="nearest")
    return h.astype(np.float32)


@node("source.gsi_dem")
class GsiDem(Node):
    """grid に center_lonlat を指定した上で、GSI DEM を height に設定。layer は auto のみ(5m→10m 補間)"""
    outputs = ("height",)
    defaults = dict(layer="auto", mode="set")

    def run(self, doc, rng):
        z = sample_grid(doc.grid, self.params["layer"])
        doc.set("height", z if self.params["mode"] == "set" else doc.height + z)
