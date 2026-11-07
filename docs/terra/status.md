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
