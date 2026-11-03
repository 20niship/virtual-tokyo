"""地形(国土地理院DEM)と、地面系メッシュ生成の共通ヘルパ。"""
import io
import math
from pathlib import Path

import numpy as np
import requests
from PIL import Image
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import triangulate

from .geo import to_lonlat
from .modules.geom import Mesh
from .osm_fetch import BBOX

ROOT = Path(__file__).resolve().parents[2]
DEMDIR = ROOT / "data/dem"
Z = 15   # dem5a_png (5m)
HEAD = {"User-Agent": "virtual-tokyo/0.1 (OSM procedural city project)"}


def _tile(x, y):
    f = DEMDIR / f"{Z}_{x}_{y}.png"
    if not f.exists():
        DEMDIR.mkdir(parents=True, exist_ok=True)
        r = requests.get(f"https://cyberjapandata.gsi.go.jp/xyz/dem5a_png/{Z}/{x}/{y}.png", headers=HEAD, timeout=30)
        f.write_bytes(r.content if r.status_code == 200 else b"")
    b = f.read_bytes()
    if not b:
        return np.full((256, 256), np.nan, dtype=np.float32)
    a = np.array(Image.open(io.BytesIO(b)).convert("RGB")).astype(np.int64)
    v = a[..., 0] * 65536 + a[..., 1] * 256 + a[..., 2]
    h = np.where(v < 2 ** 23, v * 0.01, (v - 2 ** 24) * 0.01).astype(np.float32)
    h[v == 2 ** 23] = np.nan
    return h


def _px(lon, lat):
    n = 2 ** Z * 256
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


