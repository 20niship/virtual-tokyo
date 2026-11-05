"""Anny 人物のマテリアル(肌・服・髪・目)。髪はグレースケール+アルファのカードテクスチャを色で乗算する(tint)。"""
from .materials import MATERIALS

STYLES = ["cortu_short_messy_hair", "cortu_straight_bangs", "culturalibre_hair_05", "toigo_blunt_bob", "toigo_blunt_bob_with_bangs", "toigo_inverted_bob",
          "toigo_inverted_bob_with_bangs", "toigo_curled_under_bob", "culturalibre_hair_06", "o4saken_long01"]
SKIN = ["#dcae8c", "#d4a27e", "#cb9a74", "#e2b896", "#c08c68", "#e0b090"]
COLORS = dict(white="#e8e8e4", black="#222428", navy="#24334f", gray="#7d8084", beige="#c8b898", red="#a83a3a", olive="#6a6a3a", blue="#3e6aa0", pink="#d89aa8", mustard="#c8a030",
              brown="#5a4030", khaki="#a89868", cream="#e4dcc4", lightblue="#9cb8d4", darkgreen="#2f4a38", purple="#6a4a80", orange="#d8782a", yellow="#e0c030")
HAIRC = dict(black="#181412", dark="#2a1c14", brown="#4a3020", gray="#a8a8a4", white="#d8d8d4", chestnut="#5a3a24", blond="#c8a860", auburn="#7a3a22",
             dyed_red="#a82838", pink="#d88aa8", blue="#3a5aa8", purple="#6a3a8a", silver="#b8bcc0", teal="#2a8a8a")

for _i, _c in enumerate(SKIN):
    MATERIALS[f"anny_skin_{_i}"] = dict(color=_c, rough=0.48, metal=0.0, skin=True)
for _k, _c in COLORS.items():
    MATERIALS[f"anny_cl_{_k}"] = dict(color=_c, rough=0.9, metal=0.0)
    MATERIALS[f"anny_shoe_{_k}"] = dict(color=_c, rough=0.6, metal=0.0)
for _k, _c in HAIRC.items():
    MATERIALS[f"anny_brow_{_k}"] = dict(color="#ffffff", rough=0.7, metal=0.0, tex="face_atlas.png", size=None, alpha=True, tint=_c, double_sided=True)
    MATERIALS[f"anny_stubble_{_k}"] = dict(color="#ffffff", rough=0.8, metal=0.0, tex="stubble.png", size=0.04, alpha=True, tint=_c, double_sided=True)
    MATERIALS[f"anny_beard_{_k}"] = dict(color=_c, rough=0.75, metal=0.0, hair=False)
    MATERIALS[f"anny_scalp_{_k}"] = dict(color=_c, rough=0.7, metal=0.0)
MATERIALS["anny_face"] = dict(color="#ffffff", rough=0.5, metal=0.0, tex="face_atlas.png", size=None, alpha=True, double_sided=True)
for _k, _c in dict(white="#e8e8e4", black="#1c1c1e", gum="#b8946a", brown="#3a2a20").items():
    MATERIALS[f"anny_sole_{_k}"] = dict(color=_c, rough=0.8, metal=0.0)
for _k, _c in dict(white="#f0f0ec", black="#18181a").items():
    MATERIALS[f"anny_lace_{_k}"] = dict(color=_c, rough=0.9, metal=0.0)
MATERIALS.update({
    "anny_eye_white": dict(color="#f0ede6", rough=0.25, metal=0.0), "anny_lip": dict(color="#b8706a", rough=0.5, metal=0.0),
    "anny_sclera": dict(color="#e8e4e0", rough=0.2, metal=0.0), "anny_iris": dict(color="#2a1a10", rough=0.15, metal=0.0),
    "anny_mouth": dict(color="#6a2a2a", rough=0.5, metal=0.0), "anny_eye_dark": dict(color="#3a2a22", rough=0.7, metal=0.0),
})
for _s in STYLES:
    for _k, _c in HAIRC.items():
        MATERIALS[f"anny_hair_{_s}_{_k}"] = dict(color="#ffffff", rough=0.55, metal=0.0, tex=f"anny_hair_{_s}.png", size=None, alpha=True, tint=_c, double_sided=True, hair=True, cutout=0.42)


# 生地(グレースケールのタイルを tint で着色、bump で織り目): (粗さ, bump, タイル[m])
FABRIC = dict(jersey=(0.85, 0.25, 0.10), knit=(0.95, 0.9, 0.10), denim=(0.88, 0.7, 0.12), twill=(0.85, 0.5, 0.10), pin=(0.8, 0.3, 0.10),
              check=(0.9, 0.3, 0.20), border=(0.9, 0.3, 0.12), linen=(0.92, 0.5, 0.12), wool=(0.9, 0.6, 0.12))
for _c, _hex in COLORS.items():
    for _f, (_r, _b, _sz) in FABRIC.items():
        MATERIALS[f"anny_cl_{_c}_{_f}"] = dict(color="#ffffff", rough=_r, metal=0.0, tex=f"fabric_{_f}.png", size=_sz, tint=_hex, bump=_b)
MATERIALS["anny_print"] = dict(color="#ffffff", rough=0.75, metal=0.0, tex="print_atlas.png", size=None, alpha=True, double_sided=True)
MATERIALS["anny_detail"] = dict(color="#ffffff", rough=0.8, metal=0.0, tex="detail_atlas.png", size=None, alpha=True, double_sided=True)
