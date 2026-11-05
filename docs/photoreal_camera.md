# 写実ルック(カメラ/空/露出/ポスト)

`scripts/build_city.py --look photoreal|legacy --lens MM --fstop N --no-dof`。既定は photoreal。

## 従来値(legacy)の実測
| 項目 | 値 |
|---|---|
| 焦点距離 | 地上 22(roadway)・24(intersection)・20(alley/behind/station)・22(その他)、俯瞰 28〜30mm |
| センサー | Blender 既定 36mm(水平画角: 22mm=78度、24mm=74度、30mm=61度) |
| 距離 | 俯瞰は建物上端+25m、斜め距離 約 h*0.8(広角+近距離=ミニチュア感) |
| DoF / 絞り | 無効(ピンホール、全域ピンシャープ) |
| 露出 | AgX + Medium High Contrast、estimate_exposure(中央値0.12)で自動決定 |
| 太陽 | Nishita(MULTIPLE_SCATTERING)、sun_size 1.0度(実際は0.53度)、仰角約40度、dust 1.6 |
| ポスト | 距離ヘイズ(k=1.6e-4/m)のみ。ビネット・ブルーム・色収差・粒子なし |

## photoreal の採用値
- センサー 36mm フルサイズ固定。地上(目線1.65m)は roadway/intersection/alley/underdeck/station/behind/parking=28mm(65度)、park/plaza/sidewalk/waterfront=35mm(54度)。俯瞰は 60mm(39.6度)。旧焦点距離との比だけ被写体から後退(構図維持、パースだけ浅くなる)。
- DoF: 地上 F5.6、俯瞰 F8。焦点は画面中央 5x5 レイの中央値(scene.ray_cast)、地上は上限25m(道の先に合わせず、遠景を軽くぼかす)。俯瞰は実測のまま(約500m、過焦点以遠なのでほぼ全域シャープ)。モーションブラーなし。
- 空: sun_size 0.53度、dust 1.1(従来1.6)、air 1.0、ozone 既定。ヘイズは従来のデプス合成(Cycles ボリュームなし)。
- トーン: AgX Base Contrast(地上)/Medium High(俯瞰)、露出は従来の自動露出。
- ポスト: コンポジタでブルーム(Glare Bloom, 強度0.08, 閾値=表示白)、その後 numpy で 周辺減光 35% / 横色収差 0.06% / ISO粒子 σ=1% (暗部強め) / 彩度 0.94。
- 比較画像: `out/render/photo_compare/*_before_after.jpg`(左=従来、右=photoreal)。
