"""Anny(Apache-2.0、同梱の MakeHuman 由来データは CC0)による人物生成。SMPL-X 互換トポロジ(非商用)は使わない。"""
import math
import os
import random
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PK = ROOT / "data/humans/pk"          # MakeHuman asset packs (CC0)。信頼しないデータとして data/ に隔離
TEXDIR = ROOT / "assets/textures"

# 日本人の身長(成人男性 約171cm / 女性 約158cm)に合わせた調整表。weight/muscle は anny の 0..1 値(0.5 が標準)
PROFILES = {
    "office":  dict(p_f=0.40, age=(24, 58), h=((171, 5.8), (158, 5.4)), w=(0.44, 0.10), mu=(0.46, 0.10)),
    "casual":  dict(p_f=0.50, age=(18, 62), h=((171, 6.0), (158, 5.5)), w=(0.45, 0.12), mu=(0.45, 0.12)),
    "elder":   dict(p_f=0.55, age=(66, 88), h=((165, 6.0), (151, 5.5)), w=(0.46, 0.12), mu=(0.38, 0.10)),
    "student": dict(p_f=0.50, age=(15, 18), h=((169, 5.7), (157, 5.2)), w=(0.40, 0.09), mu=(0.42, 0.10)),
    "kid":     dict(p_f=0.50, age=(5, 12), h=None, w=(0.45, 0.08), mu=(0.40, 0.06)),
    "worker":  dict(p_f=0.12, age=(22, 62), h=((171, 5.8), (158, 5.4)), w=(0.50, 0.12), mu=(0.55, 0.10)),
    "heavy":   dict(p_f=0.40, age=(30, 65), h=((170, 6.0), (157, 5.5)), w=(0.72, 0.08), mu=(0.50, 0.10)),
}


FACE_LABELS = None


def _face_labels():
    """顔まわりの local_changes ラベル(頬・顎・耳・目・鼻・口・額・眉)。腕・胸・臀部は体型パラメータ側で扱う"""
    global FACE_LABELS
    if FACE_LABELS is None:
        keys = ("cheek", "chin", "ear", "eye", "nose", "mouth", "lip", "forehead", "eyebrow", "jaw", "head")
        FACE_LABELS = [l for l in model("anny").local_change_labels if any(k in l for k in keys) and "measure" not in l]
    return FACE_LABELS


def age_param(years):
    """歳 → anny の age(0=1歳, 0.1≈2.5歳, 0.2≈6歳, 0.3≈10歳, 0.4≈14歳, 0.5=25歳, 1.0≈90歳。身長の実測から折れ線で近似)"""
    xs = [1, 2.5, 6, 10, 14, 25]
    ys = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    if years <= 25:
        return float(np.interp(years, xs, ys))
    return float(0.5 + (years - 25) / 130.0)


# ---- モデル ----
_MODELS = {}


def model(topology="anny"):
    if topology not in _MODELS:
        import warnings
        warnings.filterwarnings("ignore")
        import anny
        import torch
        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        _MODELS[topology] = anny.Anny(rig="game_engine", topology=topology, phenotypes="all", local_changes="default", facial_actions="all")
    return _MODELS[topology]


def _kw(p):
    import torch
    return {k: torch.tensor([float(v)]) for k, v in p.items()}


def run(p, topology="anny", pose=None, local=None, expr=None):
    """phenotype 辞書 p と姿勢(1,B,4,4。None=レスト)から rest/posed 頂点とボーン行列(numpy)を返す"""
    import torch
    m = model(topology)
    P = torch.eye(4)[None, None].expand(1, m.bone_count, 4, 4).clone() if pose is None else pose
    with torch.no_grad():
        o = m(pose_parameters=P, phenotype_kwargs=_kw(p), local_changes_kwargs=_kw(local) if local else None, facial_actions=_kw(expr) if expr else None)
    return {k: o[k][0].double().numpy() for k in ("rest_vertices", "vertices", "rest_bone_poses", "bone_poses")}


def height_of(p, topology="anny"):
    v = run(p, topology)["rest_vertices"]
    return float(v[:, 2].max() - v[:, 2].min()) * 100.0


def solve_height(p, cm, topology="anny"):
    """height パラメータを二分法(3点補間)で合わせる。身長は height に対しほぼ線形"""
    lo, hi = dict(p, height=0.0), dict(p, height=1.0)
    hl, hh = height_of(lo, topology), height_of(hi, topology)
    t = (cm - hl) / max(hh - hl, 1e-6)
    return float(np.clip(t, 0.0, 1.0))


