"""服・小物のバリエーション: MakeHuman(.mhclo)アセット、体表面の押し出しによる手続き衣服(ジャケット/コート/作業着)、剛体小物(リュック/傘/バッグ/ヘルメット)。
ライセンスは .mhclo ヘッダが CC0/CC BY 4.0 のものだけ使う(AGPL3 は使わない)。"""
import math

import numpy as np

from . import humans as H

TORSO = {"Root", "pelvis", "spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r"}
UPPER = {"upperarm_l", "upperarm_r"}
LOWER = {"lowerarm_l", "lowerarm_r"}
THIGH = {"thigh_l", "thigh_r"}
CALF = {"calf_l", "calf_r"}

# 使うアセット(ヘッダで CC0 / CC BY 4.0 を確認済み。AGPL3 の mini_skirt・uncle_joshis_hat・newsboy_cap などは除外)
MH = dict(
    top_m=[("shirts01", "clothes", "elvs_crude_t-shirt_male"), ("shirts01", "clothes", "namuhekam_male_polo_shirt")],
    top_f=[("shirts01", "clothes", "joepal_crude_t-shirt_female"), ("shirts01", "clothes", "toigo_camisole_top"), ("shirts01", "clothes", "toigo_keyhole_tank_top"),
           ("shirts01", "clothes", "toigo_turtleneck_halter_top")],
    pants=[("pants01", "clothes", "toigo_wool_pants"), ("pants01", "clothes", "cortu_cargo_pants")],
    loose=[("pants01", "clothes", "toigo_harem_pants")],
    shorts=[("pants01", "clothes", "cortu_jeans_shorts")],
    skirt=[("skirts01", "clothes", "toigo_long_full_skirt"), ("skirts01", "clothes", "toigo_skirt_with_lace_ruffle"), ("skirts01", "clothes", "toigo_tiered_mini_skirt")],
    dress=[("skirts01", "clothes", "toigo_tiered_skirt")],
    suit_m=[("suits01", "clothes", "toigo_male_suit_3"), ("suits01", "clothes", "toigo_male_suit_tie_and_jacket"), ("suits01", "clothes", "toigo_male_double-breasted_suit")],
    suit_f=[("suits01", "clothes", "toigo_female_suit"), ("suits01", "clothes", "toigo_female_suit_2"), ("suits01", "clothes", "toigo_female_double-breasted_suit")],
    cap=[("hats01", "clothes", "toigo_maga_hat")],
    cloche=[("hats01", "clothes", "aethelraed_unraed_cloche_hat")],
    mask=[("masks01", "clothes", "joepal_medical_mouth_protection")],
)


def _skirt_fix(rf, Vr, cw, shrink=0.76):
    """スカート/ワンピースの裾が脚の動きや体型で膨らみ過ぎないよう、腰から下を中心軸へ縮め、脚ボーンの重みを骨盤へ寄せる"""
    L = H.model("anny").bone_labels
    r = rf["rest_bone_poses"]
    c = r[L.index("pelvis")][:3, 3]
    z = Vr[:, 2]
    zf = (z - rf["rest_vertices"][:, 2].min()) / (rf["rest_vertices"][:, 2].max() - rf["rest_vertices"][:, 2].min())
    k = np.clip((0.56 - zf) / 0.12, 0.0, 1.0)[:, None]
    V = Vr.copy()
    V[:, :2] = c[:2] + (Vr[:, :2] - c[:2]) * (1 - k * (1 - shrink))
    cw = cw.copy()
    leg = [L.index(n) for n in ("thigh_l", "thigh_r", "calf_l", "calf_r")]
    pel = L.index("pelvis")
    mv = cw[:, leg].sum(1)
    cw[:, leg] *= 0.4
    cw[:, pel] += mv * 0.6
    return V, cw


def mh_piece(rf, key_or_triple, slot, color, margin, rng=None):
    """MakeHuman アセットを体に合わせた1枚。戻り: cloth 辞書(humans.build と同形式)"""
    pack, sub, name = key_or_triple
    p = H._find(pack, sub, name)
    cl = H.load_mhclo(p)
    assert cl["license"] in ("CC0", "CC BY 4.0"), (name, cl["license"])
    Vr = H.fit_cloth(cl, rf["rest_vertices"], "anny", margin=margin)
    cw = H.bind(cl, "anny")["cw"]
    if slot in ("dress",) or "skirt" in name:
        Vr, cw = _skirt_fix(rf, Vr, cw)
    return dict(slot=slot, name=name, Vrest=Vr, V=H.skin(Vr, rf["rest_bone_poses"], rf["bone_poses"], cw), cw=cw, cl=cl, mat=color, uv=False)


