"""terra の module(岩・土・砂利)を全て usdc に書き出し、ポリゴン数・usdc サイズを集計して docs/terra/modules_geo.md を更新する。"""
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from terra import modules as M  # noqa: E402
from terra.geology.tables import ROCK_NAMES_JA, ROCKS, SOIL_NAMES_JA, SOILS  # noqa: E402
from terra.modules.lib_gravel import PATCH, SIZE  # noqa: E402
from terra.modules.lib_rock_geo import KINDS, STATES  # noqa: E402
from terra.modules.lib_soil import PARAM  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
names = [n for n in M.REG if re.match(r"(rock_(granite|andesite|sandstone|limestone|tuff|river)|soil_|gravel_)", n)]
faces, size = {}, {}
for n in names:
    m = M.build(n)
    faces[n] = len(m.f)
    size[n] = M.write_module(n).stat().st_size
tot_kb = sum(size.values()) // 1024
print(f"{len(names)} modules, usdc total {tot_kb} KB")


def stat(pat, near=True):
    ns = [n for n in names if re.fullmatch(pat + ("" if near else "_far"), n)]
    return (len(ns), int(sum(faces[n] for n in ns) / max(len(ns), 1)), int(sum(size[n] for n in ns) / max(len(ns), 1) / 1024))


L = ["# Terra 岩・土・砂利 module 一覧(地質)", "",
     "`scripts/terra_modules_build.py` が生成する(ポリゴン数・usdc サイズは実測の平均)。1 module 1 usdc(`assets/terra/modules/`、再生成できるのでコミットしない)。",
     "各 module は near(近接用)と `_far`(遠景用の低ポリ)を持つ。材質は PBR(UsdPreviewSurface)、テクスチャは手続き生成の小さな PNG(`assets/terra/textures/`、`scripts/terra_textures_geo.py`)。外部素材は使っていない。",
     f"全 {len(names)} module、usdc 合計 {tot_kb} KB。", "",
     "## 地質マスク(geology.zones)", "",
     "`geology`(岩種 ID)・`soil_type`(土種 ID)・`moss`/`lichen`(付着の強さ)を作る。岩種は大域ノイズでゾーン分け(既定の割合は目安。実データではない)、土種は岩種・標高・TWI・傾斜・樹冠・土壌深から決める。",
     "スプラット材質の土色(`t0` = 土の反射率)と岩の色味(`t1`)、scatter.rocks / scatter.ground の module 選択に使う。", "",
     "| ID | 岩種 | 土種(基本) |", "|---|---|---|"]
base_soil = {"granite": "マサ土", "andesite": "黒ボク土(高所は火山灰・スコリア)", "sandstone": "砂質土(湿ると粘土)", "limestone": "赤黄色土", "tuff": "粘土(緩斜面は黒ボク)"}
for i, (k, ja) in enumerate(zip(ROCKS, ROCK_NAMES_JA)):
    L.append(f"| {i} | {k} ({ja}) | {base_soil[k]} |")
L += ["", "上書き: TWI>10.5 かつ傾斜<12 度 = ぬかるみ、森林(樹冠>0.65)の緩斜面 = 腐植・落葉層。", "",
      "## 岩 module", "",
      "名前: `rock_<岩種>_<形>_<v>`(near)/ `..._far`。形: `boulder_s|m|l`(転石)/ `outcrop`(露頭)/ `cliff`(崖パネル 14m x 9m)/ `column`(柱状節理、安山岩のみ)。v = 状態プリセット。", "",
      "### 岩種", "", "| 岩種 | 特徴 | 形の傾向 | 材質(テクスチャ) | 丸み・切り落とし面数 |", "|---|---|---|---|---|"]
feat = {"granite": "粒状・明灰", "andesite": "暗灰・気孔(柱状節理)", "sandstone": "層理・ベージュ〜茶", "limestone": "溶食の凹み・白灰", "tuff": "多孔質・淡黄灰", "river": "丸い・灰茶緑の斑"}
for k, s in KINDS.items():
    L.append(f"| {k} ({s['ja']}) | {feat[k]} | {s['shape']} | {s['tex']} | rough {s['rough']}, cuts {s['cuts']}, 扁平 {s['flat']} |")
L += ["", "### 状態(module パラメータ)", "",
      "| v | 名前 | weathering | moss | lichen | chipped | grass | soil |", "|---|---|---|---|---|---|---|---|"]
for i, s in enumerate(STATES):
    L.append(f"| {i} | {s['name']}({s['ja']}) | {s['weathering']} | {s['moss']} | {s['lichen']} | {s['chipped']} | {s['grass']} | {s['soil']} |")
