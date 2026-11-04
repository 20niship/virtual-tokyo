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

---

# 追加(モーション・服・顔・人数・都市配置)

## モーション

| 取得元 | ライセンス | 結果 |
|---|---|---|
| Quaternius Universal Animation Library[Standard](itch.io 無料版 zip) | **CC0 1.0**。同梱 `License.txt` に "CC0 1.0 Universal (CC0 1.0) Public Domain Dedication"、商用・再配布可(配布ページにも同記載) | 取得・展開済み(`data/humans/mocap/ual/`、gitignore)。glb から 16 クリップをワールド回転として抽出し、Anny へリターゲット |
| CMU Motion Capture Database | 未確認 | **取得できなかった**(`mocap.cs.cmu.edu` が名前解決・接続とも失敗。FAQ の原文を確認できないためライセンス不明のまま使わない) |

- 取得物は信頼しないデータとして隔離ディレクトリ(`data/humans/mocap/`)に展開し、展開は Python(zipfile + パス検証)で行った。コミットするのは変換後のクリップ(`assets/humans/anim/*.npz` と `*.usdc`)のみ。元の glb は再配布しない(CC0 なので可能だが、容量のため)。
- リターゲット(`src/vt/humans_motion.py`): UAL の骨名は Anny の `game_engine` リグとほぼ同名(`Head`→`head`、`root`→`Root` の大小文字だけ)なので対応表は小文字化で足りる。`A_TPose` の姿勢を基準に各ボーンのワールド回転の差分を取り、前向きのヨー補正と腕の A-pose 補正(UAL は T 基準、Anny は A 基準)を掛けて、Anny の局所回転(`local-ref`)に直す。骨盤の上下動は身長比で縮尺。
- 出力クリップ(`assets/humans/anim/<name>.npz` 局所回転 + 骨盤移動、`<name>.usdc` UsdSkel アニメ):

| クリップ | 由来 |
|---|---|
| walk / walk_slow(0.75 倍速・振幅 0.7)/ walk_formal | UAL `Walk_Loop` / `Walk_Formal_Loop` |
| jog / run | UAL `Jog_Fwd_Loop` / `Sprint_Loop` |
| idle / talk(会話)/ sit / sit_talk | UAL `Idle_Loop` / `Idle_Talking_Loop` / `Sitting_Idle_Loop` / `Sitting_Talking_Loop` |
| interact / push | UAL `Interact` / `Push_Loop` |
| idle_hands(手待ち)/ idle_phone(スマホ)/ wave(手を振る)/ carry(荷物)/ bike(自転車こぎ) | **手続き**(UAL に無いもの。腕の向きを世界方向で指定して肩・肘の回転を解く `_aim`) |

- クリップの位相は 0..1。`humans_motion.pose_at(name, phase)` が隣接フレームを補間して Anny の姿勢パラメータにする。ヒーロー USD の `Skel/WalkAnim` も `walk` クリップを使う。
- 骨格・体型が違うと骨長が違うので、`assets/humans/anim/*.usdc` は中立体型のスケルトンに焼いたもの。他の体型へは回転(`*.npz`)を使う。

## 服・小物