def sample(seed, group="casual", female=None):
    """体格サンプル。戻り値: dict(id, group, female, years, cm, p=phenotype)"""
    rng = random.Random(seed * 7919 + zlib.crc32(group.encode()) % 1000)
    pr = PROFILES[group]
    f = (rng.random() < pr["p_f"]) if female is None else female
    years = rng.uniform(*pr["age"])
    p = dict(gender=1.0 if f else 0.0, age=age_param(years), muscle=float(np.clip(rng.gauss(*pr["mu"]), 0.05, 0.95)),
             weight=float(np.clip(rng.gauss(*pr["w"]), 0.05, 0.95)), height=0.5, proportions=float(np.clip(rng.gauss(0.5, 0.12), 0.1, 0.9)),
             african=0.0, asian=1.0, caucasian=0.0, cupsize=float(np.clip(rng.gauss(0.45, 0.15), 0.1, 0.9)), firmness=float(np.clip(rng.gauss(0.5, 0.15), 0.1, 0.9)))
    cm = None
    if pr["h"]:
        mu, sd = pr["h"][1 if f else 0]
        cm = rng.gauss(mu, sd)
        if years > 60:
            cm -= (years - 60) * 0.18            # 加齢による身長低下
        p["height"] = solve_height(p, cm)
    else:
        p["height"] = float(np.clip(rng.gauss(0.5, 0.07), 0.35, 0.65))
    p["asian"] = float(np.clip(rng.gauss(0.92, 0.07), 0.6, 1.0))
    p["caucasian"] = float(np.clip(rng.gauss(0.05, 0.05), 0.0, 0.3))
    p["african"] = float(np.clip(rng.gauss(0.02, 0.03), 0.0, 0.15))
    labs = [k for k in _face_labels() if rng.random() < 0.12]
    local = {k: round(rng.uniform(0.0, 0.7), 2) for k in labs}
    expr = {}
    if rng.random() < 0.5:
        sm = round(rng.uniform(0.1, 0.45), 2)
        expr = {"mouthSmileLeft": sm, "mouthSmileRight": sm}
    return dict(id=f"{group}_{seed:03d}", group=group, seed=seed, female=bool(f), years=round(years, 1), cm=cm, p=p, local=local, expr=expr)


