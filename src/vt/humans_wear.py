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


def _head_piece(rf, V, tris, mat, name, uv=None):
    """頭ボーンに固定した手続き小物(髪の殻・ひげ・ポニーテール)。tris は V への三角形インデックス"""
    m = H.model("anny")
    cw = np.zeros((len(V), m.bone_count)); cw[:, m.bone_labels.index("head")] = 1.0
    faces = [[(int(i), int(i)) for i in t] for t in tris]
    cl = dict(faces=faces, vt=uv if uv is not None else np.zeros((len(V), 2)), license="procedural", author="procedural", name=name, path=f"procedural/{name}", tex=None)
    return dict(slot=name, name=name, Vrest=V, V=H.skin(V, rf["rest_bone_poses"], rf["bone_poses"], cw), cw=cw, cl=cl, mat=mat, uv=uv is not None)


def _head_info(rf):
    m = H.model("anny")
    F = m.faces.numpy()
    if H._PARTS is None:
        H._PARTS = H.face_parts(m)
    parts = np.array(H._PARTS)
    hf = F[parts == "head"]
    V = rf["rest_vertices"]
    Vh = V[np.unique(hf)]
    mc = F[parts == "mouth_cavity"]
    zm = V[np.unique(mc)][:, 2].mean() if len(mc) else Vh[:, 2].min() + 0.05
    return dict(F=hf, V=V, ztop=Vh[:, 2].max(), zchin=Vh[:, 2].min(), yc=Vh[:, 1].mean(), zm=zm, mouth=V[np.unique(mc)].mean(0) if len(mc) else None, nrm=H._vnormals(V, F))


def _shell(rf, hi, sel_fn, margin, mat, name, uv_planar=False):
    V, F = hi["V"], hi["F"]
    c = V[F].mean(1)
    keep = sel_fn(c)
    if keep.sum() < 4:
        return None
    ff = F[keep]
    used = np.unique(ff)
    rm = -np.ones(len(V), int); rm[used] = np.arange(len(used))
    P = V[used] + hi["nrm"][used] * margin
    uv = np.c_[P[:, 0], P[:, 2]] if uv_planar else None
    return _head_piece(rf, P, rm[ff], mat, name, uv)


def hair_piece(rf, kind, hc):
    """カード以外の髪型: buzz(短髪の殻)/ pony(ポニーテール)。hc=髪色名"""
    hi = _head_info(rf)
    zt, yc = hi["ztop"], hi["yc"]
    scalp = lambda c: (c[:, 2] > zt - 0.075) & ((c[:, 1] > yc - 0.045) | (c[:, 2] > zt - 0.035))
    out = []
    sh = _shell(rf, hi, scalp, 0.0045 if kind == "buzz" else 0.007, f"anny_scalp_{hc}", "hair_scalp")
    if sh:
        out.append(sh)
    if kind == "pony" and sh:
        n, ring = 9, 6
        a0 = np.array([0.0, yc + 0.075, zt - 0.045])
        V, T = [], []
        for i in range(n):
            t = i / (n - 1)
            c = a0 + np.array([0.0, 0.05 * t + 0.03 * t * t, -0.22 * t])
            r = 0.028 * (1 - t) + 0.011 * t
            for k in range(ring):
                a = 2 * math.pi * k / ring
                V.append(c + np.array([r * math.cos(a), r * math.sin(a), 0.0]))
        for i in range(n - 1):
            for k in range(ring):
                a, b = i * ring + k, i * ring + (k + 1) % ring
                T += [(a, b, b + ring), (a, b + ring, a + ring)]
        out.append(_head_piece(rf, np.array(V), T, f"anny_scalp_{hc}", "hair_tail"))
    return out


def beard_piece(rf, kind, hc):
    """ひげ: stubble(無精ひげ: alpha の点)/ beard(あごひげ)/ mustache(口ひげ)"""
    hi = _head_info(rf)
    if hi["mouth"] is None:
        return []
    zm, yc, mc = hi["zm"], hi["yc"], hi["mouth"]
    lip = lambda c: (np.linalg.norm(c - mc, axis=1) < 0.017)
    if kind == "mustache":
        fn = lambda c: (c[:, 2] > zm + 0.008) & (c[:, 2] < zm + 0.028) & (np.abs(c[:, 0]) < 0.036) & (c[:, 1] < yc - 0.02)
        return [x for x in [_shell(rf, hi, fn, 0.004, f"anny_beard_{hc}", "mustache")] if x]
    fn = lambda c: (c[:, 2] < zm + 0.018) & (c[:, 1] < yc - 0.015) & (np.abs(c[:, 0]) < 0.09) & ~lip(c)
    if kind == "stubble":
        return [x for x in [_shell(rf, hi, fn, 0.0015, f"anny_stubble_{hc}", "stubble", uv_planar=True)] if x]
    return [x for x in [_shell(rf, hi, fn, 0.004, f"anny_beard_{hc}", "beard")] if x]


def _pick(rng, key):
    return rng.choice(MH[key])


def _fab(rng, slot, color):
    """スロットと色から生地を決める(デニムは青系/黒/グレー、ピンストライプはスーツ、ボーダー/チェックはカジュアルのトップス)"""
    if slot == "top":
        return rng.choices(["jersey", "knit", "border", "check", "linen"], [52, 14, 12, 8, 14])[0]
    if slot == "bottom":
        return "denim" if color in ("blue", "navy", "lightblue", "black", "gray") and rng.random() < 0.4 else rng.choice(["twill", "twill", "wool", "linen"])
    if slot == "suit":
        return "pin" if rng.random() < 0.3 else "wool"
    if slot in ("jacket", "blazer", "coat"):
        return rng.choice(["wool", "twill", "wool"])
    if slot == "coverall":
        return "twill"
    return rng.choice(["jersey", "linen", "check"]) if slot == "dress" else "twill"


