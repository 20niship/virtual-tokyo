"""Terrain Document: ラスタ(layers)・ベクタ(vectors)・散布(scatter)・来歴(prov)を持つ。保存は npz + json(WKT)。"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from shapely import wkt

from .grid import Grid, Heightfield


class Document:
    def __init__(self, grid: Grid, seed: int = 0, meta: dict | None = None):
        self.grid = grid
        self.seed = seed
        self.meta = meta or {}         # climate など
        self.layers: dict[str, np.ndarray] = {}
        self.vectors: dict[str, list] = {}   # name -> [(shapely geom, props dict)]
        self.scatter: dict[str, dict[str, np.ndarray]] = {}  # name -> {pos(N,3), yaw, scale, kind}
        self.prov: dict[str, dict] = {}

    @property
    def height(self) -> np.ndarray:
        return self.layers["height"]

    def heightfield(self) -> Heightfield:
        return Heightfield(self.grid, self.layers["height"])

    def set(self, name, arr, keep64=False):
        arr = np.asarray(arr)
        if arr.shape != self.grid.shape:
            raise ValueError(f"layer {name}: shape {arr.shape} != grid {self.grid.shape}")
        if arr.dtype == np.float64 and not keep64:
            arr = arr.astype(np.float32)
        self.layers[name] = arr

    def save(self, d):
        d = Path(d)
        d.mkdir(parents=True, exist_ok=True)
        np.savez(d / "layers.npz", **self.layers)
        sc = {f"{k}__{f}": v for k, s in self.scatter.items() for f, v in s.items()}
        np.savez(d / "scatter.npz", **sc)
        vec = {k: [[g.wkt, p] for g, p in v] for k, v in self.vectors.items()}
        (d / "doc.json").write_text(json.dumps(
            dict(grid=self.grid.to_dict(), seed=self.seed, meta=self.meta, prov=self.prov, vectors=vec,
                 scatter={k: list(s) for k, s in self.scatter.items()}), ensure_ascii=False, indent=1, default=str))

    @classmethod
    def load(cls, d):
        d = Path(d)
        j = json.loads((d / "doc.json").read_text())
        doc = cls(Grid(**j["grid"]), j["seed"], j["meta"])
        doc.prov = j["prov"]
        with np.load(d / "layers.npz") as z:
            doc.layers = {k: z[k] for k in z.files}
        doc.vectors = {k: [(wkt.loads(w), p) for w, p in v] for k, v in j["vectors"].items()}
        with np.load(d / "scatter.npz") as z:
            doc.scatter = {k: {f: z[f"{k}__{f}"] for f in fs} for k, fs in j["scatter"].items()}
        return doc
