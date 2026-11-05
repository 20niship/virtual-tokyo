# 道路まわりのディテール(規格調査と採用寸法)

対象: `roads.py`(縁石/切り下げ/路面標示/誘導ブロック)・`road_extras.py`(排水/劣化)・`overlays.py`・`materials_b.py`。人物・車・建物は対象外。
調査は WebSearch で自治体/国交省の公開資料を確認(画像は参照のみ・取り込まない)。**確認できた値**と**確認できず慣例値を採用した値**を分けて書く。

## 確認できた規格(出典)

| 項目 | 規格値 | 出典 |
|---|---|---|
| 縁石(歩道)の高さ | 車道面から15cmを標準(交通安全上必要なら20cm、橋/トンネルは25cmまで) | 神戸市 https://www.city.kobe.lg.jp/documents/13647/02_03_01.pdf / 国交省 https://www.mlit.go.jp/kisha/kisha05/06/060203/03.pdf |
| 歩道の形式 | マウントアップ(縁石・歩道面とも原則15cm)/セミフラット(歩道面2cm)/フラット | 柏市 https://www.city.kashiwa.lg.jp/documents/4596/befor.pdf / 沖縄県 https://www.pref.okinawa.lg.jp/_res/projects/default_project/_page_/001/013/336/2018-03douro05.pdf |
| 車道との境界の段差(横断歩道/切下げ部) | 2cmを標準。すりつけ区間と車道の間に150cm以上の水平区間 | 神奈川県 https://pref.kanagawa.jp/documents/28484/42127.pdf |
| 切下げのすりつけ勾配 | 8%以下(開口4.2m以下)、10%以下の記載もあり。平坦部1.0m以上(横断勾配2%以下)、横断勾配1%以下(やむを得ない場合2%) | ふじみ野市 https://www.city.fujimino.saitama.jp/material/files/group/31/kirisagehyouzyun.pdf / 鎌倉市 https://www.city.kamakura.kanagawa.jp/douro/documents/douroho24shinsakijun.pdf / 川崎市 https://www.city.kawasaki.jp/530/cmsfiles/contents/0000071/71088/R02.06.hodou.pdf |
| 地先境界ブロック | 150×150×150×600mm | 埼玉県 https://www.pref.saitama.lg.jp/documents/30961/dourokouji_explanation.pdf |
| 誘導ブロック | JIS T 9251。点状=注意喚起(階段/傾斜路の端から30cm程度手前、分岐点)、線状=進行方向の案内、色は黄色が原則 | 埼玉県 https://www.pref.saitama.lg.jp/a0601/kokoronobf/tactilegroundsurfaceindicators.html / 大阪府 https://www.pref.osaka.lg.jp/documents/30294/26_annai_keiro.pdf |
| 横断歩道の白線 | 幅45cm。令和6年改正で間隔は45〜90cmに拡大(従来45〜50cm) | 神奈川県警の記事 https://www.kanaloco.jp/news/social/article-1136029.html / 青森県警 https://www.police.pref.aomori.jp/keimubu/soumu/jyouhou/5%20koutu_t.pdf/2.2060823%20hakusen_settikankaku.pdf |
| 区画線(ペイント) | 車道中央線 実線0.15〜0.20m・破線0.12〜0.15m(標準0.15m) | 国交省 https://www.mlit.go.jp/road/sign/kijyun/pdf/19741226kukakusenn.pdf |
| L型側溝 | プレキャストL型側溝 PL1(B250)=幅250mm・高さ100mm・長さ600mm | 長野県 https://www.pref.nagano.lg.jp/gijukan/infra/kensetsu/gijutsu/documents/hyo02douro.pdf |
| グレーチング | 歩道は細目(溝幅10mm)、車道は普通目(溝幅30mm) | 川崎市 https://www.city.kawasaki.jp/980/cmsfiles/contents/0000107/107099/010801-4.pdf |
| 蓋掛けU型側溝 | 250幅U型+蓋版(10m=10枚=1枚1m) | 広島市 https://www.city.hiroshima.lg.jp/_res/projects/default_project/_page_/001/054/017/1.pdf |

## 確認できなかった項目(慣例値を採用、要確認)

停止線の幅・外側線の幅・路側帯線の幅・導流帯/ゼブラゾーンの寸法・自転車横断帯・マンホール蓋の種別/紋様・ガードレール/ボラードの寸法・道路構造令の各条文は、検索結果から数値を直接確認できなかった。
既存実装の値(停止線0.45m級、ゼブラ0.45m/0.45m、マンホール径0.65m等)をそのまま使い、`道路標識、区画線及び道路標示に関する命令` 別表(e-Gov法令検索)での照合を残課題とする。

## 実装に採用した寸法

| 項目 | 採用値 | 実装 |
|---|---|---|
| 縁石高さ | 5/8cm(バリアフリー型)または12/15/18cm(`roads.Profile.curb_h`、既存) | `roads.py` |
| 縁石の面取り | 上端2cm(h>4cm の縁石のみ) | `_curb_faces` |
| 縁石天端幅 | 0.15m(地先境界ブロックの幅150mmに合わせる)。明るいコンクリ材 `curb_top` | `_curb_faces` |
| L型側溝 | 車道側に幅0.30m・路面+1.2cm の濃いコンクリ帯 `gutter_l`(PL1 B250 より少し広い余裕幅) | `_curb_faces` |
| 横断歩道部の段差 | 車道側+2cm(既存の `_ramp`、神奈川県の2cm標準と一致) | `_ramp` |
| 横断歩道 | 白線幅0.45m・間隔0.45m(既存)。令和6年の拡大間隔(最大0.9m)は未採用 | `_crossing` |
| 誘導ブロック | 30cm角・黄色。歩道は縁石から0.7m(中心)に線状、切下げ部縁に点状(既存) | `roads.py` |

## 既存で実装済みだった項目(今回は変更せず確認のみ)

車道の轍(`asphalt_rut`)・ひび(3種)・補修短冊/矩形パッチ・マンホール・グレーチング+集水桝(25〜40m間隔)・白線のかすれ(`paint_wear`)・縁石際の落ち葉/水たまり/油染み/タイヤ痕/掘削復旧帯/マンホール5種(`overlays.py`)・中央分離帯の植栽帯/ガード型・切下げ(`_ramp`)。

## 前後比較

`RENDER_ROOT=<tag> uv run python scripts/build_city.py --spot west_intersection --render --per 3 --round <N> --no-usd` → `out/render/<tag>/spots/west_intersection/round<N>/`(gitignore)。roadpre=変更前、roadpost=変更後。

## 残課題

- 歩道タイルの目地の不規則さ・欠け、点字ブロックの横断歩道前〜角の連続敷設、植樹桝の縁石、集水桝の鋳鉄蓋モジュール化は未実装。
- 上の「確認できなかった項目」の寸法照合。
