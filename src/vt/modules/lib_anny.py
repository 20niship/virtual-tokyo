"""Anny 由来の歩行者モジュール(anny_<group>_<k>)。姿勢を焼いた静的メッシュ(低ポリ topology)。
体型・服・髪は humans.py が決める。モジュール生成時だけ torch を読むので、REG への登録は名前だけの遅延生成(lazy=True)。"""
import random

from .registry import reg

GROUPS = dict(office=10, casual=16, elder=8, student=8, kid=6, heavy=4)
LOD = "notoes_collapse10pc"
POSES = ["stand", "walk", "walk", "phone", "wait"]
_CACHE = {}


def spec_of(group, k):
    from .. import humans
    return humans.sample(100 + k, group)


def pose_of(k):
    return POSES[k % len(POSES)], 0.4 + 0.9 * (k % 7)


def _subset(m, H, b, g, pred, mat_of, push=0.0):
    import numpy as np
    F, parts = b["full"]["faces"], b["full"]["parts"]
    sel = [i for i, p in enumerate(parts) if pred(p)]
    if not sel:
        return
    vi = np.unique(F[sel])
    remap = {int(v): i for i, v in enumerate(vi)}
    P = b["full"]["v"][vi] + b["full"]["nrm"][vi] * push
    o = len(m.v)
    m.v.extend(map(tuple, H.to_world(P, ground=g).tolist()))
    for i in sel:
        m.f.append(tuple(remap[int(v)] + o for v in F[i])); m.m.append(mat_of(parts[i])); m.uv.append(None)


def build_mesh(m, group, k, topology=LOD, pose_override=None):
    """humans.build の結果を Mesh(共有頂点・スムース)に詰める"""
    from .. import humans as H
    spec = spec_of(group, k)
    pn, ph = pose_override or pose_of(k)
    b = H.build(spec, topology=topology, posename=pn, phase=ph)
    g = float(b["v"][:, 2].min()) - 0.007
    of = b["outfit"]
    o = len(m.v)
    V = H.to_world(b["v"], ground=g)
    m.v.extend(map(tuple, V.tolist()))
    skin = f"anny_skin_{of['skin']}"
    parts = b["parts"]
    for i, f in enumerate(b["faces"].tolist()):
        mat = skin
        if parts is not None:
            p = parts[i]
            mat = "anny_iris" if p.startswith("eye_front") else "anny_sclera" if p.startswith("eye_back") else "anny_mouth" if p in ("mouth_cavity", "tongue") else "anny_eye_dark" if p.startswith("eye_cavity") else skin
        m.f.append(tuple(x + o for x in f)); m.m.append(mat); m.uv.append(None)
    for c in b["cloth"]:
        o = len(m.v)
        m.v.extend(map(tuple, H.to_world(c["V"], ground=g).tolist()))
        vt = c["cl"]["vt"]
        for face in c["cl"]["faces"]:
            idx = tuple(vi + o for vi, _ in face)
            if c["slot"] == "hair":
                mat = f"anny_hair_{of['hair']}_{of['hair_color']}"
                uv = [tuple(vt[t]) for _, t in face]
            else:
                mat = f"anny_shoe_{of['shoe_color']}" if c["slot"] == "shoes" else f"anny_cl_{of['tops_color' if c['slot'] == 'top' else 'bottom_color']}"
                uv = None
            m.f.append(idx); m.m.append(mat); m.uv.append(uv)
    _subset(m, H, b, g, lambda p: p.startswith("foot"), lambda p: f"anny_shoe_{of['shoe_color']}", push=0.007)
    m.smooth = True
    return b


def _fn(group, k):
    def f(m, W, H, rng):
        build_mesh(m, group, k)
    return f


for _g, _n in GROUPS.items():
    for _k in range(_n):
        reg(f"anny_{_g}_{_k}", _fn(_g, _k), W=0.6, H=1.8, cat="人(anny)", lazy=True)

NAMES = {g: [f"anny_{g}_{k}" for k in range(n)] for g, n in GROUPS.items()}
