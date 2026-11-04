"""追加モジュールをサイズ帯ごとにまとめてギャラリー画像へ。 uv run python scripts/render_extra_gallery.py [group ...]  (出力: out/render/extra/gal_<group>.png)"""
import os
import sys
from pathlib import Path

from vt import render
from vt.modules.library import REG

OUT = Path(__file__).resolve().parents[1] / "out/render/extra"
OUT.mkdir(parents=True, exist_ok=True)
EX = [n for n in REG if n.startswith("ex_")]
GROUPS = {
    "roofparts": ["ridge_cap_tile", "onigawara", "eave_gutter", "house_downpipe", "tv_antenna_yagi", "satellite_dish_wall", "roof_solar_house", "chimney_bath", "stone_lantern", "mailbox_post"],
    "gaitou": ["gate_mon_yakui", "gate_post_modern", "fence_blockwall", "fence_blockwall_low", "fence_itabei", "fence_ikegaki", "fence_stone_wall", "carport_alu", "shed_inaba", "bldg_kura", "apt_stair_side", "rural_rice_hasa"],
    "apt": ["apt_door_row", "apt_balcony_laundry", "win_jp_koshi", "win_jp_amado", "win_maker_pair", "door_maker_entry"],
    "rs_wall": ["rs_glass_front", "rs_glass_door_auto", "rs_showroom_glass", "rs_pachi_wall", "rs_family_wall", "rs_boxstore_wall", "rs_ramen_wall", "rs_drug_wall"],
    "rs_sign": ["rs_fascia_conv_a", "rs_fascia_drug_a", "rs_fascia_family_a", "rs_fascia_super_a", "rs_fascia_home_a", "rs_fascia_pachi_a", "rs_fascia_car_a", "rs_fascia_ramen_a", "rs_fascia_shop100_a", "rs_fascia_gs_a", "rs_fascia_udon", "rs_fascia_sushi"],
    "rs_pylon": ["rs_pylon_conv", "rs_pylon_drug", "rs_pylon_family", "rs_pylon_super", "rs_pylon_home", "rs_pylon_pachi", "rs_pylon_car", "rs_pylon_multi", "rs_pylon_tire", "gs_price_pole", "rs_nobori_flags", "rs_billboard_field"],
    "gs": ["gs_canopy", "gs_island", "gs_pump", "gs_vent_pipe", "gs_office_front", "pk_pay_machine", "pk_lock_plate", "pk_wheel_stop", "pk_gate_bar", "pk_mech_tower", "pk_sign_coin", "pk_carport_row"],
    "fac_wall": ["fac_wall_corr_gray", "fac_wall_corr_blue", "fac_wall_corr_green", "fac_wall_corr_cream", "fac_wall_panel_cream", "fac_window_band", "fac_door_steel", "fac_shutter_big", "fac_entry_office", "fac_sign_a", "fac_sign_d", "log_dock_leveler"],
    "fac_big": ["sp_fac_chimney_brick", "sp_fac_chimney_steel", "fac_dust_collector", "fac_silo", "fac_conveyor_gallery", "fac_gantry_crane", "log_trailer", "fac_vent_turbine"],
    "pl_tank": ["pl_tank_fixed_s", "pl_tank_fixed_m", "pl_tank_fixed_l", "pl_tank_floating_m", "pl_sphere_tank", "pl_gasholder"],
    "pl_tower": ["pl_column_a", "pl_column_b", "pl_column_c", "pl_flare_stack", "pl_stack_rw", "pl_cooling_tower"],
    "pl_small": ["pl_pipe_rack_a", "pl_pipe_rack_b", "pl_pipe_rack_low", "pl_pipe_rack_riser", "pl_pipe_loop", "pl_pipe_ground", "pl_valve_group", "pl_pump_skid", "pl_heat_exchanger", "pl_drum_horizontal", "pl_bund_wall", "pl_bund_stairs"],
    "pl_misc": ["pl_loading_rack", "pl_fire_monitor", "pl_pipeline_marker", "pl_pig_launcher", "pl_transformer", "pl_control_room", "pl_light_tower", "pl_stairs_tower"],
    "ex_a": EX[:12],
    "ex_b": EX[12:24],
    "ex_c": EX[24:36],
}
sel = sys.argv[1:] or list(GROUPS)
for g in sel:
    names = [n for n in GROUPS[g] if n in REG]
    if not names:
        continue
    cols = 4 if len(names) > 6 else 3
    render.gallery(names, OUT / f"gal_{g}.png", cols=cols, samples=int(os.environ.get("SPP", 32)), yaw=float(os.environ.get("YAW", 18)))
    print("wrote", g)
