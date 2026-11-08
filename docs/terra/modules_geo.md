# Terra 岩・土・砂利 module 一覧(地質)

`scripts/terra_modules_build.py` が生成する(ポリゴン数・usdc サイズは実測の平均)。1 module 1 usdc(`assets/terra/modules/`、再生成できるのでコミットしない)。
各 module は near(近接用)と `_far`(遠景用の低ポリ)を持つ。材質は PBR(UsdPreviewSurface)、テクスチャは手続き生成の小さな PNG(`assets/terra/textures/`、`scripts/terra_textures_geo.py`)。外部素材は使っていない。
全 448 module、usdc 合計 29346 KB。

## 地質マスク(geology.zones)

`geology`(岩種 ID)・`soil_type`(土種 ID)・`moss`/`lichen`(付着の強さ)を作る。岩種は大域ノイズでゾーン分け(既定の割合は目安。実データではない)、土種は岩種・標高・TWI・傾斜・樹冠・土壌深から決める。
スプラット材質の土色(`t0` = 土の反射率)と岩の色味(`t1`)、scatter.rocks / scatter.ground の module 選択に使う。

| ID | 岩種 | 土種(基本) |
|---|---|---|
| 0 | granite (花崗岩) | マサ土 |
| 1 | andesite (安山岩/玄武岩) | 黒ボク土(高所は火山灰・スコリア) |
| 2 | sandstone (砂岩/泥岩) | 砂質土(湿ると粘土) |
| 3 | limestone (石灰岩) | 赤黄色土 |
| 4 | tuff (凝灰岩) | 粘土(緩斜面は黒ボク) |

上書き: TWI>10.5 かつ傾斜<12 度 = ぬかるみ、森林(樹冠>0.65)の緩斜面 = 腐植・落葉層。

## 岩 module

名前: `rock_<岩種>_<形>_<v>`(near)/ `..._far`。形: `boulder_s|m|l`(転石)/ `outcrop`(露頭)/ `cliff`(崖パネル 14m x 9m)/ `column`(柱状節理、安山岩のみ)。v = 状態プリセット。

### 岩種

| 岩種 | 特徴 | 形の傾向 | 材質(テクスチャ) | 丸み・切り落とし面数 |
|---|---|---|---|---|
| granite (花崗岩) | 粒状・明灰 | round | rock_granite.png | rough 0.13, cuts 5, 扁平 0.78 |
| andesite (安山岩/玄武岩) | 暗灰・気孔(柱状節理) | angular | rock_basalt.png | rough 0.2, cuts 10, 扁平 0.72 |
| sandstone (砂岩/泥岩) | 層理・ベージュ〜茶 | slab | rock_sandstone.png | rough 0.12, cuts 8, 扁平 0.5 |
| limestone (石灰岩) | 溶食の凹み・白灰 | karst | rock_limestone.png | rough 0.22, cuts 6, 扁平 0.7 |
| tuff (凝灰岩) | 多孔質・淡黄灰 | soft | rock_tuff.png | rough 0.2, cuts 4, 扁平 0.75 |
| river (川原の丸石) | 丸い・灰茶緑の斑 | round | rock_river.png | rough 0.06, cuts 0, 扁平 0.62 |

### 状態(module パラメータ)

| v | 名前 | weathering | moss | lichen | chipped | grass | soil |
|---|---|---|---|---|---|---|---|
| 0 | fresh(新鮮・欠け) | 0.05 | 0.0 | 0.0 | 0.8 | 0 | 0.0 |
| 1 | weathered(風化・地衣類) | 0.6 | 0.1 | 0.55 | 0.1 | 0 | 0.2 |
| 2 | mossy(苔むし・草) | 0.7 | 0.9 | 0.15 | 0.0 | 3 | 0.6 |
| 3 | stained(水染み・汚れ) | 0.5 | 0.25 | 0.1 | 0.15 | 1 | 0.3 |

- weathering: 風化(角が取れる=切り落とし面と歪みが減る、下部に水染み材質)  - moss: 上向き面(法線 z>0.45)に苔材質を割り当てる割合  - lichen: 斑状の地衣類材質
- chipped: 切り落とした面を欠けた新鮮面(明るい材質)にする割合  - grass: 根元の草の房(vt の草カード)の数  - soil: 底の周りの堆積土の裾(円盤)の大きさ

