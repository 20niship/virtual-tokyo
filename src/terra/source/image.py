"""画像/配列からハイトマップ・バイオーム画像を取り込む。"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

from ..core.node import Node, node


def load_height(path, height_range=(0.0, 500.0)):
    """グレースケール画像(8/16bit)→ メートル(北が上の画像を行0=南へ反転)。.npy はそのままメートル。"""
    path = Path(path)
    if path.suffix == ".npy":
        return np.load(path, allow_pickle=False).astype(np.float32)
    im = Image.open(path)
    a = np.asarray(im.convert("I;16") if im.mode.startswith("I") else im.convert("L"), np.float64)
    a = a / (65535.0 if a.max() > 255 else 255.0)
    lo, hi = height_range
    return np.flipud(lo + a * (hi - lo)).astype(np.float32)


def resample(a, shape, order=1):
    h, w = a.shape
    jj, ii = np.meshgrid((np.arange(shape[0]) + 0.5) / shape[0] * h - 0.5, (np.arange(shape[1]) + 0.5) / shape[1] * w - 0.5, indexing="ij")
    return map_coordinates(a, [jj, ii], order=order, mode="nearest")


@node("source.image")
class ImageSource(Node):
    """ハイトマップ画像を格子全体に引き伸ばして height に設定する(mode=add で加算)。"""
    outputs = ("height",)
    defaults = dict(file=None, height_range=[0.0, 500.0], mode="set")

    def run(self, doc, rng):
        z = resample(load_height(self.params["file"], self.params["height_range"]), doc.grid.shape)
        doc.set("height", z if self.params["mode"] == "set" else doc.height + z)
