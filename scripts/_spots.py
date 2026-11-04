"""build_city / build_realism 共有のスポット定義"""
SPOTS = {   # lon, lat
    "odaiba_intersection": (139.7762, 35.6272),
    "west_intersection": (139.7478, 35.6448),
    "west_highrise": (139.7468, 35.6425),
    "yurikamome": (139.77141, 35.62589),
    "shuto": (139.7585, 35.6410),
    "rainbow": (139.7606, 35.6374),         # 芝浦側の取り付け(アンカレイジ付近)
    "rainbow_pier": (139.7620, 35.6370),    # 橋脚・主塔付近(水上)

}
PRIORITY = {"yurikamome": ["station", "sidewalk", "roadway", "intersection"], "shuto": ["underdeck", "roadway", "sidewalk", "alley"],
            "rainbow": ["underdeck", "waterfront", "roadway", "sidewalk"], "rainbow_pier": ["waterfront", "underdeck", "roadway"], "west_highrise": ["sidewalk", "alley", "roadway", "intersection"]}
