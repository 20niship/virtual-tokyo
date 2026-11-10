# 都市部のフォトリアルレンダの作り方

README 冒頭のような都市の画像(地上の目線・俯瞰・夕景・夜景)を、このリポジトリのコードで再現する方法をまとめる。使っている Blender(bpy 5.0.1)の設定、ライティング、シェーディング、カメラ、後処理、時間帯ごとの違いを、コードの定数と対応させて書く。数値は `src/vt/render.py`・`src/vt/city_render.py`・`src/vt/render_real.py` の現在の値で、動作は `west_intersection` スポットで実測して確認した(2026-11)。

- 目次: [1 全体の流れ](#1-全体の流れ) / [2 再現手順](#2-再現手順) / [3 Cycles と出力の基本設定](#3-cycles-と出力の基本設定) / [4 空・太陽・ライティング](#4-空太陽ライティング) / [5 露出とトーンマップ](#5-露出とトーンマップ) / [6 カメラ](#6-カメラ) / [7 大気遠近とブルーム(コンポジタ)](#7-大気遠近とブルームコンポジタ) / [8 ポスト処理](#8-ポスト処理) / [9 シェーディング(材質)](#9-シェーディング材質) / [10 シーンの組み立てと速度](#10-シーンの組み立てと速度) / [11 時間帯ごとのルック](#11-時間帯ごとのルック昼夕夜) / [12 視点の選び方](#12-視点の選び方) / [13 legacy との差](#13-legacy-との差) / [14 既知の限界とトラブルシュート](#14-既知の限界とトラブルシュート)

## 1. 全体の流れ

```
OSM + DEM ──▶ city.build_world(half, tile, center_ll, mode)   地面・道路・線路・建物・ファニチャ・植栽
              city_props.build_props(w)                       車・人・小物(生活感)
              city_render.make_tiles(w)                       メッシュ/インスタンスをタイル分割
                    │
                    ▼  視点ごとに Blender シーンを作り直す(city_render.render_view)
   render.init_scene   Cycles・AgX・空(Nishita 系の Multiple Scattering)・雲・コンポジタ(霞+ブルーム)
   add_mesh_object     地面/道路/線路(材質別メッシュ)+ 水面 80km 平面
   add_instances_gn    ファニチャ/植栽/小物を Geometry Nodes でインスタンス化
   add_buildings_gn    建物の殻メッシュ + モジュール(窓・1階・屋根...)をインスタンス化
   add_camera          フルサイズ 36mm・焦点距離・DoF(被写体への実測オートフォーカス)
   estimate_exposure   低解像度の試し撮りの中央値から露出[EV]を自動決定
   render.render       Cycles(デノイズ有り)→ PNG
   render.postprocess  周辺減光・色収差・粒子・彩度(numpy)→ PNG を上書き
```

- 視点ごとにシーンを丸ごと作り直す(`init_scene` が `read_factory_settings` から始める)。カメラ周辺の半径(地上 170〜260m、俯瞰 700m 前後)のタイルとインスタンスだけを読み込むので、都市全体を持たずに済む。
- 画像の質を決めているのは「材質・モジュールの作り込み」と「空・露出・カメラ・後処理の設定」の2つ。前者は [9](#9-シェーディング材質) と README の各章、後者は本書の [3〜8](#3-cycles-と出力の基本設定)。

## 2. 再現手順

### 2.1 セットアップ

```bash
uv sync                              # bpy 5.0.1(Blender 本体の別インストールは不要)、usd-core、shapely、numpy、scipy、Pillow ほか
uv run python -m vt.osm_fetch        # 初回のみ(OSM を data/osm/ にキャッシュ)。DEM は data/dem/
```

- GPU は `OPTIX`→`CUDA` の順に探して使い、無ければ CPU(`render.init_scene` の `gpu=True`)。検証環境は RTX 3060 12GB。
- 他のプロセスが GPU メモリを大きく使っていると Cycles が OOM になる。その場合は GPU メモリを使っているプロセスを止める。CPU で描くなら `render.init_scene(gpu=False)` で呼ぶ(スクリプトの引数にはしていないので、コードの該当呼び出しを書き換える)。

### 2.2 いちばん簡単な方法: 既存スクリプト

```bash
# 昼: 数百 m 四方のスポットを生成して、地上視点を数枚+俯瞰 2 枚
uv run python scripts/build_city.py --spot west_intersection --no-usd --render --per 2 --round 1
#   → out/render/spots/west_intersection/round1/*.png と sheet_0.jpg

# 昼/夕/夜を切り替える(--time は build_realism.py にある。build_city.py には無い)
uv run python scripts/build_realism.py west_intersection --time day   --round 1 --samples 24
uv run python scripts/build_realism.py west_intersection --time dusk  --round 1 --samples 24
uv run python scripts/build_realism.py west_intersection --time night --round 1 --samples 24
#   → out/render/realismA/west_intersection[_dusk|_night]/round1/

# 任意の地点
uv run python scripts/build_city.py --center 139.75,35.64 --half 200 --render
# 田舎/郊外/ロードサイド/工場/コンビナート/高架
uv run python scripts/build_extra.py <rural|suburb|roadside|town|factory|plant|expwy_west|expwy_bay> --round 1
```

- ルックのオプション(`build_city.py`): `--look photoreal|legacy`(既定 photoreal)、`--lens MM`(0=自動)、`--fstop N`(既定 5.6)、`--no-dof`、`--samples N`(既定 24)、`--radius M`(既定 260)。
- 地点プリセットは `scripts/_spots.py` の `SPOTS`(お台場の交差点・西岸の交差点・高層ビル街・ゆりかもめ・首都高・レインボーブリッジ)と `src/vt/spots_extra.py`。
- 計測(RTX 3060、1280×720、24spp、`west_intersection`、地上 `g_roadway` 1 枚): 生成 1〜10 秒(OSM と中間キャッシュ次第)+レンダ 16〜23 秒。昼・夕・夜で差はほぼ無い。俯瞰は読み込む範囲が広く、16spp でも約 90 秒かかった。

### 2.3 最小のコード(再現用)

`scripts/render_city_minimal.py` が、上の流れを 1 ファイル・約 60 行で書いた例(動作確認済み)。

```bash
uv run python scripts/render_city_minimal.py                                  # 昼・地上
uv run python scripts/render_city_minimal.py --time dusk --kind aerial        # 夕・俯瞰
uv run python scripts/render_city_minimal.py --time night --view intersection --samples 64 --res 1920x1080
uv run python scripts/render_city_minimal.py --legacy                         # 従来(ミニチュア感のある)ルック
```

核になる部分だけ抜き出すと次のとおり。

```python
from pathlib import Path
from vt import city, city_props, city_render, render

render.PHOTO = True        # 写実ルック(レンズ・DoF・太陽 0.53°・ブルーム・ポスト処理)
render.FSTOP, render.DOF = 5.6, True
city_render.LENS = 0       # 0=自動(地上 28/35mm、俯瞰 60mm)
city_render.TIME = "dusk"  # day / dusk / night
city_render.REALISM = True # 雲・霞・水面・壁の汚れ・窓の室内・自動露出
city_render.OUT = Path("out/render/minimal/dusk")

w = city.build_world(200, 400, center_ll=(139.7478, 35.6448), mode="hybrid")
w["props"] = city_props.build_props(w, life=True)
tiles = city_render.make_tiles(w)
v = [v for v in city_render.pick_ground_views(w, per=2, margin=30) if v.kind == "roadway"][0]
city_render.render_view_checked(w, tiles, v, 170, samples=24, res=(1280, 720), min_luma=6.0)
```

`render_view_checked` は、画面が暗すぎる(カメラが壁や柱の中にある。昼は平均輝度 22 未満、夜は 6 未満)ときに、視点を数 m ずらして撮り直す。

## 3. Cycles と出力の基本設定

`render.init_scene()` が設定する値。

| 項目 | 値 | 理由 |
|---|---|---|
| エンジン | Cycles(CPU/GPU)。デバイスは OPTIX→CUDA→CPU の順 | 都市は GI と反射が見た目を決めるので Eevee は使わない |
| サンプル数 | `init_scene` の既定 48、`city_render` は 24 を渡す。確認 16〜24、仕上げ 64〜128 | デノイザ前提 |
| デノイズ | 有効(Blender 既定のデノイザ) | 低サンプルで窓・植栽の粒状感を消す |
| 最大バウンス | 8(透過も 8) | 窓の反射・植栽の透過・室内を通すのに十分 |
| 解像度 | 既定 1600×900、`city_render` は 1280×720 | |
| ビュー変換 | **AgX**。ルックは地上 `AgX - Base Contrast`、俯瞰 `AgX - Medium High Contrast`(legacy は全て Medium High Contrast) | 白飛びを避けつつ昼の空を青く残せる |
| 露出 | 視点ごとに自動決定([5](#5-露出とトーンマップ)) | |
| カラーマネジメント | シーン参照で描き、AgX で表示参照へ。ポスト処理は表示参照の 8bit PNG に対して行う | |
| ライト | **ライトオブジェクトは使わない**(夜の月光 1 灯だけ)。空・太陽はワールドのノードで作る | 都市の光は空と発光材質から |

## 4. 空・太陽・ライティング

`render._world_nodes()`。ワールドは Sky Texture(`MULTIPLE_SCATTERING`)を Background に繋ぐ。

### 4.1 太陽

| 項目 | 値 |
|---|---|
| 向き | `city_render.render_view` が `sun_dir=(0.5, -0.45, 0.65)` を渡す。仰角 asin(0.65/0.935)=約 44°、方位は `atan2(0.5,-0.45)`=約 132° |
| 視直径 | photoreal 0.53°(実際の太陽)、legacy 1.0° |
| 昼 | 上の仰角そのまま。影は輪郭のはっきりした直射影 |
| 夕 | 仰角 4° に固定(`realism and time=="dusk"`) |
| 夜 | 仰角 −9°(地平線の下。太陽の直射は無い) |

太陽の影は Sky Texture の太陽が Cycles のライトとして働く(重点サンプリング)ことで落ちる。別に Sun ライトは置かない。

### 4.2 大気

| 項目 | 昼(photoreal) | 昼(legacy) | 夕・夜 |
|---|---|---|---|
| Air density | 1.0 | 1.0 | 1.4 |
| Aerosol density | **1.1** | 1.6 | **2.2**(都市の霞で空が濁り、夕焼けが赤く広がる) |

### 4.3 雲(昼・夕)

空の方向ベクトル(`Generated` 座標)を地平線に向かって引き伸ばした平面に投影し、3D ノイズ(Scale 1.7、Detail 7、Roughness 0.6、Distortion 0.4)で薄い**筋雲**を作る。しきい値 0.40〜0.66 で雲量を決め、地平線付近(仰角 0.03〜0.35)は消す。雲は空の色に 0.78/0.80/0.84(昼)または 0.9/0.7/0.62(夕)を乗算した灰色を、最大 0.8 の割合で混ぜる。夜は雲を作らない。

### 4.4 水平線より下

方向の z 成分を 0.06 以上に切り上げて Sky に渡し、水平線より下も水平線付近(仰角約 3.5°)の空の色で埋める。暗い帯が出ず、遠景の霞([7](#7-大気遠近とブルームコンポジタ))の色へ自然につながる。

### 4.5 夜

- 空: 昼の Sky(仰角 −9°)に、都市の光害として `HAZE["night"]=(0.033, 0.029, 0.042)` を 85% 混ぜる。紫がかった暗い灰色の夜空になる。星は無い。
- 月: Sun ライト 1 灯だけ。`energy=0.035`、色 (0.7, 0.8, 1.0)、角径 1.5°、回転 (38°, 0°, −30°)。
- 他のライトは無く、地面や壁を照らすのは**発光材質**(窓・看板・街灯・自販機・信号・ヘッドライト)の Cycles による間接照明。

### 4.6 地面側のフィル

法線・材質は PBR で、影のなかの明るさは空の環境光で決まる。`REALISM=False` の古い設定のときだけ Background の強さを 2 倍にしていたが、photoreal では使わない(谷間の暗さは露出で補う)。

## 5. 露出とトーンマップ

固定の露出では、昼の開けた道と高架下・夜で明るさが大きく変わる。そこで**視点ごとに試し撮りから決める**。

1. `render_view` が一旦 `exposure=-1.8`(地上)/`-2.4`(俯瞰)を入れる。
2. `estimate_exposure(target, lo, hi)`: 解像度 20%・8spp・デノイズ無し・ビュー変換 `Standard`・Look 無し・露出 0 で試し撮りして、線形輝度(Rec.709 の係数)の**中央値**を求める。空の飽和画素(輝度 0.95 以上)は除いて中央値を取る。
3. `EV = log2(target / 中央値)` を `[lo, hi]` にクランプする。目標値は昼 0.12、夕 0.08、夜 0.03。`hi` は昼 1.2、夕・夜 1.8。`lo` は −3.6。
4. **夜だけは固定** −1.0 EV(光源=窓・街灯基準。自動にすると暗い街が明るく持ち上げられて夜に見えない)。

実測(`west_intersection`、地上): 昼 −0.43〜−1.21 EV、夕 +0.17〜+0.77 EV、夜 −1.00 EV。夕は空が暗いので昼より高い露出になる。

ブルームの閾値は露出から決める(`set_glare_threshold`): 表示で白(線形 1.0)になる放射輝度は `2^-EV`。その値より明るい所だけが光る。

## 6. カメラ

`render.add_camera()`、`city_render.photo_lens()`。

- センサー幅 **36mm(フルサイズ)**、`sensor_fit=HORIZONTAL`、`clip_end=5000m`。水平画角は 2·atan(18/f)(28mm=65.5°、35mm=54°、60mm=39.6°)。
- 焦点距離: 地上(目線 1.65m)は、roadway/intersection/alley/underdeck/station/behind/parking が **28mm**、park/plaza/sidewalk/waterfront が **35mm**。俯瞰は **60mm**。
- 俯瞰は、従来の広角 28〜30mm との焦点距離の比だけ被写体から後退する(構図は維持され、パースだけ浅くなる)。広角で近づくとミニチュアに見えるのを避ける。
- **被写界深度**: 地上 F5.6、俯瞰 F8。焦点距離は画面中央の 5×5 本のレイ(±0.15·(18/f) の範囲)を `scene.ray_cast` して中央値を取る。地上は上限 25m(道の先に合わせず、遠景を軽くぼかす)。俯瞰は実測のまま(約 500m で、過焦点距離以遠なのでほぼ全域がシャープ)。モーションブラーは使わない。
- 地上のカメラ付近 36m 以内の人・車はインスタンスから除く(カメラに重なって視界を潰すため。`render_view` の `dmin`)。

## 7. 大気遠近とブルーム(コンポジタ)

`render.enable_haze()`。ボリュームの霧は使わず、**奥行きパス(Depth)から距離に応じて霞色へ混ぜる**。無限遠の空を消さず、コストもほぼゼロ。

```
fac = (1 - exp(-k · depth)) · (depth < 60000 ? 1 : 0)      # 空の画素(depth が巨大)は除外
色  = mix(Cycles の画像, HAZE[time], fac)
```

| 時間帯 | k [1/m] | 霞の色(線形、水平線の空の放射輝度の方位平均を実測) |
|---|---|---|
| 昼 | 1.6e-4(1km で約 15%、5km で約 55% が霞色に) | (11.1, 13.8, 15.0) |
| 夕 | 2.2e-4 | (4.7, 3.1, 1.8) |
| 夜 | 1.0e-4 | (0.033, 0.029, 0.042) |

photoreal では、その後ろに**ブルーム**(Glare、Bloom)を 1 段入れる: 強度 0.08、サイズ 0.55、滑らかさ 0.5。控えめで、明るい窓・太陽・ヘッドライトのまわりがにじむ程度。

## 8. ポスト処理

`render.postprocess(path)`。Cycles の PNG(表示参照 8bit)を numpy で読み、写真らしさの最終段を足して上書きする。

| 処理 | 値 | 内容 |
|---|---|---|
| 横色収差 | 0.06% | R を外側へ、B を内側へ拡大率 1±0.0006 で補間 |
| 周辺減光 | 35% | `1 - 0.35·clip(r²/1.3, 0, 1)^1.5`(r は画像の右端で 1) |
| 彩度 | ×0.94 | 輝度との差を 0.94 倍。CG 特有の鮮やかさを少し落とす |
| ISO 粒子 | σ=1% | 正規乱数を σ0.6 でぼかして ×1.8、明るさに応じて `(1.3 − 輝度)` 倍(暗部に強く)、色チャンネルは (1, 1, 1.1)。乱数シード固定 |

`city_render.render_view` は photoreal のときだけ呼ぶ。legacy は後処理なし。

## 9. シェーディング(材質)

材質は `src/vt/materials*.py` の辞書(`MATERIALS`)で定義し、`render.get_material()` が Principled BSDF のノードツリーに展開する。色・粗さ・金属・テクスチャ・汚れの定義だけを持ち、見た目の追加(`REAL` フラグが有効のとき)は `render_real.py` が担う。

### 9.1 基本

- 色は sRGB の 16 進で書き、線形に変換して Base Color へ。**PBR**(Roughness / Metallic / IOR)。
- **UV はボックス投影をメートル基準で自動生成**(`mesh_to_bpy`): 面の法線の最大成分で軸を選び、頂点座標 (x,z)/(y,z)/(x,y) をそのまま UV にする。タイルは `size`(1 枚のメートル寸法。アスファルト 5m、歩道 2.4m、芝 3m、コンクリ 3.6〜4m)で繰り返す。
- **色ムラ**: Object 座標の 3D/4D ノイズ(Scale 3、Detail 6)で汚れを乗せ、ObjectInfo の Random をノイズの W に入れて個体ごとに変える。粗さもノイズで ±0.12〜0.2 揺らす。細かい凹凸は Scale 80 のノイズを Bump に使う。
- **個体差**: 建物の色は `bvar`(建物ごとの 0〜1)を Attribute(INSTANCER)で読み、ColorRamp(CONSTANT)で色を選ぶ。
- テクスチャ(`assets/textures`、約 165 ファイル)は**すべて手続き生成**(`src/vt/textures*.py`、`veg_textures.py`、`leaf_atlas.py`)で、Git 管理する。アスファルト・歩道・タイル・誘導ブロック・路面標示・ひび割れ・補修跡・轍・看板アトラス・樹皮・葉アトラスなど。

### 9.2 `REAL=True` で足される表現(photoreal / realism で有効)

| 表現 | 実装 | 主な値 |
|---|---|---|
| 壁の汚れ(雨だれ・垂れ染み・錆) | `wall_grime.png`(R=雨だれ G=垂れ染み B=錆)を Box 投影。インスタンスごとに位置をずらして繰り返しを隠す | スケール 0.25、強さ `grime`(既定 1.4)。暗色 (0.38,0.35,0.32)、錆色 (0.2,0.14,0.09) |
| 目地(タイル・レンガ・石) | Brick Texture。1 枚ごとの色むら ±14%、目地色、目地の深さを Bump に | 壁の +y 向きを前提に (x+y, z) 平面で展開 |
| ベベル | Bevel ノード(半径 1.2cm、3 サンプル)を法線に。金属でない・非発光の材質のみ | 角にハイライトが乗り、箱のように見えない |
| 窓ガラス | **透過を使わず**、反射 + 室内を 1 枚の表面で描く(下) | IOR 1.5、Metallic 0.15、粗さ 0.03〜0.09(窓ごと) |
| 水面 | 大小の波の法線(Bump 強さ 0.22)、深い青緑 (#0a2226→#1d3a36)、粗さ 0.05 | IOR 1.333。波は一方向に長い。運河・湾が建物を映す |
| 看板・店舗の自発光 | 夜・夕のみ(下) | |
| 植物 | 葉アトラスの alpha cutout(0.45)、両面、個体ごとの色相/明度ジッター、裏面ほど透過光(Translucent、最大 0.35)、葉の反射率上限 0.88 | 逆光で葉が黄緑に透ける |
| 樹皮 | 専用の高さ画像でノーマル(深い裂け目)と、凹部ほど粗い粗さを作る | |
| 屋根・波板・サイディング・ブロック・石積み | Bump の強さと距離を大きく(近景の陰影) | 強さ ×0.8、距離 0.05 |
| 肌(人) | 皮下散乱(Subsurface 0.08、半径 (1, 0.35, 0.18))、毛穴の微細 Bump、薄い Coat | `humans.md` 参照 |
| 頂点色(岩) | color attribute "Col" を Base Color に乗せる | Terra 用。都市では使わない |

### 9.3 窓の室内(インテリアマッピング)

窓の奥を描くのに、実際の部屋ジオメトリではなく**視線と部屋の箱の交点を材質の中で計算**する(`render_real.interior`)。

- 部屋は 1 窓セル=幅 3m × 高さ 3m × 奥行 4.5m の箱。視線(Incoming をオブジェクト座標へ)から、床・天井・側壁・奥壁のどこに当たるかを求めて塗り分ける。
- セルごと(3m)の乱数(White Noise)で、**壁色**(6 色の ColorRamp)・**カーテン/ブラインド/素通し**・**点灯**を決める。カーテンは窓全面、ブラインドは上から一部を横縞で覆う。
- 家具は奥壁の低い箱(高さ 0.9〜1.5m)。
- 室内の明るさは屋外より暗い(窓が黒っぽく見える): 室内の乗算係数は昼 0.14、夕 0.18、夜 0.5。
- 点灯セルは Emission を使う。電球色 (1.0, 0.72, 0.42) と白色蛍光灯 (0.88, 0.93, 1.0) を乱数で混ぜる。

## 10. シーンの組み立てと速度

- **インスタンス化**: 窓・看板・信号・街路樹・車・人などは「モジュール 1 種類=ソースオブジェクト 1 つ+点群 1 つ」にして、Geometry Nodes(Instance on Points、位置・`rot`・`scl`・`bvar` を点の属性で渡す)でまとめて配置する(`render.add_instances_gn`)。個別オブジェクトを何万個も作るより桁違いに速く、メモリも軽い。
- **建物**: 殻(外壁・屋根の連続面)は 1 棟ずつメッシュ、窓などのモジュールは全棟ぶんまとめて GN インスタンス化(`add_buildings_gn`)。
- **地面・道路・線路**: 材質別メッシュ(`mesh_to_bpy` で `foreach_set` による一括生成)。
- **水面**: 水平線までつながる 80km 角の平面を z=0 に 1 枚。
- **読み込み範囲**: カメラから `radius` の範囲のタイルとインスタンスだけ(地上 170〜260m、俯瞰 700m。建物は +60m の余裕)。
- **速度の目安**(RTX 3060、1280×720、24spp): 地上 1 枚 16〜23 秒、俯瞰 1 枚は 16spp でも約 90 秒。サンプルを増やすのは仕上げの時だけでよい。
- キャッシュ: 配置ロジックを変えたら `out/cache` を消す。

## 11. 時間帯ごとのルック(昼・夕・夜)

`city_render.TIME`(`build_realism.py --time`)が `init_scene(time=...)` と材質の組み立てに伝わり、次がまとめて切り替わる。

### 11.1 一覧

| 項目 | 昼 | 夕 | 夜 |
|---|---|---|---|
| 太陽の仰角 | 約 44° | 4° | −9°(直射なし) |
| Air / Aerosol | 1.0 / 1.1 | 1.4 / 2.2 | 1.4 / 2.2 |
| 空 | 青+筋雲 | 橙〜赤の低い空+灰橙の雲 | 都市光害の暗い紫灰色(光害 85%)、雲なし |
| 月光 | なし | なし | Sun 0.035、青白い |
| 霞 k [1/m] / 色 | 1.6e-4 / 青灰(11.1, 13.8, 15.0) | 2.2e-4 / 橙(4.7, 3.1, 1.8) | 1.0e-4 / 暗紫(0.033, 0.029, 0.042) |
| 露出 | 自動(目標 0.12、−3.6〜+1.2 EV) | 自動(目標 0.08、〜+1.8) | **固定 −1.0 EV** |
| 窓の点灯率 `LIT` | 0 | 0.28 | 0.5 |
| 点灯窓の発光強度 | — | 25 | 55 |
| 室内の明るさ係数 | 0.14 | 0.18 | 0.5 |
| 看板テクスチャの自発光 | なし | 1.2 | 3.0 |
| 材質の発光倍率(下) | ×1(材質の既定値) | ×0.4 | ×1.0 |
| 影 | 直射のはっきりした影 | 太陽が低く、建物に隠れて影は弱い | 影は月光のみで弱い |

### 11.2 発光材質の倍率(夕・夜)

夕・夜(`REAL and TIME != "day"`)は、`emit` を持つ材質の発光強度に次の係数を掛ける(夕はさらに ×0.4)。

| 材質 | 係数 |
|---|---|
| `led_white`(LED の白色灯) | ×10 |
| `car_headlight` | ×40 |
| `sign_*`(標識・看板)と `vend_*`(自販機) | ×8 |
| その他の発光材質(信号・車のテールランプ・反射材ほか) | ×1.5 |

信号(`sig_red/yellow/green`)の材質の既定の発光は 25 で、夜はさらに ×1.5。窓以外のテクスチャ看板(店舗看板・広告・標識・駅の看板)は、Emission Color にテクスチャそのものを繋いで自発光させる(夜 3.0、夕 1.2)。

### 11.3 時間帯ごとの狙いと撮り方

- **昼**: 直射影と青い空のコントラストを活かす。谷間の道が黒く潰れないよう、地上は `Base Contrast` の Look と自動露出(−1 EV 前後)で抑える。
- **夕**: 太陽が低いので直射影は出にくく、空全体と霞が橙に染まる。窓の点灯率は 28% で「ぽつぽつ」点く程度。露出は昼より高め(+0.2〜+0.8 EV)。
- **夜**: 露出は固定。窓・看板・信号・自販機・ヘッドライトが画面の主役で、空は暗い紫灰色。路面は月光と周囲の発光材質の間接光で、うっすら見える程度。
- 時間帯だけを切り替えて同じ視点を撮れば、同じ街で 3 種のルックを比較できる。例: `build_realism.py west_intersection --time day|dusk|night --only g_roadway`。

## 12. 視点の選び方

`city_render.pick_ground_views(w, seed=5, per=2, margin=...)` が、実際の街の構造から視点を自動選定する。

- 種類: 車道中央(`roadway`、車線上)、歩道(`sidewalk`)、交差点(`intersection`)、公園、広場、水辺、高架下(`underdeck`)、駐車場、路地(`alley`)、建物裏(`behind`)、駅前(`station`)。
- 目線の高さ `EYE=1.65m`、視線はやや下向き(−0.05)、建物の中や直近(3m 以内)は除外。
- 俯瞰(`pick_aerial_views`): 最も高い建物の上(+25m、上限 380m)から中心を見下ろす斜め 4 視点、真上 1 視点、低い斜め 2 視点。焦点距離は 60mm にして引く。
- 小領域スポットでは、主題に合う種類を優先して 3〜4 枚と俯瞰 2 枚に絞る(`PRIORITY`)。

## 13. legacy との差

`--look legacy`(= `render.PHOTO=False`)で従来の見た目に戻る。写真との差が、ミニチュアのような CG に見えた原因。

| 項目 | legacy | photoreal |
|---|---|---|
| 焦点距離 | 地上 20〜24mm、俯瞰 28〜30mm | 地上 28/35mm、俯瞰 60mm(俯瞰は距離を引く) |
| DoF | なし(全域ピンシャープ) | 地上 F5.6、俯瞰 F8 |
| 太陽の視直径 | 1.0° | 0.53° |
| エアロゾル(昼) | 1.6 | 1.1 |
| Look | Medium High Contrast | 地上 Base Contrast(俯瞰は Medium High) |
| ポスト | 霞のみ | ブルーム + 周辺減光 + 色収差 + 粒子 + 彩度 0.94 |

比較の詳細は `docs/photoreal_camera.md`(旧値の実測と採用値)。

## 14. 既知の限界とトラブルシュート

既知の限界(2026-11 に昼・夕・夜を実測して確認):

- **夜の路面照明**: 街灯・道路灯に光源(発光)が付いておらず、路面を照らすのは月光、窓・看板の発光の間接光だけ。夜の道が「街灯の光だまり」のようにはならず、全体にのっぺり暗い。
- **夜の空**: 星・月が画面に出ない。空は一様な暗い紫灰色。
- **夕**: 太陽が低すぎて直射影が出ず、昼と比べて立体感が弱い。ゴールデンアワーの長い影を出したいなら、仰角を 4° ではなく 10〜15° にするのが次の改善。
- 窓の室内は 1 部屋 1 箱の簡易版(家具は箱のみ)。ガラスの汚れ・指紋は無い。
- 雲は筋雲のみ。積雲・曇天は作れない。
- 水面に白波・泡・航跡が無い。
- 車は低ポリの箱に近く、ボディの反射が乏しい(`docs/` の残課題)。

トラブルシュート:

| 症状 | 原因と対処 |
|---|---|
| `--only g_roadway` で 1 枚も描かれない | 視点名は `g_roadway_0` など。`--only g_`(接頭辞)で絞るか、領域内に車道中央が無い。`--half` を広げる/`--per` を増やす |
| 真っ暗/真っ黒 | カメラが建物や柱の中にある。`render_view_checked` が自動でずらす(昼 22 未満・夜 6 未満)。ずれても暗ければ `--spot` の位置を変える |
| Cycles が CUDA OOM | 他プロセスが GPU を使っている。解放するか、`init_scene(gpu=False)` で CPU に切り替える |
| 前回と同じ街並みのまま変わらない | `out/cache` が古い。配置コードを変えたら消す |
| 夜が昼のように明るい/暗すぎる | 夜は露出固定(−1.0 EV)。`city_render.render_view` の `vs.exposure` を変える |
| 画像が粒状/ノイジー | サンプルを増やす(64〜128)。粒子(σ=1%)は意図したポスト処理で、`render.postprocess(grain=0)` で消せる |

## 関連ファイル

- `src/vt/render.py`(ワールド・材質・カメラ・コンポジタ・ポスト処理)、`src/vt/render_real.py`(汚れ・目地・室内・水面)、`src/vt/city_render.py`(視点選定・露出・レンダ)
- `src/vt/materials.py`、`materials_b.py`、`materials_h.py`(材質の定義)、`src/vt/textures*.py`(手続きテクスチャ)
- `scripts/build_city.py`、`scripts/build_realism.py`、`scripts/build_extra.py`、`scripts/render_city_minimal.py`
- `docs/photoreal_camera.md`(カメラ/空/露出/ポストの旧値との比較)、`docs/vegetation_realism.md`、`docs/road_details.md`、`docs/humans.md`
