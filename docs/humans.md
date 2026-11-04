# 人物生成(Anny)

体格・年齢・性別・服・髪の違う人物を、商用利用・再配布できるデータだけで作る。調査は artifact「人物メッシュ生成 調査」。

## 使うもの・ライセンス(導入後に同梱ファイルで確認した結果)

| 対象 | ライセンス | 確認した場所 | 備考 |
|---|---|---|---|
| Anny(PyPI `anny` 0.6.2) | Apache-2.0 | `anny-0.6.2.dist-info/licenses/LICENSE` | 商用・改変・再配布可。原文を `assets/humans/LICENSES/` にコピー |
| Anny 同梱の MakeHuman/MPFB2 由来データ(`data/mpfb2` `faceunits01`) | CC0 1.0 | `anny/data/mpfb2/LICENSE.md` | 原文を `assets/humans/LICENSES/` にコピー |
| `soma` トポロジ | Apache-2.0(SOMA-X 由来) | anny の README | 使っていない |
| SMPL-X 互換トポロジ | **非商用のみ** | anny の README | **取得も使用もしていない**(`noncommercial.zip` は未ダウンロード)。pip 版には含まれない |
| MakeHuman asset pack(`shirts01` `pants01` `hair01`) | パック表示は CC0 だが **個別 `.mhclo` の license 行が異なる** | 各 `.mhclo` ヘッダ | 下記 |

### MakeHuman アセットの扱い(重要)
パック全体の表示が CC0 でも、個々のアセットのヘッダに `AGPL3` や `CC BY 4.0` と書かれたものが混ざっている(`hair01` の 9 件が AGPL3、`o4saken_long01` は CC BY 4.0、`shirts01` の `tube_top` も AGPL3)。
**`.mhclo` に CC0 または CC BY 4.0 と明記されたものだけを使い、AGPL3 は除外した。** CC BY 4.0 は `o4saken_long01` のみで、`assets/humans/ATTRIBUTION.md` に作者名を記している。

ダウンロードしたパックは信頼できないデータとして `data/humans/pk/` に隔離(`.gitignore`)し、リポジトリにはコミットしない。コミットするのは変換後のテクスチャ(`assets/textures/anny_hair_*.png`)と生成した USD のみ。

```bash
mkdir -p data/humans/dl && cd data/humans/dl
for p in shirts01 pants01 hair01; do curl -sSL -O https://files.makehumancommunity.org/asset_packs/$p/${p}_cc0.zip; done
# 展開は Python(zipfile)でパス検証しつつ data/humans/pk/<pack>/ へ。各パックの packs/*.json に作者・ライセンスがある
```

## 構成

| ファイル | 役割 |
|---|---|
| `src/vt/humans.py` | 体格サンプリング(日本人の身長分布の `PROFILES`)、Anny 実行、姿勢(世界軸回転)、服・髪のフィット(近傍頂点バインド+押し出し+平滑化)、衣装の割当 |
| `src/vt/humans_usd.py` | UsdSkel のヒーロー出力(体・服・髪・靴、53 ジョイント、歩行 24 フレーム)、姿勢を焼いた軽量メッシュ出力 |
| `src/vt/modules/lib_anny.py` | 歩行者モジュール `anny_<group>_<k>`(52 体、低ポリ topology `notoes_collapse10pc`、遅延生成) |
| `src/vt/materials_h.py` | 肌 6・服 10 色・靴・髪(グレー+アルファのカードを `tint` で着色) |
| `scripts/gen_humans.py` | テクスチャ・モジュール USD・ヒーロー USD・baked USD・ATTRIBUTION を一括生成 |
| `scripts/render_humans.py` | 人物ギャラリー(`--group office,casual --n 24 --cols 8`、`--zoom --cam 5`、`--pedx` で従来比較) |
| `scripts/render_hero_usd.py` | ヒーロー USD を Blender に読み込んで確認(スケルトン/アニメ) |

## 使い方

```bash
uv run python scripts/gen_humans.py                       # assets/humans, assets/modules/anny_*.usdc, textures
uv run python scripts/build_city.py --spot west_intersection --humans anny --render   # 歩行者を Anny 人物に(既定は従来の pedx)
uv run python scripts/render_humans.py out/render/humans/g.png --group all --n 24 --cols 8
```

## 出力

- `assets/humans/<group>_<seed>.usdc`: UsdSkel ヒーロー 20 体(約 1MB/体)。`/<id>` が SkelRoot、`Skel`(53 ジョイント)、`Body/Top/Bottom/Hair/Shoes`(4 ウェイト/頂点)、`Skel/WalkAnim`(歩行 1 周期)。材質は `../textures` を参照。
- `assets/humans/baked/<group>_<k>_{stand,walk}.usdc`: 姿勢を焼いた軽量メッシュ(同じ人物の低ポリ版)。
- `assets/modules/anny_<group>_<k>.usdc`: 都市配置用 52 体。建物・小物と同様に PointInstancer から reference できる。
- 人物は「前=+y、足元 z=0、m」のモジュール規約。

## 体格・年齢の指定

`humans.PROFILES` の表で group ごとに性別比・年齢範囲・身長(平均/SD)・体重・筋肉を調整する。身長は `height` パラメータを二分法で解いて cm に合わせる(加齢による低下も加味)。
`age` は anny の連続値で、`humans.age_param(歳)` が歳に直す(測定: 0=約1歳、0.2≈6歳、0.3≈10歳、0.5=25歳、1.0≈90歳)。人種パラメータは `asian=1`。

## 限界・残課題

- 服は MakeHuman の標準ボディ向けアセットを、近傍頂点へのバインドで体に合わせている。体格が極端だと裾や袖が荒れる(平滑化と押し出しで軽減)。タイトな服向きで、ゆったりした服・スカートは動きで体に食い込む。
- 低ポリ版(モジュール)は目・口を省いている。顔のディテールはヒーロー(13.7k 頂点)のみ。
- 手は指を少し曲げただけ。顔の表情・視線は未対応。
- モーションは自作の手続き歩行(世界軸回転)のみ。Quaternius / CMU の CC0 モーションを Anny スケルトンへリターゲットするのは未実施。
- 髪はカード型で、ストランド髪ではない。髪色はグレースケールのテクスチャを乗算するため、ハイライトは単調。
- 服・髪の追加には `.mhclo` ヘッダの license 確認が必要(AGPL3 は使わない)。