L += ["", "- weathering: 風化(角が取れる=切り落とし面と歪みが減る、下部に水染み材質)  - moss: 上向き面(法線 z>0.45)に苔材質を割り当てる割合  - lichen: 斑状の地衣類材質",
      "- chipped: 切り落とした面を欠けた新鮮面(明るい材質)にする割合  - grass: 根元の草の房(vt の草カード)の数  - soil: 底の周りの堆積土の裾(円盤)の大きさ", "",
      "### ポリゴン数(三角形・四角形の面数の平均)", "", "| 形 | 本数(near) | near 面数 | far 面数 | near usdc[KB] | far usdc[KB] |", "|---|---|---|---|---|---|"]
for form, pat in (("boulder_s", r"rock_(?!river)\w+?_boulder_s_\d"), ("boulder_m", r"rock_\w+?_boulder_m_\d"), ("boulder_l", r"rock_\w+?_boulder_l_\d"), ("outcrop", r"rock_\w+?_outcrop_\d"),
                  ("cliff", r"rock_\w+?_cliff_\d"), ("column", r"rock_andesite_column_\d")):
    a, b = stat(pat), stat(pat, False)
    L.append(f"| {form} | {a[0]} | {a[1]} | {b[1]} | {a[2]} | {b[2]} |")
L += ["", "## 土 module", "",
      "名前: `soil_<種>_patch_<0..2>`(3m 角の地面パッチ。near 24x24 分割 / far 6x6)、`soil_<種>_clod_<0..2>`(土塊の単体。散布用)。縁は高さ 0 へ落として地面になじませる。", "",
      "| 土種 | 色・粒度 | 形状の特徴 | 起伏[m] | patch near/far 面数 | clod near/far 面数 |", "|---|---|---|---|---|---|"]
shape = {"kuroboku": "細粒・黒褐、なだらかなこぶ", "redyellow": "赤褐・中粒", "clay": "灰黄・乾燥亀裂(多角形の溝)", "sandy": "明るい砂色・粗粒", "scoria": "黒〜赤・粗い凹凸と小さな噴石",
         "masa": "花崗岩風化砂・粗粒の淡褐", "humus": "暗褐・落ち葉片の盛り上がり", "mud": "濡れて暗い・水たまり(濡れ材質)・轍(v2)"}
for k, ja in zip(SOILS, SOIL_NAMES_JA):
    a, b = stat(rf"soil_{k}_patch_\d"), stat(rf"soil_{k}_patch_\d", False)
    c, d = stat(rf"soil_{k}_clod_\d"), stat(rf"soil_{k}_clod_\d", False)
    L.append(f"| {k} ({ja}) | {shape[k]} | | {PARAM[k][0]} | {a[1]} / {b[1]} | {c[1]} / {d[1]} |")
L += ["", "## 砂利・礫 module", "",
      "単体(散布用の 1 粒): `gravel_stone_<round|angular|flat>_<fine|medium|cobble>_<0..3>`(粒の半径 fine 1.2〜3cm / medium 3.5〜8cm / cobble(玉石)10〜22cm)。",
      "パッチ(混合サイズ): `gravel_patch_<種>_<0..2>`(基盤面 + 粒を並べた塊。2m 角、talus は 4m 角)。", "",
      "| パッチ | 内容 | 粒数(near) | near 面数 | far 面数 | near usdc[KB] |", "|---|---|---|---|---|---|"]
ja = {"sand": "砂(粒は基盤テクスチャのみ)", "fine": "細礫(丸)", "medium": "中礫(丸+細礫)", "cobble": "玉石(丸+中礫)", "river": "河原の礫(丸い玉石・中礫・扁平)", "crushed": "砕石(角)", "talus": "ガレ場(崖下の扇状堆積: 角礫・扁平礫、大小混在)", "ballast": "バラスト(道路・線路脇の均一な角礫)"}
for k in PATCH:
    a, b = stat(rf"gravel_patch_{k}_\d"), stat(rf"gravel_patch_{k}_\d", False)
    L.append(f"| {k} | {ja[k]} | {PATCH[k][2]} | {a[1]} | {b[1]} | {a[2]} |")
a, b = stat(r"gravel_stone_\w+_\d"), stat(r"gravel_stone_\w+_\d", False)
L += ["", f"単体礫: {a[0]} 種、near {a[1]} 面 / far {b[1]} 面(平均)。", "",
      "## 散布での使い方", "", "- `scatter.rocks`: 崖パネル(斜面 54 度超)・崖下の転石(扇状)・露頭・巨礫・ガレ(角礫)・川沿いの丸石。岩種は geology、状態は moss / lichen / TWI / 傾斜から選ぶ。",
      "- `scatter.ground`: 土パッチ(土種は soil_type)・河原の砂利/砂パッチ・ガレ場の礫パッチ。パッチは斜面に沿って傾ける。",
      "- near / far: render は樹木と同様、カメラから 150m 以内を near、外を `_far` に切り替える(`add_scatter` の `|lo`)。", ""]
(ROOT / "docs/terra/modules_geo.md").write_text("\n".join(L))
print("wrote docs/terra/modules_geo.md")
