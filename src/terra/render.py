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
    low, high = np.array([0.15, 0.24, 0.09]), np.array([0.33, 0.30, 0.18])
    c = low + (high - low) * t
    rock = np.clip((s[..., None] - 32) / 14, 0, 1)
    c = c * (1 - rock) + np.array([0.30, 0.27, 0.24]) * rock
    if "water_depth" in doc.layers:
        c = np.where(doc.layers["water_depth"][..., None] > 0.05, np.array([0.12, 0.13, 0.10]), c)
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


def splat_from_doc(doc):
    """splat_* 層(6 枚)→ 頂点属性 w0=(grass,litter,rock) w1=(scree,soil,alpine)。無ければ None"""
    if "splat_grass" not in doc.layers:
        return None
    L = [doc.layers["splat_" + n] for n in SPLAT]
    one = np.ones_like(L[0])
    return dict(w0=np.stack(L[:3] + [one], -1), w1=np.stack(L[3:] + [one], -1))


def add_scatter(doc: Document, protos: dict, cam=None, hi_dist=150.0):
    """doc.scatter の各エントリ → アセットごとに点群 1 オブジェクト+Geometry Nodes のインスタンス化(vt と同方式)。
    樹木は cam(x,y,z) から hi_dist 以内は高ポリ、外は低ポリ('名前|lo')。pitch は X 軸回り(崖パネルの傾き)"""
    import bpy
    from vt import render
    col = bpy.context.scene.collection
    n_inst = 0
    for sk, s in doc.scatter.items():
        names = [str(n) for n in s["assets"]]
        dist = np.hypot(s["pos"][:, 0] - cam[0], s["pos"][:, 1] - cam[1]) if cam is not None else np.zeros(len(s["pos"]))
        for ai, an in enumerate(names):
            base = s["kind"] == ai
            for lod in (0, 1):
                if lod and an + "|lo" not in protos:
                    continue
                sel = base & ((dist < hi_dist) if (an + "|lo" in protos and not lod) else (dist >= hi_dist) if lod else True)
                if not sel.any():
                    continue
                key = an + "|lo" if lod else an
                src = bpy.data.objects.new(f"{sk}_{key}_src", render.mesh_to_bpy(key, protos[key]))
                col.objects.link(src)
                src.hide_render = src.hide_viewport = True
                pts = bpy.data.meshes.new(f"{sk}_{key}_pts")
                n = int(sel.sum())
                pts.vertices.add(n)
                pts.vertices.foreach_set("co", s["pos"][sel].astype(np.float32).ravel())
                rot = np.zeros((n, 3), np.float32)
                rot[:, 0] = s["pitch"][sel] if "pitch" in s else 0
                rot[:, 2] = s["yaw"][sel]
                scl = np.repeat(s["scale"][sel].astype(np.float32)[:, None], 3, 1)
                for nm, v in (("rot", rot), ("scl", scl)):
                    a = pts.attributes.new(nm, "FLOAT_VECTOR", "POINT")
                    a.data.foreach_set("vector", v.ravel())
                a = pts.attributes.new("bvar", "FLOAT", "POINT")
                a.data.foreach_set("value", np.full(n, 0.5, np.float32))
                o = bpy.data.objects.new(f"{sk}_{key}", pts)
                col.objects.link(o)
                g, oi = render._gn_group(f"gn_{sk}_{key}")
                oi.inputs["Object"].default_value = src
                o.modifiers.new("inst", "NODES").node_group = g
                n_inst += n
    return n_inst


def _patch_textures():
    """vt.render._image が assets/terra/textures も探すようにする(vt のコードは変更しない)"""
    from pathlib import Path

    from vt import render
    if getattr(render, "_terra_patched", False):
        return
    orig, tdir = render._image, Path(__file__).resolve().parents[2] / "assets/terra/textures"

    def _image(name, noncolor=False):
        if (tdir / name).exists() and (name, noncolor) not in render._img_cache:
            import bpy
            im = bpy.data.images.load(str(tdir / name))
            if noncolor:
                im.colorspace_settings.name = "Non-Color"
            render._img_cache[(name, noncolor)] = im
        return orig(name, noncolor) if (name, noncolor) not in render._img_cache else render._img_cache[(name, noncolor)]
    render._image = _image
    render._terra_patched = True


def photo_setup(doc, res, samples, time="day"):
    from vt import render
    from . import modules  # noqa: F401  (rock_* 材質を vt.materials へ登録)
    _patch_textures()
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


def _water_material():
    import bpy
    m = bpy.data.materials.get("terra_water") or bpy.data.materials.new("terra_water")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.05, 0.11, 0.13, 1)
    b.inputs["Roughness"].default_value = 0.06
    b.inputs["IOR"].default_value = 1.33
    b.inputs["Transmission Weight"].default_value = 0.4
    return m


def water_geometry(doc: Document, min_width=3.0, lift=0.5):
    """川(幅付きリボン、中心の標高+lift で水平断面)と湖(湖セルの面、充填水位)の頂点・四角形"""
    hf = doc.heightfield()
    V, F = [], []
    for ln, pr in doc.vectors.get("rivers", []):
        xy = np.asarray(ln.coords)
        if len(xy) < 2:
            continue
        tan = np.gradient(xy, axis=0)
        tan /= np.maximum(np.linalg.norm(tan, axis=1, keepdims=True), 1e-9)
        nrm = np.stack([-tan[:, 1], tan[:, 0]], 1)
        w = max(pr["width"], min_width) / 2
        zc = hf.sample(xy[:, 0], xy[:, 1])
        zc = zc + lift
        b0 = len(V)
        for p, n, z in zip(xy, nrm, zc):
            V += [(p[0] + n[0] * w, p[1] + n[1] * w, z), (p[0] - n[0] * w, p[1] - n[1] * w, z)]
        F += [(b0 + 2 * i, b0 + 2 * i + 1, b0 + 2 * i + 3, b0 + 2 * i + 2) for i in range(len(xy) - 1)]
    if "lake" in doc.layers and doc.layers["lake"].any():
        g = doc.grid
        X, Y = g.xy()
        lk = doc.layers["lake"]
        jj, ii = np.nonzero(lk)
        zl = doc.layers["filled"][jj, ii] if "filled" in doc.layers else doc.height[jj, ii]
        h = g.res / 2
        for j, i, z in zip(jj, ii, zl):
            b0 = len(V)
            x, y = X[j, i], Y[j, i]
            V += [(x - h, y - h, z), (x + h, y - h, z), (x + h, y + h, z), (x - h, y + h, z)]
            F.append((b0, b0 + 1, b0 + 2, b0 + 3))
    return V, F


def add_water(doc: Document, **kw):
    import bpy
    V, F = water_geometry(doc, **kw)
    if not V:
        return None
    mat = _water_material()
    col = bpy.context.scene.collection
    me = bpy.data.meshes.new("water")
    me.from_pydata(V, [], F)
    me.materials.append(mat)
    o = bpy.data.objects.new("water", me)
    col.objects.link(o)
    return o


def add_far_plane(doc, z=None):
    """水平線までの遠景: 森の色の巨大平面(コンポジタの霞で空へ溶ける)。z=None は最低標高-5m"""
    import bpy
    z = float(doc.height.min()) - 5 if z is None else z
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


def estimate_ev(target=0.2):
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


def finish(path, ev_target=0.2):
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
