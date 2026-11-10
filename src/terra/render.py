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


def terrain_object(doc: Document, name="terrain", box=None, stride=1, colors=None, splat=None, pad=0.35, normal_image=None, ij=None):
    """box=(x0,y0,x1,y1) ローカル座標でクリップ。colors: (ny,nx,4) 頂点色。splat: dict(w0=(ny,nx,4), w1=(ny,nx,4))。pad>0 は box なし時の外周延長"""
    import bpy
    if pad and not box:
        doc, colors, splat = _padded(doc, colors, splat, pad)
    g = doc.grid
    X, Y = g.xy()
    sl = (slice(0, g.ny, stride), slice(0, g.nx, stride))
    if ij is not None:
        sl = (slice(ij[2], ij[3], stride), slice(ij[0], ij[1], stride))
    elif box:
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
    uv.data.foreach_set("uv", np.stack([(x - g.x0) / (g.nx * g.res), (y - g.y0) / (g.ny * g.res)], -1).reshape(-1, 2)[quads.ravel()].astype(np.float32).ravel())

    def attr(nm, arr):
        a = me.color_attributes.new(nm, "FLOAT_COLOR", "POINT")
        a.data.foreach_set("color", arr[sl].reshape(-1, 4).astype(np.float32).ravel())
    if splat:
        attr("w0", splat["w0"])
        attr("w1", splat["w1"])
        attr("t0", splat["t0"])
        attr("t1", splat["t1"])
        from . import terrain_material
        mat = terrain_material.build(normal_image)
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


def splat_from_doc(doc):
    """splat_* 層 → 頂点属性 w0=(grass,litter,rock) w1=(scree,soil,alpine) と、地質による色 t0=(土の反射率, 苔) t1=(岩の色味, 地衣類)。splat が無ければ None"""
    if "splat_grass" not in doc.layers:
        return None
    from .geology.tables import ROCK_TINT, SOIL_ALBEDO
    L = [doc.layers["splat_" + n] for n in SPLAT]
    one = np.ones_like(L[0])
    zero = np.zeros_like(L[0])
    sd = doc.layers.get("soil_type")
    geo = doc.layers.get("geology")
    soil = SOIL_ALBEDO[sd] if sd is not None else np.broadcast_to(np.array([0.3, 0.22, 0.14], np.float32), L[0].shape + (3,))
    rock = ROCK_TINT[geo] if geo is not None else np.ones(L[0].shape + (3,), np.float32)
    return dict(w0=np.stack(L[:3] + [one], -1), w1=np.stack(L[3:] + [one], -1),
                t0=np.concatenate([soil, doc.layers.get("moss", zero)[..., None]], -1), t1=np.concatenate([rock, doc.layers.get("lichen", zero)[..., None]], -1))


