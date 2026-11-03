"""最小メッシュビルダ。モジュール座標: x=壁に沿う(中心0), y=外向き(壁面y=0), z=上(床0)。"""
import math


# 材質ごとの自動面取り量[m]。小さい面は寸法/4に制限、薄板(ガラス等)は対象外
BEV = {"rc_concrete": 0.012, "paint_main": 0.008, "paint_dark": 0.008, "paint_white": 0.008, "alc": 0.004,
       "stone_main": 0.006, "quartz": 0.004, "marble": 0.004, "brick_main": 0.003, "tile_main": 0.0025,
       "alu_main": 0.003, "alu_silver": 0.003, "alu_black": 0.003, "steel_gray": 0.004, "steel_white": 0.004,
       "steel_green": 0.004, "steel_galv": 0.003, "wood": 0.004, "metal_siding": 0.003, "ac_white": 0.008,
       "plastic_gray": 0.004, "spray_main": 0.006}


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _newell(p):
    n = [0.0, 0.0, 0.0]
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]
        n[0] += (a[1] - b[1]) * (a[2] + b[2])
        n[1] += (a[2] - b[2]) * (a[0] + b[0])
        n[2] += (a[0] - b[0]) * (a[1] + b[1])
    return n


class Mesh:
    def __init__(s):
        s.v, s.f, s.m, s.uv, s.lights = [], [], [], [], []   # lights: USD光源の記述。uv: 面ごとの頂点UV列(None=自動のボックス投影[m])

    def quad(s, a, b, c, d, mat, uv=None):
        s.poly([a, b, c, d], mat, uv)

    def poly(s, pts, mat, uv=None):
        i = len(s.v)
        s.v.extend(pts)
        s.f.append(tuple(range(i, i + len(pts))))
        s.m.append(mat)
        s.uv.append(uv)

    def oriented(s, pts, outward, mat, uv=None):
        n = _newell(pts)
        if n[0] * outward[0] + n[1] * outward[1] + n[2] * outward[2] < 0:
            pts = pts[::-1]
            uv = uv[::-1] if uv else None
        s.poly(pts, mat, uv)

    def lathe(s, cx, cy, z0, prof, mat, n=16):
        """z軸まわりの回転体。prof=[(r,dz)...]を下から上へ(外面)。(cx,cy,z0)が基準"""
        for i in range(len(prof) - 1):
            (r0, d0), (r1, d1) = prof[i], prof[i + 1]
            if r0 <= 1e-9 and r1 <= 1e-9:
                continue
            dr, dz = r1 - r0, d1 - d0
            for k in range(n):
                a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
                P = lambda r, d, a: (cx + r * math.cos(a), cy + r * math.sin(a), z0 + d)
                am = (a0 + a1) / 2
                out = (dz * math.cos(am), dz * math.sin(am), -dr)
                pts = [P(r0, d0, a0), P(r0, d0, a1), P(r1, d1, a1), P(r1, d1, a0)]
                if r0 <= 1e-9:
                    pts = [P(r0, d0, a0), P(r1, d1, a1), P(r1, d1, a0)]
                elif r1 <= 1e-9:
                    pts = [P(r0, d0, a0), P(r0, d0, a1), P(r1, d1, a0)]
                s.oriented(pts, out, mat)

    def transformed(s, rot=0.0, tx=0.0, ty=0.0, tz=0.0):
        """z軸回りrot回転+平行移動した複製"""
        c, sn = math.cos(rot), math.sin(rot)
        o = Mesh()
        o.v = [(x * c - y * sn + tx, x * sn + y * c + ty, z + tz) for x, y, z in s.v]
        o.f, o.m, o.uv = list(s.f), list(s.m), list(s.uv)
        o.lights = [dict(l, pos=(l["pos"][0] * c - l["pos"][1] * sn + tx, l["pos"][0] * sn + l["pos"][1] * c + ty, l["pos"][2] + tz)) for l in s.lights]
        return o

    def bbox(s, x0, y0, z0, x1, y1, z1, mat, b):
        """12稜を面取りしたボックス(面6 + 稜12 + 隅8)"""
        lo, hi = (x0, y0, z0), (x1, y1, z1)

        def V(sg, a):
            return tuple((hi[i] if sg[i] > 0 else lo[i]) + (0 if i == a else -sg[i] * b) for i in range(3))
        S = (-1, 1)
        for a in range(3):
            o, p = [i for i in range(3) if i != a]
            for sa in S:
                pts = []
                for so, sp in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    sg = [0, 0, 0]; sg[a], sg[o], sg[p] = sa, so, sp
                    pts.append(V(sg, a))
                out = [0, 0, 0]; out[a] = sa
                s.oriented(pts, out, mat)
        for a, bb, c in ((0, 1, 2), (0, 2, 1), (1, 2, 0)):
            for sa in S:
                for sb in S:
                    pts = []
                    for sc in (-1, 1):
                        sg = [0, 0, 0]; sg[a], sg[bb], sg[c] = sa, sb, sc
                        pts += [V(sg, a), V(sg, bb)] if sc < 0 else [V(sg, bb), V(sg, a)]
                    out = [0, 0, 0]; out[a], out[bb] = sa, sb
                    s.oriented(pts, out, mat)
        for sx in S:
            for sy in S:
                for sz in S:
                    sg = (sx, sy, sz)
                    s.oriented([V(sg, 0), V(sg, 1), V(sg, 2)], sg, mat)

    def ring(s, O, I, y0, y1, mat, bo=0.0, bi=0.0):
        """矩形リング(外O, 内I=(x0,x1,z0,z1))をy0..y1に作る。外前縁bo/内前縁biを面取り。隅は自然に留め継ぎ。"""
        def R(r, d, y):
            return (r[0] + d, r[1] - d, r[2] + d, r[3] - d, y)
        secs = [R(O, 0, y0), R(O, 0, y1 - bo), R(O, bo, y1), R(I, -bi, y1), R(I, 0, y1 - bi), R(I, 0, y0)]
        s.loft(secs, mat)

    def loft(s, secs, mat):
        """secs=(x0,x1,z0,z1,y)の閉断面列を矩形で連結。最大y・平坦な区間の法線が+yになるよう向きを揃える。"""
        n = len(secs)
        quads = []
        for i in range(n):
            A, B = secs[i], secs[(i + 1) % n]
            if A == B:
                continue
            cA = [(A[0], A[4], A[2]), (A[1], A[4], A[2]), (A[1], A[4], A[3]), (A[0], A[4], A[3])]
            cB = [(B[0], B[4], B[2]), (B[1], B[4], B[2]), (B[1], B[4], B[3]), (B[0], B[4], B[3])]
            for k in range(4):
                q = [cA[k], cA[(k + 1) % 4], cB[(k + 1) % 4], cB[k]]
                if len({tuple(round(c, 6) for c in v) for v in q}) >= 3:
                    quads.append((i, q))
        ymax = max(sc[4] for sc in secs)
        flip = False
        for i, q in quads:
            if secs[i][4] == ymax and secs[(i + 1) % n][4] == ymax:
                flip = _newell(q)[1] < 0
                break
        for _, q in quads:
            s.poly(q[::-1] if flip else q, mat)

    def box(s, x0, y0, z0, x1, y1, z1, mat, skip=""):
        if x1 <= x0 or y1 <= y0 or z1 <= z0:
            return
        b = BEV.get(mat, 0.0)
        dm = min(x1 - x0, y1 - y0, z1 - z0)
        if b and not skip and dm >= 0.02:
            return s.bbox(x0, y0, z0, x1, y1, z1, mat, min(b, dm / 4))
        P = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        F = {"b": (0, 3, 2, 1), "t": (4, 5, 6, 7), "f": (0, 1, 5, 4), "k": (2, 3, 7, 6), "l": (3, 0, 4, 7), "r": (1, 2, 6, 5)}
        for k, idx in F.items():
            if k not in skip:
                s.poly([P[i] for i in idx], mat)

    def prism(s, prof, axis, a0, a1, mat, caps=True):
        """prof: CCWの2D輪郭(軸まわりの循環座標: x→(y,z), y→(z,x), z→(x,y))を軸方向に押し出す"""
        def p3(pt, a):
            u, v = pt
            return {"x": (a, u, v), "y": (v, a, u), "z": (u, v, a)}[axis]
        n = len(prof)
        for i in range(n):
            A, B = prof[i], prof[(i + 1) % n]
            s.poly([p3(A, a0), p3(B, a0), p3(B, a1), p3(A, a1)], mat)
        if caps:
            s.poly([p3(p, a1) for p in prof], mat)
            s.poly([p3(p, a0) for p in reversed(prof)], mat)

    def cyl(s, cx, cy, cz, r, length, axis, mat, n=16, caps=True):
        """axis方向に長さlengthの円柱。(cx,cy,cz)は始端中心"""
        prof_c = {"x": (cy, cz), "y": (cz, cx), "z": (cx, cy)}[axis]
        a0 = {"x": cx, "y": cy, "z": cz}[axis]
        prof = [(prof_c[0] + r * math.cos(2 * math.pi * i / n), prof_c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        s.prism(prof, axis, a0, a0 + length, mat, caps)

    def tube(s, cx, cy, cz, r_out, r_in, length, axis, mat, n=24):
        prof_c = {"x": (cy, cz), "y": (cz, cx), "z": (cx, cy)}[axis]
        a0 = {"x": cx, "y": cy, "z": cz}[axis]

        def p3(u, v, a):
            return {"x": (a, u, v), "y": (v, a, u), "z": (u, v, a)}[axis]
        for i in range(n):
            t0, t1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            c0, s0, c1, s1 = math.cos(t0), math.sin(t0), math.cos(t1), math.sin(t1)
            O = lambda c, sn, a: p3(prof_c[0] + r_out * c, prof_c[1] + r_out * sn, a)
            I = lambda c, sn, a: p3(prof_c[0] + r_in * c, prof_c[1] + r_in * sn, a)
            s.poly([O(c0, s0, a0), O(c1, s1, a0), O(c1, s1, a0 + length), O(c0, s0, a0 + length)], mat)
            s.poly([I(c1, s1, a0), I(c0, s0, a0), I(c0, s0, a0 + length), I(c1, s1, a0 + length)], mat)
            s.poly([O(c1, s1, a0 + length), I(c1, s1, a0 + length), I(c0, s0, a0 + length), O(c0, s0, a0 + length)], mat)
            s.poly([O(c0, s0, a0), I(c0, s0, a0), I(c1, s1, a0), O(c1, s1, a0)], mat)

    def slat_x(s, x0, x1, yc, zc, length, thick, ang, mat):
        """x方向に押し出した傾斜板(yz断面, 中心(yc,zc), 角度ang[rad]で傾く)"""
        c, sn = math.cos(ang), math.sin(ang)
        pts = []
        for (u, v) in [(-length / 2, -thick / 2), (length / 2, -thick / 2), (length / 2, thick / 2), (-length / 2, thick / 2)]:
            pts.append((yc + u * c - v * sn, zc + u * sn + v * c))
        s.prism(pts, "x", x0, x1, mat)

    def add(s, o, tx=0, ty=0, tz=0):
        i = len(s.v)
        s.v.extend((x + tx, y + ty, z + tz) for x, y, z in o.v)
        s.f.extend(tuple(j + i for j in f) for f in o.f)
        s.m.extend(o.m)
        s.uv.extend(o.uv)
