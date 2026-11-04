"""Anny 由来の歩行者モジュール(anny_<group>_<k>)。姿勢(モーションクリップの位相)を焼いた静的メッシュ(低ポリ topology)。
体型・服・髪は humans.py / humans_wear.py が決める。生成時だけ torch を読むので、REG への登録は名前だけの遅延生成(lazy=True)。"""
from .registry import reg

GROUPS = dict(office=16, casual=34, elder=14, student=14, kid=10, heavy=6, worker=10)
LOD = "notoes_collapse10pc"
DECIM_MIN = int(__import__("os").environ.get("HVT_DECIM_MIN", 2500))
# group ごとのモーション(クリップ名, 重み)。walk 系=歩道を歩く人 / idle 系=横断待ち・立ち話 / sit=ベンチ
CLIPS = dict(
    office=[("walk_formal", 5), ("walk", 3), ("idle_phone", 2), ("idle", 2), ("carry", 2), ("talk", 1)],
    casual=[("walk", 5), ("walk_slow", 2), ("idle", 3), ("idle_phone", 3), ("talk", 2), ("carry", 2), ("jog", 1), ("idle_hands", 1), ("wave", 1), ("sit", 1)],
    elder=[("walk_slow", 6), ("idle", 3), ("talk", 2), ("carry", 2), ("sit", 1), ("idle_hands", 1)],
    student=[("walk", 4), ("jog", 1), ("idle_phone", 3), ("talk", 3), ("idle", 2), ("wave", 1), ("sit_talk", 1)],
    kid=[("walk", 3), ("run", 2), ("jog", 1), ("idle", 2), ("wave", 1)],
    heavy=[("walk_slow", 4), ("idle", 2), ("idle_phone", 1), ("carry", 1)],
    worker=[("walk", 4), ("idle", 2), ("carry", 3), ("push", 1), ("interact", 1)],
)
WALK = {"walk", "walk_slow", "walk_formal", "jog", "run", "carry", "push"}
WAIT = {"idle", "idle_phone", "idle_hands", "talk", "wave", "interact"}
PARK = {"talk", "idle", "idle_phone", "wave", "idle_hands"}


def spec_of(group, k):
    from .. import humans
    return humans.sample(100 + k, group)


def pose_of(group, k):
    """k 番目の人物のクリップと位相(人ごとにずらす)"""
    import random
    r = random.Random((k * 2654435761 + len(group) * 97) % 10 ** 9)
    cl = CLIPS[group]
    names = [c for c, _ in cl]
    ph = (k * 0.381966 + r.random() * 0.2) % 1.0
    return r.choices(names, weights=[w for _, w in cl])[0], ph


def _subset(m, H, b, g, pred, mat_of, push=0.0, cell=0.0):
    import numpy as np
    F, parts = b["full"]["faces"], b["full"]["parts"]
    sel = [i for i, p in enumerate(parts) if pred(p)]
    if not sel:
        return
    vi = np.unique(F[sel])
    remap = {int(v): i for i, v in enumerate(vi)}
    P = b["full"]["v"][vi] + b["full"]["nrm"][vi] * push
    o = len(m.v)
    if cell:
        V2, tris = H.decimate(H.to_world(P, ground=g), [[remap[int(v)] for v in F[i]] for i in sel], cell)
        m.v.extend(map(tuple, V2.tolist()))
        mat = mat_of(parts[sel[0]])
        for t in tris:
            m.f.append(tuple(i + o for i in t)); m.m.append(mat); m.uv.append(None)
        return
    m.v.extend(map(tuple, H.to_world(P, ground=g).tolist()))
    for i in sel:
        m.f.append(tuple(remap[int(v)] + o for v in F[i])); m.m.append(mat_of(parts[i])); m.uv.append(None)


def _push_out(H, b, g, V, margin=0.009):
    """間引いた衣服が体の中に潜らないよう、低ポリ体表の外側へ押し出す(2回)"""
    import numpy as np
    from scipy.spatial import cKDTree
    Vb = H.to_world(b["v"], ground=g)
    nb = H._vnormals(Vb, b["faces"])
    kd = cKDTree(Vb)
    V = V.copy()
    for _ in range(2):
        _, j = kd.query(V, k=4)
        sd = ((V[:, None, :] - Vb[j]) * nb[j]).sum(2)
        w = np.argmin(sd, axis=1)
        jj = j[np.arange(len(V)), w]
        V += nb[jj] * np.maximum(0.0, margin - sd[np.arange(len(V)), w])[:, None]
    return V


