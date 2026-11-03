# Procedual生成された東京/お台場都市

## 概要

- BlenderとPythonを使用して東京の建物、道路, 公共交通機関をProcedualに生成するプロジェクトです。
- 生成物はusdなどで出力され, 適切なフォルダ構成でgit管理される
- 道路モデルはOSMの地形データを使用
- UEのMatrixデモくらいフォトリアルにすること。現実と区別がつかないレベルでリアルな都市を生成することを目標とする

## 参考リンク

### UEのThe Matrix AwakensのProcedual生成の解説

- https://dev.epicgames.com/documentation/unreal-engine/city-sample-project-unreal-engine-demonstration?lang=ja
- https://dev.epicgames.com/documentation/unreal-engine/city-sample-quick-start-for-generating-a-city-and-freeway-using-houdini?lang=ja
- https://dev.epicgames.com/documentation/unreal-engine/city-sample-quick-start-for-generating-a-city-and-freeway-in-unreal-engine-5?lang=jam


## 建物生成

- moduleを複数作ってそれらを組み合わせることで多様な建物の生成を可能にする
- そのためにUSDを使ってモジュールを定義（複数のドア/窓/1span分の壁, 天井、意匠パネル, 柵、非常階段、ドア, 屋上設備など）
- 1つの建物でもフロアごとに階高が異なる(1階だけ天井高が高い、最上階だけ天井高が低いなど)場合があるので、フロアごとにモジュールを定義し,textureも切り替えることで多様なビル種類を生成する
- 天空率や射線制限を考慮して一部の建物は頂点部分がベベルされていたりする
- ベランダがあったり2Fまでと3F以降で意匠デザインが変わったり、途中で建物形状が変わったりetc...

## 道路生成

- 日本にあるような電灯,標識, 道路標示, 横断歩道, 車止め, ガードレールなども複数のモジュールを個別に生成
- 歩道, 横断歩道、車線や道路標示などもProcedualに生成できるようにすること。なおこれらはtextureで配置し、汚れやカスレも表現できるように
- その他看板、ベンチ、なども実装すること


## NOTE

- moduleを生成する時は非常にフォトリアルにすること. 
- PBRマテリアルを適当ようすること。汚れや傷なども適度に入れる
