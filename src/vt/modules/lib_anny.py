"""Anny 由来の歩行者モジュール(anny_<group>_<k>)。姿勢(モーションクリップの位相)を焼いた静的メッシュ(低ポリ topology)。
体型・服・髪は humans.py / humans_wear.py が決める。生成時だけ torch を読むので、REG への登録は名前だけの遅延生成(lazy=True)。"""
from .registry import reg

GROUPS = dict(office=16, casual=34, elder=14, student=14, kid=10, heavy=6, worker=10)
LOD = "notoes_collapse10pc"
DECIM_MIN = int(__import__("os").environ.get("HVT_DECIM_MIN", 2500))
# group ごとのモーション(クリップ名, 重み)。walk 系=歩道を歩く人 / idle 系=横断待ち・立ち話 / sit=ベンチ
CLIPS = dict(
    office=[("walk_formal", 7), ("walk", 3), ("idle", 4), ("idle_phone", 2), ("carry", 2), ("talk", 1)],
    casual=[("walk", 8), ("walk_slow", 2), ("idle", 5), ("idle_phone", 3), ("talk", 1), ("carry", 2), ("jog", 1), ("wave", 1)],
    elder=[("walk_slow", 8), ("idle", 4), ("talk", 1), ("carry", 2), ("idle_hands", 1)],
    student=[("walk", 6), ("jog", 1), ("idle_phone", 3), ("talk", 1), ("idle", 3), ("wave", 1)],
    kid=[("walk", 4), ("run", 2), ("jog", 1), ("idle", 3), ("wave", 1)],
    heavy=[("walk_slow", 5), ("idle", 3), ("idle_phone", 1), ("carry", 1)],
    worker=[("walk", 5), ("idle", 3), ("carry", 3), ("push", 1)],
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


def _shoes(m, H, b, g, of, lod):
    """靴: 足の面を押し出し、高さでソール/アッパーに材質を分け、スニーカーは甲に紐を足す"""
    import numpy as np
    F, parts, Vf, nf = b["full"]["faces"], b["full"]["parts"], b["full"]["v"], b["full"]["nrm"]
    sel = [i for i, p in enumerate(parts) if p.startswith("foot")]
    if not sel:
        return
    vi = np.unique(F[sel])
    rm = {int(v): i for i, v in enumerate(vi)}
    P = H.to_world(Vf[vi] + nf[vi] * 0.007, ground=g)
    faces = [[rm[int(v)] for v in F[i]] for i in sel]
    if lod:
        P, faces = H.decimate(P, faces, 0.016)
    o = len(m.v)
    m.v.extend(map(tuple, P.tolist()))
    sole, upper = f"anny_sole_{of['sole']}", f"anny_shoe_{of['shoe_color']}"
    for t in faces:
        zc = sum(P[i][2] for i in t) / len(t)
        m.f.append(tuple(i + o for i in t)); m.m.append(sole if zc < 0.022 else upper); m.uv.append(None)
    if of["shoe_type"] != "sneaker":
        return
    L = H.model("anny").bone_labels
    bp = b["bones_pose"]
    for sd in ("l", "r"):
        foot, ball = bp[L.index(f"foot_{sd}")][:3, 3], bp[L.index(f"ball_{sd}")][:3, 3]
        d = (ball - foot) * np.array([1, 1, 0.0])
        dl = np.linalg.norm(d)
        if dl < 1e-3:
            continue
        d /= dl
        lat = np.array([-d[1], d[0], 0.0])
        pts = Vf[vi]
        for t in np.linspace(0.1, 0.55, 5):
            c = foot + d * dl * t
            rel = pts - c
            near = (np.abs(rel @ d) < 0.012) & (np.abs(rel @ lat) < 0.03)
            if not near.any():
                continue
            zc = pts[near][:, 2].max() + 0.007 + 0.002
            q = np.array([c + lat * 0.024 + d * 0.004, c - lat * 0.024 + d * 0.004, c - lat * 0.024 - d * 0.004, c + lat * 0.024 - d * 0.004])
            q[:, 2] = zc
            W = H.to_world(q, ground=g)
            o = len(m.v)
            m.v.extend(map(tuple, W.tolist()))
            m.f.append((o, o + 1, o + 2)); m.m.append(f"anny_lace_{of['lace']}"); m.uv.append(None)
            m.f.append((o, o + 2, o + 3)); m.m.append(f"anny_lace_{of['lace']}"); m.uv.append(None)


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


def _quad(m, H, g, c, t, u, w, h, uv, mat, flip=False):
    """面上のテクスチャ付き四角形デカール(c=中心、t=右、u=上、Anny 座標)。uv=(u0,v0,u1,v1)"""
    import numpy as np
    u0, v0, u1, v1 = uv
    if flip:
        u0, u1 = u1, u0
    P = np.array([c - t * w / 2 + u * h / 2, c + t * w / 2 + u * h / 2, c + t * w / 2 - u * h / 2, c - t * w / 2 - u * h / 2])
    UV = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
    W = H.to_world(P, ground=g)
    o = len(m.v)
    m.v.extend(map(tuple, W.tolist()))
    nrm = np.cross(t, u)
    nw = np.array([-nrm[0], -nrm[1], nrm[2]])
    for tri in ((0, 1, 2), (0, 2, 3)):
        e = np.cross(W[tri[1]] - W[tri[0]], W[tri[2]] - W[tri[0]])
        idx = tri if e @ nw >= 0 else (tri[0], tri[2], tri[1])
        m.f.append(tuple(o + i for i in idx)); m.m.append(mat); m.uv.append([UV[i] for i in idx])


def _face_decals(m, H, b, g, of):
    """低ポリ頭部に顔のデカールを貼る: 目(虹彩・白目・ハイライト・まつげ)・眉・唇(笑顔で歯)・血色・くま・そばかす・ほくろ・しわ。年齢・性別・髪色に連動"""
    import random

    import numpy as np
    from scipy.spatial import cKDTree

    from .. import textures_human as TH
    spec = b["spec"]
    rng = random.Random(spec["seed"] * 101 + 7)
    yr, fem = spec["years"], spec["female"]
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
        return p, n, t, np.cross(n, t)
    k = [0]

    def put(p, n, t, u, off_t, off_u, w, h, uv, mat, flip=False):
        k[0] += 1
        c = p + t * off_t + u * off_u + n * (0.0011 + 0.00018 * k[0])
        _quad(m, H, g, c, t, u, w, h, uv, mat, flip)
    eye = rng.randrange(4) if rng.random() < 0.15 else rng.choice([0, 1, 1])
    brow = rng.randrange(4)
    hc = of["hair_color"] if of["hair_color"] in ("black", "dark", "brown", "chestnut", "gray", "white", "blond", "auburn") else "dark"
    pts = {}
    for sd in ("L", "R"):
        c = centroid(lambda p, sd=sd: p == f"eye_front.{sd}")
        if c is None:
            continue
        p, n, t, u = frame(c)
        pts[sd] = (p, n, t, u)
        flip = sd == "R"
        put(p, n, t, u, 0.0, 0.0, 0.047, 0.0245, TH.face_uv("eye", eye), "anny_face", flip)
        put(p, n, t, u, 0.0, 0.0285, 0.050, 0.0155, TH.face_uv("brow", brow), f"anny_brow_{hc}", flip)
        out = 1.0 if sd == "L" else -1.0
        if (fem and yr < 42 and rng.random() < 0.7) or rng.random() < 0.2:
            put(p, n, t, u, out * 0.012, -0.040, 0.058, 0.042, TH.face_uv("blush", 0), "anny_face")
        if yr > 38 or rng.random() < 0.2:
            put(p, n, t, u, 0.0, -0.0165, 0.036, 0.018, TH.face_uv("blush", 1), "anny_face")
        if yr > 45:
            put(p, n, t, u, out * 0.030, 0.0, 0.028, 0.022, TH.face_uv("wrinkle", 1), "anny_face", sd == "R")
    if "L" in pts and "R" in pts:
        mid = (pts["L"][0] + pts["R"][0]) / 2
        p, n, t, u = frame(mid)
        if yr > 50:
            put(p, n, t, u, 0.0, 0.052, 0.085, 0.032, TH.face_uv("wrinkle", 0), "anny_face")
        if yr < 40 and rng.random() < 0.18:
            put(p, n, t, u, 0.0, -0.022, 0.105, 0.042, TH.face_uv("blush", 2), "anny_face")
        if rng.random() < 0.10:
            put(p, n, t, u, rng.uniform(-0.04, 0.04), rng.uniform(-0.05, -0.02), 0.0065, 0.0065, TH.face_uv("blush", 3), "anny_face")
    c = centroid(lambda p: p == "mouth_cavity")
    if c is not None:
        p, n, t, u = frame(c)
        smile = spec.get("expr", {}).get("mouthSmileLeft", 0.0)
        tile = 3 if smile > 0.32 else (1 if fem and rng.random() < 0.5 else rng.choice([0, 0, 2]))
        put(p, n, t, u, 0.0, 0.0, 0.044, 0.022, TH.face_uv("lips", tile), "anny_face")
        if yr > 50:
            for sg in (1, -1):
                put(p, n, t, u, sg * 0.024, 0.016, 0.03, 0.038, TH.face_uv("wrinkle", 2), "anny_face", sg < 0)


def build_mesh(m, group, k, topology=LOD, pose_override=None, cache=None, ground=None, decimate=True):
    """humans.build の結果を Mesh(共有頂点・スムース)に詰める"""
    from .. import humans as H
    spec = spec_of(group, k)
    pn, ph = pose_override or pose_of(group, k)
    b = H.build(spec, topology=topology, posename=pn, phase=ph, cache=cache)
    g = float(b["v"][:, 2].min()) - 0.007 if ground is None else ground
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
        if decimate and topology != "anny" and not c["uv"] and len(faces) > DECIM_MIN:
            cell = 0.006
            while True:
                V2, tris = H.decimate(Vc, [[vi for vi, _ in f] for f in faces], cell)
                if len(tris) <= 5000 or cell > 0.011:
                    break
                cell *= 1.2
            V2 = V2 if any(k in c["name"] for k in ("skirt", "tiered")) else _push_out(H, b, g, V2)
            m.v.extend(map(tuple, V2.tolist()))
            for t in tris:
                m.f.append(tuple(i + o for i in t)); m.m.append(c["mat"]); m.uv.append(None)
            continue
        m.v.extend(map(tuple, Vc.tolist()))
        for face in faces:
            m.f.append(tuple(vi + o for vi, _ in face)); m.m.append(c["mat"])
            m.uv.append([tuple(vt[t]) for _, t in face] if c["uv"] else None)
    if topology != "anny":
        _subset(m, H, b, g, lambda p: p.startswith("hand"), lambda p: f"anny_skin_{of['skin']}", push=0.004, cell=0.0045 if decimate else 0.0)
    _shoes(m, H, b, g, of, decimate and topology != "anny")
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
