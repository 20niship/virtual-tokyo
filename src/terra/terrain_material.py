"""地形のスプラット材質(Blender)。6 層(grass, litter, rock, scree, soil, alpine)の重み w0/w1 を頂点属性から受け、
- 各層は縮尺・回転の違う 2 サンプルのボックス投影(トライプラナー)を混ぜる(ミクロ)+約 45m 周期の明暗ムラ(マクロ)でタイル感を消す
- 土の色は地質の土種(t0.rgb = 土の反射率)、岩の色は岩種(t1.rgb = 色味)で変える。t0.a = 苔、t1.a = 地衣類の付きやすさ
- 色の明暗から Bump(微小な凹凸)。far 用に object-space の法線マップ(normal_image)を重ねられる"""
from __future__ import annotations

import math
from pathlib import Path

SPLAT = ["grass", "litter", "rock", "scree", "soil", "alpine"]
SCALE = dict(grass=2.4, litter=2.0, rock=3.0, scree=1.6, soil=2.2, alpine=3.0)       # ミクロ 1 周期[m]。マクロ側は x3.3
TINT = dict(grass=(0.80, 0.88, 0.66), litter=(1.85, 1.6, 1.35), scree=(0.95, 0.93, 0.9), alpine=(1.0, 1.0, 0.95))
ROOT = Path(__file__).resolve().parents[2] / "assets"
PATHS = {"grass": ROOT / "textures/grass.png", "litter": ROOT / "terra/textures/forest_litter.png", "rock": ROOT / "terra/textures/rock_cliff.png",
         "scree": ROOT / "terra/textures/gravel_medium.png", "soil": ROOT / "textures/soil.png", "alpine": ROOT / "terra/textures/alpine_turf.png",
         "moss": ROOT / "terra/textures/moss.png"}


