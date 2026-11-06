"""トップダウンのハイトシェード(+川・植生オーバーレイ)。matplotlib 不要で numpy + PIL。"""
from __future__ import annotations

import numpy as np
from PIL import Image

HYPSO = np.array([[0.00, (70, 110, 60)], [0.25, (120, 150, 80)], [0.5, (175, 160, 105)],
                  [0.75, (150, 120, 95)], [1.0, (245, 245, 245)]], dtype=object)


def hillshade(z, res, az=315.0, alt=45.0, exag=1.0):
    gy, gx = np.gradient(z.astype(np.float64) * exag, res)
    slope = np.arctan(np.hypot(gx, gy))
    asp = np.arctan2(gy, -gx)
    a, h = np.radians(360 - az + 90), np.radians(alt)
    s = np.sin(h) * np.cos(slope) + np.cos(h) * np.sin(slope) * np.cos(a - asp)
    return np.clip(s, 0, 1)


def _tint(z):
    t = (z - z.min()) / max(float(z.max() - z.min()), 1e-6)
    xs = [float(p[0]) for p in HYPSO]
    return np.stack([np.interp(t, xs, [p[1][c] for p in HYPSO]) for c in range(3)], -1)


def render_top(doc, overlays=(), box=None, scale=1, exag=1.0):
    """box=(x0,y0,x1,y1) ローカル座標。overlays: 'river' など。RGB uint8 PIL を返す"""
    z = doc.height
    img = _tint(z) * (0.35 + 0.65 * hillshade(z, doc.grid.res, exag=exag))[..., None]
    for o in overlays:
        if o in doc.layers:
            m = doc.layers[o]
            if o == "water_depth":
                img[m > 0.05] = img[m > 0.05] * 0.3 + np.array([40, 90, 200]) * 0.7
            elif o == "river":
                img[m > 0] = np.array([30, 90, 230])
            elif o == "biome":
                pal = np.array([[90, 90, 90], [60, 130, 60], [40, 100, 50], [30, 80, 70], [90, 120, 80], [150, 150, 130], [190, 190, 190], [120, 170, 60], [180, 160, 80]])
                c = pal[np.clip(m.astype(int), 0, len(pal) - 1)]
                img = img * 0.5 + c * 0.5
    img = np.clip(img, 0, 255).astype(np.uint8)
    if box:
        g = doc.grid
        i0, j0 = int((box[0] - g.x0) / g.res), int((box[1] - g.y0) / g.res)
        i1, j1 = int((box[2] - g.x0) / g.res), int((box[3] - g.y0) / g.res)
        img = img[max(j0, 0):j1, max(i0, 0):i1]
    im = Image.fromarray(np.flipud(img))
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.BILINEAR)
    return im
