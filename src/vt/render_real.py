"""リアリズム用の材質ノード群(render.get_material から呼ばれる): 目地(Brick)・壁の汚れ・窓の室内(インテリアマッピング)・水面。"""
import bpy  # noqa: F401  (ノード型を使う)


def _R():
    from . import render
    return render


def mth(nt, op, a, b=None, clamp=False):
    """Math ノードを作って出力socketを返す(a,b は socket か数値)"""
    n = nt.nodes.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def brick(nt, d, base, texc):
    """タイル/レンガ/石の目地: 1枚ごとの色むら+目地色。Fac は bump の高さに使う"""
    N, L = nt.nodes.new, nt.links.new
    j = d["joint"]
    b = N("ShaderNodeTexBrick")
    b.offset = j.get("offset", 0.5); b.offset_frequency = 2; b.squash = 1.0
    b.inputs["Scale"].default_value = 1.0
    b.inputs["Brick Width"].default_value = j["w"]; b.inputs["Row Height"].default_value = j["h"]
    b.inputs["Mortar Size"].default_value = j.get("mortar", 0.006); b.inputs["Mortar Smooth"].default_value = 0.08
    b.inputs["Bias"].default_value = 0.0
    k = j.get("var", 0.14)
    b.inputs["Color1"].default_value = tuple(min(1, c * (1 + k)) for c in base[:3]) + (1,)
    b.inputs["Color2"].default_value = tuple(c * (1 - k) for c in base[:3]) + (1,)
    b.inputs["Mortar"].default_value = _R()._rgb(j.get("mortar_col", "#8a8782"))
    # 壁面は +y 向き(x=壁に沿う, z=上): 目地は (x+y, z) 平面。側面(±x向き)でも y 方向に目地が並ぶ
    sp = nt.nodes.new("ShaderNodeSeparateXYZ"); L(texc.outputs["Object"], sp.inputs[0])
    cb = nt.nodes.new("ShaderNodeCombineXYZ")
    L(mth(nt, "ADD", sp.outputs[0], sp.outputs[1]), cb.inputs[0]); L(sp.outputs[2], cb.inputs[1])
    L(cb.outputs[0], b.inputs["Vector"])
    return b