def build(normal_image=None, bump=0.9, debug=None):
    import bpy
    m = bpy.data.materials.new("terrain_splat")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out, bs = N("ShaderNodeOutputMaterial"), N("ShaderNodeBsdfPrincipled")
    L(bs.outputs[0], out.inputs[0])
    tc = N("ShaderNodeTexCoord")

    def mapping(scale, rot=0.0):
        mp = N("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1 / scale,) * 3
        mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot))
        L(tc.outputs["Object"], mp.inputs["Vector"])
        return mp

    def img(path, scale, rot=0.0):
        im = N("ShaderNodeTexImage")
        im.image = bpy.data.images.load(str(path))
        im.projection = "BOX"
        im.projection_blend = 0.25
        L(mapping(scale, rot).outputs[0], im.inputs["Vector"])
        return im.outputs["Color"]

    def mix(a, b, f, blend="MIX"):
        n = N("ShaderNodeMix")
        n.data_type = "RGBA"
        n.blend_type = blend
        if isinstance(f, (int, float)):
            n.inputs[0].default_value = f
        else:
            L(f, n.inputs[0])
        for i, v in ((6, a), (7, b)):
            if isinstance(v, tuple):
                n.inputs[i].default_value = (*v, 1.0)
            else:
                L(v, n.inputs[i])
        return n.outputs[2]

    def mathn(op, a, b=None, clamp=False):
        n = N("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]

    def noise(scale, detail=4.0, rough=0.55):
        n = N("ShaderNodeTexNoise")
        n.noise_dimensions = "3D"
        n.inputs["Scale"].default_value = 1.0 / scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        L(tc.outputs["Object"], n.inputs["Vector"])
        return n.outputs["Fac"]

    def attr(name):
        a = N("ShaderNodeAttribute")
        a.attribute_name = name
        s = N("ShaderNodeSeparateColor")
        L(a.outputs["Color"], s.inputs[0])
        return a.outputs["Color"], s.outputs[0], s.outputs[1], s.outputs[2], a.outputs["Alpha"]

    w0c, g_w, l_w, r_w, _a0 = attr("w0")
    w1c, s_w, so_w, al_w, _a1 = attr("w1")
    t0c, _, _, _, moss = attr("t0")
    t1c, _, _, _, lichen = attr("t1")
    cols = {}
    for k in SPLAT:
        c = mix(img(PATHS[k], SCALE[k]), img(PATHS[k], SCALE[k] * 3.3, 37), 0.5)
        c = mix(c, img(PATHS[k], SCALE[k] / 7.0, 71), 0.4, "OVERLAY") if k in ("soil", "litter", "scree", "rock") else c      # 近接で見える粒(約 0.3m 周期)
        gm = N("ShaderNodeGamma")                                                      # 粒・層理のコントラストを強める(平均の明るさは x1.8 で戻す)
        gm.inputs["Gamma"].default_value = 1.7 if k in ("rock", "scree", "litter", "soil") else 1.25
        L(c, gm.inputs["Color"])
        c = mix(gm.outputs[0], (1.6, 1.6, 1.6), 1.0, "MULTIPLY")
        if k == "soil":
            v = N("ShaderNodeRGBToBW")
            L(c, v.inputs[0])
            vv = mathn("MULTIPLY", v.outputs[0], 3.4)
            cmb = N("ShaderNodeCombineColor")
            for i in range(3):
                L(vv, cmb.inputs[i])
            c = mix(cmb.outputs[0], t0c, 1.0, "MULTIPLY")             # 土種の色
        elif k in ("rock", "scree"):
            c = mix(c, t1c, 1.0, "MULTIPLY")                          # 岩種の色味
        elif k in TINT:
            c = mix(c, TINT[k], 1.0, "MULTIPLY")
        if k == "grass":                                                           # 草の色ムラ: 約 7m の斑で黄褐色(枯れ草)・約 2m の斑で明暗。一様な緑のフェルトに見えないように
            c = mix(c, mix(c, (1.3, 1.08, 0.7), 1.0, "MULTIPLY"), mathn("MULTIPLY", mathn("SUBTRACT", noise(7.0, 3.0), 0.40), 2.2, True))
            c = mix(c, mix(c, (0.78, 0.82, 0.7), 1.0, "MULTIPLY"), mathn("MULTIPLY", mathn("SUBTRACT", noise(2.2, 3.0), 0.45), 2.5, True))
        cols[k] = c
    wts = dict(grass=g_w, litter=l_w, rock=r_w, scree=s_w, soil=so_w, alpine=al_w)
    acc = None
    for k in SPLAT:
        wc = N("ShaderNodeCombineColor")
        for i in range(3):
            L(wts[k], wc.inputs[i])
        t = mix(cols[k], wc.outputs[0], 1.0, "MULTIPLY")
        acc = t if acc is None else mix(acc, t, 1.0, "ADD")
    acc_dbg = acc
    # 苔・地衣類(岩と礫の上に、斑状に)
    # 斑の縁は頂点属性(moss/lichen)×ノイズのしきい値を滑らかに(clamp((n - a) * k))で出す。面単位の材質割り当てではない
    soft = lambda n, a, k: mathn("MULTIPLY", mathn("SUBTRACT", n, a), k, True)
    rockw = mathn("ADD", mathn("ADD", r_w, s_w), mathn("MULTIPLY", l_w, 0.45), True)             # 岩・礫の上と、湿った林床の落ち葉の上にも苔
    mnoise = soft(noise(1.3, 6.0), 0.40, 7.0)
    moss_f = mathn("MULTIPLY", mathn("MULTIPLY", moss, rockw), mnoise, True)
    acc = mix(acc, mix(img(PATHS["moss"], 0.6), (0.9, 0.95, 0.8), 0.3, "MULTIPLY"), mathn("MULTIPLY", moss_f, 0.85), "MIX")
    lich_f = mathn("MULTIPLY", mathn("MULTIPLY", lichen, r_w), soft(noise(0.55, 5.0), 0.48, 7.0), True)
    acc = mix(acc, (0.62, 0.60, 0.34), mathn("MULTIPLY", lich_f, 0.5), "MIX")
    # マクロの明暗・色味のムラ(約 45m と約 9m の 2 スケール)と、全体の反射率の抑え(裸地が一様な薄ベージュに見えないように)
    m1 = mathn("ADD", mathn("MULTIPLY", mathn("SUBTRACT", noise(45.0, 3.0), 0.5), 1.9), 0.82)
    m2 = mathn("ADD", mathn("MULTIPLY", mathn("SUBTRACT", noise(9.0, 4.0), 0.5), 0.8), 1.0)
    m0 = mathn("ADD", mathn("MULTIPLY", mathn("SUBTRACT", noise(170.0, 3.0), 0.5), 1.1), 0.95)      # 約 170m の明暗ムラ(遠景の山肌がのっぺりしない)
    macro = mathn("MULTIPLY", mathn("MULTIPLY", m1, m2), m0)
    warm = mix(acc, mix(acc, (1.0, 0.9, 0.78), 1.0, "MULTIPLY"), mathn("MULTIPLY", noise(30.0, 2.0), 1.4, True))      # 暖色/寒色の斑
    acc = mix(warm, (0.78, 0.78, 0.78), 1.0, "MULTIPLY")
    # 樹冠下の光斑(木漏れ日): 落ち葉の層の上に、暖色で明るい斑を ~1m 周期で足す(空の散乱光だけの青暗い無地に見えないように)。控えめな演出
    fleck = mathn("MULTIPLY", soft(noise(1.2, 3.0, 0.5), 0.58, 6.0), mathn("MULTIPLY", l_w, 0.7), True)
    acc = mix(acc, mix(acc, (1.9, 1.7, 1.35), 1.0, "MULTIPLY"), fleck, "MIX")
    mc = N("ShaderNodeCombineColor")
    for i in range(3):
        L(macro, mc.inputs[i])
    base = mix(acc, mc.outputs[0], 1.0, "MULTIPLY")
    L(base, bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.92
    # 微小な凹凸: 細かいノイズ(岩・礫の上で強い)+ 色の明暗
    crumble = N("ShaderNodeBump")
    crumble.inputs["Strength"].default_value = 0.7
    crumble.inputs["Distance"].default_value = 0.12
    L(noise(0.22, 8.0, 0.65), crumble.inputs["Height"])
    bw = N("ShaderNodeRGBToBW")
    L(base, bw.inputs[0])
    bp = N("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    bp.inputs["Distance"].default_value = 0.08
    L(bw.outputs[0], bp.inputs["Height"])
    L(crumble.outputs["Normal"], bp.inputs["Normal"])
    nrm = bp.outputs["Normal"]
    if normal_image is not None:               # far: 全解像度の高さから焼いた object-space の法線マップ
        ni = N("ShaderNodeTexImage")
        ni.image = normal_image
        ni.interpolation = "Linear"
        ni.extension = "EXTEND"
        uv = N("ShaderNodeUVMap")
        L(uv.outputs["UV"], ni.inputs["Vector"])
        nm = N("ShaderNodeNormalMap")
        nm.space = "OBJECT"
        L(ni.outputs["Color"], nm.inputs["Color"])
        bp2 = N("ShaderNodeBump")
        bp2.inputs["Strength"].default_value = bump
        bp2.inputs["Distance"].default_value = 0.04
        L(bw.outputs[0], bp2.inputs["Height"])
        L(nm.outputs["Normal"], bp2.inputs["Normal"])
        nrm = bp2.outputs["Normal"]
    L(nrm, bs.inputs["Normal"])
    if debug:                      # 診断用: 途中の色をそのまま放射で出す
        em = N("ShaderNodeEmission")
        L({"litter": cols["litter"], "soil": cols["soil"], "rock": cols["rock"], "acc": acc_dbg, "base": base}[debug], em.inputs["Color"])
        L(em.outputs[0], out.inputs[0])
    return m
