# Terra 実装状況

設計書: フェーズ T0〜T8。本ファイルは T0〜T3 の進捗(担当範囲)。画像は `out/terra/<phase>/`(gitignore)。

## T0 基盤 — 完了
- [x] core/: Grid, Heightfield, Document(npz+json 保存), Node 基底+レジストリ, 決定的乱数(seed+ノード名), 入力ハッシュのキャッシュ(`<out>/.cache`)
- [x] YAML レシピ読み込み(`core/pipeline.py`)
- [x] cli: `terra generate / fetch / preview / export`
- [x] export: heightmap(RAW16・PNG16+json サイドカー), GeoTIFF(float32, EPSG 時は地理参照)
- [x] tests/terra
- 検証: 空レシピ+同一シードで GeoTIFF/RAW16/PNG16 のバイト列が一致(`tests/terra/test_t0.py`)

## T1 地形 — 完了
- [x] gen/noise(fBm・ridged・billow・Worley・domain warp, Numba), gen/shapes(山・火山・台地・クレーター・尾根), gen/stamp(画像/npy/実 DEM、回転・ブレンド・縁合わせ `fit`)
- [x] source/image.py(8/16bit 画像・npy), source/gsi_dem.py(国土地理院 標高タイル DEM5A z15、範囲外は DEM10B 補間。デコードは `python -I` 別プロセス)
- [x] 利用条件を原文(地理院タイル一覧)で確認し `data/terra/SOURCES.md` に記録(出典明示のみで可。規約本文サイトは取得不可だった旨も明記)
- [x] masks/(slope, aspect, curvature, height_band)
- [x] 仮想 8km 地形(`recipes/terra/virtual_alps.yaml`, 8m 格子 1000x1000, 生成 約 2.5 秒)と実 DEM(`fuji_foothills.yaml` 富士山 北東斜面 3km, 5m 格子 600x600)が同じ Document に入る。`mixed_fuji_in_alps.yaml` は仮想 8km の中へ実 DEM を貼り込む
- [x] scripts/terra_render.py(vt.render の写実カメラ: 60mm 俯瞰 F8 / 28mm 目線 F5.6, DoF, ブルーム, ビネット, 粒子)
- 検証: 実 DEM 標高 1446〜2509m・最大傾斜 63度(傾斜・曲率が不自然でない。林道のヘアピンが DEM に出ている)。`tests/terra/test_t1.py` 5 件(ノイズ決定性、キャッシュ、傾斜/向きの解析解、スタンプ、GSI 画素デコード)
- 画像: `out/terra/t1/{alps,fuji,mixed}_top.png`(ハイトシェード), `{alps,fuji}_oblique.png`, `{alps,fuji}_ground.png`。JPG は `out/terra/gallery/`

## T2 侵食と水系 — 完了
- [x] erosion/hydraulic(格子パイプモデル, Numba 並列・決定的), erosion/thermal(安息角, Jacobi 方式で質量保存), erosion/fluvial(ストリームパワー則の陰解法。粗い格子で解き変化量だけ補間、窪地を先に充填して樹枝状の谷網にする)
- [x] hydro/flow(priority-flood+ε, D8, 流量=上流面積, TWI), hydro/rivers(合流点ごとの折れ線・幅・流量・Strahler 次数), 湖(充填深さ・面積の閾値)
- [x] 実 DEM は `mode: derive`(hydraulic の高さを据え置く)に対応
- 性能(2km 角・2m 格子 1000x1000, 12 コア): fluvial 2.5s / hydraulic(120 反復)4.5s / thermal 0.6s / hydro.flow 0.3s、全ステップ合計 約 8 秒(JIT キャッシュ後)
- 検証(tests/terra/test_t2.py 5 件): 全セルが厳密に下流へ下る、出口の流量合計 = 全面積(保存)、全セルが境界へ到達、川の始点>終点標高、窪地→湖、侵食の決定性と熱侵食の質量保存
- 実 DEM(奥多摩 2km, 4m 格子)との統計比較(`scripts/terra_stats.py`):

| 指標 | 仮想(侵食後) | 実 DEM |
|---|---|---|
| 傾斜 中央値/90% [度] | 37〜41 / 53〜55 | 43 / 55 |
| 河川密度 [km/km²](0.03km² 以上) | 3.4〜3.8 | 3.3 |
| 河川の本数 / 最大次数 | 66〜68 / 3 | 67 / 3 |
| 最大流域 [km²] | 2.6 | 3.3 |
| 標高の電力スペクトル傾き | -4.7 | -4.4 |
- 画像: `out/terra/t2/{v2k_top,v2k_oblique,v2k_ground,okutama_top,stats}.png`、動画 `out/terra/t2/v2k_orbit.mp4`(H.264 yuv420p 1280x720 708KB)。JPG は `out/terra/gallery/t2_*.jpg`
- 既知の課題: 水力侵食に格子軸方向の筋が残る。陰影は T3 の材質で目立たなくなる