def _ellipse(m, H, g, c, t, u, a, bb, mat, n=12):
    """面上の楕円デカール(扇形。法線 t×u 向き)。c,t,u は Anny 座標"""
    import math

    import numpy as np
    ring = [c + t * a * math.cos(2 * math.pi * k / n) + u * bb * math.sin(2 * math.pi * k / n) for k in range(n)]
    P = H.to_world(np.array([c] + ring), ground=g)
    o = len(m.v)
    m.v.extend(map(tuple, P.tolist()))
    nrm = np.cross(t, u)
    nw = np.array([-nrm[0], -nrm[1], nrm[2]])
    for k in range(n):
        tri = (o, o + 1 + k, o + 1 + (k + 1) % n)
        e = np.cross(P[tri[1] - o] - P[0], P[tri[2] - o] - P[0])
        if e @ nw < 0:
            tri = (tri[0], tri[2], tri[1])
        m.f.append(tri); m.m.append(mat); m.uv.append(None)


def _face_decals(m, H, b, g, of):
    """低ポリ頭部に目(白目+黒目+まぶた線)・眉・口をデカールで足す。穴にならないよう表面に貼る"""
    import numpy as np
    from scipy.spatial import cKDTree
    F, parts, Vf = b["full"]["faces"], b["full"]["parts"], b["full"]["v"]
    nrm_l = H._vnormals(b["v"], b["faces"])
    Vl = b["v"]
    kd = cKDTree(Vl)
    up = np.array([0, 0, 1.0])

    def centroid(pred):
        sel = [i for i, p in enumerate(parts) if pred(p)]
        return Vf[np.unique(F[sel])].mean(0) if sel else None

    def frame(c):
        d, j = kd.query(c)
        n = nrm_l[j]
        p = c - n * ((c - Vl[j]) @ n)
        t = np.cross(up, n)
        t /= max(np.linalg.norm(t), 1e-9)
        u = np.cross(n, t)
        return p, n, t, u
    for sd in ("L", "R"):
        c = centroid(lambda p, sd=sd: p == f"eye_front.{sd}")
        if c is None:
            continue
        p, n, t, u = frame(c)
        _ellipse(m, H, g, p + n * 0.0012, t, u, 0.0138, 0.0074, "anny_eye_dark")
        _ellipse(m, H, g, p + n * 0.0016, t, u, 0.0120, 0.0056, "anny_eye_white")
        _ellipse(m, H, g, p + n * 0.0020, t, u, 0.0050, 0.0050, "anny_iris")
        brow = p + u * 0.0235 + n * 0.0014
        _ellipse(m, H, g, brow, t, u, 0.0165, 0.0036, f"anny_brow_{of['hair_color']}", 8)
    c = centroid(lambda p: p == "mouth_cavity")
    if c is not None:
        p, n, t, u = frame(c)
        _ellipse(m, H, g, p + n * 0.0012, t, u, 0.0190, 0.0042, "anny_lip")


def build_mesh(m, group, k, topology=LOD, pose_override=None):
    """humans.build の結果を Mesh(共有頂点・スムース)に詰める"""
    from .. import humans as H
    spec = spec_of(group, k)
    pn, ph = pose_override or pose_of(group, k)
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
    outer = any(c["slot"] in ("jacket", "blazer", "coat") for c in b["cloth"])
    for c in b["cloth"]:
        if outer and c["slot"] == "top":
            continue
        o = len(m.v)
        Vc = H.to_world(c["V"], ground=g)
        vt = c["cl"]["vt"]
        faces = c["cl"]["faces"]
        if topology != "anny" and not c["uv"] and len(faces) > DECIM_MIN:
            cell = 0.006
            while True:
                V2, tris = H.decimate(Vc, [[vi for vi, _ in f] for f in faces], cell)
                if len(tris) <= 5000 or cell > 0.011:
                    break
                cell *= 1.2
            V2 = _push_out(H, b, g, V2)
            m.v.extend(map(tuple, V2.tolist()))
            for t in tris:
                m.f.append(tuple(i + o for i in t)); m.m.append(c["mat"]); m.uv.append(None)
            continue
        m.v.extend(map(tuple, Vc.tolist()))
        for face in faces:
            m.f.append(tuple(vi + o for vi, _ in face)); m.m.append(c["mat"])
            m.uv.append([tuple(vt[t]) for _, t in face] if c["uv"] else None)
    _subset(m, H, b, g, lambda p: p.startswith("foot"), lambda p: f"anny_shoe_{of['shoe_color']}", push=0.007, cell=0.016 if topology != "anny" else 0.0)
    if topology != "anny":
        _face_decals(m, H, b, g, of)
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
ALL = [n for v in NAMES.values() for n in v]


def clip_of(name):
    """モジュール名 → そのクリップ名(都市配置の役割分けに使う)"""
    _, g, k = name.split("_")
    return pose_of(g, int(k))[0]


def by_role(role):
    """role: walk(歩道を歩く)/ wait(横断待ち・立ち話)/ park(公園・ベンチ)。該当クリップの人物名のリスト"""
    s = dict(walk=WALK, wait=WAIT, park=PARK)[role]
    return [n for n in ALL if clip_of(n) in s]