def _weights_full(topology="anny"):
    m = H.model(topology)
    W = np.zeros((len(m.template_vertices), m.bone_count))
    np.put_along_axis(W, m.vertex_bone_indices.numpy(), m.vertex_bone_weights.numpy(), axis=1)
    return W


_WF = {}


def garment(rf, name, zlo, arms="long", legs="none", legz=0.0, margin=0.02, color="navy", topology="anny"):
    """体表面の領域を法線方向に押し出した衣服。zlo=裾の高さ(身長比)、arms=none|short|long、legs=none|thigh|full、legz=脚側の裾の高さ(身長比)"""
    if topology not in _WF:
        _WF[topology] = _weights_full(topology)
    WF = _WF[topology]
    m = H.model(topology)
    V = rf["rest_vertices"]
    zf = (V[:, 2] - V[:, 2].min()) / (V[:, 2].max() - V[:, 2].min())
    dom = np.array(m.bone_labels)[WF.argmax(1)]
    isin = lambda s: np.isin(dom, list(s))
    sel = isin(TORSO) & (zf >= zlo)
    if arms in ("short", "long"):
        sel |= isin(UPPER)
    if arms == "long":
        sel |= isin(LOWER)
    if legs in ("thigh", "full"):
        sel |= isin(THIGH) & (zf >= legz)
    if legs == "full":
        sel |= isin(CALF) & (zf >= max(legz, 0.04))
    F = m.faces.numpy()
    keep = sel[F].all(1)
    used = np.unique(F[keep])
    rm = -np.ones(len(V), int)
    rm[used] = np.arange(len(used))
    nrm = H._vnormals(V, F)
    Vr = V[used] + nrm[used] * margin
    cw = WF[used]
    cl = dict(faces=[[(int(rm[i]), -1) for i in f] for f in F[keep]], vt=np.zeros((1, 2)), license="procedural", author="procedural", name=name, path=f"procedural/{name}", tex=None)
    return dict(slot=name, name=name, Vrest=Vr, V=H.skin(Vr, rf["rest_bone_poses"], rf["bone_poses"], cw), cw=cw, cl=cl, mat=color, uv=False)


def _mesh_piece(rf, name, Vrest, tris, bone, color, follow="rot"):
    """剛体小物を1ボーンに固定(follow=rot: ボーンと一緒に回転、pos: 位置だけ追従して直立のまま)"""
    m = H.model("anny")
    L = m.bone_labels
    bi = L.index(bone)
    cw = np.zeros((len(Vrest), m.bone_count)); cw[:, bi] = 1.0
    if follow == "rot":
        V = H.skin(Vrest, rf["rest_bone_poses"], rf["bone_poses"], cw)
    else:
        V = Vrest + (rf["bone_poses"][bi][:3, 3] - rf["rest_bone_poses"][bi][:3, 3])
    cl = dict(faces=[[(int(i), -1) for i in t] for t in tris], vt=np.zeros((1, 2)), license="procedural", author="procedural", name=name, path=f"procedural/{name}", tex=None)
    return dict(slot=name, name=name, Vrest=Vrest, V=V, cw=cw, cl=cl, mat=color, uv=False, follow=follow, bone=bone)


def repose(pc, rf):
    """フィット済みの1枚を別のポーズへ(フィットし直さない)。動画のフレームごとの更新用"""
    if pc.get("follow") == "pos":
        bi = H.model("anny").bone_labels.index(pc["bone"])
        V = pc["Vrest"] + (rf["bone_poses"][bi][:3, 3] - rf["rest_bone_poses"][bi][:3, 3])
    else:
        V = H.skin(pc["Vrest"], rf["rest_bone_poses"], rf["bone_poses"], pc["cw"])
    return dict(pc, V=V)


