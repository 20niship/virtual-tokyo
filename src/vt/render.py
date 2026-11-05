"""bpyでのシーン構築とCyclesレンダ(モジュールギャラリー / 街区)。"""
import math
import random

import bpy
import numpy as np
from mathutils import Vector

from .materials import MATERIALS

_mat_cache = {}


def _rgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c]
    return (*lin, 1.0)


REAL = False          # init_scene(realism=True) で有効: 壁の汚れ・目地・ベベル・夜間発光


def get_material(mid):
    if mid in _mat_cache:
        return _mat_cache[mid]
    d = MATERIALS[mid]
    mat = bpy.data.materials.new(mid)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    N = nt.nodes.new
    L = nt.links.new
    out = N("ShaderNodeOutputMaterial")
    bsdf = N("ShaderNodeBsdfPrincipled")
    L(bsdf.outputs[0], out.inputs[0])
    objinfo = N("ShaderNodeObjectInfo")
    texc = N("ShaderNodeTexCoord")
    # 色
    base = _rgb(d["color"])
    colsock = None
    if "vary" in d:
        attr = N("ShaderNodeAttribute"); attr.attribute_type = "INSTANCER"; attr.attribute_name = "bvar"
        ramp = N("ShaderNodeValToRGB")
        cols = d["vary"]
        ramp.color_ramp.interpolation = "CONSTANT"
        while len(ramp.color_ramp.elements) < len(cols):
            ramp.color_ramp.elements.new(0.5)
        for i, c in enumerate(cols):
            ramp.color_ramp.elements[i].position = i / len(cols) + 0.001
            ramp.color_ramp.elements[i].color = _rgb(c)
        ramp.color_ramp.elements[0].position = 0.0
        L(attr.outputs["Fac"], ramp.inputs[0])
        colsock = ramp.outputs[0]
    # 汚れ・ムラ(ノイズ)
    noise = N("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 6.0
    L(texc.outputs["Object"], noise.inputs["Vector"])
    L(objinfo.outputs["Random"], noise.inputs["W"])
    fine = N("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 80.0
    fine.inputs["Detail"].default_value = 3.0
    L(texc.outputs["Object"], fine.inputs["Vector"])
    if d.get("emit"):
        bsdf.inputs["Emission Color"].default_value = _rgb(d["emit"][0])
        k = 1.0
        if REAL and TIME != "day":       # 夜・夕景は街灯/看板/自販機/ヘッドライトを強く光らせる
            k = (10.0 if mid == "led_white" else 40.0 if mid == "car_headlight" else 8.0 if mid.startswith(("sign_", "vend_")) else 1.5) * (1.0 if TIME == "night" else 0.4)
        bsdf.inputs["Emission Strength"].default_value = d["emit"][1] * k
    if d.get("glass") and REAL and mid == "glass_main":
        # 窓ガラス: 透過を使わず「反射+室内(インテリアマッピング)」を1枚の表面で描く。窓ごとにカーテン/ブラインド/点灯が変わり、夜は窓が光る
        from . import render_real
        bsdf.inputs["IOR"].default_value = 1.5
        bsdf.inputs["Metallic"].default_value = 0.15
        rg = N("ShaderNodeMath"); rg.operation = "MULTIPLY_ADD"; rg.inputs[1].default_value = 0.06; rg.inputs[2].default_value = 0.03
        L(objinfo.outputs["Random"], rg.inputs[0]); L(rg.outputs[0], bsdf.inputs["Roughness"])
        render_real.interior(nt, out, bsdf, texc, objinfo)
    elif d.get("glass"):
        bsdf.inputs["Transmission Weight"].default_value = 1.0
        bsdf.inputs["IOR"].default_value = 1.5
        bsdf.inputs["Base Color"].default_value = base
        if colsock:
            L(colsock, bsdf.inputs["Base Color"])
        rg = N("ShaderNodeMath"); rg.operation = "MULTIPLY_ADD"; rg.inputs[1].default_value = 0.05; rg.inputs[2].default_value = 0.012   # 窓ごとに反射のにじみを変える
        L(objinfo.outputs["Random"], rg.inputs[0]); L(rg.outputs[0], bsdf.inputs["Roughness"])
        mat.use_backface_culling = False
    elif d.get("interior"):
        from . import render_real
        render_real.interior(nt, out, bsdf, texc, objinfo)
    elif d.get("water"):
        from . import render_real
        render_real.water(nt, bsdf, texc)
    elif d.get("foliage"):
        _foliage(nt, out, bsdf, d, texc)
    elif d.get("tex") or d.get("wear"):
        _textured(nt, bsdf, d, base, texc, objinfo)
    else:
        mix = N("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = 0.0
        if d.get("dirt"):
            ramp2 = N("ShaderNodeValToRGB")
            ramp2.color_ramp.elements[0].position = 0.35
            ramp2.color_ramp.elements[1].position = 0.7
            ramp2.color_ramp.elements[0].color = (0.72, 0.7, 0.68, 1)
            ramp2.color_ramp.elements[1].color = (1, 1, 1, 1)
            L(noise.outputs["Fac"], ramp2.inputs[0])
            mix.inputs[0].default_value = 1.0
            L(ramp2.outputs[0], mix.inputs[7])
        else:
            mix.inputs[7].default_value = (1, 1, 1, 1)
        brick = None
        if REAL and d.get("joint"):
            from . import render_real
            brick = render_real.brick(nt, d, base, texc)
            L(brick.outputs["Color"], mix.inputs[6])
        elif colsock:
            L(colsock, mix.inputs[6])
        else:
            mix.inputs[6].default_value = base
        basecol = mix.outputs[2]
        if d.get("dirt") and REAL:
            from . import render_real
            basecol = render_real.grime(nt, basecol, texc, objinfo, d)
        L(basecol, bsdf.inputs["Base Color"])
        rough = d["rough"]
        bsdf.inputs["Roughness"].default_value = rough
        if d.get("dirt"):
            m2 = N("ShaderNodeMapRange"); m2.inputs[3].default_value = max(0.0, rough - 0.12); m2.inputs[4].default_value = min(1.0, rough + 0.2)
            L(noise.outputs["Fac"], m2.inputs[0])
            L(m2.outputs[0], bsdf.inputs["Roughness"])
        bsdf.inputs["Metallic"].default_value = d["metal"]
        nrm = None
        if REAL and d.get("metal", 0) < 0.95 and not d.get("emit"):
            bv = N("ShaderNodeBevel"); bv.inputs["Radius"].default_value = 0.012; bv.samples = 3
            nrm = bv.outputs[0]
        if d.get("bump") or brick is not None:
            bump = N("ShaderNodeBump"); bump.inputs["Strength"].default_value = min(1.0, (d.get("bump") or 0.5) * 0.5)
            bump.inputs["Distance"].default_value = 0.01
            if brick is not None:
                L(brick.outputs["Fac"], bump.inputs["Height"])
                bump.inputs["Strength"].default_value = 0.8; bump.inputs["Distance"].default_value = d["joint"].get("depth", 0.004)
            else:
                L(fine.outputs["Fac"], bump.inputs["Height"])
            if nrm is not None:
                L(nrm, bump.inputs["Normal"])
            L(bump.outputs[0], bsdf.inputs["Normal"])
        elif nrm is not None:
            L(nrm, bsdf.inputs["Normal"])
        if d.get("wood"):
            wv = N("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 6; wv.inputs["Distortion"].default_value = 4
            L(texc.outputs["Object"], wv.inputs["Vector"])
            wm = N("ShaderNodeMix"); wm.data_type = "RGBA"; wm.blend_type = "MULTIPLY"; wm.inputs[0].default_value = 0.5
            L(mix.outputs[2], wm.inputs[6]); L(wv.outputs["Color"], wm.inputs[7])
            L(wm.outputs[2], bsdf.inputs["Base Color"])
    if not d.get("glass"):
        bsdf.inputs["Metallic"].default_value = d["metal"]
    if REAL and TIME != "day" and d.get("tex") in ("shop_atlas.png", "ad_atlas.png", "sign_atlas.png", "station_signs.png"):
        img = next((n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image and n.image.name.startswith(d["tex"][:8])), None)
        if img is not None:       # 看板テクスチャを自発光させる(夜の店舗看板・広告)
            L(img.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = 3.0 if TIME == "night" else 1.2
    _mat_cache[mid] = mat
    return mat


TEXDIR = __import__("pathlib").Path(__file__).resolve().parents[2] / "assets/textures"
_img_cache = {}


def _image(name, noncolor=False):
    key = (name, noncolor)
    if key not in _img_cache:
        im = bpy.data.images.load(str(TEXDIR / name))
        if noncolor:
            im.colorspace_settings.name = "Non-Color"
        _img_cache[key] = im
    return _img_cache[key]


def _textured(nt, bsdf, d, base, texc, objinfo):
    """画像テクスチャ(タイル/デカール)材質。UVはメートル(size指定)か0..1。"""
    N, L = nt.nodes.new, nt.links.new

    def mapping(size):
        m = N("ShaderNodeMapping")
        sx, sy = (size, size) if not isinstance(size, tuple) else size
        m.inputs["Scale"].default_value = (1 / sx, 1 / sy, 1)
        L(texc.outputs["UV"], m.inputs["Vector"])
        return m
    if d.get("tex"):
        img = N("ShaderNodeTexImage"); img.image = _image(d["tex"])
        img.extension = "REPEAT" if d.get("size") else "CLIP"
        img.interpolation = "Linear"
        if d.get("size"):
            L(mapping(d["size"]).outputs[0], img.inputs["Vector"])
        else:
            L(texc.outputs["UV"], img.inputs["Vector"])
        L(img.outputs["Color"], bsdf.inputs["Base Color"])
        if d.get("tint"):
            tn = N("ShaderNodeMix"); tn.data_type = "RGBA"; tn.blend_type = "MULTIPLY"; tn.inputs[0].default_value = 1.0
            tn.inputs[7].default_value = _rgb(d["tint"])
            L(img.outputs["Color"], tn.inputs[6])
            L(tn.outputs[2], bsdf.inputs["Base Color"])
            img = type("T", (), {"outputs": {"Color": tn.outputs[2], "Alpha": img.outputs["Alpha"]}})()
        if d.get("alpha"):
            alpha = img.outputs["Alpha"]
        else:
            alpha = None
        if d.get("bump"):
            bw = N("ShaderNodeRGBToBW"); L(img.outputs["Color"], bw.inputs[0])
            bp = N("ShaderNodeBump"); bp.inputs["Strength"].default_value = min(1.0, d["bump"] * 0.5); bp.inputs["Distance"].default_value = 0.02
            if REAL and d["tex"].startswith(("roof_", "corrugated", "siding_", "cmu_", "riprap", "steel_rusty")):    # 瓦・波板・サイディング・ブロック・石積みは凹凸を深く(近景の陰影)
                bp.inputs["Strength"].default_value = min(1.0, d["bump"] * 0.8); bp.inputs["Distance"].default_value = 0.05
            hsrc = bw.outputs[0]
            if d.get("hmap"):          # 樹皮: 専用の高さ画像でノーマル(深い裂け目)と粗さ(凹部ほど粗い)を作る
                hi = N("ShaderNodeTexImage"); hi.image = _image(d["hmap"], True); hi.extension = "REPEAT"
                L(mapping(d["size"]).outputs[0], hi.inputs["Vector"])
                hsrc = hi.outputs["Color"]
                bp.inputs["Strength"].default_value = 1.0; bp.inputs["Distance"].default_value = 0.035
                rm = N("ShaderNodeMapRange"); rm.inputs[3].default_value = d["rough"] + 0.08; rm.inputs[4].default_value = max(0.4, d["rough"] - 0.3)
                L(hi.outputs["Color"], rm.inputs[0]); L(rm.outputs[0], bsdf.inputs["Roughness"])
            L(hsrc, bp.inputs["Height"]); L(bp.outputs[0], bsdf.inputs["Normal"])
        # 汚れ・濃淡(低周波)で色ムラ
        nz = N("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.35; nz.inputs["Detail"].default_value = 4
        L(texc.outputs["Object"], nz.inputs["Vector"])
        mx = N("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 0.35
        L(img.outputs["Color"], mx.inputs[6]); L(nz.outputs["Color"], mx.inputs[7])
        if not d.get("alpha"):
            L(mx.outputs[2], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = base
        alpha = None
    if d.get("wear"):
        wi = N("ShaderNodeTexImage"); wi.image = _image(d["wear"], True); wi.extension = "REPEAT"
        wm = N("ShaderNodeMapping"); sz = d.get("wear_size", 2.5)
        wm.inputs["Scale"].default_value = (1 / sz, 1 / sz, 1 / sz)
        L(texc.outputs["Object"], wm.inputs["Vector"])
        L(wm.outputs[0], wi.inputs["Vector"])
        if alpha is not None:
            mu = N("ShaderNodeMath"); mu.operation = "MULTIPLY"
            L(alpha, mu.inputs[0]); L(wi.outputs["Color"], mu.inputs[1]); alpha = mu.outputs[0]
        else:
            alpha = wi.outputs["Color"]
            # 塗装はかすれの部分が透けるように閾値
            cr = N("ShaderNodeMath"); cr.operation = "SUBTRACT"; cr.inputs[1].default_value = 0.2
            L(alpha, cr.inputs[0]); mu = N("ShaderNodeMath"); mu.operation = "MULTIPLY"; mu.inputs[1].default_value = 2.0
            L(cr.outputs[0], mu.inputs[0]); alpha = mu.outputs[0]
    if alpha is not None:
        L(alpha, bsdf.inputs["Alpha"])
    if not d.get("hmap"):
        bsdf.inputs["Roughness"].default_value = d["rough"]
    bsdf.inputs["Metallic"].default_value = d["metal"]


def _foliage(nt, out, bsdf, d, texc):
    """葉アトラス: alpha cutout・両面・個体ごとの色相/明度ジッター(object属性bvar)・透過光(Translucent)を混ぜる"""
    N, L = nt.nodes.new, nt.links.new
    img = N("ShaderNodeTexImage")
    img.image = _image(d["tex"]); img.extension = "CLIP"; img.interpolation = "Linear"
    L(texc.outputs["UV"], img.inputs["Vector"])
    attr = N("ShaderNodeAttribute"); attr.attribute_type = "INSTANCER"; attr.attribute_name = "bvar"
    hs = N("ShaderNodeHueSaturation")
    hm = N("ShaderNodeMapRange"); hm.inputs[3].default_value = 0.405; hm.inputs[4].default_value = 0.485     # 青緑寄りの葉を黄緑側へ寄せつつ個体差
    vm = N("ShaderNodeMapRange"); vm.inputs[3].default_value = 0.62; vm.inputs[4].default_value = 0.86
    hs.inputs["Saturation"].default_value = 1.2
    L(attr.outputs["Fac"], hm.inputs[0]); L(attr.outputs["Fac"], vm.inputs[0])
    L(hm.outputs[0], hs.inputs["Hue"]); L(vm.outputs[0], hs.inputs["Value"])
    # 葉塊ごとの色むら: オブジェクト座標の低周波ノイズで明度/色相を揺らす(同じ木の中でも日向と日陰/若葉と古葉)
    texc2 = N("ShaderNodeTexCoord")
    nz = N("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.9; nz.inputs["Detail"].default_value = 2.0
    L(texc2.outputs["Object"], nz.inputs["Vector"])
    nm = N("ShaderNodeMix"); nm.data_type = "RGBA"; nm.blend_type = "MULTIPLY"; nm.inputs[0].default_value = 0.55
    tint = N("ShaderNodeValToRGB")
    tint.color_ramp.elements[0].color = (0.62, 0.7, 0.45, 1); tint.color_ramp.elements[1].color = (1.0, 0.96, 0.78, 1)
    L(nz.outputs["Fac"], tint.inputs[0]); L(tint.outputs[0], nm.inputs[7]); L(img.outputs["Color"], nm.inputs[6])
    L(nm.outputs[2], hs.inputs["Color"])
    cut = N("ShaderNodeMath"); cut.operation = "GREATER_THAN"; cut.inputs[1].default_value = d.get("cutout", 0.45)
    L(img.outputs["Alpha"], cut.inputs[0])
    bc = N("ShaderNodeMix"); bc.data_type = "RGBA"; bc.blend_type = "MULTIPLY"; bc.inputs[0].default_value = 1.0
    bc.inputs[7].default_value = (0.88, 0.88, 0.84, 1)                          # 葉の反射率上限(アトラスの明るい画素が白く飛ばない)
    L(hs.outputs["Color"], bc.inputs[6]); L(bc.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = d["rough"]
    tr = N("ShaderNodeBsdfTranslucent")
    tcol = N("ShaderNodeMix"); tcol.data_type = "RGBA"; tcol.blend_type = "MULTIPLY"; tcol.inputs[0].default_value = 1.0   # 透過色は葉色の暗め・彩度維持(白飛び防止)
    tcol.inputs[7].default_value = (0.55, 0.65, 0.3, 1)
    L(hs.outputs["Color"], tcol.inputs[6]); L(tcol.outputs[2], tr.inputs["Color"])
    mx = N("ShaderNodeMixShader")
    geo = N("ShaderNodeNewGeometry")                     # 裏面ほど透過光(Translucent)を強く: 逆光で葉が黄緑に透ける
    bk = N("ShaderNodeMath"); bk.operation = "MULTIPLY_ADD"; bk.inputs[1].default_value = 0.15; bk.inputs[2].default_value = 0.2       # 透過光の割合は最大0.35にクランプ
    L(geo.outputs["Backfacing"], bk.inputs[0]); L(bk.outputs[0], mx.inputs[0])
    L(bsdf.outputs[0], mx.inputs[1]); L(tr.outputs[0], mx.inputs[2])
    tp = N("ShaderNodeBsdfTransparent")
    cutmix = N("ShaderNodeMixShader")                 # alpha=0の所は完全に透明(影も落とさない)
    L(cut.outputs[0], cutmix.inputs[0])
    L(tp.outputs[0], cutmix.inputs[1]); L(mx.outputs[0], cutmix.inputs[2])
    for lk in list(out.inputs[0].links):
        nt.links.remove(lk)
    L(cutmix.outputs[0], out.inputs[0])


def mesh_to_bpy(name, mesh):
    mats = sorted(set(mesh.m))
    me = bpy.data.meshes.new(name)
    if not mesh.f:
        return me
    verts = np.array(mesh.v, dtype=np.float32).reshape(-1, 3)
    nloops = [len(f) for f in mesh.f]
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.ravel())
    loop_vi = np.fromiter((i for f in mesh.f for i in f), dtype=np.int32)
    me.loops.add(len(loop_vi))
    me.loops.foreach_set("vertex_index", loop_vi)
    starts = np.concatenate([[0], np.cumsum(nloops)[:-1]]).astype(np.int32)
    me.polygons.add(len(mesh.f))
    me.polygons.foreach_set("loop_start", starts)
    me.polygons.foreach_set("loop_total", np.array(nloops, dtype=np.int32))
    idx = {m: i for i, m in enumerate(mats)}
    me.polygons.foreach_set("material_index", np.array([idx[m] for m in mesh.m], dtype=np.int32))
    me.polygons.foreach_set("use_smooth", np.full(len(mesh.f), bool(getattr(mesh, "smooth", False)), dtype=bool))
    me.update(calc_edges=True)
    # UV(ボックス投影, メートル基準)
    uv = me.uv_layers.new(name="UVMap")
    P = verts[loop_vi]
    nrm = np.zeros((len(mesh.f), 3), dtype=np.float32)
    for k, f in enumerate(mesh.f):
        if len(f) >= 3:
            a, b, c = verts[f[0]], verts[f[1]], verts[f[2]]
            nrm[k] = np.cross(b - a, c - a)
    face_of_loop = np.repeat(np.arange(len(mesh.f)), nloops)
    ax = np.abs(nrm[face_of_loop]).argmax(axis=1)
    u = np.where(ax == 0, P[:, 1], P[:, 0]); v = np.where(ax == 2, P[:, 1], P[:, 2])
    UV = np.stack([u, v], axis=1).astype(np.float32)
    if any(x is not None for x in mesh.uv):
        for k, x in enumerate(mesh.uv):
            if x is not None:
                UV[starts[k]:starts[k] + nloops[k]] = np.array(x, dtype=np.float32)
    uv.data.foreach_set("uv", UV.ravel())
    for m in mats:
        me.materials.append(get_material(m))
    return me


TIME = "day"          # init_scene(time=...) が設定。夜/夕景では窓明かり・看板の発光を材質へ入れる
LIT = dict(day=0.0, dusk=0.28, night=0.5)    # 窓の点灯率
HAZE = dict(day=(11.1, 13.8, 15.0, 1), dusk=(4.7, 3.1, 1.8, 1), night=(0.033, 0.029, 0.042, 1))     # 水平線の空の放射輝度(probeで実測、方位平均): 遠景はこの色へ収束
HAZE_K = dict(day=1.6e-4, dusk=2.2e-4, night=1.0e-4)      # 消散係数[1/m]: 1kmで約15%、5kmで約55%が霞色へ


def _w_math(nt, op, a, b=None, clamp=False):
    """ワールド/材質ノードの Math を作って返す(a,b は socket か数値)"""
    n = nt.nodes.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _world_nodes(w, sun_dir, time, realism):
    nt = w.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    sky = N("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    d = Vector(sun_dir).normalized()
    el = math.asin(d.z)
    if realism and time == "dusk":
        el = math.radians(4.0)
    elif realism and time == "night":
        el = math.radians(-9.0)
    sky.sun_elevation = el
    sky.sun_rotation = math.atan2(d.x, d.y)
    sky.sun_size = math.radians(1.0)
    if realism:
        sky.air_density = 1.4 if time != "day" else 1.0
        sky.aerosol_density = 2.2 if time != "day" else 1.6        # 都市の霞
    bg = N("ShaderNodeBackground"); bg.inputs["Strength"].default_value = 1.0
    out = N("ShaderNodeOutputWorld")
    col = sky.outputs[0]
    if realism and time != "night":
        # 薄い雲: 方向を平面に投影して fBm、地平線付近は消す
        tc = N("ShaderNodeTexCoord")
        sep = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Generated"], sep.inputs[0])
        zz = _w_math(nt, "ADD", _w_math(nt, "MAXIMUM", sep.outputs[2], 0.0), 0.18)
        cmb = N("ShaderNodeCombineXYZ")
        L(_w_math(nt, "MULTIPLY", _w_math(nt, "DIVIDE", sep.outputs[0], zz), 0.45), cmb.inputs[0]); L(_w_math(nt, "MULTIPLY", _w_math(nt, "DIVIDE", sep.outputs[1], zz), 1.6), cmb.inputs[1])   # 筋雲(一方向に伸びる)
        nz = N("ShaderNodeTexNoise"); nz.noise_dimensions = "3D"
        nz.inputs["Scale"].default_value = 1.7; nz.inputs["Detail"].default_value = 7.0; nz.inputs["Roughness"].default_value = 0.6
        nz.inputs["Distortion"].default_value = 0.4
        L(cmb.outputs[0], nz.inputs["Vector"])
        rp = N("ShaderNodeMapRange"); rp.inputs[1].default_value = 0.40; rp.inputs[2].default_value = 0.66
        L(nz.outputs["Fac"], rp.inputs[0])
        fade = N("ShaderNodeMapRange"); fade.inputs[1].default_value = 0.03; fade.inputs[2].default_value = 0.35
        L(sep.outputs[2], fade.inputs[0])
        cf = _w_math(nt, "MULTIPLY", _w_math(nt, "MULTIPLY", rp.outputs[0], fade.outputs[0]), 0.8)
        cc = N("ShaderNodeMix"); cc.data_type = "RGBA"
        L(cf, cc.inputs[0]); L(sky.outputs[0], cc.inputs[6])
        gray = N("ShaderNodeMix"); gray.data_type = "RGBA"; gray.blend_type = "MULTIPLY"; gray.inputs[0].default_value = 1.0
        L(sky.outputs[0], gray.inputs[6]); gray.inputs[7].default_value = (0.78, 0.8, 0.84, 1) if time == "day" else (0.9, 0.7, 0.62, 1)
        L(gray.outputs[2], cc.inputs[7])
        col = cc.outputs[2]
    if realism:
        # 水平線より下は、水平線(仰角3.5°)の空の色で埋める: 暗い帯が出ず、遠景の霞(コンポジタ, HAZE色)へ自然につながる
        tc2 = N("ShaderNodeTexCoord")
        sz = N("ShaderNodeSeparateXYZ"); L(tc2.outputs["Generated"], sz.inputs[0])
        cz = N("ShaderNodeCombineXYZ"); L(sz.outputs[0], cz.inputs[0]); L(sz.outputs[1], cz.inputs[1]); L(_w_math(nt, "MAXIMUM", sz.outputs[2], 0.06), cz.inputs[2])
        L(cz.outputs[0], sky.inputs[0])
    if realism and time == "night":
        gl = N("ShaderNodeMix"); gl.data_type = "RGBA"; gl.inputs[0].default_value = 0.85     # 都市の光害: 紫がかった灰色の夜空
        L(col, gl.inputs[6]); gl.inputs[7].default_value = HAZE["night"]
        col = gl.outputs[2]
    L(col, bg.inputs[0]); L(bg.outputs[0], out.inputs[0])
    return sky


def init_scene(res=(1600, 900), samples=48, sun_dir=(0.45, -0.35, 0.8), gpu=True, time="day", realism=False):
    global TIME, REAL
    TIME = time if realism else "day"
    REAL = realism
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mat_cache.clear(); _img_cache.clear()
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = -2.9
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.cycles.device = "CPU"
    if gpu:
        try:
            pr = bpy.context.preferences.addons["cycles"].preferences
            for t in ("OPTIX", "CUDA"):
                try:
                    pr.compute_device_type = t
                    pr.get_devices()
                    devs = [d for d in pr.devices if d.type == t]
                    if devs:
                        for d in pr.devices:
                            d.use = d.type == t
                        sc.cycles.device = "GPU"
                        break
                except Exception:
                    continue
        except Exception:
            pass
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    _world_nodes(w, sun_dir, time, realism)
    if realism:
        enable_haze(time)
    if realism and time == "night":
        # 月明かり(弱い青白い太陽光)
        ld = bpy.data.lights.new("moon", "SUN"); ld.energy = 0.035; ld.color = (0.7, 0.8, 1.0); ld.angle = math.radians(1.5)
        lo = bpy.data.objects.new("moon", ld); lo.rotation_euler = (math.radians(38), 0, math.radians(-30))
        sc.collection.objects.link(lo)
    return sc


def enable_haze(time):
    """奥行きパスから 1-exp(-k z) だけ霞色へ混ぜる(空の画素=Depth巨大は除外)。ボリュームと違い無限遠の空を消さず、コストもほぼゼロ"""
    sc = bpy.context.scene
    sc.view_layers[0].use_pass_z = True
    ng = bpy.data.node_groups.new("haze", "CompositorNodeTree")
    sc.compositing_node_group = ng
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    N, L = ng.nodes.new, ng.links.new
    rl = N("CompositorNodeRLayers"); out = N("NodeGroupOutput")
    e = _w_math(ng, "POWER", 2.718281828, _w_math(ng, "MULTIPLY", rl.outputs["Depth"], -HAZE_K[time]))
    fac = _w_math(ng, "MULTIPLY", _w_math(ng, "SUBTRACT", 1.0, e), _w_math(ng, "LESS_THAN", rl.outputs["Depth"], 60000.0), True)
    mx = N("ShaderNodeMix"); mx.data_type = "RGBA"
    L(fac, mx.inputs[0]); L(rl.outputs["Image"], mx.inputs[6]); mx.inputs[7].default_value = HAZE[time]
    L(mx.outputs[2], out.inputs[0])


def estimate_exposure(target=0.16, lo=-3.6, hi=1.2):
    """低解像度・低サンプルの試し撮りの中央値(線形輝度)から露出[EV]を決める。谷間・高架下・夜でも潰れない/白飛びしない"""
    import os, tempfile
    from PIL import Image
    sc = bpy.context.scene
    save = (sc.render.resolution_percentage, sc.cycles.samples, sc.cycles.use_denoising, sc.view_settings.view_transform,
            sc.view_settings.look, sc.view_settings.exposure)
    sc.render.resolution_percentage = 20
    sc.cycles.samples = 8
    sc.cycles.use_denoising = False
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"; sc.view_settings.exposure = 0.0
    fd, tmp = tempfile.mkstemp(suffix=".png"); os.close(fd)
    render(tmp)
    a = np.asarray(Image.open(tmp).convert("RGB"), dtype=np.float32) / 255.0
    os.remove(tmp)
    (sc.render.resolution_percentage, sc.cycles.samples, sc.cycles.use_denoising, sc.view_settings.view_transform,
     sc.view_settings.look, sc.view_settings.exposure) = save
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    y = lin @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    yy = y[y < 0.95]
    m = float(np.percentile(yy if yy.size > 50 else y, 50))     # 空の飽和画素は除く
    ev = math.log2(target / max(m, 1e-4))
    return max(lo, min(hi, ev))


def add_camera(loc, target, lens=50):
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    cam.data.lens = lens
    cam.data.clip_end = 5000
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def add_plane(size, z=0.0, mat="ground", loc=(0, 0)):
    me = bpy.data.meshes.new("plane")
    h = size / 2
    me.from_pydata([(-h, -h, z), (h, -h, z), (h, h, z), (-h, h, z)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, c in enumerate([(-h, -h), (h, -h), (h, h), (-h, h)]):
        uv.data[i].uv = c
    me.materials.append(get_material(mat))
    o = bpy.data.objects.new("plane", me)
    o.location = (loc[0], loc[1], 0)
    bpy.context.scene.collection.objects.link(o)
    return o


def render(path):
    sc = bpy.context.scene
    sc.render.filepath = str(path)
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)


# ---- ギャラリー ----
def gallery(names, out, cols=4, res=(1800, 1000), samples=64, label=True, yaw=18, pitch=6):
    from .modules.library import get
    sc = init_scene(res, samples, sun_dir=(0.55, 0.5, 0.65))
    rng = random.Random(1)
    rows = math.ceil(len(names) / cols)
    maxw = max(__import__("vt.modules.registry", fromlist=["REG"]).REG[n]["W"] for n in names)
    maxh = max(__import__("vt.modules.registry", fromlist=["REG"]).REG[n]["H"] for n in names)
    sx, sz = maxw + 1.2, maxh + 1.2
    add_plane(400, 0.0, "ground")
    for i, n in enumerate(names):
        r, c = divmod(i, cols)
        me = mesh_to_bpy(n, get(n))
        o = bpy.data.objects.new(n, me)
        o.location = (-(c - (cols - 1) / 2) * sx, 0, (rows - 1 - r) * sz + 0.0)
        o["bvar"] = rng.random()
        bpy.context.scene.collection.objects.link(o)
        if label:
            cu = bpy.data.curves.new(n, "FONT"); cu.body = n; cu.size = 0.22; cu.align_x = "CENTER"
            t = bpy.data.objects.new(n + "_t", cu)
            t.location = (o.location.x, 0.5, o.location.z - 0.25 + 0.0)
            t.rotation_euler = (math.pi / 2, 0, math.pi)
            cu.materials.append(get_material("alu_black"))
            bpy.context.scene.collection.objects.link(t)
    # 壁の背後に薄い白壁(空抜け防止) と床
    W_all = cols * sx
    H_all = rows * sz
    dist = max(W_all * 0.95, H_all * 1.9) * 1.3 + 1.5 * max(maxw, maxh)
    cx, cz = 0, (rows - 1) * sz / 2 + maxh / 2
    cam_loc = (cx + dist * math.sin(math.radians(yaw)), dist * math.cos(math.radians(yaw)), cz + dist * math.sin(math.radians(pitch)))
    add_camera(cam_loc, (cx, 0, cz), lens=45)
    render(out)


# ---- 街区 ----
def _poly_obj(geom, z, mat, name):
    from .assemble import _tess
    m = __import__("vt.modules.geom", fromlist=["Mesh"]).Mesh()
    gs = [geom] if geom.geom_type == "Polygon" else [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
    for g in gs:
        if g.area < 0.5:
            continue
        for tri in _tess(g):
            pts = [(v.x, v.y, z) for v in tri]
            a, b, c = pts
            n = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            m.poly(pts if n > 0 else pts[::-1], mat)
    if not m.f:
        return
    o = bpy.data.objects.new(name, mesh_to_bpy(name, m))
    bpy.context.scene.collection.objects.link(o)
    return o


def build_district(builts, L, center, radius):
    """建物インスタンス + 簡易な地面/道路/水面"""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    from .layers import HIGHWAY_DEFAULT
    from .modules.library import get
    cp = Point(center)
    area = cp.buffer(radius * 1.6)
    # 水面
    add_plane(6000, -0.6, "water", loc=center)
    # 陸地 = 道路/建物/緑地の周辺を丸めた和集合
    parts = [f.geom.buffer(10) for f in L["roads"] if f.geom.intersects(area) and HIGHWAY_DEFAULT.get(f.tags["highway"], (0, 0, 0))[0] >= 1]
    parts += [f.geom.buffer(14) for f in L["buildings"] if f.geom.intersects(area)]
    parts += [f.geom.buffer(2) for f in L["green"] if f.geom.intersects(area)]
    land = unary_union(parts).buffer(12).buffer(-12).intersection(area.buffer(300))
    _poly_obj(land, 0.0, "ground", "land")
    # 道路(幅員デフォルト表から)
    rd = []
    for f in L["roads"]:
        t = f.tags
        if f.geom.intersects(area) and t["highway"] in HIGHWAY_DEFAULT and HIGHWAY_DEFAULT[t["highway"]][1] > 0 and t.get("layer") in (None, "0") and t.get("bridge") is None and t.get("tunnel") is None:
            lanes, wid, sw = HIGHWAY_DEFAULT[t["highway"]]
            rd.append(f.geom.buffer(wid / 2, cap_style=2))
    sw = []
    for f in L["roads"]:
        t = f.tags
        if f.geom.intersects(area) and t["highway"] in HIGHWAY_DEFAULT and HIGHWAY_DEFAULT[t["highway"]][2] > 0 and t.get("layer") in (None, "0") and t.get("bridge") is None and t.get("tunnel") is None:
            lanes, wid, s = HIGHWAY_DEFAULT[t["highway"]]
            sw.append(f.geom.buffer(wid / 2 + s, cap_style=2))
    if sw:
        _poly_obj(unary_union(sw).intersection(land), 0.02, "sidewalk", "sidewalk")
    if rd:
        _poly_obj(unary_union(rd).intersection(land), 0.04, "asphalt", "roads")
    # 建物
    n_inst = 0
    cache = {}
    col = bpy.context.scene.collection
    for b in builts:
        so = bpy.data.objects.new(f"shell{b.id}", mesh_to_bpy(f"shell{b.id}", b.shell))
        so["bvar"] = b.meta["bvar"]; col.objects.link(so)
        for i in b.insts:
            me = cache.get(i.name)
            if me is None:
                me = cache[i.name] = mesh_to_bpy(i.name, get(i.name))
            o = bpy.data.objects.new(i.name, me)
            o.location = (i.x, i.y, i.z); o.rotation_euler = (0, 0, i.rot); o.scale = (i.sx, i.sy, i.sz)
            o["bvar"] = b.meta["bvar"]
            col.objects.link(o)
            n_inst += 1
    return n_inst


def add_mesh_object(name, mesh):
    o = bpy.data.objects.new(name, mesh_to_bpy(name, mesh))
    bpy.context.scene.collection.objects.link(o)
    return o


def add_buildings(builts):
    """建物(モジュールのインスタンス)をシーンへ"""
    from .modules.library import get
    cache, col = {}, bpy.context.scene.collection
    for b in builts:
        so = bpy.data.objects.new(f"shell{b.id}", mesh_to_bpy(f"shell{b.id}", b.shell))
        so["bvar"] = b.meta["bvar"]; col.objects.link(so)
        for i in b.insts:
            me = cache.get(i.name)
            if me is None:
                me = cache[i.name] = mesh_to_bpy(i.name, get(i.name))
            o = bpy.data.objects.new(i.name, me)
            o.location = (i.x, i.y, i.z + b.meta.get("zbase", 0.0)); o.rotation_euler = (0, 0, i.rot); o.scale = (i.sx, i.sy, i.sz)
            o["bvar"] = b.meta["bvar"]; col.objects.link(o)


def _gn_group(name):
    """点→オブジェクトのインスタンス化(位置/回転/スケール/bvarは点属性)を行うGeometry Nodesグループ"""
    g = bpy.data.node_groups.new(name, "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    inp = g.nodes.new("NodeGroupInput")
    out = g.nodes.new("NodeGroupOutput")
    ip = g.nodes.new("GeometryNodeInstanceOnPoints")
    oi = g.nodes.new("GeometryNodeObjectInfo")
    oi.transform_space = "RELATIVE"
    oi.inputs["As Instance"].default_value = True
    rot = g.nodes.new("GeometryNodeInputNamedAttribute"); rot.data_type = "FLOAT_VECTOR"; rot.inputs["Name"].default_value = "rot"
    scl = g.nodes.new("GeometryNodeInputNamedAttribute"); scl.data_type = "FLOAT_VECTOR"; scl.inputs["Name"].default_value = "scl"
    L = g.links.new
    L(inp.outputs[0], ip.inputs["Points"]); L(oi.outputs["Geometry"], ip.inputs["Instance"])
    L(rot.outputs["Attribute"], ip.inputs["Rotation"]); L(scl.outputs["Attribute"], ip.inputs["Scale"])
    L(ip.outputs["Instances"], out.inputs[0])
    return g, oi


def add_instances_gn(insts, bvars=None):
    """大量インスタンス用: モジュールごとに1オブジェクト(点群)+Geometry Nodes のインスタンス化。個別オブジェクトを作るより桁違いに速くメモリも軽い。
    bvars=None なら0.5固定、listなら insts と同順の建物ごとの色相値"""
    from .modules.library import get
    by = {}
    for k, i in enumerate(insts):
        by.setdefault(i.name, []).append(k)
    col = bpy.context.scene.collection
    for name, idx in by.items():
        me = mesh_to_bpy(name, get(name))
        src = bpy.data.objects.new(name + "_src", me)
        col.objects.link(src)
        src.hide_render = True
        src.hide_viewport = True
        pts = bpy.data.meshes.new(name + "_pts")
        n = len(idx)
        pts.vertices.add(n)
        pts.vertices.foreach_set("co", np.array([(insts[k].x, insts[k].y, insts[k].z) for k in idx], dtype=np.float32).ravel())
        for attr, vals in (("rot", [(0.0, 0.0, insts[k].rot) for k in idx]), ("scl", [(insts[k].sx, insts[k].sy, insts[k].sz) for k in idx])):
            a = pts.attributes.new(attr, "FLOAT_VECTOR", "POINT")
            a.data.foreach_set("vector", np.array(vals, dtype=np.float32).ravel())
        a = pts.attributes.new("bvar", "FLOAT", "POINT")
        a.data.foreach_set("value", np.array([0.5 if bvars is None else bvars[k] for k in idx], dtype=np.float32))
        o = bpy.data.objects.new(name + "_inst", pts)
        col.objects.link(o)
        g, oi = _gn_group("gn_" + name)
        oi.inputs["Object"].default_value = src
        md = o.modifiers.new("inst", "NODES")
        md.node_group = g


def add_buildings_gn(builts):
    """建物(Built)の殻は個別メッシュ、モジュールはGeometry Nodesでまとめてインスタンス化(建物ごとのbvarを点属性で渡す)"""
    col = bpy.context.scene.collection
    allv, allb = [], []
    for b in builts:
        so = bpy.data.objects.new(f"shell{b.id}", mesh_to_bpy(f"shell{b.id}", b.shell))
        so["bvar"] = b.meta["bvar"]
        col.objects.link(so)
        allv += b.insts
        allb += [b.meta["bvar"]] * len(b.insts)
    add_instances_gn(allv, allb)


def add_instances(insts):
    """配置済みインスタンス(Inst)をそのままシーンへ(道路ファニチャ等)"""
    from .modules.library import get
    cache, col = {}, bpy.context.scene.collection
    for i in insts:
        me = cache.get(i.name)
        if me is None:
            me = cache[i.name] = mesh_to_bpy(i.name, get(i.name))
        o = bpy.data.objects.new(i.name, me)
        o.location = (i.x, i.y, i.z); o.rotation_euler = (0, 0, i.rot); o.scale = (i.sx, i.sy, i.sz)
        o["bvar"] = 0.5
        col.objects.link(o)