- MakeHuman アセット(ヘッダが CC0 / CC BY 4.0 のものだけ): スカート 3(`toigo_long_full_skirt` `skirt_with_lace_ruffle` `tiered_mini_skirt`)、ワンピース 1(`toigo_tiered_skirt`)、スーツ 6(男女のシングル・ダブル・ジャケット+ネクタイ)、ゆったりパンツ(`harem`)、ショートパンツ、帽子(キャップ・クロッシュ)、医療用マスク。`mini_skirt`・`uncle_joshis_hat`・`newsboy_cap` は **AGPL3 のため除外**。`dress01` パックは取得できなかった。
- 手続き生成(`humans_wear.garment`): 体表面の領域を法線方向に押し出す。ジャケット・ブレザー(制服)・コート(膝上丈)・作業着(つなぎ)。下の層より外側になるよう余白を 3.4〜4.6cm にして、上着から下の服が透けないようにした。
- 剛体の小物: リュック(背骨に追従)、ヘルメット(頭に追従)、傘・手提げバッグ(右手の位置に追従し直立のまま)。
- 構成は group ごとの傾向で決める(会社員=スーツ/シャツ+ジャケット、学生=ブレザー+スカート/パンツ+リュック、作業員=つなぎ+ヘルメット、高齢者=コート・帽子・ゆったりパンツ、子供=リュック・ショートパンツ、一般=Tシャツ・スカート・ワンピース・ジャケット・コート・キャップ・マスク・傘・バッグ)。
- パンツの穴と裾の荒れ: 近傍 4 頂点のうち最も内側のものを基準に押し出す(従来は最近傍 1 頂点)。低ポリ版は衣服を頂点クラスタリングで間引いた後にもう一度体表の外へ押し出す。

## 顔・髪・体

- 低ポリ版にも目(まぶた線+白目+黒目)・眉・口を、頭表面に貼るデカールとして追加(穴や立体の目玉にしない)。ヒーロー(フル topology)は Anny 本来の目・口。
- 顔の多様性: Anny の `local_changes`(頬・顎・耳・目・鼻・口・額・眉の約 100 ラベル)をランダムに数個ずつ、表情(`mouthSmile`)を一部に付与。人種パラメータは asian を中心に少量の混合。肌色 6、髪型 10(CC0 が 9、CC BY 4.0 が 1)× 髪色 6、服色 17、靴色 5。
- 体: 身長は日本人の分布、`weight` `muscle` `proportions` `cupsize` を group ごとの平均・SD で変化。年齢は子供(5〜12)〜高齢者(88)。

## 人数・都市への配置

- 104 体(office 16 / casual 34 / elder 14 / student 14 / kid 10 / heavy 6 / worker 10)。年齢・体格・服装・モーション・位相はシード固定で決まり、位相は人ごとにずらす(`lib_anny.pose_of`)。
- `city_props._ped(rng, rank, role)` が role に合うモーションの人物を選ぶ: 歩道・歩行者専用道 = walk 系(walk / walk_slow / walk_formal / jog / run / carry / push)、横断待ち・立ち話 = wait 系(idle / idle_phone / idle_hands / talk / wave / interact)、公園 = park 系(talk / idle / idle_phone / wave / idle_hands)。座り(sit)は座る場所が無いので配置しない。
- 実行: `uv run python scripts/build_city.py --spot west_intersection --humans anny --render`。モジュール USD は `assets/modules/anny_*.usdc`(約 30MB)、ヒーロー 24 体は `assets/humans/*.usdc`、姿勢を焼いた版 48 は `assets/humans/baked/`。

## 確認スクリプト

- `scripts/render_clips.py out.png walk,idle,... --phases 0.1,0.6`: 同じ人物に各クリップを当てて並べる。
- `scripts/render_humans.py out.png --group all --stride 4 --n 24 --cols 8`: 人物ギャラリー。
- `scripts/extract_ual.py`: UAL の glb からワールド回転を取り出す(bpy)。`scripts/gen_humans.py` が一括生成(クリップ・モジュール・ヒーロー・baked・ATTRIBUTION)。

## 残課題(追加分)

- 手の形は指を少し曲げただけ。物を握る形は無い(傘・バッグは手の位置に置いているだけ)。
- sit / 自転車こぎクリップは座面・自転車が無いと空中に見える。bike は自転車モジュールとの組み合わせが未実装。
- 低ポリ版の服は MakeHuman アセットを間引いたもので、ゆるい服の裾で穴が出ることがある(間引きのセル幅で調整)。
- CMU Mocap は取得できずライセンス未確認のため未使用。UAL の戦闘・ジャンプ・水泳などは都市向きでないので出していない。
- 目・口はデカールで、表情やまばたきのアニメーションは無い(ヒーローは `facial_actions` を持つが USD には出していない)。