def _box(c, s):
    cx, cy, cz = c
    hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
    V = np.array([[cx + sx * hx, cy + sy * hy, cz + sz * hz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
    q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return V, [t for a, b, c2, d in q for t in ((a, b, c2), (a, c2, d))]


def _cyl(c, r, h, n=8):
    V = np.array([(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n), c[2] + z) for z in (0, h) for k in range(n)])
    tris = []
    for k in range(n):
        a, b = k, (k + 1) % n
        tris += [(a, b, n + b), (a, n + b, n + a)]
    return V, tris


def _merge(parts):
    V, T, o = [], [], 0
    for v, t in parts:
        V.append(v); T += [tuple(i + o for i in tri) for tri in t]; o += len(v)
    return np.vstack(V), T


def backpack(rf, color):
    r = rf["rest_bone_poses"]
    L = H.model("anny").bone_labels
    p = r[L.index("spine_03")][:3, 3]
    V, T = _box((p[0], p[1] + 0.13, p[2] - 0.02), (0.29, 0.13, 0.36))
    return _mesh_piece(rf, "backpack", V, T, "spine_03", color)


def helmet(rf, color):
    p = rf["rest_bone_poses"][H.model("anny").bone_labels.index("head")][:3, 3]
    c = (p[0], p[1] + 0.02, p[2] + 0.07)
    n, rings, R = 14, 4, 0.118
    V, T = [], []
    for j in range(rings + 1):
        el = (math.pi / 2) * j / rings
        for k in range(n):
            a = 2 * math.pi * k / n
            V.append((c[0] + R * math.cos(el) * math.cos(a), c[1] + R * math.cos(el) * math.sin(a) * 1.08, c[2] + R * math.sin(el) * 0.9))
    for j in range(rings):
        for k in range(n):
            a, b = j * n + k, j * n + (k + 1) % n
            T += [(a, b, b + n), (a, b + n, a + n)]
    return _mesh_piece(rf, "helmet", np.array(V), T, "head", color)


def umbrella(rf, color, closed=False):
    L = H.model("anny").bone_labels
    h = rf["rest_bone_poses"][L.index("hand_r")][:3, 3]
    Vp, Tp = _cyl((h[0], h[1], h[2] - 0.2), 0.008, 0.95, 6)
    top = (h[0], h[1], h[2] + 0.75)
    n = 14
    R, hh = (0.05, 0.05) if closed else (0.5, 0.17)
    Vc = [top] + [(top[0] + R * math.cos(2 * math.pi * k / n), top[1] + R * math.sin(2 * math.pi * k / n), top[2] - hh) for k in range(n)]
    Tc = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)] + [(0, 1 + (k + 1) % n, 1 + k) for k in range(n)]
    Vm, Tm = _merge([(Vp, Tp), (np.array(Vc), Tc)])
    return _mesh_piece(rf, "umbrella", Vm, Tm, "hand_r", color, follow="pos")


def bag(rf, color):
    L = H.model("anny").bone_labels
    h = rf["rest_bone_poses"][L.index("hand_r")][:3, 3]
    V, T = _box((h[0], h[1], h[2] - 0.17), (0.34, 0.12, 0.28))
    return _mesh_piece(rf, "bag", V, T, "hand_r", color, follow="pos")


def _pick(rng, key):
    return rng.choice(MH[key])


