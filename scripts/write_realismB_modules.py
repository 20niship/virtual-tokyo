"""リアリズム強化Bで追加/変更したモジュール(車両・人・生活感)だけを assets/modules/*.usdc へ出力: uv run python scripts/write_realismB_modules.py"""
from vt import usd_out
from vt.modules.library import REG, get

PRE = ("lf_", "pedx_", "cyclist_", "scooter_", "car_", "truck_", "bus_", "motorbike", "bicycle_", "person_")
n = 0
for name, r in REG.items():
    if name.startswith(PRE):
        usd_out.write_module(name, get(name), r)
        n += 1
print("wrote", n)
