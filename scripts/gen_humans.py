"""Anny 人物の一括生成(前提: data/humans/pk に MakeHuman の asset pack を展開済み。docs/humans.md 参照)"""
import shutil
import sys
from pathlib import Path

from vt import humans as H
from vt import humans_usd as U
from vt import usd_out
from vt.modules import lib_anny
from vt.modules.library import REG, get

ROOT = Path(__file__).resolve().parents[1]
HERO = dict(office=4, casual=6, elder=3, student=4, kid=3, heavy=1, worker=3)

from vt import humans_motion as HM
from vt import textures_human as TX
print("hair textures:", len(H.make_hair_textures()), "fabrics:", len(TX.make_all()))
TX.make_face()
if "--no-anim" not in sys.argv:
    clips = HM.make_all() if HM.MOCAP.exists() else {}
    if clips:
        HM.save(clips)
    for n in HM.names():
        HM.write_usd(n)
    print("clips:", HM.names())

used, rows = {}, []
for g, n in lib_anny.GROUPS.items():
    for k in range(n):
        spec = lib_anny.spec_of(g, k)
        b = H.build(spec, topology=lib_anny.LOD, posename="idle")
        rows.append((spec["id"], spec["group"], spec["years"], "F" if spec["female"] else "M", round(b["rest"][:, 2].max() * 100 - b["rest"][:, 2].min() * 100, 1)))
        for c in b["cloth"]:
            cl = c["cl"]
            if cl["license"] == "procedural":
                continue
            assert cl["license"] in ("CC0", "CC BY 4.0"), (cl["path"], cl["license"])
            used[cl["path"]] = (cl["name"], cl["author"] if cl["author"] != "?" else Path(cl["path"]).parent.name.split("_")[0].capitalize(), cl["license"])

if "--no-modules" not in sys.argv:
    n = 0
    for name, r in REG.items():
        if name.startswith("anny_"):
            usd_out.write_module(name, get(name), r)
            n += 1
    print("modules:", n)

if "--no-heroes" not in sys.argv:
    for g, n in HERO.items():
        for k in range(n):
            spec = lib_anny.spec_of(g, k)
            p = U.write_hero(spec)
            for pose in ("idle", "walk"):
                U.write_baked(g, k, pose)
            print("hero", spec["id"], f"{p.stat().st_size / 1e6:.1f}MB")

lic = ROOT / "assets/humans/LICENSES"
lic.mkdir(parents=True, exist_ok=True)
import anny
d = Path(anny.__file__).parent
shutil.copy(d.parent / "anny-0.6.2.dist-info/licenses/LICENSE", lic / "Anny_LICENSE_Apache-2.0.txt")
shutil.copy(d / "data/mpfb2/LICENSE.md", lic / "MakeHuman_MPFB2_data_CC0.md")
with open(ROOT / "assets/humans/ATTRIBUTION.md", "w") as f:
    f.write("# 人物アセットの出典とライセンス\n\n- 体モデル: Anny (NAVER LABS Europe, Apache-2.0)。同梱の MakeHuman/MPFB2 由来データは CC0。`LICENSES/` に原文。\n"
            "- 服・髪: MakeHuman Community の asset pack のうち、`.mhclo` ヘッダに CC0 または CC BY 4.0 と明記されたものだけを使う(パック全体の表示は CC0 でも、個別ヘッダが AGPL3 のアセットがあるため除外)。CC BY 4.0 は下表の作者名の表示が必要。\n"
            "- SMPL-X 互換トポロジ(非商用)は使用していない。\n\n| 名前 | 作者 | ライセンス | 元ファイル |\n|---|---|---|---|\n")
    for p, (nm, au, li) in sorted(used.items()):
        f.write(f"| {nm} | {au} | {li} | `{p.split('data/humans/')[-1]}` |\n")
    f.write("\n## 生成した人物\n\n| id | group | 年齢 | 性別 | 身長[cm] |\n|---|---|---|---|---|\n")
    for r in rows:
        f.write("| " + " | ".join(map(str, r)) + " |\n")
print("done", len(rows), "people")
