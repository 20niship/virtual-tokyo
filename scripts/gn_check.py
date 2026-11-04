"""GN インスタンス化の動作確認: uv run python scripts/test_gn.py out.png"""
import sys

from vt import render
from vt.assemble import Inst

render.init_scene((900, 500), 24, sun_dir=(0.5, 0.45, 0.7))
render.add_plane(100, 0.0, "asphalt")
ins = [Inst("wall_spray", i * 4.0, 0, 0, 0.0) for i in range(6)] + [Inst("car_sedan_white", i * 5.0, -6, 0, 0.3 * i) for i in range(4)]
render.add_instances_gn(ins, [i / 6 for i in range(6)] + [0.5] * 4)
render.add_camera((10, -22, 5), (10, 0, 1.5), 40)
render.render(sys.argv[1])