### ポリゴン数(三角形・四角形の面数の平均)

| 形 | 本数(near) | near 面数 | far 面数 | near usdc[KB] | far usdc[KB] |
|---|---|---|---|---|---|
| boulder_s | 20 | 329 | 89 | 20 | 8 |
| boulder_m | 24 | 1292 | 89 | 64 | 7 |
| boulder_l | 24 | 5132 | 89 | 242 | 7 |
| outcrop | 20 | 5775 | 169 | 297 | 12 |
| cliff | 20 | 513 | 79 | 67 | 12 |
| column | 4 | 202 | 91 | 30 | 15 |

## 土 module

名前: `soil_<種>_patch_<0..2>`(3m 角の地面パッチ。near 24x24 分割 / far 6x6)、`soil_<種>_clod_<0..2>`(土塊の単体。散布用)。縁は高さ 0 へ落として地面になじませる。

| 土種 | 色・粒度 | 形状の特徴 | 起伏[m] | patch near/far 面数 | clod near/far 面数 |
|---|---|---|---|---|---|
| kuroboku (黒ボク土) | 細粒・黒褐、なだらかなこぶ | | 0.09 | 431 / 15 | 80 / 20 |
| redyellow (赤黄色土) | 赤褐・中粒 | | 0.08 | 431 / 15 | 80 / 20 |
| clay (粘土) | 灰黄・乾燥亀裂(多角形の溝) | | 0.05 | 431 / 15 | 80 / 20 |
| sandy (砂質土) | 明るい砂色・粗粒 | | 0.06 | 431 / 15 | 80 / 20 |
| scoria (火山灰・スコリア) | 黒〜赤・粗い凹凸と小さな噴石 | | 0.14 | 1231 / 15 | 80 / 20 |
| masa (マサ土) | 花崗岩風化砂・粗粒の淡褐 | | 0.09 | 431 / 15 | 80 / 20 |
| humus (腐植・落葉層) | 暗褐・落ち葉片の盛り上がり | | 0.1 | 431 / 15 | 80 / 20 |
| mud (ぬかるみ) | 濡れて暗い・水たまり(濡れ材質)・轍(v2) | | 0.08 | 431 / 15 | 80 / 20 |

## 砂利・礫 module

単体(散布用の 1 粒): `gravel_stone_<round|angular|flat>_<fine|medium|cobble>_<0..3>`(粒の半径 fine 1.2〜3cm / medium 3.5〜8cm / cobble(玉石)10〜22cm)。
パッチ(混合サイズ): `gravel_patch_<種>_<0..2>`(基盤面 + 粒を並べた塊。2m 角、talus は 4m 角)。

| パッチ | 内容 | 粒数(near) | near 面数 | far 面数 | near usdc[KB] |
|---|---|---|---|---|---|
| sand | 砂(粒は基盤テクスチャのみ) | 0 | 68 | 7 | 10 |
| fine | 細礫(丸) | 70 | 1468 | 287 | 142 |
| medium | 中礫(丸+細礫) | 90 | 3768 | 367 | 358 |
| cobble | 玉石(丸+中礫) | 50 | 3588 | 207 | 341 |
| river | 河原の礫(丸い玉石・中礫・扁平) | 70 | 4868 | 287 | 461 |
| crushed | 砕石(角) | 120 | 5208 | 487 | 493 |
| talus | ガレ場(崖下の扇状堆積: 角礫・扁平礫、大小混在) | 90 | 7268 | 367 | 686 |
| ballast | バラスト(道路・線路脇の均一な角礫) | 150 | 7868 | 607 | 742 |

単体礫: 36 種、near 80 面 / far 20 面(平均)。

## 散布での使い方

- `scatter.rocks`: 崖パネル(斜面 54 度超)・崖下の転石(扇状)・露頭・巨礫・ガレ(角礫)・川沿いの丸石。岩種は geology、状態は moss / lichen / TWI / 傾斜から選ぶ。
- `scatter.ground`: 土パッチ(土種は soil_type)・河原の砂利/砂パッチ・ガレ場の礫パッチ。パッチは斜面に沿って傾ける。
- near / far: render は樹木と同様、カメラから 150m 以内を near、外を `_far` に切り替える(`add_scatter` の `|lo`)。
