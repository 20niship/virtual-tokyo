"""仮想地形(侵食後)と実 DEM の統計比較: terra_stats.py <仮想 doc dir> <実 doc dir> [出力 png]。解像度は粗い方へ揃える。"""
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from terra.core import Document  # noqa: E402
from terra.core.grid import Grid  # noqa: E402
from terra.stats import coarsen, terrain_stats  # noqa: E402

va, re_ = Document.load(sys.argv[1]), Document.load(sys.argv[2])
res = max(va.grid.res, re_.grid.res)
out = {}
for nm, d in (("virtual", va), ("real", re_)):
    k = int(round(res / d.grid.res))
    z = coarsen(d.height.astype(np.float64), k) if k > 1 else d.height.astype(np.float64)
    g = Grid(z.shape[1], z.shape[0], res, d.grid.x0, d.grid.y0, d.grid.crs)
    out[nm] = terrain_stats(z, res, g)
keys = ["relief_m", "z_std", "slope_p10", "slope_p50", "slope_p90", "drainage_km_per_km2", "n_reaches", "max_order", "max_basin_km2", "psd_slope"]
print(f"{'metric':24s}{'virtual':>12s}{'real':>12s}")
for k in keys:
    print(f"{k:24s}{out['virtual'][k]:12.2f}{out['real'][k]:12.2f}")
fig, ax = plt.subplots(figsize=(6, 3.5))
x = np.arange(2.5, 90, 5)
ax.plot(x, out["virtual"]["slope_hist"], label="virtual (eroded)")
ax.plot(x, out["real"]["slope_hist"], label="real DEM (Okutama)")
ax.set_xlabel("slope [deg]")
ax.set_ylabel("density")
ax.legend()
fig.tight_layout()
fig.savefig(sys.argv[3] if len(sys.argv) > 3 else "out/terra/t2/stats.png", dpi=110)