# ---- 姿勢(world軸まわりの回転。実測: local-ref はレスト向き=ワールド軸) ----
def _R(ax, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    R = np.eye(4)
    if ax == "x":
        R[1, 1], R[1, 2], R[2, 1], R[2, 2] = c, -s, s, c
    elif ax == "y":
        R[0, 0], R[0, 2], R[2, 0], R[2, 2] = c, s, -s, c
    else:
        R[0, 0], R[0, 1], R[1, 0], R[1, 1] = c, -s, s, c
    return R


def pose(kind="stand", phase=0.0, rng=None):
    """(1,B,4,4) の torch テンソル。kind=stand|walk|phone(片手を顔へ)|wait(両腕を前で軽く)。右側は y/z の符号を反転"""
    import torch
    m = model("anny")
    L = m.bone_labels
    P = np.tile(np.eye(4), (len(L), 1, 1))
    rng = rng or random.Random(0)

    def setb(name, *rots):
        R = np.eye(4)
        for ax, d in rots:
            R = R @ _R(ax, d)
        P[L.index(name)] = R @ P[L.index(name)]

    def both(name, rots_l):
        setb(name + "_l", *rots_l)
        setb(name + "_r", *[(ax, -d if ax in "yz" else d) for ax, d in rots_l])
    j = rng.uniform(-4, 4)
    if kind == "walk":
        s, c = math.sin(phase), math.cos(phase)
        a = 24
        setb("thigh_l", ("x", -a * s)); setb("thigh_r", ("x", a * s))
        setb("calf_l", ("x", 4 + 34 * max(0.0, c))); setb("calf_r", ("x", 4 + 34 * max(0.0, -c)))
        setb("foot_l", ("x", 8 * s - 10 * max(0.0, c))); setb("foot_r", ("x", -8 * s - 10 * max(0.0, -c)))
        setb("upperarm_l", ("x", 18 * s), ("y", 40 + j)); setb("upperarm_r", ("x", -18 * s), ("y", -(40 + j)))
        setb("lowerarm_l", ("x", -14 - 10 * max(0, -s))); setb("lowerarm_r", ("x", -14 - 10 * max(0, s)))
        setb("spine_02", ("z", 5 * s)); setb("pelvis", ("z", -4 * s))
    else:
        both("upperarm", [("y", 40 + j)])
        both("lowerarm", [("x", -10 - rng.uniform(0, 12))])
        setb("thigh_l", ("y", rng.uniform(-2, 3))); setb("thigh_r", ("y", rng.uniform(-3, 2)))
        if kind == "phone":
            setb("upperarm_r", ("y", -25), ("x", -35)); setb("lowerarm_r", ("x", -95))
        if kind == "wait":
            both("upperarm", [("y", 28), ("x", -12)]); both("lowerarm", [("x", -35)])
    for f in ("index", "middle", "ring", "pinky", "thumb"):
        for i, d in ((1, 14), (2, 22), (3, 18)):
            both(f"{f}_0{i}", [("x", -d - rng.uniform(0, 8))])
    return torch.tensor(P, dtype=torch.float32)[None]


# ---- 面ごとの材質(UV セグメンテーション) ----
_SEG = None


def _seg():
    global _SEG
    if _SEG is None:
        import anny
        import yaml
        from PIL import Image
        d = Path(anny.__file__).parent / "data/segmentation"
        cols = yaml.safe_load(open(d / "body_parts_segmentation.yaml"))["colors"]
        _SEG = (np.array(Image.open(d / "body_parts_segmentation.png").convert("RGB")), list(cols), np.array(list(cols.values())))
    return _SEG


def face_parts(m):
    """full topology の三角形ごとの部位名(UV重心の色で判定)。戻り: list[str]"""
    img, names, cols = _seg()
    H, W, _ = img.shape
    uv = m.texture_coordinates.numpy()
    fu = m.face_texture_coordinate_indices.numpy()
    c = uv[fu].mean(axis=1)
    px = np.clip((c[:, 0] * W).astype(int), 0, W - 1)
    py = np.clip(((1 - c[:, 1]) * H).astype(int), 0, H - 1)
    rgb = img[py, px].astype(int)
    d = ((rgb[:, None, :] - cols[None, :, :]) ** 2).sum(-1)
    return [names[i] for i in d.argmin(1)]


# ---- 服・髪(MakeHuman .mhclo) ----
def _read_obj(p):
    v, vt, faces = [], [], []
    for l in open(p, errors="ignore"):
        t = l.split()
        if not t:
            continue
        if t[0] == "v":
            v.append([float(x) for x in t[1:4]])
        elif t[0] == "vt":
            vt.append([float(t[1]), float(t[2])])
        elif t[0] == "f":
            faces.append([tuple(int(x) - 1 if x else -1 for x in (w.split("/") + ["", ""])[:2]) for w in t[1:]])
    return np.array(v), np.array(vt) if vt else np.zeros((1, 2)), faces


_BASE = None


def _base():
    """MakeHuman base.obj(dm, Y-up)と、Anny 空間への affine(頂点対応 base_mesh_vertex_indices から最小二乗)"""
    global _BASE
    if _BASE is None:
        import anny
        p = Path(anny.__file__).parent / "data/mpfb2/3dobjs/base.obj"
        B = _read_obj(p)[0]
        m = model("anny")
        r = run(dict(gender=0.5, age=0.5, muscle=0.5, weight=0.5, height=0.5, proportions=0.5, african=0.5, asian=0.5, caucasian=0.5, cupsize=0.5, firmness=0.5))
        A = r["rest_vertices"]
        X = np.c_[B[m.base_mesh_vertex_indices.numpy()], np.ones(len(A))]
        T, *_ = np.linalg.lstsq(X, A, rcond=None)
        _BASE = (B, T, A)
    return _BASE


def load_mhclo(path):
    """.mhclo → dict(pos=Anny空間でのレスト位置(N,3), faces, uv, tex, license, name)"""
    path = Path(path)
    hdr, rows = {}, []
    for l in open(path, errors="ignore"):
        t = l.split()
        if t and t[0] == "#" and any(w in ("CC0", "CC-0") for w in t) and "license" not in hdr:
            hdr["license"] = "CC0"
        if not t or t[0].startswith("#"):
            if t and t[0] == "#" and len(t) > 2 and t[1].rstrip(":") in ("license", "author"):
                hdr[t[1].rstrip(":")] = " ".join(t[2:])
            continue
        if len(t) == 9 and t[0].lstrip("-").isdigit():
            rows.append([float(x) for x in t])
        elif t[0] in ("x_scale", "y_scale", "z_scale"):
            hdr[t[0]] = (int(t[1]), int(t[2]), float(t[3]))
        elif t[0] in ("obj_file", "material", "name"):
            hdr[t[0]] = " ".join(t[1:])
    B, T, _ = _base()
    R = np.array(rows)
    i = R[:, :3].astype(int)
    w = R[:, 3:6]
    off = R[:, 6:9]
    sc = []
    for k, key in enumerate(("x_scale", "y_scale", "z_scale")):
        if key not in hdr:
            sc.append(1.0)
            continue
        a, b, s = hdr[key]
        sc.append(abs(B[a, k] - B[b, k]) / s)
    p = (B[i] * w[:, :, None]).sum(1) + off * np.array(sc)
    pos = np.c_[p, np.ones(len(p))] @ T
    v, vt, faces = _read_obj(path.parent / hdr["obj_file"])
    assert len(v) == len(pos), (len(v), len(pos))
    tex = None
    mat = hdr.get("material")
    if mat and (path.parent / mat).exists():
        for l in open(path.parent / mat, errors="ignore"):
            t = l.split()
            if t and t[0] == "diffuseTexture":
                tex = path.parent / " ".join(t[1:])
    return dict(pos=pos, faces=faces, vt=vt, tex=tex, license=hdr.get("license", "?").split(" (")[0].replace("CC-0", "CC0"), author=hdr.get("author", "?"), name=hdr.get("name", path.stem), path=str(path.relative_to(ROOT)))


def _vnormals(V, F):
    n = np.zeros_like(V)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    fn = np.cross(b - a, c - a)
    for k in range(3):
        np.add.at(n, F[:, k], fn)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


_BIND = {}
_PARTS = None


def bind(cloth, topology):
    """服頂点を体のレスト頂点(中立体型)の近傍 K=3 頂点に結び付ける: 重み・表面からの高さ・接線残差・スキンウェイト"""
    key = (cloth["path"], topology)
    if key in _BIND:
        return _BIND[key]
    from scipy.spatial import cKDTree
    m = model(topology)
    _, _, A = _base()
    N = run(dict(gender=0.5, age=0.5, muscle=0.5, weight=0.5, height=0.5, proportions=0.5, african=0.5, asian=0.5, caucasian=0.5, cupsize=0.5, firmness=0.5), topology)["rest_vertices"]
    F = m.faces.numpy()
    nrm = _vnormals(N, F)
    d, idx = cKDTree(N).query(cloth["pos"], k=3)
    w = 1.0 / (d + 2e-3)
    w /= w.sum(1, keepdims=True)
    p0 = (N[idx] * w[:, :, None]).sum(1)
    n0 = (nrm[idx] * w[:, :, None]).sum(1)
    n0 /= np.maximum(np.linalg.norm(n0, axis=1, keepdims=True), 1e-12)
    dv = cloth["pos"] - p0
    h = (dv * n0).sum(1)
    t = dv - h[:, None] * n0
    # スキンウェイト(密)
    bi, bw = m.vertex_bone_indices.numpy(), m.vertex_bone_weights.numpy()
    Wd = np.zeros((len(N), m.bone_count))
    np.put_along_axis(Wd, bi, bw, axis=1)
    cw = (Wd[idx] * w[:, :, None]).sum(1)
    out = dict(idx=idx, w=w, h=np.maximum(h, 0.004), t=t, cw=cw)
    _BIND[key] = out
    return out


def fit_cloth(cloth, V, topology, margin=0.006):
    """体の(レスト)頂点 V に服を合わせる。戻り: (N,3)"""
    m = model(topology)
    b = bind(cloth, topology)
    nrm = _vnormals(V, m.faces.numpy())
    p = (V[b["idx"]] * b["w"][:, :, None]).sum(1)
    n = (nrm[b["idx"]] * b["w"][:, :, None]).sum(1)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    C = p + n * b["h"][:, None] + b["t"]
    from scipy.spatial import cKDTree
    kd = cKDTree(V)
    if "adj" not in cloth:
        E = set()
        for f in cloth["faces"]:
            ids = [vi for vi, _ in f]
            for a, c2 in zip(ids, ids[1:] + ids[:1]):
                E.add((a, c2)); E.add((c2, a))
        E = np.array(sorted(E))
        cloth["adj"] = E

    def push():
        nonlocal C
        _, j = kd.query(C, k=4)
        sd = ((C[:, None, :] - V[j]) * nrm[j]).sum(2)
        w = np.argmin(sd, axis=1)
        jj = j[np.arange(len(C)), w]
        C = C + nrm[jj] * np.maximum(0.0, margin - sd[np.arange(len(C)), w])[:, None]
    push()
    E = cloth["adj"]
    cnt = np.bincount(E[:, 0], minlength=len(C)).astype(float)
    for _ in range(3):
        acc = np.zeros_like(C)
        np.add.at(acc, E[:, 0], C[E[:, 1]])
        has = cnt > 0
        C[has] = 0.5 * C[has] + 0.5 * acc[has] / cnt[has, None]
        push()
    return C


def skin(V_rest, bones_rest, bones_pose, weights):
    """LBS: V_rest(N,3), bones_*(B,4,4 ワールド), weights(N,B)。pose は rest に対する変換 = pose @ inv(rest)"""
    M = bones_pose @ np.linalg.inv(bones_rest)
    Vh = np.c_[V_rest, np.ones(len(V_rest))]
    out = np.einsum("nb,bij,nj->ni", weights, M, Vh)
    return out[:, :3]


# ---- 衣装・髪のカタログ(CC0 パックのみ) ----
def _find(pack, sub, name):
    return PK / pack / sub / name / (name + ".mhclo")


TOPS = dict(m=["elvs_crude_t-shirt_male", "namuhekam_male_polo_shirt", "toigo_fisherman_sweater"],
            f=["joepal_crude_t-shirt_female", "toigo_camisole_top", "toigo_keyhole_tank_top", "toigo_turtleneck_halter_top", "toigo_fisherman_sweater"])
BOTTOMS = ["cortu_cargo_pants", "toigo_wool_pants", "toigo_harem_pants", "cortu_jeans_shorts"]
HAIRS = dict(m=["cortu_short_messy_hair", "cortu_straight_bangs", "culturalibre_hair_05"],
             f=["toigo_blunt_bob", "toigo_blunt_bob_with_bangs", "toigo_inverted_bob", "toigo_inverted_bob_with_bangs", "toigo_curled_under_bob", "culturalibre_hair_06", "o4saken_long01"])
SHOES = ["toigo_ankle_boots_male", "toigo_ballet_flats_with_bows"]

COLORS = dict(white="#e8e8e4", black="#222428", navy="#24334f", gray="#7d8084", beige="#c8b898", red="#a83a3a", olive="#6a6a3a", blue="#3e6aa0", pink="#d89aa8", mustard="#c8a030")
HAIRC = dict(black="#181412", dark="#2a1c14", brown="#4a3020", gray="#a8a8a4", white="#d8d8d4", chestnut="#5a3a24")
SKIN = ["#e7c3a3", "#dfb694", "#d8aa84", "#e9cdb2", "#cfa27b", "#eacbb0"]


def outfit(spec, rng):
    """人物 spec の服装・髪・肌色・靴色。服は humans_wear.make_outfit(pieces)"""
    from . import humans_wear as W
    f = spec["female"]
    o = dict(pieces=W.make_outfit(spec, rng), hair=rng.choice(HAIRS["f" if f else "m"]))
    if spec["years"] > 60:
        o["hair_color"] = rng.choice(["gray", "gray", "white", "black"])
    else:
        o["hair_color"] = rng.choice(["black"] * 6 + ["dark", "brown", "chestnut"])
    o["skin"] = rng.randrange(len(SKIN))
    o["shoe_color"] = rng.choice(["black", "white", "navy", "gray", "brown"])
    hat = any(p[1] in ("hat", "helmet") for p in o["pieces"])
    o["hat"] = hat
    return o


def build(spec, outfit_d=None, topology="anny", posename="stand", phase=0.0):
    """人物1体を組む。戻り dict(rest, v, faces, bones_rest, bones_pose, W, parts, full, cloth=[dict(slot,name,V,Vrest,cw,cl,mat,uv)])"""
    from . import humans_wear as WR
    rng = random.Random(spec["seed"] * 31 + 5)
    of = outfit_d or outfit(spec, rng)
    m = model(topology)
    from . import humans_motion as HM
    P = HM.pose_at(posename, phase) if (HM.ANIM / f"{posename}.npz").exists() else pose(posename, phase, random.Random(spec["seed"]))
    r = run(spec["p"], topology, P, spec.get("local"), spec.get("expr"))
    bi, bw = m.vertex_bone_indices.numpy(), m.vertex_bone_weights.numpy()
    Wd = np.zeros((len(r["rest_vertices"]), m.bone_count))
    np.put_along_axis(Wd, bi, bw, axis=1)
    out = dict(spec=spec, outfit=of, topology=topology, rest=r["rest_vertices"], v=r["vertices"], faces=m.faces.numpy(), bones_rest=r["rest_bone_poses"], bones_pose=r["bone_poses"], W=Wd, cloth=[])
    rf = r if topology == "anny" else run(spec["p"], "anny", P, spec.get("local"), spec.get("expr"))
    mf = model("anny")
    global _PARTS
    if _PARTS is None:
        _PARTS = face_parts(mf)
    out["parts"] = _PARTS if topology == "anny" else None
    out["full"] = dict(v=rf["vertices"], rest=rf["rest_vertices"], faces=mf.faces.numpy(), parts=_PARTS, nrm=_vnormals(rf["vertices"], mf.faces.numpy()))
    out["cloth"] = WR.build_pieces(rf, of["pieces"], r, topology)
    for pc in out["cloth"]:
        pc["mat"] = f"anny_cl_{pc['mat']}"
    if not of.get("hat"):
        nm = of["hair"]
        cl = load_mhclo(_find("hair01", "hair", nm))
        Vr = fit_cloth(cl, rf["rest_vertices"], "anny", margin=0.004)
        cw = bind(cl, "anny")["cw"]
        out["cloth"].append(dict(slot="hair", name=nm, Vrest=Vr, V=skin(Vr, rf["rest_bone_poses"], rf["bone_poses"], cw), cw=cw, cl=cl, mat=f"anny_hair_{nm}_{of['hair_color']}", uv=True))
    return out


def to_world(Vp, yaw=math.pi, ground=None):
    """Anny座標(前=-y)→ モジュール座標(前=+y, 足元z=0, xy中心=骨盤)。ground=床 z(None なら Vp.min)"""
    c, s = math.cos(yaw), math.sin(yaw)
    x, y = Vp[:, 0] * c - Vp[:, 1] * s, Vp[:, 0] * s + Vp[:, 1] * c
    return np.c_[x, y, Vp[:, 2] - (Vp[:, 2].min() if ground is None else ground)]


def make_hair_textures(size=1024):
    """髪カードの diffuse を グレースケール+アルファ にして assets/textures/anny_hair_<style>.png へ(色は材質の tint で乗算)"""
    from PIL import Image
    from .materials_h import STYLES
    out = []
    for st in STYLES:
        for s in ("m", "f"):
            p = _find("hair01", "hair", st)
            if p.exists():
                break
        cl = load_mhclo(p)
        im = Image.open(cl["tex"]).convert("RGBA")
        im.thumbnail((size, size))
        a = np.array(im).astype(np.float32)
        lum = (a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11) / 255.0
        m = a[..., 3] > 128
        lum = lum / max(float(lum[m].mean()), 1e-3) * 0.8 if m.any() else lum
        g = np.clip(lum * 255, 0, 255).astype(np.uint8)
        Image.fromarray(np.dstack([g, g, g, a[..., 3].astype(np.uint8)]), "RGBA").save(TEXDIR / f"anny_hair_{st}.png", optimize=True)
        out.append(st)
    return out


def decimate(V, faces, cell=0.012):
    """頂点クラスタリングによる簡易間引き(cell[m] の格子ごとに頂点を平均)。faces は頂点番号のリスト(多角形可)。戻り: (V2, tris)"""
    V = np.asarray(V)
    key = np.floor(V / cell).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    n = inv.max() + 1
    cnt = np.bincount(inv, minlength=n)[:, None]
    V2 = np.zeros((n, 3))
    for k in range(3):
        V2[:, k] = np.bincount(inv, weights=V[:, k], minlength=n)
    V2 /= cnt
    seen, tris = set(), []
    for f in faces:
        for i in range(1, len(f) - 1):
            t = (inv[f[0]], inv[f[i]], inv[f[i + 1]])
            if len(set(t)) == 3:
                k = tuple(sorted(t))
                if k not in seen:
                    seen.add(k)
                    tris.append(t)
    return V2, tris
