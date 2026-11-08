"""地質ゾーン・土種の ID と色(スプラット材質・module が共有)。色は目安の反射率(sRGB 0..1)。"""
import numpy as np

ROCKS = ["granite", "andesite", "sandstone", "limestone", "tuff"]       # geology 層の ID = 添字
ROCK_NAMES_JA = ["花崗岩", "安山岩/玄武岩", "砂岩/泥岩", "石灰岩", "凝灰岩"]
ROCK_TINT = np.array([[1.0, 1.0, 1.0], [0.75, 0.75, 0.78], [1.05, 0.95, 0.80], [1.1, 1.1, 1.05], [1.0, 0.96, 0.82]], np.float32)

SOILS = ["kuroboku", "redyellow", "clay", "sandy", "scoria", "masa", "humus", "mud"]   # soil_type 層の ID = 添字
SOIL_NAMES_JA = ["黒ボク土", "赤黄色土", "粘土", "砂質土", "火山灰・スコリア", "マサ土", "腐植・落葉層", "ぬかるみ"]
SOIL_ALBEDO = np.array([[0.19, 0.145, 0.11], [0.45, 0.25, 0.13], [0.50, 0.46, 0.35], [0.62, 0.54, 0.40], [0.20, 0.13, 0.10],
                        [0.62, 0.54, 0.45], [0.24, 0.16, 0.09], [0.22, 0.17, 0.12]], np.float32)
