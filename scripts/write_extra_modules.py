"""追加モジュール(田舎/ロードサイド/工業/高架細部)だけを assets/modules/*.usdc へ出力する。 uv run python scripts/write_extra_modules.py"""
from vt import usd_out
from vt.modules.library import REG, get

CATS = {"日本家屋", "戸建", "アパート", "外構", "農業", "屋根部材", "農村", "ロードサイド", "店舗看板", "ガソリンスタンド", "工場", "プラント", "高架"}
EXTRA = {"pk_pay_machine", "pk_lock_plate", "pk_wheel_stop", "pk_gate_bar", "pk_mech_tower", "pk_sign_coin", "pk_carport_row", "log_dock_leveler", "log_trailer"}
n = 0
for name, r in REG.items():
    if r["cat"] in CATS or name in EXTRA:
        usd_out.write_module(name, get(name), r)
        n += 1
print("wrote", n)
