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
        attr = N("ShaderNodeAttribute"); attr.attribute_type = "OBJECT"; attr.attribute_name = "bvar"
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
        bsdf.inputs["Emission Strength"].default_value = d["emit"][1]
    if d.get("glass"):
        bsdf.inputs["Transmission Weight"].default_value = 1.0
        bsdf.inputs["IOR"].default_value = 1.5
        bsdf.inputs["Base Color"].default_value = base
        if colsock:
            L(colsock, bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.02
        mat.use_backface_culling = False
    elif d.get("interior"):
        # 室内: カーテン色をランダム、2割は点灯(夜用)
        ramp = N("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = "CONSTANT"
        cs = ["#2a2622", "#b8b2a0", "#6d7b88", "#d8d4c8", "#4a3d36", "#7a6a5a"]
        while len(ramp.color_ramp.elements) < len(cs):
            ramp.color_ramp.elements.new(0.5)
        for i, c in enumerate(cs):
            ramp.color_ramp.elements[i].position = i / len(cs) + 0.001
            ramp.color_ramp.elements[i].color = _rgb(c)
        ramp.color_ramp.elements[0].position = 0.0
        L(objinfo.outputs["Random"], ramp.inputs[0])
        L(ramp.outputs[0], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.9
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
        if colsock:
            L(colsock, mix.inputs[6])
        else:
            mix.inputs[6].default_value = base
        L(mix.outputs[2], bsdf.inputs["Base Color"])
        rough = d["rough"]
        bsdf.inputs["Roughness"].default_value = rough
        if d.get("dirt"):
            m2 = N("ShaderNodeMapRange"); m2.inputs[3].default_value = max(0.0, rough - 0.12); m2.inputs[4].default_value = min(1.0, rough + 0.2)
            L(noise.outputs["Fac"], m2.inputs[0])
            L(m2.outputs[0], bsdf.inputs["Roughness"])
        bsdf.inputs["Metallic"].default_value = d["metal"]
        if d.get("bump"):
            bump = N("ShaderNodeBump"); bump.inputs["Strength"].default_value = min(1.0, d["bump"] * 0.5)
            bump.inputs["Distance"].default_value = 0.01
            L(fine.outputs["Fac"], bump.inputs["Height"])
            L(bump.outputs[0], bsdf.inputs["Normal"])
        if d.get("wood"):
            wv = N("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 6; wv.inputs["Distortion"].default_value = 4
            L(texc.outputs["Object"], wv.inputs["Vector"])
            wm = N("ShaderNodeMix"); wm.data_type = "RGBA"; wm.blend_type = "MULTIPLY"; wm.inputs[0].default_value = 0.5
            L(mix.outputs[2], wm.inputs[6]); L(wv.outputs["Color"], wm.inputs[7])
            L(wm.outputs[2], bsdf.inputs["Base Color"])
    if not d.get("glass"):
        bsdf.inputs["Metallic"].default_value = d["metal"]
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
        if d.get("alpha"):
            alpha = img.outputs["Alpha"]
        else:
            alpha = None
        if d.get("bump"):
            bw = N("ShaderNodeRGBToBW"); L(img.outputs["Color"], bw.inputs[0])
            bp = N("ShaderNodeBump"); bp.inputs["Strength"].default_value = min(1.0, d["bump"] * 0.5); bp.inputs["Distance"].default_value = 0.02
            L(bw.outputs[0], bp.inputs["Height"]); L(bp.outputs[0], bsdf.inputs["Normal"])
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
    bsdf.inputs["Roughness"].default_value = d["rough"]
    bsdf.inputs["Metallic"].default_value = d["metal"]


def mesh_to_bpy(name, mesh):
    mats = sorted(set(mesh.m))
    me = bpy.data.meshes.new(name)
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
    me.polygons.foreach_set("use_smooth", np.zeros(len(mesh.f), dtype=bool))
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


def init_scene(res=(1600, 900), samples=48, sun_dir=(0.45, -0.35, 0.8), gpu=True):
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
    nt = w.node_tree
    nt.nodes.clear()
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    d = Vector(sun_dir).normalized()
    sky.sun_elevation = math.asin(d.z)
    sky.sun_rotation = math.atan2(d.x, d.y)
    sky.sun_size = math.radians(1.0)
    bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sky.outputs[0], bg.inputs[0]); nt.links.new(bg.outputs[0], out.inputs[0])
    return sc


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
    dist = max(W_all * 0.95, H_all * 1.9) * 1.3 + 4
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
