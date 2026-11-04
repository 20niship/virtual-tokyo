"""植栽: 樹種ライブラリ → モジュールUSD(.usdc) → ギャラリー/配置シーンのレンダ。
uv run python scripts/build_vegetation.py [gallery] [usd] [scene]   (引数なし=すべて)
環境変数 SPP=サンプル数"""
import math
import os
import sys
from pathlib import Path

from vt import render, usd_out
from vt.modules.library import REG

OUT = Path(__file__).resolve().parents[1] / "out/render"
OUT.mkdir(parents=True, exist_ok=True)
SPP = int(os.environ.get("SPP", 48))
args = set(sys.argv[1:]) or {"gallery", "usd", "scene"}

SETS = {
    "street_summer": [f"veg_{s}_m_0_summer" for s in ("ichou", "keyaki", "platanus", "sakura", "tokaikaede", "hanamizuki")] + ["veg_kusunoki_m_0_summer", "veg_shii_m_0_summer"],
    "seasons_ichou": [f"veg_ichou_m_0_{s}" for s in ("spring", "summer", "autumn_y", "winter")] + [f"veg_sakura_m_0_{s}" for s in ("spring", "summer", "autumn_r", "winter")],
    "sizes_keyaki": [f"veg_keyaki_{z}_{s}_summer" for z in ("s", "m", "l") for s in (0, 1)],
    "special": ["veg_kuromatsu_m_0_summer", "veg_kuromatsu_l_1_summer", "veg_yanagi_m_0_summer", "veg_yashi_canary_m_0_summer", "veg_yashi_washingtonia_m_0_summer", "veg_shuro_m_0_summer"],
    "shrubs": ["veg_azalea_0_r8", "veg_azalea_1_r8", "veg_azalea_2_r8", "veg_azalea_green_r8", "veg_tsuge_dome_r8", "veg_hydrangea_0_r75", "veg_hydrangea_1_r75",
               "veg_hedge_mid_0", "veg_hedge_tall_1", "veg_hedge_low_0", "veg_flowerbed_0", "veg_flowerbed_1", "veg_groundcover_ivy", "veg_grass_tuft_0", "veg_grass_plume_0", "veg_ivy_wall_2x2",
               "veg_tree_pit_grating", "veg_tree_ring_curb"],
}

if "usd" in args:
    n = 0
    for name, r in REG.items():
        if r["cat"] == "植栽":
            from vt.modules.library import get
            usd_out.write_module(name, get(name), r)
            n += 1
    print("wrote", n, "vegetation module usdc")

def build_scene_data(radius=700, center_ll=(139.7745, 35.6265)):
    from shapely.geometry import Point

    from vt import bridges, furniture, ground, roads
    from vt.geo import to_local
    from vt.layers import load, load_extra
    from vt.world import Terrain
    L = load()
    X = load_extra()
    bridges.install(L)
    c = to_local(*center_ll)
    area = Point(c).buffer(radius)
    T = Terrain()
    land = ground.land_polygon(L, area)
    W = dict(area=area, land=land, zf=T, center=c)
    g = ground.build_ground(L, W)
    r, edges, info = roads.build_roads(L, W)
    furn = furniture.build_furniture(L, W, edges, info, roads.CFG, X=X)
    return L, X, W, edges, info, g, r, furn, c


if "scene" in args or "veg" in args:
    import bpy  # noqa: F401
    from vt import vegetation
    L, X, W, edges, info, g, r, furn, c = build_scene_data()
    veg = vegetation.build_vegetation(L, X, W, edges, info, roads_cfg := __import__("vt.roads", fromlist=["CFG"]).CFG, seed=3, avoid=furn)
    print("vegetation", vegetation.build_vegetation.stats)
    usd_out.write_vegetation(veg)
    if "scene" in args:
        from vt.modules.library import get

        def view(name, cam, tgt, lens, near=260):
            render.init_scene((1920, 1080), SPP, sun_dir=(0.5, -0.45, 0.65))
            render.add_mesh_object("ground", g); render.add_mesh_object("roads", r)
            from vt import ground as gr
            render.add_mesh_object("water", gr.water_mesh(W))
            render.add_instances([i for i in furn if math.dist((i.x, i.y), tgt[:2]) < near])
            cache, col = {}, __import__("bpy").context.scene.collection
            bpy = __import__("bpy")
            for i in veg:
                if math.dist((i.x, i.y), tgt[:2]) > near:
                    continue
                me = cache.get(i.name) or cache.setdefault(i.name, render.mesh_to_bpy(i.name, get(i.name)))
                o = bpy.data.objects.new(i.name, me)
                o.location = (i.x, i.y, i.z); o.rotation_euler = (0, 0, i.rot); o.scale = (i.sx, i.sy, i.sz)
                o["bvar"] = ((i.x * 12.9898 + i.y * 78.233) % 1.0)
                col.objects.link(o)
            render.add_camera(cam, tgt, lens)
            render.render(OUT / f"{name}.png")
        # 並木のある道路と公園(密度の高い所)を自動選択
        import collections
        dens = collections.Counter((int(i.x // 60), int(i.y // 60)) for i in veg if i.name.startswith("veg_") and "_tree_" not in i.name)
        (kx, ky), _ = dens.most_common(1)[0]
        tx, ty = kx * 60 + 30, ky * 60 + 30
        z0 = W["zf"](tx, ty)
        view("veg_scene_street", (tx - 55, ty - 40, z0 + 2.0), (tx, ty, z0 + 4), 32)
        view("veg_scene_aerial", (tx - 120, ty - 150, z0 + 70), (tx, ty, z0), 35, near=320)

if "gallery" in args:
    for key, names in SETS.items():
        render.gallery(names, OUT / f"veg_{key}.png", cols=4 if len(names) > 6 else 3, samples=SPP, label=True)
        print("wrote", OUT / f"veg_{key}.png")