class Terrain:
    """zg(x,y): ローカルm座標→標高[m]。DEMが無い場所は海面(0)。"""

    def __init__(self, bbox=BBOX, flat=None):
        self.flat = flat
        if flat is not None:
            return
        x0, y1 = _px(bbox[1], bbox[0]); x1, y0 = _px(bbox[3], bbox[2])
        tx0, tx1, ty0, ty1 = int(x0 // 256), int(x1 // 256), int(y0 // 256), int(y1 // 256)
        self.tx0, self.ty0 = tx0, ty0
        rows = [np.hstack([_tile(x, y) for x in range(tx0, tx1 + 1)]) for y in range(ty0, ty1 + 1)]
        a = np.vstack(rows)
        a = self._fill(a)
        self.a = self._blur(a, 4)

    @staticmethod
    def _blur(a, r):
        """DEMの量子化ノイズ(±数十cm)を消すボックス平滑(2パス)。三角形の線形補間誤差を小さくして上に重ねる面のZファイトを防ぐ"""
        k = 2 * r + 1
        for _ in range(2):
            for ax in (0, 1):
                pad = np.pad(a, [(r, r) if i == ax else (0, 0) for i in range(2)], mode="edge")
                c = np.cumsum(pad, axis=ax, dtype=np.float64)
                z = np.zeros_like(c.take([0], axis=ax))
                c = np.concatenate([z, c], axis=ax)
                a = (c.take(range(k, c.shape[ax]), axis=ax) - c.take(range(0, c.shape[ax] - k), axis=ax)) / k
        return a.astype(np.float32)

    @staticmethod
    def _fill(a):
        """欠測(海・欠け)を近傍の有効値で埋める。海に面した値は最終的に0へ"""
        a = a.copy()
        m = np.isnan(a)
        for _ in range(40):
            if not m.any():
                break
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                sh = np.roll(a, (dy, dx), (0, 1))
                ok = m & ~np.isnan(sh)
                a[ok] = sh[ok]
                m = np.isnan(a)
        a[np.isnan(a)] = 0
        return a

    def __call__(self, x, y):
        if self.flat is not None:
            return self.flat
        lon, lat = to_lonlat(x, y)
        px, py = _px(lon, lat)
        px -= self.tx0 * 256; py -= self.ty0 * 256
        h, w = self.a.shape
        px = min(max(px, 0), w - 1.001); py = min(max(py, 0), h - 1.001)
        i, j = int(px), int(py); fx, fy = px - i, py - j
        a = self.a
        return float((a[j, i] * (1 - fx) + a[j, i + 1] * fx) * (1 - fy) + (a[j + 1, i] * (1 - fx) + a[j + 1, i + 1] * fx) * fy)


def densify(geom, step):
    return geom.segmentize(step)


def _split(tri, maxe, out, depth=0, zf=None, tol=0.05):
    """最長辺が短ければそのまま。長い辺は、地形が線形補間から tol[m] 以上ずれる(または150m超)ときだけ最長辺の中点で2分割(再帰)"""
    a, b, c = tri
    e = [(math.dist(a, b), 0), (math.dist(b, c), 1), (math.dist(c, a), 2)]
    L, k = max(e)
    if L <= maxe or depth > 14:
        out.append(tri)
        return
    if zf is not None and L < 150:
        cx, cy = (a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3
        lin = (zf(*a) + zf(*b) + zf(*c)) / 3
        mids = [zf((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) - (zf(*a) + zf(*b)) / 2, zf((b[0] + c[0]) / 2, (b[1] + c[1]) / 2) - (zf(*b) + zf(*c)) / 2]
        if abs(zf(cx, cy) - lin) < tol and max(abs(x) for x in mids) < tol:
            out.append(tri)
            return
    if k == 0:
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2); _split((a, m, c), maxe, out, depth + 1, zf, tol); _split((m, b, c), maxe, out, depth + 1, zf, tol)
    elif k == 1:
        m = ((b[0] + c[0]) / 2, (b[1] + c[1]) / 2); _split((a, b, m), maxe, out, depth + 1, zf, tol); _split((a, m, c), maxe, out, depth + 1, zf, tol)
    else:
        m = ((c[0] + a[0]) / 2, (c[1] + a[1]) / 2); _split((a, b, m), maxe, out, depth + 1, zf, tol); _split((m, b, c), maxe, out, depth + 1, zf, tol)


def triangles(geom, spacing=6.0, interior=True, zf=None):
    """shapely(Multi)Polygon → 三角形[(p,p,p)]。制約付きearcutで穴なく分割し、interior=Trueなら最長辺を2*spacing以下に細分化(地形追従)"""
    from .assemble import _tess
    out = []
    gs = []

    def collect(x):
        if x.geom_type == "Polygon":
            gs.append(x)
        elif hasattr(x, "geoms"):
            for y in x.geoms:
                collect(y)
    collect(geom)
    for g in gs:
        if g.area < 0.3:
            continue
        g = g.segmentize(spacing)
        if g.geom_type != "Polygon":
            out += triangles(g, spacing, interior, zf)
            continue
        for tri in _tess(g):
            t = tuple((v.x, v.y) for v in tri)
            if interior:
                _split(t, spacing * 1.6, out, 0, zf)
            else:
                out.append(t)
    return out


def fill(mesh, geom, zf, mat, spacing=6.0, interior=True, uv=None):
    """面geomを地形zf(x,y)に沿って塗る(上向き)。uvは(x,y)->(u,v)で省略時はメートルのボックス投影"""
    for t in triangles(geom, spacing, interior, zf):
        pts = [(x, y, zf(x, y)) for x, y in t]
        a, b, c = pts
        n = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if n < 0:
            pts = pts[::-1]
        mesh.poly(pts, mat, [uv(p[0], p[1]) for p in pts] if uv else None)


def sample_line(line, step):
    n = max(1, int(math.ceil(line.length / step)))
    return [line.interpolate(line.length * i / n) for i in range(n + 1)], line.length


def frames(pts):
    """点列→(x,y,tx,ty,nx,ny): 接線と左法線(隅は前後平均)"""
    xy = [(p.x, p.y) for p in pts] if hasattr(pts[0], "x") else list(pts)
    out = []
    for i, (x, y) in enumerate(xy):
        a = xy[max(i - 1, 0)]; b = xy[min(i + 1, len(xy) - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1.0
        tx, ty = tx / L, ty / L
        out.append((x, y, tx, ty, -ty, tx))
    return out


def sweep(mesh, path, profile, zf_path):
    """経路(点列)に沿って断面(t,dz)の閉多角形を押し出す。
    path: [(x,y)], profile: i→[(t,dz,mat)] の閉多角形(CCW, t=経路の左が+, dz=上が+, matはその頂点から次頂点への辺の材質)。zf_path[i]=経路の高さ。
    UV=(経路長s[m], 断面の周長v[m]) なので、テクスチャは経路に沿って貼られる。"""
    fr = frames(path)
    prev = None
    s_acc = 0.0
    for i, (x, y, tx, ty, nx, ny) in enumerate(fr):
        if i:
            s_acc += math.hypot(x - fr[i - 1][0], y - fr[i - 1][1])
        prof = profile(i)
        ring = [(x + nx * t, y + ny * t, zf_path[i] + dz) for t, dz, _ in prof]
        per = [0.0]
        for k in range(len(prof)):
            k2 = (k + 1) % len(prof)
            per.append(per[-1] + math.hypot(prof[k2][0] - prof[k][0], prof[k2][1] - prof[k][1]))
        if prev is not None and len(prev[0]) == len(ring):
            pr, ps = prev
            n = len(ring)
            for k in range(n):
                k2 = (k + 1) % n
                t0, d0, m = prof[k]; t1, d1, _ = prof[k2]
                et, ez = t1 - t0, d1 - d0
                L = math.hypot(et, ez) or 1.0
                ont, onz = ez / L, -et / L
                out = (nx * ont, ny * ont, onz)
                mesh.oriented([pr[k], pr[k2], ring[k2], ring[k]], out, m, [(ps, per[k]), (ps, per[k + 1]), (s_acc, per[k + 1]), (s_acc, per[k])])
        prev = (ring, s_acc)


def ribbon(mesh, path, zs, t0, t1, mat, zoff=0.0, swap=False):
    """経路沿いの水平帯(上向き)。UV=(経路長s[m], 横t[m])"""
    fr = frames(path)
    s = 0.0
    prev = None
    for i, (x, y, tx, ty, nx, ny) in enumerate(fr):
        if i:
            s += math.hypot(x - fr[i - 1][0], y - fr[i - 1][1])
        a = (x + nx * t0, y + ny * t0, zs[i] + zoff); b = (x + nx * t1, y + ny * t1, zs[i] + zoff)
        cur = (a, b, s)
        if prev:
            pa, pb, ps = prev
            uv = [(ps, t0), (ps, t1), (s, t1), (s, t0)]
            mesh.oriented([pa, pb, b, a], (0, 0, 1), mat, [(v, u) for u, v in uv] if swap else uv)
        prev = cur


def decal(mesh, cx, cy, ang, w, l, mat, zf, off=0.012, mirror=False):
    """向きang(進行方向)に長さl・幅wのデカール。UV: u=横, v=進行方向(画像の上=進行方向)"""
    c, s = math.cos(ang), math.sin(ang)
    corners = [(-w / 2, -l / 2), (w / 2, -l / 2), (w / 2, l / 2), (-w / 2, l / 2)]
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
    pts = []
    for (u, v) in corners:
        # 横方向=右手(進行方向の右)
        x = cx + c * v + s * u
        y = cy + s * v - c * u
        pts.append((x, y, zf(x, y) + off))
    mesh.oriented(pts, (0, 0, 1), mat, uvs)


def stripe(mesh, line, off, width, on, gap, mat, zf, z_off=0.01, start=0.0, end=None):
    """線に沿ったライン標示。on/gap=破線の線長/空き(gap=0で実線)。lineの左がoff>0"""
    if line.length < 0.5:
        return
    try:
        ol = line.offset_curve(off) if abs(off) > 1e-6 else line
    except Exception:
        return
    if ol.is_empty or ol.geom_type != "LineString":
        return
    L = ol.length
    end = L if end is None else min(end, L)
    s = start
    while s < end - 0.05:
        e = min(s + (on if gap else end - start), end)
        n = max(1, int((e - s) / 3))
        pts = [ol.interpolate(s + (e - s) * i / n) for i in range(n + 1)]
        fr = frames(pts)
        prev = None
        for i, (x, y, tx, ty, nx, ny) in enumerate(fr):
            a = (x + nx * width / 2, y + ny * width / 2); b = (x - nx * width / 2, y - ny * width / 2)
            cur = (a, b, s + (e - s) * i / n)
            if prev:
                pa, pb, ps = prev
                P = [(q[0], q[1], zf(q[0], q[1]) + z_off) for q in (pa, pb, b, a)]
                mesh.oriented(P, (0, 0, 1), mat, [(ps, 0), (ps, 1), (cur[2], 1), (cur[2], 0)])
            prev = cur
        s += on + gap if gap else 1e9