def grime(nt, basecol, texc, objinfo, d):
    """壁面の汚れ: wall_grime.png(R=雨だれ G=垂れ染み B=錆)を Box 投影。インスタンスごとに位置をずらして繰り返しを隠す"""
    N, L = nt.nodes.new, nt.links.new
    R = _R()
    img = N("ShaderNodeTexImage"); img.image = R._image("wall_grime.png", True)
    img.projection = "BOX"; img.projection_blend = 0.25; img.extension = "REPEAT"
    mp = N("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.25, 0.25, 0.25)
    off = N("ShaderNodeVectorMath"); off.operation = "SCALE"; off.inputs["Scale"].default_value = 3.7
    rv = N("ShaderNodeCombineXYZ"); L(objinfo.outputs["Random"], rv.inputs[0]); L(objinfo.outputs["Random"], rv.inputs[2])
    L(rv.outputs[0], off.inputs[0]); L(off.outputs[0], mp.inputs["Location"])
    L(texc.outputs["Object"], mp.inputs["Vector"]); L(mp.outputs[0], img.inputs["Vector"])
    sep = N("ShaderNodeSeparateColor"); L(img.outputs["Color"], sep.inputs[0])
    st = d.get("grime", 1.4)
    dk = N("ShaderNodeMix"); dk.data_type = "RGBA"; dk.blend_type = "MULTIPLY"
    ftot = mth(nt, "ADD", mth(nt, "MULTIPLY", sep.outputs[0], 0.5 * st), mth(nt, "MULTIPLY", sep.outputs[1], 0.42 * st), True)
    L(ftot, dk.inputs[0]); L(basecol, dk.inputs[6]); dk.inputs[7].default_value = (0.38, 0.35, 0.32, 1)
    rs = N("ShaderNodeMix"); rs.data_type = "RGBA"
    L(mth(nt, "MULTIPLY", sep.outputs[2], 0.38 * st), rs.inputs[0]); L(dk.outputs[2], rs.inputs[6]); rs.inputs[7].default_value = (0.2, 0.14, 0.09, 1)
    return rs.outputs[2]


def _ramp(nt, hexes):
    R = _R()
    r = nt.nodes.new("ShaderNodeValToRGB"); r.color_ramp.interpolation = "CONSTANT"
    while len(r.color_ramp.elements) < len(hexes):
        r.color_ramp.elements.new(0.5)
    for i, c in enumerate(hexes):
        r.color_ramp.elements[i].position = i / len(hexes) + 0.001
        r.color_ramp.elements[i].color = R._rgb(c)
    r.color_ramp.elements[0].position = 0.0
    return r


def interior(nt, out, bsdf, texc, objinfo):
    """窓の奥の室内(簡易インテリアマッピング): 視線と部屋(幅3m×高さ3m×奥行4.5m)の箱の交点で床/天井/側壁/奥壁を塗り分け、
    窓ごと(3mセル)にカーテン/ブラインド/素通し/点灯をハッシュで決める。夜・夕景は点灯セルが発光する。"""
    N, L = nt.nodes.new, nt.links.new
    R = _R()
    M = lambda op, a, b=None, c=False: mth(nt, op, a, b, c)
    CW, RH, D = 3.0, 3.0, 4.5
    geo = N("ShaderNodeNewGeometry")
    vt = N("ShaderNodeVectorTransform"); vt.vector_type = "VECTOR"; vt.convert_from = "WORLD"; vt.convert_to = "OBJECT"
    L(geo.outputs["Incoming"], vt.inputs[0])
    sv = N("ShaderNodeSeparateXYZ"); L(vt.outputs[0], sv.inputs[0])
    px = N("ShaderNodeSeparateXYZ"); L(texc.outputs["Object"], px.inputs[0])
    dx, dy, dz = (M("MULTIPLY", sv.outputs[i], -1.0) for i in range(3))       # 視線方向(壁の奥へ)
    cellf = M("DIVIDE", M("ADD", px.outputs[0], 60.0), CW)
    cell = M("FLOOR", cellf)
    xl = M("MULTIPLY", M("SUBTRACT", cellf, cell), CW)
    zl = M("MINIMUM", M("MAXIMUM", px.outputs[2], 0.05), RH - 0.05)
    tb = M("DIVIDE", D, M("MAXIMUM", dy, 0.04))
    pos = M("GREATER_THAN", dx, 0.0)
    tx = M("ADD", M("MULTIPLY", M("DIVIDE", M("SUBTRACT", CW, xl), M("MAXIMUM", dx, 1e-3)), pos),
           M("MULTIPLY", M("DIVIDE", xl, M("MAXIMUM", M("MULTIPLY", dx, -1.0), 1e-3)), M("SUBTRACT", 1.0, pos)))
    up = M("GREATER_THAN", dz, 0.0)
    tz = M("ADD", M("MULTIPLY", M("DIVIDE", M("SUBTRACT", RH, zl), M("MAXIMUM", dz, 1e-3)), up),
           M("MULTIPLY", M("DIVIDE", zl, M("MAXIMUM", M("MULTIPLY", dz, -1.0), 1e-3)), M("SUBTRACT", 1.0, up)))
    tm = M("MINIMUM", tb, M("MINIMUM", tx, tz))
    is_back = M("LESS_THAN", M("SUBTRACT", tb, tm), 1e-4)
    is_z = M("MULTIPLY", M("SUBTRACT", 1.0, is_back), M("LESS_THAN", M("SUBTRACT", tz, tm), 1e-4))
    # 窓セルごとの乱数(R=壁色, G=カーテン種, B=点灯)
    wn = N("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "3D"
    cv = N("ShaderNodeCombineXYZ"); L(cell, cv.inputs[0]); L(objinfo.outputs["Random"], cv.inputs[1])
    L(cv.outputs[0], wn.inputs["Vector"])
    sc_ = N("ShaderNodeSeparateColor"); L(wn.outputs["Color"], sc_.inputs[0])
    r_wall, r_cur, r_lit = sc_.outputs[0], sc_.outputs[1], sc_.outputs[2]
    wallc = _ramp(nt, ["#d9d4c6", "#b9b2a0", "#e8e6de", "#8f9aa3", "#c9b9a0", "#9ea39b"]); L(r_wall, wallc.inputs[0])
    surf = N("ShaderNodeMix"); surf.data_type = "RGBA"                       # 床(暗い茶)/天井(白)
    L(up, surf.inputs[0]); surf.inputs[6].default_value = R._rgb("#5a4634"); surf.inputs[7].default_value = R._rgb("#f0eee8")
    sidew = N("ShaderNodeMix"); sidew.data_type = "RGBA"; sidew.blend_type = "MULTIPLY"; sidew.inputs[0].default_value = 1.0
    L(wallc.outputs[0], sidew.inputs[6]); sidew.inputs[7].default_value = (0.78, 0.78, 0.78, 1)
    m1 = N("ShaderNodeMix"); m1.data_type = "RGBA"                           # 側壁 or 奥壁
    L(is_back, m1.inputs[0]); L(sidew.outputs[2], m1.inputs[6]); L(wallc.outputs[0], m1.inputs[7])
    m2 = N("ShaderNodeMix"); m2.data_type = "RGBA"                           # 床/天井
    L(is_z, m2.inputs[0]); L(m1.outputs[2], m2.inputs[6]); L(surf.outputs[2], m2.inputs[7])
    # 家具(奥壁の低い箱: 高さ0.9〜1.5m、幅は部屋の半分程度)と、昼間の室内は屋外より暗い(窓が黒っぽく見える)
    low = M("LESS_THAN", zl, M("ADD", 0.9, M("MULTIPLY", M("FRACT", M("MULTIPLY", r_wall, 17.3)), 0.7)))
    strip = M("LESS_THAN", M("FRACT", M("ADD", M("MULTIPLY", xl, 0.33), M("MULTIPLY", r_cur, 7.0))), 0.45)
    furn = M("MULTIPLY", M("MULTIPLY", low, strip), is_back)
    fm = N("ShaderNodeMix"); fm.data_type = "RGBA"; fm.blend_type = "MULTIPLY"
    L(M("MULTIPLY", furn, 0.6), fm.inputs[0]); L(m2.outputs[2], fm.inputs[6]); fm.inputs[7].default_value = (0.3, 0.26, 0.22, 1)
    dim = N("ShaderNodeMix"); dim.data_type = "RGBA"; dim.blend_type = "MULTIPLY"; dim.inputs[0].default_value = 1.0
    L(fm.outputs[2], dim.inputs[6]); k = {"day": 0.14, "dusk": 0.18}.get(R.TIME, 0.5)      # 室内の照度は屋外の数%
    dim.inputs[7].default_value = (k, k, k, 1)
    # カーテン(G<0.28)は窓全面、ブラインド(0.28..0.5)は上から一部を横縞で覆う
    curc = _ramp(nt, ["#d8d2c2", "#7b6a5a", "#a8b0b4", "#c9b79c", "#59606a", "#e4e0d6"])
    L(M("FRACT", M("MULTIPLY", r_cur, 37.7)), curc.inputs[0])
    mcur = N("ShaderNodeMix"); mcur.data_type = "RGBA"
    L(M("LESS_THAN", r_cur, 0.28), mcur.inputs[0]); L(dim.outputs[2], mcur.inputs[6]); L(curc.outputs[0], mcur.inputs[7])
    stripe = M("GREATER_THAN", M("SINE", M("MULTIPLY", px.outputs[2], 55.0)), -0.1)
    blind_on = M("MULTIPLY", M("MULTIPLY", M("GREATER_THAN", r_cur, 0.28), M("LESS_THAN", r_cur, 0.5)),
                 M("GREATER_THAN", zl, M("MULTIPLY", RH, M("SUBTRACT", 1.0, M("FRACT", M("MULTIPLY", r_cur, 91.3))))))
    mbl = N("ShaderNodeMix"); mbl.data_type = "RGBA"
    L(M("MULTIPLY", blind_on, stripe), mbl.inputs[0]); L(mcur.outputs[2], mbl.inputs[6]); mbl.inputs[7].default_value = R._rgb("#cfcbbf")
    col = mbl.outputs[2]
    L(col, bsdf.inputs["Base Color"])
    if not bsdf.inputs["Roughness"].links:
        bsdf.inputs["Roughness"].default_value = 0.9
    lit_frac = R.LIT.get(R.TIME, 0.0)
    if lit_frac > 0:
        lit = M("LESS_THAN", r_lit, lit_frac)
        warm = N("ShaderNodeMix"); warm.data_type = "RGBA"                    # 電球色/白色蛍光灯
        L(M("GREATER_THAN", M("FRACT", M("MULTIPLY", r_lit, 53.1)), 0.35), warm.inputs[0])
        warm.inputs[6].default_value = (1.0, 0.72, 0.42, 1); warm.inputs[7].default_value = (0.88, 0.93, 1.0, 1)
        em = N("ShaderNodeMix"); em.data_type = "RGBA"; em.blend_type = "MULTIPLY"; em.inputs[0].default_value = 1.0
        L(col, em.inputs[6]); L(warm.outputs[2], em.inputs[7])
        L(em.outputs[2], bsdf.inputs["Emission Color"])
        L(M("MULTIPLY", lit, 55.0 if R.TIME == "night" else 25.0), bsdf.inputs["Emission Strength"])


def water(nt, bsdf, texc):
    """水面: 大小の波の法線+深い青緑。粗さを少し持たせ、水平線が鏡のように白く飛ばないようにする"""
    N, L = nt.nodes.new, nt.links.new
    R = _R()
    bsdf.inputs["IOR"].default_value = 1.333
    bsdf.inputs["Roughness"].default_value = 0.05          # 運河・湾は鏡のように建物の灯りを映す
    bsdf.inputs["Metallic"].default_value = 0.0
    mp = N("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.35, 0.8, 1.0)      # 波は一方向に長い
    L(texc.outputs["Object"], mp.inputs["Vector"])
    n1 = N("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 1.0; n1.inputs["Detail"].default_value = 5.0; n1.inputs["Roughness"].default_value = 0.6
    L(mp.outputs[0], n1.inputs["Vector"])
    n2 = N("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 0.18; n2.inputs["Detail"].default_value = 3.0
    L(texc.outputs["Object"], n2.inputs["Vector"])
    hs = N("ShaderNodeMix"); hs.data_type = "RGBA"; hs.inputs[0].default_value = 0.5
    L(n1.outputs["Fac"], hs.inputs[6]); L(n2.outputs["Fac"], hs.inputs[7])
    bp = N("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.22; bp.inputs["Distance"].default_value = 0.3
    L(hs.outputs[2], bp.inputs["Height"]); L(bp.outputs[0], bsdf.inputs["Normal"])
    mc = N("ShaderNodeMix"); mc.data_type = "RGBA"
    L(n2.outputs["Fac"], mc.inputs[0]); mc.inputs[6].default_value = R._rgb("#0a2226"); mc.inputs[7].default_value = R._rgb("#1d3a36")
    L(mc.outputs[2], bsdf.inputs["Base Color"])