## T3 バイオームと散布 — 完了
- [x] biome/jp_forest(標高・緯度・気温・傾斜・向き・TWI から 照葉樹林→落葉広葉樹林→亜高山針葉樹林→ハイマツ→高山荒原、岩、湿地/草地。境界高度は気候でずらす。soil_depth・bedrock・canopy・splat 6 層も出力)
- [x] scatter/(Bridson ポアソンディスク(Numba)+密度マスク+除外領域(川・湖・道路・送電線の幅+余裕。road/powerline は T4/T5 でベクタが入ると自動で効く))
  - scatter.trees: vt の植栽 module(veg_shii/kusunoki/keyaki/tokaikaede/sakura/kuromatsu)+針葉樹 terra_sugi/shirabiso(`modules/lib_forest.py`、vt の tree_gen を使用)
  - scatter.shrubs: ツツジ・ツゲ・アジサイ・草。scatter.rocks: 崖パネル・崖下の転石(扇状)・露頭・巨礫・川沿いの礫
- [x] modules/lib_rock.py(boulder 12 種, outcrop 3, scree 3, pebble 3, cliff 3 = 手続き生成、PBR 材質 rock_*、1 module 1 usdc、`assets/terra/modules/`)。テクスチャ(rock_cliff / forest_litter / alpine_turf, 512px タイル可能, 計 1MB)は `scripts/terra_textures.py` で生成
- [x] export/usd.py(地形タイル 250 セル角を UsdGeomMesh+頂点色の焼き込み、水面、散布は PointInstancer(module は usdc 参照))、export_splat(splat0/1.png + splat.json)
- [x] scripts/terra_render.py(--look photoreal = vt.render の写実カメラ: 60mm 俯瞰 F8 / 28mm 目線 F5.6、DoF、ブルーム、ビネット、粒子)、scripts/terra_video.py
- 検証(仮想 2km 角・2m 格子 `recipes/terra/virtual_2km.yaml`):
  - 散布数: 木 約 135,000 + 低木・草 約 108,000 + 岩 約 4,000〜28,000 = 約 27 万インスタンス(PointInstancer 3 つ)
  - 生成時間: 全ステップ 約 10 秒(侵食 7s、散布 5s)。USD 44MB(地形 100 万四角形が大半)
  - Blender(Cycles)でレンダ可: 1280x720・32spp、27 万インスタンスを Geometry Nodes でインスタンス化。樹木は 150m 以内を高ポリ、外を低ポリ(約 1/5)
  - 生成した USD を Blender 5.0.1 へ `wm.usd_import` で読み込み可(地形 998,001 四角形、インスタンス展開 130 万)
  - tests/terra/test_t3.py: ポアソン最小間隔・決定性、植生帯が標高順で気候により上下、散布が川・湖に入らず接地、岩 module と USD(PointInstancer 総数=散布数)
- 画像: `out/terra/t3/{v2k_top,v2k_biome,v2k_oblique,v2k_ground}.png`、動画 `out/terra/t3/v2k_fly.mp4`(川沿いフライスルー)。JPG は `out/terra/gallery/t3_*.jpg`
- 既知の課題: 急斜面の裸地は材質が単調(岩テクスチャの強調が必要)。崖パネルは斜面に半分埋め込む配置だが数を絞っている。水力侵食の格子軸方向の筋。針葉樹の葉は広葉の葉アトラスを流用(針葉カードが無い)

## T3 追補: 近接品質の改善と地質 module — 完了
詳細は `docs/terra/closeup.md`(違和感リストと対応・プロファイル別の統計)と `docs/terra/modules_geo.md`(module 一覧・ポリ数)。
- [x] 近接レンダの違和感を列挙(14 項目)し修正: 地質別の土色・岩色・苔/地衣類、層理と岩の角(`gen.crags`)、水力侵食の格子軸の縞の除去、近接の微細起伏、草・低木の密度とスケール・草の彩度、遠景の大気遠近、地形メッシュの細分化と法線ベイク、露出推定、崖パネル、ガレ場・河原の礫
- [x] 詳細度プロファイル `--detail near|far|legacy`(scripts/terra_render.py): far = 4m 間引き+法線ベイク+散布を間引き+強い霞 / near = 視点周辺 220m 角を 0.5m 格子へ細分化+微細起伏+高密度散布(`terra/detail.py`)
- [x] `geology.zones`: 岩種 5・土種 8・moss/lichen。スプラット材質の土色・岩色が地質で変わる
- [x] 岩・土・砂利の module 約 450 個(各 near / far): `lib_rock_geo.py`(岩種 6 × 形 × 状態 4)、`lib_soil.py`(土種 8 のパッチ・土塊)、`lib_gravel.py`(砂利パッチ 8・単体礫 36)。手続き生成テクスチャ(`scripts/terra_textures_geo.py`、計 3MB の小さな PNG)
- [x] scatter.rocks(地質で岩種・状態を選ぶ)・scatter.ground(土パッチ・砂利パッチ)
- [x] tests/terra/test_closeup.py(8 件): 地質層、module の near/far・岩種・状態・土の違い、侵食の縞指標、crags は急斜面だけ、near ドキュメントのひび割れ無し・高密度・決定性、視線の廊下
- 画像: `out/terra/closeup/{before,after,far,legacy}/`、前後比較 `out/terra/closeup/compare_*.jpg`、module のコンタクトシート `out/terra/modules/sheet_{rocks,forms,soils,gravel,far}.png`(いずれも gitignore。JPG は `out/terra/gallery/`)
