"""人物アニメの動画: uv run python scripts/render_anim.py clips|city [--frames N] [--samples S] [--res WxH] [--spot NAME]"""
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
opt = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
MODE = args[0] if args else "clips"
OUT = ROOT / opt("--out", "out/render/videos")
FRAMES = opt("--frames", 240 if MODE == "clips" else 144)
SAMPLES = opt("--samples", 10)
RES = tuple(int(x) for x in opt("--res", "1280x720" if MODE == "clips" else "960x540").split("x"))
FPS = 24

CLIPS = ["walk", "walk_slow", "walk_formal", "jog", "run", "idle", "talk", "idle_hands", "idle_phone", "wave", "carry", "bike", "sit", "sit_talk", "push", "interact"]
CAST = [("office", 1), ("casual", 2), ("elder", 3), ("student", 4), ("casual", 5), ("office", 6), ("casual", 7), ("student", 8),
        ("elder", 9), ("casual", 10), ("worker", 1), ("casual", 11), ("casual", 12), ("casual", 13), ("worker", 2), ("office", 3)]


def encode(frames_dir, mp4, crf=23):
    """PNG 連番 → mp4。サイズが 10MB を超えたら CRF を上げて撮り直す"""
    for c in (crf, crf + 3, crf + 6, crf + 9):
        subprocess.run(["/usr/bin/ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames_dir / "%04d.png"), "-c:v", "libx264", "-crf", str(c),
                        "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)], check=True)
        if mp4.stat().st_size <= 10 * 1024 * 1024:
            return c
    return c


class Person:
    """1人分: フィット済みの服を cache に持ち、フレームごとに姿勢だけ変えて頂点を更新する"""

    def __init__(self, group, k, clip, phase0=0.0, collection=None, loc=(0, 0, 0), rot=0.0):
        import bpy
        from vt import humans as H
        from vt import humans_motion as HM
        from vt import render
        from vt.modules import lib_anny as A
        from vt.modules.geom import Mesh
        self.A, self.Mesh, self.clip, self.group, self.k = A, Mesh, clip, group, k
        self.cache = {}
        self.n = len(HM.load(clip)[0])
        self.phase0 = phase0
        spec = A.spec_of(group, k)
        b0 = H.build(spec, topology=A.LOD, posename="idle", cache=self.cache)
        self.ground = float(b0["v"][:, 2].min()) - 0.007
        m = self._mesh(0.0)
        self.me = render.mesh_to_bpy(f"p_{group}_{k}_{clip}", m)
        self.obj = bpy.data.objects.new(f"p_{group}_{k}_{clip}", self.me)
        self.obj.location = loc
        self.obj.rotation_euler = (0, 0, rot)
        (collection or bpy.context.scene.collection).objects.link(self.obj)
        self.height = max(v[2] for v in m.v)

    def _mesh(self, t):
        m = self.Mesh()
        ph = (self.phase0 + t * FPS / self.n) % 1.0
        self.A.build_mesh(m, self.group, self.k, self.A.LOD, pose_override=(self.clip, ph), cache=self.cache, ground=self.ground, decimate=False)
        return m

    def update(self, t):
        m = self._mesh(t)
        self.me.vertices.foreach_set("co", np.array(m.v, dtype=np.float32).ravel())
        self.me.update()


def run_clips():
    import bpy
    from bpy_extras.object_utils import world_to_camera_view
    from PIL import Image, ImageDraw, ImageFont

    from vt import render
    fd = OUT / "_frames_clips"
    fd.mkdir(parents=True, exist_ok=True)
    render.init_scene(RES, SAMPLES, sun_dir=(0.5, 0.45, 0.65), realism=True)
    render.add_plane(200, 0.0, "sidewalk")
    sp = 1.36
    ppl = []
    for i, (c, (g, k)) in enumerate(zip(CLIPS, CAST)):
        row, col = divmod(i, 8)
        x = (col - 3.5) * sp + (0.5 * sp if row else 0.0) - (0.25 * sp)
        ppl.append(Person(g, k, c, phase0=(i * 0.13) % 1.0, loc=(x, -row * 2.9, 0)))
    cam = render.add_camera((0, 13.4, 4.9), (0, -1.4, 0.9), 38)
    sc = bpy.context.scene
    sc.view_settings.look = "AgX - Base Contrast"
    sc.view_settings.exposure = render.estimate_exposure(0.17) - 0.9
    bpy.context.view_layer.update()
    lab = []
    for p in ppl:
        v = world_to_camera_view(sc, cam, p.obj.location)
        lab.append((v.x * RES[0], (1 - v.y) * RES[1], p.height))
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
    sc.render.image_settings.file_format = "PNG"
    for f in range(FRAMES):
        t = f / FPS
        for p in ppl:
            p.update(t)
        sc.render.filepath = str(fd / f"{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        im = Image.open(fd / f"{f:04d}.png").convert("RGB")
        d = ImageDraw.Draw(im)
        for i, ((x, y, hh), c) in enumerate(zip(lab, CLIPS)):
            w = d.textlength(c, font=font)
            yy = y + 4 if i < 8 else y - hh * 118 - 30
            d.rectangle((x - w / 2 - 4, yy, x + w / 2 + 4, yy + 22), fill=(20, 24, 28))
            d.text((x - w / 2, yy + 2), c, font=font, fill=(240, 240, 235))
        im.save(fd / f"{f:04d}.png")
        if f % 24 == 0:
            print("frame", f, flush=True)
    mp4 = OUT / "motion_clips.mp4"
    print("crf", encode(fd, mp4), mp4.stat().st_size / 1e6, "MB")


SPEED = dict(walk=1.35, walk_slow=0.95, walk_formal=1.4, jog=2.6, run=4.5, carry=1.3, push=1.0)
CARS = ("car_", "bus_", "truck_", "taxi")


def run_city():
    import bpy

    from vt import city, city_props, city_render, render
    from vt.modules import lib_anny as A
    from vt.modules.library import get
    sys.path.insert(0, str(ROOT / "scripts"))
    from _spots import SPOTS
    city_props.HUMANS = "anny"
    spot, view = opt("--spot", "west_intersection"), opt("--view", "g_intersection_1")
    dolly, car_speed = opt("--dolly", 1.0), opt("--car", 6.5)
    w = city.build_world(200, 200, center_ll=SPOTS[spot], mode="hybrid")
    w["props"] = city_props.build_props(w, life=True)
    tiles = city_render.make_tiles(w)
    v = next(x for x in city_render.pick_ground_views(w, per=4, margin=30) if x.name == view)
    cx, cy = v.cam[0], v.cam[1]
    fx, fy = v.tgt[0] - cx, v.tgt[1] - cy
    n = math.hypot(fx, fy)
    fx, fy = fx / n, fy / n
    radius = 150.0
    render.init_scene(RES, SAMPLES, sun_dir=(0.5, -0.45, 0.65), time=city_render.TIME, realism=city_render.REALISM)
    vs = bpy.context.scene.view_settings
    vs.look = "AgX - Medium High Contrast" if city_render.REALISM else "AgX - Base Contrast"
    from shapely.geometry import Point
    for name in ("g", "r", "t"):
        for (i, j), m in tiles[name].items():
            if w["tiler"].box(i, j).distance(Point(cx, cy)) < radius:
                render.add_mesh_object(f"{name}{i}_{j}", m)
    render.add_plane(80000, 0.0, "water", loc=w["center"])
    sel = []
    for key in ("furn", "veg", "props"):
        for ij, lst in tiles[key].items():
            if w["tiler"].box(*ij).distance(Point(cx, cy)) < radius:
                sel += [i for i in lst if (i.x - cx) ** 2 + (i.y - cy) ** 2 < radius * radius]
    ahead = lambda i, d, d0=3: d0 < (i.x - cx) * fx + (i.y - cy) * fy < d and abs(-(i.x - cx) * fy + (i.y - cy) * fx) < 0.7 * ((i.x - cx) * fx + (i.y - cy) * fy) + 3
    rng = random.Random(7)
    peds = [i for i in sel if i.name.startswith("anny_") and ahead(i, 38, 5)]
    cars = [i for i in sel if i.name.startswith(CARS) and ahead(i, 75, 11)]
    rng.shuffle(peds); rng.shuffle(cars)
    peds, cars = peds[:14], cars[:12]
    moving = {id(i) for i in peds} | {id(i) for i in cars}
    render.add_instances_gn([i for i in sel if id(i) not in moving])
    bl = [b for b in w["builts"] if (b.insts[0].x - cx) ** 2 + (b.insts[0].y - cy) ** 2 < (radius + 60) ** 2]
    render.add_buildings_gn(bl)
    actors = []
    for i in peds:
        _, g, k = i.name.split("_")
        clip, ph = A.pose_of(g, int(k))
        pr = Person(g, int(k), clip, phase0=ph, loc=(i.x, i.y, i.z), rot=i.rot)
        sp = SPEED.get(clip, 0.0)
        actors.append(("ped", pr, i, (-math.sin(i.rot) * sp, math.cos(i.rot) * sp)))
    for i in cars:
        o = bpy.data.objects.new(i.name, render.mesh_to_bpy(i.name, get(i.name)))
        o.location, o.rotation_euler = (i.x, i.y, i.z), (0, 0, i.rot)
        bpy.context.scene.collection.objects.link(o)
        sp = car_speed * rng.uniform(0.7, 1.2) if rng.random() < 0.65 else 0.0
        actors.append(("car", o, i, (-math.sin(i.rot) * sp, math.cos(i.rot) * sp)))
    cam = render.add_camera(v.cam, v.tgt, v.lens)
    off = (v.tgt[0] - v.cam[0], v.tgt[1] - v.cam[1], v.tgt[2] - v.cam[2])
    if city_render.REALISM:
        vs.exposure = render.estimate_exposure(city_render.EV_TARGET[city_render.TIME], hi=1.2)
    fd = OUT / f"_frames_city_{spot}"
    fd.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    sc.render.image_settings.file_format = "PNG"
    for f in range(FRAMES):
        t = f / FPS
        cam.location = (v.cam[0] + fx * dolly * t, v.cam[1] + fy * dolly * t, v.cam[2])
        for kind, obj, inst, (vx, vy) in actors:
            if kind == "ped":
                obj.update(t)
                obj.obj.location = (inst.x + vx * t, inst.y + vy * t, inst.z)
            else:
                obj.location = (inst.x + vx * t, inst.y + vy * t, inst.z)
        sc.render.filepath = str(fd / f"{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        if f % 12 == 0:
            print("frame", f, flush=True)
    mp4 = OUT / f"city_{spot}_{view}.mp4"
    print("crf", encode(fd, mp4), mp4.stat().st_size / 1e6, "MB")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    if MODE == "clips":
        run_clips()
    else:
        run_city()
