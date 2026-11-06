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
