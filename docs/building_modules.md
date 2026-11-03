# 建物モジュール(フェーズA2: 実在建物ベースの追加)

## 調査メモ
| 建物類型 | 参照した実在例・資料 | 見分けポイント(モジュール化した要素) |
|---|---|---|
| 放送局・シンボル | フジテレビ本社(丹下健三 1996, 25F・123m, 球体展望室φ32m, 格子架構) | 大スパン格子フレーム、ガラス+金属パネル、コリドール → `x_brace_ext`, `double_skin_panel`, `curtain_*` |
| 大型商業 | アクアシティ/ダイバーシティ/デックス東京ビーチ(船モチーフ・ウッドデッキ) | 大庇、2層吹抜けガラス、サイン塔、ウッドデッキ手すり、外部エスカレーター → `mall_atrium_glass`, `mall_sign_tower`, `deck_wood_rail`, `escalator_tube` |
| 団地 | UR都市機構(階段室型/片廊下型/スターハウス/テラスハウス) | 階段室の縦長窓・ガラスブロック、片廊下の幾何柄面格子、隔て板、メーターBOX → `stairhall_*`, `corridor_geo_grille`, `bal_partition_board`, `meter_box_door` |
| 雑居ビル | 繁華街のテナントビル | 袖看板・壁面箱看板・室外機ラック・屋外非常階段・縦配管・テント → `sign_sode_*`, `ac_rack_wall_*`, `stair_ext_*`, `duct_vertical_pipes`, `awning_shop_stripe` |
| タワマン/ホテル | 湾岸の超高層住宅 | 連続ガラス手すりバルコニー、ルーバー隔て板、大庇、ユニットCW、機械室階ルーバー、頂部ルーバー冠 |
| 駐車場ビル | 商業施設併設 | 開放スロット、斜路面、メッシュ/ルーバーパネル、ゲート → `pk_*` |
| 物流倉庫 | 臨海部 | ドックシェルター、ドック庇、人用ドア、連続高窓、屋根モニター → `wh_*` |
| 屋上 | 共通 | ヘリポート、機械室、角型パネルタンク、基地局アンテナ、排気塔群、屋上看板、プランター |
| 小物建物 | 街角 | 自販機コーナー、ゴミ集積所、駐輪場、バス停上屋、売店、キュービクル、公衆トイレ、小屋、変電所、鳥居/石灯籠 |
| 戸建 | 住宅地 | 切妻/寄棟屋根(瓦・金属)、軒の出、玄関ポーチ、ガレージ → `house_*` + 勾配屋根 |

出典: フジテレビ施設情報(検索結果)、UR都市機構「団地100」資料、各施設の観光・公式情報。細部は一般的な日本建築の構成要素で補った(隔て板・メーターBOX・非常階段等は一次資料が見つからず、一般知識による)。

## 既存98種に対する不足と追加した83種(+窓バリエーション45種)
| カテゴリ | 追加モジュール |
|---|---|
| 看板 | sign_sode_2/4/6(袖看板), sign_tsukidashi_yoko, sign_wall_box, sign_roof_pylon, awning_shop_stripe, a_frame_sign, tenant_plate_board |
| 設備 | ac_rack_wall_2/4/6, ac_group_ground, duct_vertical_pipes, gas_meter_box, water_heater_unit |
| 階段 | stair_ext_zigzag(2層折返し), stair_ext_spiral(螺旋), stair_ext_straight_long |
| 団地 | stairhall_slit / glass_block / open, corridor_geo_grille, meter_box_door, bal_partition_board, bal_flat_old, mail_box_bank |
| タワー | bal_glass_continuous, bal_louver_partition, entrance_canopy_big, porch_stone_columns, curtain_unitized, fin_ceramic_vertical, mech_floor_louver, crown_louver_top, sky_lobby_glass |
| オフィス | glass_elevator_shaft, curtain_louver_band, double_skin_panel, x_brace_ext |
| 駐車場 | pk_slot_open, pk_slot_mesh, pk_louver_panel, pk_ramp_face, pk_entry_gate |
| 倉庫 | wh_dock_shelter, wh_canopy_dock, wh_man_door, wh_high_window_band, wh_roof_monitor, pallet_stack |
| 商業施設 | mall_atrium_glass, mall_sign_tower, escalator_tube, deck_wood_rail, flag_poles_3 |
| 屋上 | roof_helipad, roof_machine_room, water_tank_sq, roof_billboard, roof_telecom_cluster, exhaust_stack_group, roof_planter_row, roof_dish_pair |
| 小物建物(プレハブ) | bldg_vending_corner, bldg_trash_enclosure, bldg_bike_shed, bldg_bus_shelter, bldg_kiosk, bldg_cubicle, bldg_toilet, bldg_hut, bldg_substation |
| 小物 | vending_machine, vending_double, gate_slide, fence_block_span, hedge_planter, mailbox_post, torii_small, stone_lantern |
| 住宅 | house_entrance_porch, house_garage_shutter |
| 窓バリエーション | win_{sliding2,sliding4,fix,casement,high}_{bronze,black,white}_{spray,alc,tile} |

材質追加: alu_bronze, roof_tile, glass_green, ceramic, plant, sign_red/blue/white/yellow, vend_*, ground_slab。

## 手続き生成(assemble.py)
- レシピ(STYLES) 16種: office_glass, office_tile, tower_mansion, apartment, danchi_stair(階段室型), danchi_corridor(片廊下型), zakkyo(雑居ビル), commercial, mall, warehouse, parking, school, hotel, public, house, shrine。他に小面積/設備用の micro(プレハブ小物建物9種)。
- フロア帯: 1階 / 2〜n階(基壇 `f2`) / 中層 / 最上階(`top`) ごとに候補が違い、辺ごとに窓割り・意匠の挿入間隔(k)・色と壁材(window variant)を選ぶ。長辺/短辺で別レシピ(`variants`)。
- 付加部材(`extras`): 確率とフロア帯で袖看板・室外機ラック・縦配管・メーターBOX・テント等を貼る。特殊部材(`special`): 非常階段・EVシャフト・エスカレーター・サイン塔・頂部ルーバー・鳥居。
- 2階建て以下の長方形は切妻/寄棟の勾配屋根(瓦/金属、軒の出0.45m)。複数階モジュール(H≥1.7×階高)は複数階分に伸縮。セットバックの上層は別レシピ。
- すべて(OSM id, seed)固定で決定論的。USD出力は従来どおり PointInstancer。
