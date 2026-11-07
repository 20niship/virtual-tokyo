"""fBm / ridged / billow / Worley + ドメインワープ(Numba、決定的)。"""
from __future__ import annotations

import numpy as np
from numba import njit, prange

from ..core.node import Node, node

KINDS = {"fbm": 0, "ridged": 1, "billow": 2, "worley": 3}


def make_tables(rng):
    perm = rng.permutation(256).astype(np.int32)
    perm = np.concatenate([perm, perm])
    ang = rng.random(256) * 2 * np.pi
    return perm, np.cos(ang), np.sin(ang)


@njit(cache=True, inline="always")
def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


@njit(cache=True)
def _perlin(x, y, perm, gx, gy):
    xi, yi = int(np.floor(x)), int(np.floor(y))
    xf, yf = x - xi, y - yi
    xi &= 255
    yi &= 255
    a = perm[perm[xi] + yi]
    b = perm[perm[xi + 1] + yi]
    c = perm[perm[xi] + yi + 1]
    d = perm[perm[xi + 1] + yi + 1]
    n00 = gx[a] * xf + gy[a] * yf
    n10 = gx[b] * (xf - 1) + gy[b] * yf
    n01 = gx[c] * xf + gy[c] * (yf - 1)
    n11 = gx[d] * (xf - 1) + gy[d] * (yf - 1)
    u, v = _fade(xf), _fade(yf)
    return (n00 + u * (n10 - n00)) * (1 - v) + (n01 + u * (n11 - n01)) * v   # 概ね [-0.7, 0.7]


@njit(cache=True)
def _worley(x, y, perm, gx, gy):
    xi, yi = int(np.floor(x)), int(np.floor(y))
    best = 9.0
    for j in range(-1, 2):
        for i in range(-1, 2):
            cx, cy = xi + i, yi + j
            h = perm[perm[cx & 255] + (cy & 255)]
            px = cx + 0.5 + 0.5 * gx[h]
            py = cy + 0.5 + 0.5 * gy[h]
            d = (px - x) ** 2 + (py - y) ** 2
            if d < best:
                best = d
    return np.sqrt(best)


@njit(cache=True, parallel=True)
def noise_field(nx, ny, x0, y0, res, wl, octaves, lac, gain, kind, warp, perm, gx, gy):
    out = np.zeros((ny, nx), np.float32)
    inv = 1.0 / wl
    for j in prange(ny):
        for i in range(nx):
            x = (x0 + (i + 0.5) * res) * inv
            y = (y0 + (j + 0.5) * res) * inv
            if warp > 0:
                wx = _perlin(x * 0.7 + 17.3, y * 0.7 + 3.1, perm, gx, gy)
                wy = _perlin(x * 0.7 - 9.7, y * 0.7 + 41.9, perm, gx, gy)
                x += warp * wx * 2
                y += warp * wy * 2
            amp, f, s, norm = 1.0, 1.0, 0.0, 0.0
            w = 1.0
            for o in range(octaves):
                if kind == 3:
                    n = 1.0 - min(_worley(x * f + o * 7.1, y * f + o * 3.3, perm, gx, gy), 1.0)
                    s += amp * n
                    norm += amp
                elif kind == 1:
                    n = 1.0 - abs(_perlin(x * f + o * 5.2, y * f + o * 1.3, perm, gx, gy) * 1.42)
                    n = n * n * w
                    w = min(max(n * 2.0, 0.0), 1.0)
                    s += amp * n
                    norm += amp
                elif kind == 2:
                    s += amp * abs(_perlin(x * f + o * 5.2, y * f + o * 1.3, perm, gx, gy) * 1.42)
                    norm += amp
                else:
                    s += amp * _perlin(x * f + o * 5.2, y * f + o * 1.3, perm, gx, gy) * 1.42
                    norm += amp
                amp *= gain
                f *= lac
            v = s / norm
            if kind == 0:
                v = 0.5 + 0.5 * v
            out[j, i] = v
    return out


def make_noise(grid, rng, kind="fbm", wavelength_m=2000.0, octaves=6, lacunarity=2.0, gain=0.5, warp=0.0, normalize=True):
    perm, gx, gy = make_tables(rng)
    n = noise_field(grid.nx, grid.ny, grid.x0, grid.y0,
                    grid.res, float(wavelength_m), int(octaves), float(lacunarity), float(gain), KINDS[kind], float(warp), perm, gx, gy)
    if normalize:
        lo, hi = float(n.min()), float(n.max())
        n = (n - lo) / max(hi - lo, 1e-9)
    return n.astype(np.float32)


@node("gen.noise")
class Noise(Node):
    """height += base_height * noise。mode: add | set | mul(既存高さ × (1-strength+strength*noise))"""
    outputs = ("height",)
    defaults = dict(kind="fbm", wavelength_m=2000.0, octaves=6, lacunarity=2.0, gain=0.5, warp=0.0,
                    base_height=500.0, offset=0.0, mode="add", power=1.0)

    def run(self, doc, rng):
        p = self.params
        n = make_noise(doc.grid, rng, p["kind"], p["wavelength_m"], p["octaves"], p["lacunarity"], p["gain"], p["warp"])
        if p["power"] != 1.0:
            n = n ** p["power"]
        h = p["base_height"] * n + p["offset"]
        doc.set("height", h if p["mode"] == "set" else doc.height + h)