def make_outfit(spec, rng):
    """人物 spec の服装一式。戻り: dict(pieces=[(kind, slot, arg, color, margin)], hair, hair_color, skin, shoe_color, mask, ...)"""
    f, g, yr = spec["female"], spec["group"], spec["years"]
    pcs = []
    col = lambda *c: rng.choice(c)
    casual = ["white", "black", "navy", "gray", "beige", "red", "olive", "blue", "pink", "mustard", "brown", "khaki", "cream", "lightblue", "darkgreen", "purple", "orange"]
    dark = ["navy", "black", "gray", "beige", "olive", "brown", "khaki", "blue"]
    top = lambda c: pcs.append(("mh", "top", _pick(rng, "top_f" if f else "top_m"), c, 0.016))
    if g == "office":
        if rng.random() < 0.55:
            pcs.append(("mh", "suit", _pick(rng, "suit_f" if f else "suit_m"), col("navy", "black", "gray"), 0.014))
        else:
            top(col("white", "white", "lightblue", "cream"))
            if f and rng.random() < 0.5:
                pcs.append(("mh", "bottom", _pick(rng, "skirt"), col("navy", "black", "gray"), 0.010))
            else:
                pcs.append(("mh", "bottom", _pick(rng, "pants"), col("navy", "black", "gray"), 0.010))
            if rng.random() < 0.4:
                pcs.append(("garment", "jacket", dict(zlo=0.52, arms="long", margin=0.024), col("navy", "gray", "black", "beige"), 0))
    elif g == "student":
        pcs.append(("garment", "blazer", dict(zlo=0.52, arms="long", margin=0.024), col("navy", "navy", "gray"), 0)) if rng.random() < 0.7 else None
        top("white")
        if f:
            pcs.append(("mh", "bottom", ("skirts01", "clothes", "toigo_tiered_mini_skirt"), col("navy", "gray", "darkgreen"), 0.010))
        else:
            pcs.append(("mh", "bottom", _pick(rng, "pants"), col("navy", "gray", "black"), 0.012))
        if rng.random() < 0.65:
            pcs.append(("rigid", "backpack", None, col("black", "navy", "gray", "blue"), 0))
    elif g == "worker":
        pcs.append(("garment", "coverall", dict(zlo=0.52, arms="long", legs="full", legz=0.04, margin=0.016), col("navy", "khaki", "gray", "olive", "blue"), 0))
        if rng.random() < 0.7:
            pcs.append(("rigid", "helmet", None, col("white", "white", "yellow", "orange"), 0))
    elif g == "elder":
        if f and rng.random() < 0.35:
            pcs.append(("mh", "dress", _pick(rng, "dress"), col("beige", "navy", "purple", "olive", "pink"), 0.012))
        else:
            top(col(*casual))
            pcs.append(("mh", "bottom", _pick(rng, "pants" if rng.random() < 0.6 else "loose"), col(*dark), 0.012))
        if rng.random() < 0.45:
            pcs.append(("garment", "coat", dict(zlo=0.40, arms="long", legs="thigh", legz=0.40, margin=0.030), col("beige", "navy", "brown", "gray", "darkgreen"), 0))
        elif rng.random() < 0.5:
            pcs.append(("garment", "jacket", dict(zlo=0.52, arms="long", margin=0.024), col(*dark), 0))
        if rng.random() < 0.3:
            pcs.append(("mh", "hat", _pick(rng, "cloche" if f else "cap"), col("beige", "gray", "navy"), 0.006))
    elif g == "kid":
        top(col(*casual))
        pcs.append(("mh", "bottom", _pick(rng, "shorts" if rng.random() < 0.5 else "pants"), col("navy", "gray", "khaki", "blue"), 0.012))
        if rng.random() < 0.5:
            pcs.append(("rigid", "backpack", None, col("red", "blue", "orange", "pink", "navy"), 0))
    else:
        r = rng.random()
        if f and r < 0.18:
            pcs.append(("mh", "dress", _pick(rng, "dress"), col(*casual), 0.012))
        else:
            top(col(*casual))
            if f and r < 0.45:
                pcs.append(("mh", "bottom", _pick(rng, "skirt"), col(*dark), 0.010))
            else:
                k = "loose" if r > 0.85 else ("shorts" if r > 0.78 and not f else "pants")
                pcs.append(("mh", "bottom", _pick(rng, k), col(*dark), 0.012))
        r2 = rng.random()
        if r2 < 0.22:
            pcs.append(("garment", "jacket", dict(zlo=0.52, arms="long", margin=0.024), col(*dark), 0))
        elif r2 < 0.34:
            pcs.append(("garment", "coat", dict(zlo=0.40, arms="long", legs="thigh", legz=0.40, margin=0.030), col("beige", "navy", "gray", "black", "brown"), 0))
        if rng.random() < 0.22:
            pcs.append(("mh", "hat", _pick(rng, "cap"), col("black", "navy", "gray", "red", "white"), 0.006))
        if rng.random() < 0.28:
            pcs.append(("rigid", "backpack", None, col("black", "navy", "gray", "olive"), 0))
    if rng.random() < (0.09 if g != "worker" else 0.15):
        pcs.append(("mh", "mask", _pick(rng, "mask"), col("white", "white", "lightblue", "gray"), 0.004))
    r3 = rng.random()
    if r3 < 0.12 and not any(p[1] == "backpack" for p in pcs):
        pcs.append(("rigid", "umbrella", None, col("navy", "black", "red", "beige", "darkgreen", "lightblue"), 0))
    elif r3 < 0.28 and not any(p[1] == "backpack" for p in pcs):
        pcs.append(("rigid", "bag", None, col("brown", "black", "beige", "red", "navy"), 0))
    return pcs


def build_pieces(rf, pieces, rb=None, topology="anny"):
    """rf=フル解像度の体(MakeHuman アセット・小物用)、rb=体メッシュ側の run 結果(衣服の押し出し用。低ポリのとき衣服も低ポリになる)"""
    rb = rf if rb is None else rb
    out = []
    for kind, slot, arg, color, margin in pieces:
        if kind == "mh":
            out.append(mh_piece(rf, arg, slot, color, margin))
        elif kind == "garment":
            out.append(garment(rb, slot, color=color, topology=topology, **arg))
        else:
            out.append(dict(backpack=backpack, helmet=helmet, umbrella=umbrella, bag=bag)[slot](rf, color))
    return out
