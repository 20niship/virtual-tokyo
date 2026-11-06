"""Terra の Blender(Cycles)描画。vt.render(写実カメラ: フルサイズ換算の焦点距離・DoF・ブルーム・ビネット・粒子)を再利用する。
地形は Document から直接メッシュ化し、散布は vt と同じ Geometry Nodes のインスタンス化で描く。"""
from __future__ import annotations

import math
import os

import numpy as np

from .core.document import Document
from .masks.terrain import slope_aspect

SPLAT = ["grass", "litter", "rock", "scree", "soil", "alpine"]    # w0=RGB(grass,litter,rock) w1=RGB(scree,soil,alpine)


def default_colors(doc: Document):
    """生成済みの biome/splat が無い時の仮色: 標高・傾斜から"""
    z = doc.height
    s, _ = slope_aspect(z, doc.grid.res)
    t = np.clip((z - z.min()) / max(float(np.ptp(z)), 1.0), 0, 1)[..., None]
    low, mid, high = np.array([0.16, 0.26, 0.10]), np.array([0.30, 0.25, 0.14]), np.array([0.62, 0.60, 0.56])
    c = np.where(t < 0.5, low + (mid - low) * (t / 0.5), mid + (high - mid) * ((t - 0.5) / 0.5))
    rock = np.clip((s[..., None] - 30) / 15, 0, 1)
    c = c * (1 - rock) + np.array([0.32, 0.30, 0.28]) * rock
    return np.concatenate([c, np.ones_like(t)], -1)


def _padded(doc, colors, splat, frac):
    """スポット描画用の外周延長: 高さと材質重みを鏡像で frac(格子比)だけ外へ広げる(地平線が欠けて見えない)"""
    from .core.grid import Grid
    n = int(doc.grid.nx * frac)
    g = doc.grid
    d2 = Document(Grid(g.nx + 2 * n, g.ny + 2 * n, g.res, g.x0 - n * g.res, g.y0 - n * g.res, g.crs), doc.seed)
    pad = lambda a: np.pad(a, ((n, n), (n, n)) + ((0, 0),) * (a.ndim - 2), mode="reflect")
    d2.layers["height"] = pad(doc.height)
    if splat:
        splat = {k: pad(v) for k, v in splat.items()}
    elif colors is not None:
        colors = pad(colors)
    return d2, colors, splat


