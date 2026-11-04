"""Anny 人物のマテリアル(肌・服・髪・目)。髪はグレースケール+アルファのカードテクスチャを色で乗算する(tint)。"""
from .materials import MATERIALS

STYLES = ["cortu_short_messy_hair", "cortu_straight_bangs", "culturalibre_hair_05", "toigo_blunt_bob", "toigo_blunt_bob_with_bangs", "toigo_inverted_bob",
          "toigo_inverted_bob_with_bangs", "toigo_curled_under_bob", "culturalibre_hair_06", "o4saken_long01"]
SKIN = ["#e7c3a3", "#dfb694", "#d8aa84", "#e9cdb2", "#cfa27b", "#eacbb0"]
COLORS = dict(white="#e8e8e4", black="#222428", navy="#24334f", gray="#7d8084", beige="#c8b898", red="#a83a3a", olive="#6a6a3a", blue="#3e6aa0", pink="#d89aa8", mustard="#c8a030",
              brown="#5a4030", khaki="#a89868", cream="#e4dcc4", lightblue="#9cb8d4", darkgreen="#2f4a38", purple="#6a4a80", orange="#d8782a", yellow="#e0c030")
HAIRC = dict(black="#181412", dark="#2a1c14", brown="#4a3020", gray="#a8a8a4", white="#d8d8d4", chestnut="#5a3a24")

for _i, _c in enumerate(SKIN):
    MATERIALS[f"anny_skin_{_i}"] = dict(color=_c, rough=0.55, metal=0.0)
for _k, _c in COLORS.items():
    MATERIALS[f"anny_cl_{_k}"] = dict(color=_c, rough=0.9, metal=0.0)
    MATERIALS[f"anny_shoe_{_k}"] = dict(color=_c, rough=0.6, metal=0.0)
for _k, _c in HAIRC.items():
    MATERIALS[f"anny_brow_{_k}"] = dict(color=_c, rough=0.7, metal=0.0)
MATERIALS.update({
    "anny_eye_white": dict(color="#f0ede6", rough=0.25, metal=0.0), "anny_lip": dict(color="#b8706a", rough=0.5, metal=0.0),
    "anny_sclera": dict(color="#e8e4e0", rough=0.2, metal=0.0), "anny_iris": dict(color="#2a1a10", rough=0.15, metal=0.0),
    "anny_mouth": dict(color="#6a2a2a", rough=0.5, metal=0.0), "anny_eye_dark": dict(color="#3a2a22", rough=0.7, metal=0.0),
})
for _s in STYLES:
    for _k, _c in HAIRC.items():
        MATERIALS[f"anny_hair_{_s}_{_k}"] = dict(color="#ffffff", rough=0.55, metal=0.0, tex=f"anny_hair_{_s}.png", size=None, alpha=True, tint=_c, double_sided=True)
