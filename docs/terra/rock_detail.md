# Terra 岩のディテール強化(岩石海岸・岩山)

参照: 画像1(堆積岩の海食崖)・画像2(多孔質の岩山の頂部)。画像・動画・usdc は gitignore(`out/terra/rock/`)。

## 1. 現状との差(強化前のレンダで確認)

比較カメラ: `scripts/terra_rock_ref.py coast|peak <module>`(海面から崖を中距離 / 岩の上面を近接+遠景の緑地)。強化前は `rock_sandstone_cliff_1_hi`(崖パネル)・`rock_granite_outcrop_1_hi`(露頭)。

| # | 参照の特徴 | 強化前 | 原因 | 対応 |
|---|---|---|---|---|
| 1 | 水平の層理で層ごとに出入り(差別侵食の棚・凹み) | 太い波状のうねり。棚は無く、全体が 1 枚の板(輪郭が長方形) | 崖パネルは `sin` の凸凹 + 低周波ノイズ | `seacliff`: 層ごとに厚さ・硬さを乱数で決め、軟らかい層ほど凹ませる(硬い層は棚として張り出す)。層はわずかに傾ける |
| 2 | 垂直・斜交の節理で四角いブロック、欠け落ちた跡 | 無い(ひび割れのみ) | 節理の概念が無い | 節理 2 方向(傾き付き)+斜交の面でブロックに割り、ブロックごとの出入り、約 8% のブロックを矩形に欠け落ちさせる。節理線に沿う溝 |
| 3 | 波食ノッチ・洞・オーバーハング・張り出す棚 | 無い | 変位のみで穴を作れない | 水面付近のノッチ(層ごとの凹みに加算)、楕円体の洞(SDF で削る)。オーバーハングは層の硬さ差で出る |
| 4 | 蜂の巣状の穴(タフォニ)・ピット | 単発の大穴が数個 | `pits` は少数の楕円体 | `honeycomb`: 3 次元の揺らぎ格子の各セルに球状のピットを置き、隣と壁を共有する蜂の巣にする。3 スケール(m・dm・cm)。場所ごとの出やすさをノイズで変える。海食崖は下部・日陰に多い |
| 5 | 尖った突起・鞍部・瘤・深い割れ目が混在する大形状 | 丸い塊 1〜3 個 | 露頭 = 球状の塊の和 | `spire`: 鞍部となる広い土台 + 2〜3 本の尖塔(傾き・先細り)+ 縁や肩の丸い瘤 + 先細りの深い割れ目(`cleft`)。さらに欠け・蜂の巣・皺 |
| 6 | 色: 層ごとの濃淡、縦の雨筋 | 一様な色ムラのみ | 材質が曲率とノイズだけ | 層ごとの明度(硬い層は明るい黄褐)・縦長ノイズの雨筋(`streak`)を追加 |
| 7 | 地衣類は上面・縁、ピット内は暗い | 地衣類が斑状に散る | `_assign` の `nz` が内向き(skimage の法線は d<0 が内側のとき内向き)で、苔・地衣類が下向き面に付いていた(PR #6 以来の不具合) | 法線の向きを修正。地衣類は上向き+凸部(曲率)+高所に優先。ピット(曲率の下位 7%)は暗色 |
| 8 | 水際の濡れ帯・塩・藻 | 底の濡れ帯のみ | 水面の概念が無い | 水面 `zw` を基準に 暗い藻(0〜0.45m)・濡れ(〜0.9m)・塩の白帯(〜1.9m) |
| 9 | 巨大な崖・山塊スケール | 14m x 9m の崖パネルのみ | 地形側に崖の概念が無い | 下記 4 |
| 10 | 岩石海岸(波食棚・転石・ノッチ・海) | 無い | 海が無い | `gen.sea_cliff`+`scatter.rocks` の海食崖 module・転石 |
| 11 | 水際の暗い転石 | 近接 boulder に三角形の斑(材質を面単位で割当て) | 低分割 | 既知(#13)。 `_hi` の転石を使う |

## 2. 形状生成(`src/terra/modules/lib_rock_crag.py`、`lib_rock_sdf.py`)

SDF ボクセルを marching cubes でメッシュ化する(穴・オーバーハングを作るため)。新 module:

- `rock_<岩種>_seacliff_<v>[_far|_hi]`(岩種 seacliff・sandstone・limestone・tuff、22m x 11m x 13m)
- `rock_<岩種>_spire_<v>[_far|_hi]`(岩種 peakrock・granite・andesite・tuff・sandstone・seashore、約 5m x 4m)
- 新岩種 `seacliff`(堆積岩・黄褐)・`peakrock`(多孔質の暗灰褐)

near / far / hi は同じ形を粗さの違うボクセルで作る(`LOD_H`: hi 1.0 / near 1.9 / far 7.0)。near は小さなピット・洞を減らし、far は粗いボクセルのみ。細部の凹凸(mm〜cm)はボクセル未満のため、岩種の Bump 高さ画像(`rockh_*.png`)で表す(far の法線マップのベイクは岩 module では未実施で、頂点法線+Bump)。

ポリ数・生成時間(状態 v=2 のサンプル、12 コア CPU):

| module | far | near | hi |
|---|---|---|---|
| seacliff | 6,876 面 / 0.0s | 162,832 面 / 2.5s | 773,908 面 / 26s |
| spire (peakrock) | 1,164 面 / 0.1s | 15,346 面 / 1.7s | 174,028 面 / 18s |
| spire (granite, v=1) | - | 42,742 面 / 2.7s | 198,712 面 / 18s |

(hi の seacliff は ピーク RSS 約 1.7GB。)

## 3. 材質

岩種 14 変種に `algae`・`salt`・`streak` を追加。`_assign` に `ctx`(層の色の濃淡 `tone`、水面 `zw`、ピット暗色)を渡すと有効になる。既存の岩 module(ctx なし)の見た目は、法線の向きの修正(上記 #7)以外は変えていない。

## 4. 地形側

- `gen.crags` 強化: 層の厚さ・硬さを層ごとに変える(`hardness_var`、硬い層は平らな棚)、層の傾き `dip_deg`、垂直節理のブロック `joint_m` / `joint_amp`(ブロックごとの上下差+溝。2m 格子で解像できない段は σ=1 セルで丸める)。`hardness_var: 0, joint_m: 0` で従来の挙動。
- `gen.sea_cliff`(新): 内陸の台地 → 海食崖(層理の棚・節理・崖脚のノッチ溝)→ 波食棚(潮だまりの凹凸)→ 沖。`sea_level` を `doc.meta` に持ち、render が海面を張る(`add_sea`)。マスク `coast_cliff`・`shore_talus`・`wave_platform`・`sea`・`no_veg`・`water_depth` を出力。高さ場なので張り出し(オーバーハング)は地形では表せず、module 側が担う。
- `scatter.rocks`: `coast_cliff` があれば崖脚に seacliff module(間隔 16m、岩壁として連なる)、`shore_talus` に暗い転石(seashore boulder)。`peaks: true` で高所の急斜面に spire。樹木・低木は `no_veg`(崖・棚・海)に置かない。
- レシピ: `recipes/terra/rocky_coast.yaml`(800m 角・2m 格子)、`recipes/terra/rock_peak.yaml`。

## 5. 検証

- 画像(`out/terra/rock/`): 強化前 `before_coast.png`・`before_peak.png`、強化後 `after_coast.png`・`after_peak.png`、コンタクトシート `sheet_crag.png`、地形 `coast/coast_oblique.png`・`peak/peak_terrain_oblique.png`(前 `peak_before/peak_terrain_before_oblique.png`)。
- 生成: `terra generate rocky_coast.yaml` 約 5 秒(gen.sea_cliff 0.08s、散布 約 1.7s)。レンダ(Cycles 32spp 1200x760、CPU)は 40〜110 秒。
- テスト: `tests/terra/test_rock_detail.py`(near/far・材質・決定性、棚と壁の割合、地衣類が上向きに偏る、crags の層理・節理、sea_cliff の海・崖・棚・植生)。
- GPU が埋まっている環境では `TERRA_CPU=1` で CPU レンダ。

## 6. 残課題(違和感)

- near の seacliff はボクセルが粗く粘土細工のように滑らか。層理・節理の鋭さは hi のみ。near を 0.1m にすると 1 module 50 万面超になる。
- 岩種の色が面単位の材質割当てのため、斑の縁が三角形(迷彩状)。テクスチャ化(頂点色/UV)が理想。
- 地形の崖は高さ場(2m 格子)のため、節理のブロックは細い溝にしか見えない。崖の見た目は module 頼り。`rock_peak` の地形は急斜面が多い(傾斜 90 パーセンタイル 44 度)。
- 遠景の海は平面 1 枚(波・白波なし)。崖下の波しぶき・濡れ帯は module 側の材質のみ。
- 画像 2 のような遠景(杉林・集落)との同一画面の合成は未実施(module 単体と地形を別に検証)。
