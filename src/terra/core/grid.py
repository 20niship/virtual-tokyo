"""Grid(原点・解像度・サイズ・CRS)と Heightfield。配列は行0=南(y 最小)、列0=西。セル中心は原点+(i+0.5)*res。"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Grid:
    nx: int
    ny: int
    res: float
    x0: float = 0.0   # 南西端の x[m]
    y0: float = 0.0
    crs: str = "local"  # "local" か "EPSG:xxxx"

    @classmethod
    def from_size(cls, size_m, res_m, crs="local", x0=0.0, y0=0.0):
        sx, sy = (size_m, size_m) if np.isscalar(size_m) else size_m
        return cls(int(round(sx / res_m)), int(round(sy / res_m)), float(res_m), float(x0), float(y0), crs)

    @property
    def shape(self):
        return (self.ny, self.nx)

    @property
    def size(self):
        return (self.nx * self.res, self.ny * self.res)

    def xy(self):
        """セル中心座標 (X, Y) 2次元配列(float64)"""
        x = self.x0 + (np.arange(self.nx) + 0.5) * self.res
        y = self.y0 + (np.arange(self.ny) + 0.5) * self.res
        return np.meshgrid(x, y)

    def to_ij(self, x, y):
        """座標 → 連続セル座標(列, 行)。セル中心が整数"""
        return (np.asarray(x) - self.x0) / self.res - 0.5, (np.asarray(y) - self.y0) / self.res - 0.5

    def to_dict(self):
        return dict(nx=self.nx, ny=self.ny, res=self.res, x0=self.x0, y0=self.y0, crs=self.crs)


@dataclass
class Heightfield:
    grid: Grid
    z: np.ndarray

    def sample(self, x, y):
        """バイリニア補間で標高を返す(範囲外は端の値)"""
        from scipy.ndimage import map_coordinates
        i, j = self.grid.to_ij(x, y)
        return map_coordinates(self.z, [np.ravel(j), np.ravel(i)], order=1, mode="nearest").reshape(np.shape(x))
