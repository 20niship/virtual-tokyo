# Terra 実装状況

設計書: フェーズ T0〜T8。本ファイルは T0〜T3 の進捗(担当範囲)。画像は `out/terra/<phase>/`(gitignore)。

## T0 基盤 — 完了
- [x] core/: Grid, Heightfield, Document(npz+json 保存), Node 基底+レジストリ, 決定的乱数(seed+ノード名), 入力ハッシュのキャッシュ(`<out>/.cache`)
- [x] YAML レシピ読み込み(`core/pipeline.py`)
- [x] cli: `terra generate / fetch / preview / export`
- [x] export: heightmap(RAW16・PNG16+json サイドカー), GeoTIFF(float32, EPSG 時は地理参照)
- [x] tests/terra
- 検証: 空レシピ+同一シードで GeoTIFF/RAW16/PNG16 のバイト列が一致(`tests/terra/test_t0.py`)
