"""決定的乱数: seed + ノード名 から独立なストリームを作る(順序や他ノードに依存しない)。"""
import hashlib

import numpy as np


def node_rng(seed: int, label: str) -> np.random.Generator:
    h = hashlib.sha256(f"{int(seed)}:{label}".encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))
