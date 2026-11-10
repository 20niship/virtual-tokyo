# Procedual生成された東京/お台場都市

<p align="center"><img src="https://github.com/user-attachments/assets/85d3355d-9059-4ff4-9f32-59183678c9fa" alt="生成した都市のレンダリング(空中・夕景・夜景・車線目線・橋・高架・田舎・ロードサイド)" width="900"></p>

BlenderとPythonを使って、OpenStreetMap(OSM)と国土地理院DEMから東京(お台場〜田町・品川)の街を手続き生成するプロジェクトです。生成物はUSDで出力します。UEのThe Matrix Awakensくらいフォトリアルで、現実と区別がつかない都市を目標にしています。

## 目次

1. [思想: モジュール単位で作る](#思想-モジュール単位で作る)
2. [セットアップと実行](#セットアップと実行)
3. [フォルダ構成](#フォルダ構成)
4. [生成パイプライン](#生成パイプライン)
5. [建物の生成](#建物の生成)
6. [道路の生成](#道路の生成)
7. [道路に沿って建物を配置する方法(街区→ロット→建物)](#道路に沿って建物を配置する方法)
8. [別の地域を生成する方法](#別の地域を生成する方法)
9. [新しいモジュールを追加する方法](#新しいモジュールを追加する方法)
10. [レンダリング・確認用スクリプト](#レンダリング確認用スクリプト)
11. [Git管理のルール](#git管理のルール)
12. [既知の制約・残課題](#既知の制約残課題)
13. [データの出典・ライセンス](#データの出典ライセンス)
14. [参考リンク](#参考リンク)

## 思想: モジュール単位で作る

<p align="center"><img src="https://github.com/user-attachments/assets/780cb5c1-d973-4142-a884-cc0679d3f1b2" alt="窓モジュールのギャラリー" width="720"></p>

<p align="center"><img src="https://github.com/user-attachments/assets/ac1a0db7-7d73-4c08-b4c3-7ecb68713111" alt="1階(基壇部)モジュール" width="720"></p>

<p align="center"><sub>1モジュール=1つのUSD。窓・1階・屋根・意匠などを組み合わせて建物にする</sub></p>

- 都市は「**小さな部品(モジュール)を大量に作り、配置ルールで組み合わせる**」ことで作ります。窓1スパン、壁1スパン、庇、非常階段、屋上設備、信号機、標識、街路灯、木、車、人などがそれぞれ1つのモジュールです。
- モジュールは **1モジュール=1つの `.usdc`**(`assets/modules/`)です。建物・ファニチャ・植栽・車などは、モジュールUSDを **reference** し、位置・回転・スケールを持つ **PointInstancer** で配置します(同じ部品を何万回でも低コストで使い回せる)。
- 外形(躯体)・地面・道路・線路のような連続した面だけは、材質別のメッシュとして生成します。
- 規約: モジュールのローカル座標は x=壁に沿う方向、+y=外向き(正面)、z=上。原点は壁の左下手前。単位はm。
- 多様性は「**モジュールの種類を増やす**」「**様式(style)・材質・テクスチャを切り替える**」「**乱数シードで変化をつける**」の3つで出します。乱数は対象IDからシード固定するので、同じ入力なら同じ都市になります(再現性)。
- フォトリアル方針: ベベル、サッシ、目地、汚れ・劣化・かすれをモジュール側で作り込む。PBRマテリアルを使い、色むらや傷を適度に入れる。
- 参考: UEのCity Sample(Matrix Awakens)のモジュール式手続き生成(下の参考リンク)。

## セットアップと実行

<p align="center"><img src="https://github.com/user-attachments/assets/3505e2e9-4bf5-4365-a079-b23f3b0cf91c" alt="手続き生成したテクスチャ(路面・タイル・誘導ブロック・路面文字など。assets/textures にGit管理)" width="720"></p>

```bash
# Python 3.11 + 依存(bpy 5.x, usd-core, shapely, pyproj, numpy, ...)は uv で導入
uv sync

# テスト
uv run pytest -q

# OSM取得(初回のみネットワーク必要。data/osm/ にキャッシュされる)
uv run python -m vt.osm_fetch

# モジュールUSDの再生成(assets/modules/*.usdc)
uv run python -c "from vt import usd_out; usd_out.write_all_modules()"

# 地面・道路・線路・ファニチャ・植栽・建物(OSM実建物)をUSD出力+代表視点をレンダ
uv run python scripts/build_phase_b.py            # --no-render でUSDのみ

# 全域/領域の生成(街区ベースの建物自動配置、車・人・小物込み)
uv run python scripts/build_city.py --region west --mode hybrid --render --per 2 --radius 240
uv run python scripts/build_city.py --region odaiba --half 900 --tile 450      # 約1.8km角を16タイルで出力

# 数百m四方の「スポット」だけ生成してレンダ(改善の反復向け、1地点 生成15秒+レンダ10〜25秒)
uv run python scripts/build_city.py --spot west_intersection --no-usd --render --per 2 --round 1
uv run python scripts/build_city.py --center 139.75,35.64 --half 200 --render
uv run python scripts/build_extra.py <spot> --round N   # 田舎/郊外/ロードサイド/工場/コンビナート/高架のスポット
```

- Blender(bpy)はPythonモジュールとして使うため、別途Blenderのインストールは不要です。Cyclesはデフォルト設定ならCPUでも動きますがGPUが速いです。
- 生成物(`out/`)のうち画像は `.gitignore` 済みです。

## フォルダ構成

```
.
├── README.md / pyproject.toml / uv.lock(gitignore)
├── assets/
│   ├── modules/      # モジュール1つ=1つの .usdc(約1,100個。win_*, wall_*, rs_*, pl_*, sign_*, veg_*, car_*, ...)
│   ├── textures/     # 手続き生成したテクスチャPNG(Git管理)。標識/広告/葉/樹皮/路面標示/店舗看板などのアトラスも含む
│   └── buildings/    # 建物1棟=1つの .usda(build_phase_b.py 実行で生成。モジュール・テクスチャをreferenceで束ねたモデル)
├── data/             # OSM・DEMのキャッシュ(gitignore)
├── out/
│   ├── usd/          # 生成した地面/道路/線路/ファニチャ/植栽/建物のレイヤと city.usda(巨大なので原則Git管理しない)
│   ├── render/       # レンダ画像(gitignore)
│   └── cache/        # 生成キャッシュ(pickle。配置ロジックを変えたら `out/cache` を消す(`build_extra.py` は `--no-cache` も可))
├── docs/             # 設計メモ・各フェーズの記録(building_modules / final_phase / extra_details / realism_b)
├── scripts/          # 実行用スクリプト(build_*.py, render_*.py, probe_spots.py など)
├── src/vt/           # 本体(下表)
└── tests/            # pytest
```

`src/vt/` の主なファイル:

| 分類 | ファイル | 役割 |
|---|---|---|
| データ | `osm_fetch.py`, `layers.py`, `geo.py` | Overpass取得、レイヤ化(道路/建物/鉄道/水域/緑地/駅/POI…)、座標変換(EPSG:6677、bbox中心が原点) |
| 地面 | `world.py`, `ground.py` | DEMから地形、陸地/水面/護岸、緑地、駐車場の区画線 |
| 道路 | `roads.py`, `road_extras.py`, `overlays.py` | RoadProfile、交差点、横断歩道、標示、高架、路面の汚れ/補修/マンホール |
| 鉄道・橋 | `rail.py`, `rails_c.py`, `bridges.py`, `expwy.py` | 線路、ゆりかもめ、首都高の桁・橋脚・細部、レインボーブリッジ |
| 建物 | `assemble.py`, `roofs.py`, `styles_extra.py`, `district.py`, `blocks.py` | 建物組立(様式・階構成・屋根)、地区タイプ、街区→ロット→建物 |
| 街 | `furniture.py`, `furniture_osm.py`, `vegetation.py`, `city_props.py`, `city_life.py` | 信号/街灯/標識、OSM由来の小物、植栽、車・人・生活感の小物 |
| モジュール | `modules/lib_*.py`, `modules/registry.py` | モジュール定義(`@mod`/`reg`でREGに登録) |
| 出力 | `usd_out.py`, `materials*.py`, `textures*.py` | USD書き出し、マテリアル表、テクスチャ生成 |
| レンダ | `render.py`, `city_render.py` | bpy+Cyclesでのシーン構築、視点の自動選定 |
| 全体 | `city.py` | 領域を一括生成してタイルに振り分ける |

## 生成パイプライン

<p align="center"><img src="https://github.com/user-attachments/assets/2141de36-1dae-4fc6-84a4-e46063ad2f34" alt="植栽モジュール(樹木)のタイル" width="900"></p>

<p align="center"><img src="https://github.com/user-attachments/assets/d9e62d84-bbf4-44fe-a5fd-93bd7464fe68" alt="レインボーブリッジ" width="720"></p>

<p align="center"><img src="https://github.com/user-attachments/assets/1ac7d78c-6d23-4de6-88e9-95c4e35406c8" alt="首都高の桁と橋脚" width="720"></p>

1. **OSM取得**(`osm_fetch.py`): 道路・建物・鉄道・水域・緑地・POI・街路樹・電柱などを取得して `data/osm/` に保存。
2. **地形**(`world.py`): 国土地理院DEM(5m)を取得して平滑化。陸地・水面・護岸(直立/石積み/階段)を作る。
3. **道路**(`roads.py`): 道路ごとに`RoadProfile`を決め、車道・歩道・交差点・標示・横断歩道を生成。高架は箱桁+橋脚。
4. **鉄道・橋**: 地上線路、JR高架、ゆりかもめ、首都高、レインボーブリッジ。
5. **建物**: OSMの実建物を様式付きで組み立て、空き地は街区ベースで自動配置(hybrid)。
6. **ファニチャ・植栽・車・人**: 道路形状・OSM・規則から配置。
7. **USD出力**: 地面/道路/線路は材質別Mesh、建物・ファニチャ・植栽・小物はPointInstancer。`city.usda`で束ねる。巨大な領域は450mタイルに分割して書く。
8. **レンダ**: 地面視点(目線1.65m)と空中視点を自動選定してCyclesでレンダ。多数のインスタンスはGeometry Nodesで扱い、1枚15〜35秒。

## 建物の生成

<p align="center"><img src="https://github.com/user-attachments/assets/9b039d9d-014a-49d5-8d8d-c07b9e0a5bb4" alt="建物様式の一覧" width="900"></p>

- 入口は `assemble.build_building(Feature)`。敷地ポリゴン・`building`タグ・階数/高さ・乱数シードから、様式(style)を選んで **躯体(シェル) + モジュール配置** を作る。
- **様式(style)**: オフィス、タワマン、団地、商業ビル、倉庫、駐車場、ホテルなど16種に加え、田舎/郊外/ロードサイド/工場(`styles_extra.py`)を含め約50種。1階(基壇)・中層・最上階で別の階構成にでき、階高は用途別(住宅3.0m、事務所3.9m、工場4.5m など)。
- **多様性の出し方**: 窓(引違い/FIX/連窓/縦スリット/出窓/高窓…約70種) × 窓まわり(庇/ルーバー/フィン/面格子) × 壁材 × 色 × 屋上設備 × セットバック・斜線ベベル。`bvar`(建物ごとの色むら)も付く。
- **屋根**: 切妻・寄棟・入母屋・片流れ・陸屋根 × 瓦/金属/スレート等11材質(`roofs.py`)。
- **地区タイプ**(`district.py`): `rural / suburb / town / roadside / factory / plant`。`city.build_world(..., district="roadside")`のように指定すると、住宅の外構、ロードサイドの店舗と駐車場、コンビナートのタンクヤードなどを自動配置する。東京の既定は変わらない。
- 1棟だけ試す(例): `Feature(1, Polygon([(0,0),(20,0),(20,12),(0,12)]), {"building":"apartments","_top":25.0,"_min":0.0})` を `build_building` に渡す(`tests/test_modules.py` 参照)。`usd_out.write_building_asset` で1棟分のUSDアセット(`assets/buildings/`)にできる。

## 道路の生成

<p align="center"><img src="https://github.com/user-attachments/assets/4fad2538-def5-46bb-95b9-26cc3fa33f33" alt="交差点(横断歩道・路面標示・信号)" width="900"></p>

<p align="center"><img src="https://github.com/user-attachments/assets/0407fad0-1615-4290-8494-1a24d1cf85a2" alt="道路の真上からの図" width="900"></p>

- 道路ごとに`RoadProfile`(車線数・車線幅・路肩・中央分離帯・歩道ON/OFF(左右別)・歩道幅・縁石高・植栽帯・自転車レーン・路面劣化)を持つ。決定順は **OSMタグ → 種別デフォルト → 乱数ジッター → ユーザー指定(上書き)**。乱数は`(osm_id, 区間index)`でシード固定。
- **複数種類にする方法**: `roads.CFG`(`city_age / wetness / barrier_free_rate / tactile_rate / bike_lane_rate / parking_rate / bus_lane_rate / hump_rate / scramble_rate / escort_rate / ...`)を変えると、全体の傾向が変わる。種別ごとの基本値は`roads.BASE`、地区ごとの倍率で上書きもできる。
- 交差点は隅切り・横断歩道(スクランブル含む)・停止線・右折レーン・導流帯・歩道コーナーの切り下げ・エスコートゾーン・点字ブロックを生成。立体交差(layer違い)は交差点を作らない。
- 路面標示は `(s, t)` 座標のベクタからマスクとして貼り、かすれ(タイヤ通過帯)・補修・ひび・轍・落ち葉・水たまり等の劣化を重ねる(`overlays.py`)。
- 標識は1枚のアトラス(`sign_atlas.png/json`、約140種)をUVで貼る。信号は旧式/LED/薄型/歩行者用/矢印付など、街灯・ガードレール・ガードパイプ・カーブミラー・電柱・電線も複数種類ある。

## 道路に沿って建物を配置する方法

<p align="center"><img src="https://github.com/user-attachments/assets/1b4bb2d3-2a69-46b7-9584-3e1a31e49740" alt="街区から自動配置した西岸の空中図" width="900"></p>

`blocks.py` の `infill()`(地区タイプ指定時は `district.infill()`)が、道路から街区・ロット・建物を自動で作る。

1. **街区を取る**: 領域から「道路(車道+歩道)・緑地・水域・線路/高架・護岸・駅・(hybridでは)OSMの実建物」を引いた残りを **街区** とする。公園や水際は空いたままになる。
2. **ロットに分割**: 街区を、道路に面する辺を基準にした奥行きと間口でロットに再帰分割する(`split_lot`)。
3. **ゾーン**: 道路密度と領域中心からの距離で `core / urban / mid / low / industrial` を決め、中心ほど高く、外側ほど低くする。
4. **建物を割り当て**: ロットごとに用途・階数・高さ・様式を乱数(シード固定)で決め、`assemble.build_building`で組み立てる。道路側が正面になるよう向きを決める。小ロットは小物建物、一部は駐車場(区画線+車)になる。
5. **mode**: `osm`=OSM実建物だけ / `infill`=全自動 / `hybrid`=OSM実建物を優先し空き地だけ自動(既定)。
6. 実行: `uv run python scripts/build_city.py --region west --mode hybrid`。道路の両側にビルが連なる見た目になる(西岸で建物約2,500棟)。

## 別の地域を生成する方法

<p align="center"><img src="https://github.com/user-attachments/assets/80c7c395-fac5-4033-a04a-5df1cce6170a" alt="地区タイプ(rural/suburb/roadside/factory/plant)のレンダ" width="900"></p>

現在はお台場〜田町・品川を対象にしている。他の地域(日本国内)は次の手順で作る。

1. `src/vt/osm_fetch.py` の `BBOX = (南, 西, 北, 東)` を対象範囲に変える。キャッシュ名はbbox込みなので、再取得は自動で行われる。座標原点(`geo.py`)とDEM範囲もこのBBOXから決まる。
2. `uv run python -m vt.osm_fetch` でOSMを取得する。
3. `scripts/build_city.py` の `CENTERS` に `"名前": (経度, 緯度)` を足し、`--region 名前` のchoicesにも加える(または `--center 経度,緯度 --half 400` を直接指定する)。
4. 建物の雰囲気は `district` で選ぶ(都市部は既定、郊外は `suburb`、地方の住宅地は `rural`、国道沿いは `roadside`、工業地帯は `factory`、コンビナートは `plant`)。
5. 日本国内で平面直角座標系の系が異なる場合は、`geo.py` の `EPSG:6677`(IX系)を該当の系に変える(例: 関西は VI系=6674)。
6. 海外は、DEMの取得元(国土地理院)と座標系の変更が必要で、現状は未対応。
7. 範囲が広い場合は `--half` と `--tile` でタイル分割して出力する。

## 新しいモジュールを追加する方法

<p align="center"><img src="https://github.com/user-attachments/assets/af642cec-7d26-49b3-9938-21102b6d3db7" alt="車モジュールのギャラリー" width="900"></p>

1. `src/vt/modules/lib_*.py` に、`@mod("名前", W=幅, H=高さ, cat="カテゴリ")` を付けた関数を追加する。関数は `fn(mesh, W, H, rng)` で、`Mesh`にフェース(材質名・UV付き)を足す。複数パターンは名前違いで `reg()` する。
2. 材質は `materials.py`(または `materials_b.py`)のマテリアル表に足す。テクスチャが要る場合は `textures*.py` で手続き生成し、`assets/textures/` に置いてコミットする。
3. `uv run python -c "from vt import usd_out; usd_out.write_all_modules()"` で `assets/modules/<名前>.usdc` を書き出す。
4. 建物なら `assemble.py` の様式から名前で参照する。ファニチャ/植栽/小物なら `furniture.py` / `vegetation.py` / `city_props.py` から配置する。
5. `scripts/render_gallery.py` でギャラリーレンダして見た目を確認し、`tests/` に最低限のテストを足す。

## レンダリング・確認用スクリプト

<p align="center"><img src="https://github.com/user-attachments/assets/305c0c9f-04d2-43c0-aff4-17abfe5a8768" alt="夜景(窓の発光・街灯・信号)" width="900"></p>

| スクリプト | 用途 |
|---|---|
| `scripts/render_gallery.py`, `render_extra_gallery.py` | モジュールのギャラリー(部品確認) |
| `scripts/render_styles.py` | 建物様式の一覧 |
| `scripts/render_veg_tiles.py` | 植生モジュールをタイル状に並べた画像 |
| `scripts/road_test_grid.py` | 道路・交差点のパターン確認 |
| `scripts/build_city.py --spot ...` | 数百m四方のスポット生成とレンダ |
| `scripts/probe_spots.py` | OSMからスポット座標を探す |

## Gitのルール

- 生成物のうち **モジュールUSD(`assets/modules`)・テクスチャ(`assets/textures`)・建物アセット(`assets/buildings`)はGit管理する**。
- レンダ画像(`out/**/*.png|jpg`, `out/render/`)、OSM/DEMのキャッシュ(`data/`)、`uv.lock` は管理しない。
- 巨大な最終USD(`out/usd/city_*`、地面/道路/線路のメッシュ)は原則Git管理しない。必要なら生成し直す。
- コミットメッセージは日本語。作業はdevブランチ。
- 配置ロジックを変えたら `out/cache` を消す(`build_extra.py` は `--no-cache` も可)。

## 既知の制約・残課題

- 人は低ポリで、3m以内の近接では不自然。車はフラットシェーディングで角張って見える箇所がある。
- 水面の反射で水平線が白飛びする視点がある。
- コンビナートの区画間パイプライン、非常階段から桁への渡り通路は未実装。
- 建物の高さ・階数はOSMタグ依存で、無い場合は推定(PLATEAUの3D都市モデル取り込みは未実施)。
- LOD(遠景簡略化)は未実装(手動で行う前提)。
- OSMのデータは完全ではないため、道路幅員・信号位置は実際と違う場合がある。
- 詳細な記録は `docs/` を参照。

## Terra(地形・自然の自動生成)

`src/terra/` は都市(`src/vt/`)の外側の地面・水系・植生を作る別パッケージ。実 DEM(国土地理院の標高タイル)と仮想地形(ノイズ・形状)を同じ Document に入れ、侵食 → 水系 → バイオーム → 散布 → USD / Blender まで通す。設計と進捗は `docs/terra/status.md`。実装済みは T0〜T3(道路・ダム・電線・タイル分割などは未実装)。

```bash
uv sync --extra terra
uv run terra generate recipes/terra/virtual_2km.yaml --out out/terra/v2k      # 仮想 2km 角(侵食・川・植生・岩。USD も出力)
uv run terra generate recipes/terra/fuji_foothills.yaml --out out/terra/fuji  # 実 DEM(初回は標高タイルを data/terra/ に取得)
uv run terra preview out/terra/v2k --overlay river,biome                      # トップダウンのハイトシェード
uv run terra export out/terra/v2k --usd --splat --geotiff --heightmap raw16
uv run python scripts/terra_render.py out/terra/v2k --view all -o out/terra/v2k --look photoreal   # Cycles(vt の写実カメラ設定を再利用)
uv run python scripts/terra_video.py out/terra/v2k --mode fly -o out/terra/v2k_fly.mp4
uv run python scripts/terra_stats.py out/terra/v2k out/terra/okutama           # 実 DEM との統計比較
```

- フォルダ: `src/terra/{core,source,gen,masks,erosion,hydro,biome,scatter,modules,export}`、レシピ `recipes/terra/`、小さなテクスチャ・岩の USD module `assets/terra/`、取得データ `data/terra/`(gitignore。出典と条件は `data/terra/SOURCES.md`)、テスト `tests/terra/`。
- レシピ(YAML)は `steps` に `名前: パラメータ` を並べる。ノードごとに入力ハッシュでキャッシュ(`<out>/.cache`。コードを直した時は `--no-cache`)。乱数は seed+ノード名で決定的。

```yaml
seed: 7
grid: {size_m: 2000, res_m: 2, crs: local}        # 実空間は center_lonlat: [lon, lat]
climate: {lat: 36.0, sea_level_temp_c: 15}
steps:
  - gen.noise: {kind: fbm, wavelength_m: 1100, base_height: 400, offset: 700, power: 1.4}
  - erosion.fluvial: {iterations: 30, k: 0.015}
  - erosion.hydraulic: {iterations: 120}
  - masks.slope: {}
  - hydro.flow: {}
  - hydro.rivers: {min_area_km2: 0.03}
  - biome.jp_forest: {}
  - scatter.trees: {r_m: 3.6, exclude: [river, lake]}
  - scatter.rocks: {cliff_deg: 54}
export: {usd: true, splat: true}
```

### Terra の詳細度プロファイル(near / far)と地質 module

- `--detail far`(既定): 全域を低ポリ(4m 間引き+全解像度の高さから焼いた法線マップ)で描き、散布を間引き、大気遠近(霞・青み)を強める。`--detail near --view near`: 視点周辺 約 220m 角を 0.5m 格子へ細分化し、微細な起伏(岩の角・層理・礫・土のこぶ)と高密度の散布を足す。`--detail legacy` は従来表示。
- `geology.zones` が岩種(花崗岩/安山岩/砂岩/石灰岩/凝灰岩)・土種(黒ボク/赤黄色土/粘土/砂質土/スコリア/マサ土/腐植/ぬかるみ)・苔/地衣類の付きやすさを作り、スプラット材質の土色・岩色と `scatter.rocks` / `scatter.ground` の module 選択に使う。
- 岩・土・砂利の module(`src/terra/modules/lib_rock_geo.py`, `lib_soil.py`, `lib_gravel.py`)は 約 450 個(各 near / `_far`)。一覧とポリ数は `docs/terra/modules_geo.md`、近接の違和感と対応は `docs/terra/closeup.md`。
  `uv run python scripts/terra_modules_build.py`(usdc 書き出し+一覧更新)、`scripts/terra_modules_sheet.py rocks|forms|soils|gravel|far`(コンタクトシート)、`scripts/terra_profiles.sh`(3 プロファイルのレンダと統計)。

### Terra の林床・針葉樹・キャッシュ

- 林床: `scatter.floor`(落ち葉の層・倒木・枯れ枝・ササ・シダの module `lib_floor.py`)と、地形材質の光斑(木漏れ日)・落ち葉の暖色化・苔の滑らかな縁。針葉樹(スギ・ヒノキ・シラビソ・カラマツ)は専用の葉アトラス(`scripts/terra_textures_conifer.py` で手続き生成)を使う。
- キャッシュ(`<out>/.cache`)のキーにはノードのサブパッケージと `core/` のコードの内容ハッシュが入るので、コードを変えると `--no-cache` なしで自動的に再計算される。

### Terra の道路(T4)

`infra.road` が 2 集落(レシピの `places`)の間に最小コスト経路で道路を引き、縦断勾配の上限(既定 10%)を守って切土・盛土し、谷・川は橋、尾根はトンネルにする。`infra.furniture` がガードレール・擁壁・落石防止網・カーブミラー・側溝(U 字溝/蓋付き)・縁石・橋桁・橋脚・坑口とトンネル内部(覆工・路面・照明)の module を置く。最小曲線半径は既定 15m(`infra.road.min_radius`)。`infra.village` は道路沿いに集落(家屋 3 種・納屋・畑・取り付け道)を作り敷地を整地する。木・低木・岩・林床は道路の伐採帯・坑口・集落を避けて散布される。
`recipes/terra/virtual_2km_road.yaml`、`uv run python scripts/terra_render.py <doc> --view road --detail near`、`scripts/terra_video.py <doc> --mode road`、`scripts/terra_road_compare.py`(道路あり/なしの前後比較)。仕組みと統計は `docs/terra/infra.md`、既定値(原文で確認できた数値は無く設計上の既定値)は `docs/terra/infra_defaults.md`。

## データの出典・ライセンス

- 地図データ: © OpenStreetMap contributors(ODbL)。このリポジトリの生成物のうちOSM由来の形状は、ODbLの帰属表示が必要。
- 標高: 国土地理院 基盤地図情報(DEM5m)。Terra の標高タイルは「国土地理院(地理院タイル)」https://maps.gsi.go.jp/development/ichiran.html を出典とする(条件は `data/terra/SOURCES.md`)。
- 葉テクスチャなど元素材の原本はコミットしていない(変換したアトラスのみ)。
- 店舗名・看板・ナンバーは架空。実在企業のロゴは使わない。

## 参考リンク

### UEのThe Matrix AwakensのProcedual生成の解説

- https://dev.epicgames.com/documentation/unreal-engine/city-sample-project-unreal-engine-demonstration?lang=ja
- https://dev.epicgames.com/documentation/unreal-engine/city-sample-quick-start-for-generating-a-city-and-freeway-using-houdini?lang=ja
- https://dev.epicgames.com/documentation/unreal-engine/city-sample-quick-start-for-generating-a-city-and-freeway-in-unreal-engine-5?lang=jam
