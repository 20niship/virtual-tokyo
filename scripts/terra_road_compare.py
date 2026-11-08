"""道路の前後比較: 道路ありの doc の道路視点を、道路なしの doc でも同じカメラで撮り、左右に並べた JPG を作る。
使い方: terra_road_compare.py <道路あり doc> <道路なし doc> <出力ディレクトリ>"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from terra import render as R  # noqa: E402
from terra.core import Document  # noqa: E402

with_dir, without_dir, out = sys.argv[1:4]
out = Path(out)
out.mkdir(parents=True, exist_ok=True)
poses = R.road_poses(Document.load(with_dir))
here = Path(__file__).resolve().parent
for name in ("road_cut", "road_bridge", "road_portal", "road_aerial2"):
    if name not in poses:
        continue
    (loc, tgt) = poses[name]
    pose = ",".join(f"{v:.2f}" for v in (*loc, *tgt))
    lens = "34" if "aerial" in name else "28"
    for tag, d in (("after", with_dir), ("before", without_dir)):
        subprocess.run([sys.executable, str(here / "terra_render.py"), d, "--view", "ground", "--detail", "legacy", "--stride", "2", "--lens", lens, "--no-dof",
                        "--pose", pose, "-o", str(out), "--name", f"cmp_{name}_{tag}", "--samples", "32"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([sys.executable, str(here / "terra_compare.py"), str(out / f"cmp_{name}_before_ground.png"), str(out / f"cmp_{name}_after_ground.png"),
                    str(out / f"compare_{name}.jpg"), "before (no road)", "after (road)"], check=True)
