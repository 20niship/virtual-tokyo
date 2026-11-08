"""レシピ(YAML)読み込みと実行。ノードごとに「直前までのキー+ノード+パラメータ+seed」のハッシュでキャッシュする。"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import yaml
from shapely import wkt

from .document import Document
from .grid import Grid
from .node import get_node
from .rng import node_rng


def load_recipe(path_or_dict) -> dict:
    r = path_or_dict if isinstance(path_or_dict, dict) else yaml.safe_load(Path(path_or_dict).read_text())
    return r or {}


def make_grid(g: dict) -> Grid:
    if "center_lonlat" in g:      # 実空間: 中心の経緯度から UTM の Grid を作る
        from ..source.gsi_dem import lonlat_grid
        return lonlat_grid(g["center_lonlat"], g.get("size_m", 1000), g.get("res_m", 4))
    return Grid.from_size(g.get("size_m", 1000), g.get("res_m", 4), g.get("crs", "local"), g.get("x0", 0.0), g.get("y0", 0.0))


def _key(prev, label, params, seed):
    s = json.dumps([prev, label, params, seed], sort_keys=True, default=str)
    return hashlib.sha256(s.encode()).hexdigest()[:20]


def _save_outputs(nd, doc, path):
    arrs = {f"L__{k}": doc.layers[k] for k in nd.outputs}
    for k in nd.scatter_outputs:
        for f, v in doc.scatter[k].items():
            arrs[f"S__{k}__{f}"] = v
    vec = {k: [[g.wkt, p] for g, p in doc.vectors[k]] for k in nd.vec_outputs}
    arrs["V"] = np.frombuffer(json.dumps(vec, default=str).encode(), np.uint8)
    np.savez(path, **arrs)


def _load_outputs(doc, path):
    with np.load(path) as z:
        for f in z.files:
            if f.startswith("L__"):
                doc.layers[f[3:]] = z[f]
            elif f.startswith("S__"):
                _, k, ff = f.split("__", 2)
                doc.scatter.setdefault(k, {})[ff] = z[f]
        for k, v in json.loads(bytes(z["V"]).decode()).items():
            doc.vectors[k] = [(wkt.loads(w), p) for w, p in v]


def run_recipe(recipe, seed=None, out=None, cache=True, log=print, grid_over=None) -> Document:
    """recipe: パス or dict。grid_over で grid を上書き(size_m/res_m 等)。"""
    r = load_recipe(recipe)
    g = {**r.get("grid", {}), **(grid_over or {})}
    seed = int(r.get("seed", 0) if seed is None else seed)
    doc = Document(make_grid(g), seed, meta=dict(climate=r.get("climate", {}), center_lonlat=g.get("center_lonlat"), places=r.get("places", {})))
    doc.layers["height"] = np.zeros(doc.grid.shape, np.float32)
    cdir = Path(out or ".") / ".cache"
    if cache:
        cdir.mkdir(parents=True, exist_ok=True)
    key = _key("root", doc.grid.to_dict(), doc.meta, seed)
    seen: dict[str, int] = {}
    for step in r.get("steps") or []:
        (name, params), = step.items()
        params = dict(params or {})
        n = seen.get(name, 0)
        seen[name] = n + 1
        label = name if n == 0 else f"{name}.{n}"
        nd = get_node(name)(**params)
        key = _key(key, label, nd.params, seed)
        cp = cdir / f"{key}.npz"
        t = time.time()
        if cache and cp.exists():
            _load_outputs(doc, cp)
            how = "cache"
        else:
            nd.run(doc, node_rng(seed, label))
            if cache:
                _save_outputs(nd, doc, cp)
            how = "run"
        for k in nd.outputs:
            doc.prov[k] = dict(node=label, key=key, params=nd.params)
        log(f"[terra] {label:24s} {how:5s} {time.time() - t:6.2f}s")
    return doc