def _desaturate(obj, sat=0.7, val=0.9):
    """オブジェクトの材質を複製し、Base Color の手前に Hue/Saturation を挟む(草の彩度を下げる。他の木と材質を共有しないよう複製)"""
    import bpy
    for i, m in enumerate(obj.data.materials):
        if m is None or not m.use_nodes:
            continue
        m2 = m.copy()
        nt = m2.node_tree
        for bs in [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"]:
            inp = bs.inputs["Base Color"]
            hs = nt.nodes.new("ShaderNodeHueSaturation")
            hs.inputs["Saturation"].default_value = sat
            hs.inputs["Value"].default_value = val
            if inp.links:
                src = inp.links[0].from_socket
                nt.links.new(src, hs.inputs["Color"])
            else:
                hs.inputs["Color"].default_value = inp.default_value
            nt.links.new(hs.outputs["Color"], inp)
        obj.data.materials[i] = m2


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
                if sk == "shrubs" and "grass" in an:
                    _desaturate(src)
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


def estimate_ev(target=0.2, pct=50):
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
    m = float(np.percentile(lin[lin.shape[0] // 2:], pct)) * 16.0
    return float(np.clip(math.log2(target / max(m, 1e-4)), -8.0, 3.0))


def finish(path, ev_target=0.2, pct=50):
    """露出自動決定→描画→写実ポスト(ビネット・粒子)"""
    import bpy
    from vt import render
    vs = bpy.context.scene.view_settings
    vs.look = "AgX - Base Contrast"
    vs.exposure = estimate_ev(ev_target, pct)
    render.set_glare_threshold(vs.exposure)
    os.makedirs(os.path.dirname(str(path)) or ".", exist_ok=True)
    render.render(path)
    if render.PHOTO:
        render.postprocess(path)
    return vs.exposure


def near_poses(doc: Document, seed=3):
    """近接レンダ用の 3 視点を地形から自動で選ぶ。slope: 急な裸地を斜め下から / forest: 林内の目線 / river: 川の脇。返り値 {名前: (loc, target)}"""
    g = doc.grid
    X, Y = g.xy()
    sl, hf = doc.layers["slope"], doc.heightfield()
    rng = np.random.default_rng(seed)
    m = 60.0 / g.res
    inner = np.zeros(g.shape, bool)
    inner[int(m):-int(m), int(m):-int(m)] = True
    zat = lambda x, y: float(hf.sample(np.array([x]), np.array([y]))[0])
    out = {}
    cand = np.flatnonzero((sl > 38) & (sl < 55) & inner & (doc.layers.get("splat_rock", sl * 0 + 1) > 0.25).ravel().reshape(g.shape))
    if len(cand):
        c = int(rng.choice(cand))
        cx, cy = X.ravel()[c], Y.ravel()[c]
        a = np.radians(doc.layers["aspect"].ravel()[c])
        d = np.array([np.sin(a), np.cos(a)])          # 下り方向
        loc = (cx + d[0] * 11, cy + d[1] * 11)
        out["slope"] = ((loc[0], loc[1], zat(*loc) + 2.0), (cx, cy, zat(cx, cy) + 1.5))
    can = doc.layers.get("canopy", sl * 0)
    cand = np.flatnonzero((can > 0.7) & (sl > 12) & (sl < 28) & inner)
    if len(cand):
        c = int(rng.choice(cand))
        cx, cy = X.ravel()[c], Y.ravel()[c]
        ang = rng.uniform(0, 6.28)
        tgt = (cx + 25 * np.cos(ang), cy + 25 * np.sin(ang))
        out["forest"] = ((cx, cy, zat(cx, cy) + 1.7), (tgt[0], tgt[1], zat(*tgt) + 3.0))
    cand = np.flatnonzero((sl > 6) & (sl < 30) & inner)
    if len(cand):
        cv = can.ravel()[cand]
        cand = cand[cv <= np.percentile(cv, 20)]            # 林冠の薄い所(地面がよく見える)
        c = int(rng.choice(cand))
        cx, cy = X.ravel()[c], Y.ravel()[c]
        tgt = (cx + 4.0, cy + 3.0)
        out["ground"] = ((cx, cy, zat(cx, cy) + 1.5), (tgt[0], tgt[1], zat(*tgt) + 0.2))
    rv = doc.layers.get("river", sl * 0)
    cand = np.flatnonzero((rv > 0) & (sl < 32) & inner)
    if len(cand):
        c = int(rng.choice(cand))
        cx, cy = X.ravel()[c], Y.ravel()[c]
        loc = (cx - 18, cy - 14)
        out["river"] = ((loc[0], loc[1], zat(*loc) + 2.0), (cx, cy, zat(cx, cy) + 1.0))
    return out


def terrain_parts(doc: Document, hole, stride=2, splat=None, pad=0.35):
    """near スポット(hole=(x0,y0,x1,y1), 粗い格子の頂点に合わせてある)を空けた far 地形を 4 枚の板で作る。縁の頂点は共有されひび割れない"""
    big, _, splat = _padded(doc, None, splat, pad)
    g = big.grid
    ih0, ih1 = int(round((hole[0] - g.x0) / g.res - 0.5)), int(round((hole[2] - g.x0) / g.res - 0.5))
    jh0, jh1 = int(round((hole[1] - g.y0) / g.res - 0.5)), int(round((hole[3] - g.y0) / g.res - 0.5))
    parts = [(0, ih0 + 1, 0, g.ny), (ih1, g.nx, 0, g.ny), (ih0, ih1 + 1, 0, jh0 + 1), (ih0, ih1 + 1, jh1, g.ny)]
    return [terrain_object(big, f"terrain_far{k}", stride=stride, splat=splat, pad=0, ij=p) for k, p in enumerate(parts)], big


def bake_normal_image(doc: Document, name="terrain_nrm"):
    """全解像度の高さから object-space の法線マップ(far 用の「法線ベイク」)。画像の (u,v) は格子全体の 0..1(行 0 = 南 = v 0)"""
    import bpy
    g = doc.grid
    gy, gx = np.gradient(doc.height.astype(np.float64), g.res)
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    px = np.concatenate([n * 0.5 + 0.5, np.ones(g.shape + (1,))], -1).astype(np.float32)
    im = bpy.data.images.new(name, g.nx, g.ny, alpha=False, float_buffer=False)
    im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(px.ravel())
    im.pack()
    return im


def add_roads(doc: Document):
    """道路の路面(アスファルト+白線)を曲面リボンで描く。橋・トンネルは module(road_furniture)が受け持つ"""
    import bpy
    from vt import render
    from .infra.roadmesh import road_mesh
    m = road_mesh(doc)
    if not m.f:
        return None
    o = bpy.data.objects.new("roads", render.mesh_to_bpy("roads", m))
    bpy.context.scene.collection.objects.link(o)
    return o


def road_poses(doc: Document):
    """道路の検証用カメラ: cut=切土法面(道路の手前から)/ bridge=最長の橋(斜め前から)/ portal=トンネル坑口(手前から)/ road=路面の目線"""
    hf = doc.heightfield()
    zat = lambda x, y: float(hf.sample(np.array([x]), np.array([y]))[0])
    out = {}
    roads = [(np.asarray(ln.coords), np.asarray(pr["z"]), pr) for ln, pr in doc.vectors.get("roads", [])]
    best = (0.0, None)
    for P, z, pr in roads:
        if pr["kind"] != "road":
            continue
        for i in range(2, len(P) - 8):
            d = P[i + 1] - P[i - 1]
            d /= max(np.hypot(*d), 1e-9)
            for sgn in (1, -1):
                n = np.array([d[1], -d[0]]) * sgn
                cut = zat(*(P[i] + n * 8.0)) - z[i]
                if cut > best[0]:
                    best = (cut, (P[i], d, n, z[i]))
    if best[1] is not None:
        c, d, n, zr = best[1]
        loc = c - d * 16                                        # 路面の上(道路の手前)から切土法面を見る
        out["road_cut"] = ((loc[0], loc[1], zr + 1.8), (c[0] + n[0] * 7, c[1] + n[1] * 7, zr + 3.5))
    br = [(pr["length"], P, z) for P, z, pr in roads if pr["kind"] == "bridge"]
    if br:
        L, P, z = max(br, key=lambda t: t[0])
        mid = P[len(P) // 2]
        d = P[-1] - P[0]
        d /= max(np.hypot(*d), 1e-9)
        n = np.array([d[1], -d[0]])
        loc = mid + n * max(25.0, L * 0.5) - d * 10
        out["road_bridge"] = ((loc[0], loc[1], zat(*loc) + 6.0), (mid[0], mid[1], float(z[len(z) // 2])))
    tn = doc.vectors.get("tunnels", [])
    if tn:
        ln, pr = max(tn, key=lambda t: t[1]["length"])
        P = np.asarray(ln.coords)
        d = P[3] - P[0]
        d /= max(np.hypot(*d), 1e-9)
        n = np.array([d[1], -d[0]])
        loc = P[0] - d * 28 + n * 8
        out["road_portal"] = ((loc[0], loc[1], zat(*loc) + 2.2), (P[0, 0], P[0, 1], pr["z"][0] + 2.5))
    if roads:
        allp = np.concatenate([P for P, _, _ in roads])
        c = (allp.min(0) + allp.max(0)) / 2
        ext = float(np.ptp(allp, axis=0).max())
        out["road_aerial"] = ((c[0] - ext * 0.5, c[1] - ext * 0.6, zat(*c) + ext * 0.45), (c[0], c[1], zat(*c) - 20))
        out["road_aerial2"] = ((c[0] + ext * 0.6, c[1] - ext * 0.2, zat(*c) + ext * 0.4), (c[0], c[1], zat(*c) - 20))
        P, z, pr = max(roads, key=lambda t: len(t[0]) if t[2]["kind"] == "road" else 0)
        i = len(P) // 3
        d = P[min(i + 6, len(P) - 1)] - P[i]
        d /= max(np.hypot(*d), 1e-9)
        out["road_surface"] = ((P[i, 0], P[i, 1], z[i] + 1.7), (P[i, 0] + d[0] * 40, P[i, 1] + d[1] * 40, z[min(i + 20, len(z) - 1)] + 1.5))
    return out
