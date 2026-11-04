import random

from .geom import Mesh

REG = {}  # name -> dict(fn, W, H, cat)
T = 0.25  # 壁厚(y: -T..0)


def mod(name, W=3.6, H=3.5, cat="misc", **meta):
    def deco(fn):
        REG[name] = dict(fn=fn, W=W, H=H, cat=cat, **meta)
        return fn
    return deco


def reg(name, fn, W=3.6, H=3.5, cat="misc", **meta):
    REG[name] = dict(fn=fn, W=W, H=H, cat=cat, **meta)


def build(name):
    r = REG[name]
    m = Mesh()
    r["fn"](m, r["W"], r["H"], random.Random(name))
    return m


def hole_wall(m, W, H, x0, x1, z0, z1, mat, t=T, seam=0.006, reveal=0.006):
    """開口付き壁。1枚の閉メッシュ(リング)で、モジュール境界(継ぎ目)と開口見付に面取りを付ける。"""
    m.ring((-W / 2, W / 2, 0, H), (x0, x1, z0, z1), -t, 0.0, mat, seam, reveal)


def frame(m, x0, x1, z0, z1, mat, fw=0.06, d=0.1, y=-0.16):
    """サッシ枠: 外枠(面取り) + 段付きの内側リップ + ガスケット(ゴム) + 押縁(グレイジングビード)。"""
    O = (x0, x1, z0, z1)
    I = (x0 + fw, x1 - fw, z0 + fw, z1 - fw)
    m.ring(O, I, y, y + d, mat, min(0.006, fw * 0.15), 0.003)
    lip = min(0.02, fw * 0.4)
    I2 = (I[0] + lip, I[1] - lip, I[2] + lip, I[3] - lip)
    m.ring(I, I2, y, y + d * 0.45, mat)  # ガラスを受けるリップ(奥)
    g = 0.007
    I3 = (I[0] + g, I[1] - g, I[2] + g, I[3] - g)
    m.ring(I, I3, y + d * 0.3, y + d * 0.75, "rubber")  # ガスケット
    I4 = (I[0] + 0.015, I[1] - 0.015, I[2] + 0.015, I[3] - 0.015)
    m.ring(I3, I4, y + d * 0.6, y + d * 0.92, mat, 0.0, 0.002)  # 押縁(ビード)


def glass(m, x0, x1, z0, z1, y=-0.11, mat="glass_main"):
    m.box(x0, y, z0, x1, y + 0.012, z1, mat)


def interior(m, x0, x1, z0, z1, y=-0.24):
    m.box(x0, y - 0.01, z0, x1, y, z1, "interior")