def terrain_object(doc: Document, name="terrain", box=None, stride=1, colors=None, splat=None, pad=0.35):
    """box=(x0,y0,x1,y1) ローカル座標でクリップ。colors: (ny,nx,4) 頂点色。splat: dict(w0=(ny,nx,4), w1=(ny,nx,4))。pad>0 は box なし時の外周延長"""
    import bpy
    if pad and not box:
        doc, colors, splat = _padded(doc, colors, splat, pad)
    g = doc.grid
    X, Y = g.xy()
    sl = (slice(0, g.ny, stride), slice(0, g.nx, stride))
    if box:
        i0, j0 = max(int((box[0] - g.x0) / g.res), 0), max(int((box[1] - g.y0) / g.res), 0)
        i1, j1 = min(int((box[2] - g.x0) / g.res), g.nx), min(int((box[3] - g.y0) / g.res), g.ny)
        sl = (slice(j0, j1, stride), slice(i0, i1, stride))
    z = doc.height[sl]
    ny, nx = z.shape
    x, y = X[sl], Y[sl]
    verts = np.stack([x, y, z], -1).reshape(-1, 3).astype(np.float32)
    ii = (np.arange(ny - 1)[:, None] * nx + np.arange(nx - 1)[None, :]).ravel()
    quads = np.stack([ii, ii + 1, ii + nx + 1, ii + nx], 1).astype(np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.ravel())
    me.loops.add(quads.size)
    me.loops.foreach_set("vertex_index", quads.ravel())
    me.polygons.add(len(quads))
    me.polygons.foreach_set("loop_start", np.arange(0, quads.size, 4, dtype=np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(quads), 4, np.int32))
    me.polygons.foreach_set("use_smooth", np.ones(len(quads), bool))
    me.update(calc_edges=True)
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", np.stack([x, y], -1).reshape(-1, 2)[quads.ravel()].astype(np.float32).ravel())

    def attr(nm, arr):
        a = me.color_attributes.new(nm, "FLOAT_COLOR", "POINT")
        a.data.foreach_set("color", arr[sl].reshape(-1, 4).astype(np.float32).ravel())
    if splat:
        attr("w0", splat["w0"])
        attr("w1", splat["w1"])
        mat = terrain_material_splat()
    else:
        attr("col", colors if colors is not None else default_colors(doc))
        mat = terrain_material_vcol()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def terrain_material_vcol():
    import bpy
    m = bpy.data.materials.new("terrain_vcol")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out, bs, at = nt.nodes.new("ShaderNodeOutputMaterial"), nt.nodes.new("ShaderNodeBsdfPrincipled"), nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "col"
    bs.inputs["Roughness"].default_value = 0.92
    nt.links.new(at.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(bs.outputs[0], out.inputs[0])
    return m


TEXROOT = None


def _tex_paths():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "assets"
    return {"grass": root / "textures/grass.png", "litter": root / "terra/textures/forest_litter.png", "rock": root / "terra/textures/rock_cliff.png",
            "scree": root / "textures/gravel.png", "soil": root / "textures/soil.png", "alpine": root / "terra/textures/alpine_turf.png"}


def terrain_material_splat():
    """スプラット材質: 6 層(w0/w1 の頂点属性が重み)を、約4m/11mの 2 サンプル(回転・スケール違い)+ボックス投影で混ぜる(タイル繰り返しを目立たなくする)。"""
    import bpy
    m = bpy.data.materials.new("terrain_splat")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out, bs = N("ShaderNodeOutputMaterial"), N("ShaderNodeBsdfPrincipled")
    L(bs.outputs[0], out.inputs[0])
    tc = N("ShaderNodeTexCoord")
    paths = _tex_paths()

    def sample(layer, scale, rot):
        mp = N("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1 / scale,) * 3
        mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot))
        L(tc.outputs["Object"], mp.inputs["Vector"])
        im = N("ShaderNodeTexImage")
        im.image = bpy.data.images.load(str(paths[layer]))
        im.projection = "BOX"
        im.projection_blend = 0.25
        L(mp.outputs[0], im.inputs["Vector"])
        return im.outputs["Color"]

    def mix(a, b, f):
        n = N("ShaderNodeMix")
        n.data_type = "RGBA"
        n.inputs[0].default_value = f
        L(a, n.inputs[6])
        L(b, n.inputs[7])
        return n.outputs[2]
    cols = {}
    for k in SPLAT:
        cols[k] = mix(sample(k, 4.0, 0), sample(k, 11.0, 37), 0.5)
    w0, w1 = N("ShaderNodeAttribute"), N("ShaderNodeAttribute")
    w0.attribute_name, w1.attribute_name = "w0", "w1"
    s0, s1 = N("ShaderNodeSeparateColor"), N("ShaderNodeSeparateColor")
    L(w0.outputs["Color"], s0.inputs[0])
    L(w1.outputs["Color"], s1.inputs[0])
    wts = list(s0.outputs[:3]) + list(s1.outputs[:3])
    acc = None
    for k, w in zip(SPLAT, wts):
        mul = N("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        L(cols[k], mul.inputs[6])
        wc = N("ShaderNodeCombineColor")
        for i in range(3):
            L(w, wc.inputs[i])
        L(wc.outputs[0], mul.inputs[7])
        if acc is None:
            acc = mul.outputs[2]
        else:
            add = N("ShaderNodeMix")
            add.data_type = "RGBA"
            add.blend_type = "ADD"
            add.inputs[0].default_value = 1.0
            L(acc, add.inputs[6])
            L(mul.outputs[2], add.inputs[7])
            acc = add.outputs[2]
    L(acc, bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.93
    return m


def add_scatter(doc: Document, protos: dict, kinds_per_scatter=None):
    """doc.scatter の各エントリ(pos,yaw,scale,kind)→ アセットごと 1 オブジェクト(点群)+GN インスタンス。
    protos: {asset 名: vt 形式の Mesh}。doc.scatter[k]['asset_idx'] が names 配列(doc.meta['assets'][k])の添字。"""
    import bpy
    from vt import render
    col = bpy.context.scene.collection
    n_inst = 0
    for sk, s in doc.scatter.items():
        names = doc.meta["assets"][sk]
        for ai, an in enumerate(names):
            sel = s["kind"] == ai
            if not sel.any():
                continue
            src = bpy.data.objects.new(f"{sk}_{an}_src", render.mesh_to_bpy(an, protos[an]))
            col.objects.link(src)
            src.hide_render = src.hide_viewport = True
            pts = bpy.data.meshes.new(f"{sk}_{an}_pts")
            n = int(sel.sum())
            pts.vertices.add(n)
            pts.vertices.foreach_set("co", s["pos"][sel].astype(np.float32).ravel())
            rot = np.zeros((n, 3), np.float32)
            rot[:, 2] = s["yaw"][sel]
            scl = s["scale"][sel].astype(np.float32)
            if scl.ndim == 1:
                scl = np.repeat(scl[:, None], 3, 1)
            for nm, v in (("rot", rot), ("scl", scl)):
                a = pts.attributes.new(nm, "FLOAT_VECTOR", "POINT")
                a.data.foreach_set("vector", v.ravel())
            a = pts.attributes.new("bvar", "FLOAT", "POINT")
            a.data.foreach_set("value", np.full(n, 0.5, np.float32))
            o = bpy.data.objects.new(f"{sk}_{an}", pts)
            col.objects.link(o)
            g, oi = render._gn_group(f"gn_{sk}_{an}")
            oi.inputs["Object"].default_value = src
            o.modifiers.new("inst", "NODES").node_group = g
            n_inst += n
    return n_inst


def photo_setup(doc, res, samples, time="day"):
    from vt import render
    render.HAZE_K["day"] = 5e-5      # 山岳は数 km 先まで見えるので都市用(1.6e-4)より薄く: 5km で約22%
    return render.init_scene(res, samples, sun_dir=(0.5, -0.45, 0.65), time=time, realism=True)


def make_camera(doc, view, box=None, lens=0, fstop=5.6, dof=True, seed=0, pose=None):
    """view: oblique(60mm 俯瞰) | ground(28mm 目線 1.7m)。box の中心を狙う。pose=(loc, target) で直接指定"""
    import bpy
    from vt import render
    g = doc.grid
    b = box or (g.x0, g.y0, g.x0 + g.nx * g.res, g.y0 + g.ny * g.res)
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    half = (b[2] - b[0]) / 2
    hf = doc.heightfield()

    def zat(x, y):
        return float(hf.sample(np.array([x]), np.array([y]))[0])
    if pose:
        loc, tgt = pose
        lens = lens or 28
    elif view == "oblique":
        lens = lens or 60
        tgt = (cx, cy, zat(cx, cy))
        d = half * 3.2 * (lens / 60.0) ** 0.5 * 1.1
        el = math.radians(32)
        loc = (cx, cy - d * math.cos(el), tgt[2] + d * math.sin(el) + 40)
    elif view == "ground":
        lens = lens or 28
        px, py = cx - half * 0.55, cy - half * 0.55
        loc = (px, py, zat(px, py) + 1.7)
        tgt = (cx, cy, zat(cx, cy) + 8)
    else:
        raise ValueError(view)
    cam = render.add_camera(loc, tgt, lens)
    cam.data.clip_end = 60000
    if dof:
        render.enable_dof(cam, fstop if view == "ground" else max(fstop, 8.0), 25.0 if view == "ground" else None)
    return cam


def add_far_plane(doc, z=None):
    """水平線までの遠景: 森の色の巨大平面(コンポジタの霞で空へ溶ける)。z=None は外周高さの下位 10%"""
    import bpy
    h = doc.height
    z = float(np.percentile(np.r_[h[0], h[-1], h[:, 0], h[:, -1]], 10)) - 5 if z is None else z
    me = bpy.data.meshes.new("far")
    me.from_pydata([(-6e4, -6e4, z), (6e4, -6e4, z), (6e4, 6e4, z), (-6e4, 6e4, z)], [], [(0, 1, 2, 3)])
    mat = bpy.data.materials.new("far")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.10, 0.15, 0.07, 1)
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    me.materials.append(mat)
    o = bpy.data.objects.new("far", me)
    o.location = (doc.grid.x0 + doc.grid.nx * doc.grid.res / 2, doc.grid.y0 + doc.grid.ny * doc.grid.res / 2, 0)
    bpy.context.scene.collection.objects.link(o)


def estimate_ev(target=0.28):
    """低解像度の試し撮り(EV-4 で飽和を避ける)の下半分(地面)の線形輝度の中央値から露出[EV]を決める。地形は日向が明るく vt の自動露出だと飽和する"""
    import tempfile
    import bpy
    from PIL import Image
    from vt import render
    sc = bpy.context.scene
    save = (sc.render.resolution_percentage, sc.cycles.samples, sc.cycles.use_denoising, sc.view_settings.view_transform, sc.view_settings.look, sc.view_settings.exposure)
    sc.render.resolution_percentage, sc.cycles.samples, sc.cycles.use_denoising = 20, 8, False
    sc.view_settings.view_transform, sc.view_settings.look, sc.view_settings.exposure = "Standard", "None", -4.0
    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    render.render(tmp)
    a = np.asarray(Image.open(tmp).convert("RGB"), np.float32) / 255.0
    os.remove(tmp)
    (sc.render.resolution_percentage, sc.cycles.samples, sc.cycles.use_denoising, sc.view_settings.view_transform, sc.view_settings.look, sc.view_settings.exposure) = save
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    m = float(np.median(lin[lin.shape[0] // 2:])) * 16.0
    return float(np.clip(math.log2(target / max(m, 1e-4)), -8.0, 2.0))


def finish(path, ev_target=0.28):
    """露出自動決定→描画→写実ポスト(ビネット・粒子)"""
    import bpy
    from vt import render
    vs = bpy.context.scene.view_settings
    vs.look = "AgX - Base Contrast"
    vs.exposure = estimate_ev(ev_target)
    render.set_glare_threshold(vs.exposure)
    os.makedirs(os.path.dirname(str(path)) or ".", exist_ok=True)
    render.render(path)
    if render.PHOTO:
        render.postprocess(path)
    return vs.exposure