def make_outfit(spec, rng):
    """人物 spec の服装一式。戻り: dict(pieces=[(kind, slot, arg, color, margin)], hair, hair_color, skin, shoe_color, mask, ...)"""
    f, g, yr = spec["female"], spec["group"], spec["years"]
    pcs = []
    col = lambda *c: rng.choice(c)
    casual = ["white", "black", "navy", "gray", "beige", "red", "olive", "blue", "pink", "mustard", "brown", "khaki", "cream", "lightblue", "darkgreen", "purple", "orange"]
    dark = ["navy", "black", "gray", "beige", "olive", "brown", "khaki", "blue"]
    top = lambda c: pcs.append(("mh", "top", _pick(rng, "top_f" if f else "top_m"), c, 0.022))
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
    fabricable = ("top", "bottom", "suit", "dress", "jacket", "blazer", "coat", "coverall")
    return [(k, sl, a, (f"{c}_{_fab(rng, sl, c)}" if sl in fabricable else c), m) for k, sl, a, c, m in pcs]


def _nearest_cw(src_V, src_cw, P):
    from scipy.spatial import cKDTree
    return src_cw[cKDTree(src_V).query(P)[1]]


def _grid_decal(rf, top, cx, zc, w, h, uv, name, front=True, n=3, y_off=0.003):
    """布の表面に沿って貼る格子状のデカール。top の頂点の (x,z) 最近傍から奥行きを取り、布の変形(重み)に追従させる"""
    from scipy.spatial import cKDTree
    V = top["Vrest"]
    kd = cKDTree(V[:, [0, 2]])
    gx = np.linspace(cx - w / 2, cx + w / 2, n + 1)
    gz = np.linspace(zc + h / 2, zc - h / 2, n + 1)
    P = []
    for z in gz:
        for x in gx:
            d, i = kd.query([x, z], k=6)
            ys = V[i, 1]
            if d.min() > 0.05:
                return None
            P.append((x, ys.min() - y_off if front else ys.max() + y_off, z))
    P = np.array(P)
    u0, v0, u1, v1 = uv
    UV = np.array([(u0 + (u1 - u0) * i / n, v0 + (v1 - v0) * (1 - j / n)) for j in range(n + 1) for i in range(n + 1)])
    faces = []
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            q = (a, a + 1, a + n + 2, a + n + 1)
            if not front:
                q = q[::-1]
            faces.append([(q[0], q[0]), (q[1], q[1]), (q[2], q[2])])
            faces.append([(q[0], q[0]), (q[2], q[2]), (q[3], q[3])])
    cw = _nearest_cw(V, top["cw"], P)
    cl = dict(faces=faces, vt=UV, license="procedural", author="procedural", name=name, path=f"procedural/{name}", tex=None)
    Vp = H.skin(P, rf["rest_bone_poses"], rf["bone_poses"], cw)
    return dict(slot=name, name=name, Vrest=P, V=Vp, cw=cw, cl=cl, mat="anny_print" if name.startswith("print") else "anny_detail", uv=True)


def decals(rf, cloth, rng, group, years):
    """T シャツのプリント・ポロの前立て・パンツのポケット(ジオメトリ増はほぼ無し。アルファのデカール)"""
    from .textures_human import UV
    L = H.model("anny").bone_labels
    r = rf["rest_bone_poses"]
    top = next((c for c in cloth if c["slot"] == "top"), None)
    bottom = next((c for c in cloth if c["slot"] == "bottom"), None)
    outer = any(c["slot"] in ("jacket", "blazer", "coat", "coverall", "suit", "dress") for c in cloth)
    zh = rf["rest_vertices"][:, 2].max() - rf["rest_vertices"][:, 2].min()
    sc = zh / 1.70
    out = []
    zc = r[L.index("spine_03")][2, 3] - 0.02 * sc
    if top is not None and not outer:
        if "polo" in top["name"]:
            d = _grid_decal(rf, top, 0.0, zc + 0.02 * sc, 0.045 * sc, 0.17 * sc, UV["detail"](0), "detail_placket", n=2)
            d and out.append(d)
        elif group in ("casual", "student", "kid", "elder") and rng.random() < 0.4:
            i = rng.randrange(8)
            s_ = rng.uniform(0.11, 0.16) * sc
            d = _grid_decal(rf, top, rng.uniform(-0.01, 0.01), zc - 0.02 * sc, s_, s_, UV["print"](i), f"print_{i}")
            d and out.append(d)
            if rng.random() < 0.25:
                d = _grid_decal(rf, top, 0.0, zc - 0.01 * sc, 0.26 * sc, 0.26 * sc, UV["print"](rng.randrange(8)), "print_back", front=False)
                d and out.append(d)
    if bottom is not None and "skirt" not in bottom["name"] and "tiered" not in bottom["name"] and "jean" not in bottom["name"] and rng.random() < 0.75:
        zp = r[L.index("pelvis")][2, 3] - 0.06 * sc
        for sgn in (1, -1):
            u0, v0, u1, v1 = UV["detail"](1)
            uv = (u1, v0, u0, v1) if sgn < 0 else (u0, v0, u1, v1)
            d = _grid_decal(rf, bottom, sgn * 0.095 * sc, zp, 0.11 * sc, 0.12 * sc, uv, "detail_pocket", n=2, y_off=0.002)
            d and out.append(d)
    return out


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
