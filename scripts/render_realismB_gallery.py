"""リアリズム強化(B)のモジュールをグループごとにギャラリー画像へ。 uv run python scripts/render_realismB_gallery.py [group ...] (出力: out/render/realismB/gal_<group>.png)
環境変数: SPP(サンプル数) YAW(ヨー角) ROUND(サブフォルダ名)"""
import os
import sys
from pathlib import Path

from vt import render
from vt.modules.library import REG

OUT = Path(__file__).resolve().parents[1] / "out/render/realismB" / os.environ.get("ROUND", "gallery")
OUT.mkdir(parents=True, exist_ok=True)
P = lambda pre: [n for n in REG if n.startswith(pre)]
GROUPS = {
    "cars": ["car_sedan_white", "car_taxi", "car_hatch_pearl", "car_suv_navy", "car_minivan_silver", "car_kei_sky", "car_wagon_gray", "car_van_white", "car_keivan_yellow", "truck_kei_white", "car_sedan_wine", "car_suv_black"],
    "big": ["truck_box_white", "truck_dump", "bus_city", "bus_city_blue", "bus_coach", "bus_mini"],
    "two": ["scooter_white", "scooter_rider_0", "scooter_rider_1", "bicycle_mama", "bicycle_silver", "bicycle_black_basket", "bicycle_abandoned", "cyclist_commuter", "cyclist_student", "cyclist_mama", "motorbike", "bicycle_red"],
    "ped_a": P("pedx_office_") + P("pedx_woman_"),
    "ped_b": P("pedx_casual_") + P("pedx_phone_"),
    "ped_c": P("pedx_elder_") + P("pedx_parasol_") + P("pedx_student_") + P("pedx_kid_"),
    "life_a": P("lf_vend") + P("lf_ac") + P("lf_laundry") + P("lf_pot"),
    "life_b": P("lf_bike") + P("lf_garb") + P("lf_nobori") + P("lf_chou") + P("lf_stand"),
    "life_c": P("lf_scaf") + P("lf_hoard") + P("lf_barri") + P("lf_cone") + P("lf_mail"),
    "life_d": P("lf_down") + P("lf_hyd") + P("lf_fire") + P("lf_pole") + P("lf_curb") + P("lf_planter"),
}
sel = sys.argv[1:] or list(GROUPS)
for g in sel:
    names = GROUPS[g]
    if not names:
        continue
    cols = {"cars": 4, "big": 3, "two": 4}.get(g, 6 if g.startswith("ped") else 5)
    res = (2000, 1100) if g.startswith(("ped", "life")) else (1800, 1000)
    render.gallery(names, OUT / f"gal_{g}.png", cols=cols, res=res, samples=int(os.environ.get("SPP", 32)), yaw=float(os.environ.get("YAW", 22)))
    print("wrote", g)
