"""高架道路(首都高)の細部の配置: 非常階段・非常電話・照明柱・案内標識/情報板・CCTV・ケーブルトレイ・伸縮装置下カバー、橋脚の縦樋/ハシゴ/番号板/足場金具/鳥よけネット/落橋防止。
bridges.elevated_roads から呼ばれ、Inst のリストを返す(座標は絶対z)。"""
import math
import random

from shapely.geometry import Point

from .assemble import Inst
from .world import frames

STAIR_H = 7.2


def pier_extras(x, y, ang, zg, zdeck, th, hw, kind, rng, on_land):
    """橋脚1基まわりの細部。ang=橋脚ローカル座標の回転(x=橋軸直角の右, y=橋軸)。bridges.pier と同じ寸法規則で柱位置を求める。"""
    H = zdeck - th - 0.28 - zg
    if H < 2.5:
        return []
    top = zdeck - th - 0.28
    d_cap = min(2.0, max(1.1, H * 0.22))
    col_top = top - d_cap
    hcol = col_top - zg
    cols = [0.0] if kind == "T" else [-hw * 0.55, hw * 0.55]
    cw, cl = (2.2, 2.0) if kind == "T" else (1.9, 1.8)
    c, s = math.cos(ang), math.sin(ang)
    out = []

    def put(name, lx, ly, z, rot, sx=1.0, sz=1.0):
        out.append(Inst(name, x + lx * c - ly * s, y + lx * s + ly * c, z, rot, sx, 1.0, sz))
    for ci, cx in enumerate(cols):
        face = rng.choice([1, -1])                                                   # 縦樋を付ける面(+y/-y)
        rot_f = ang if face > 0 else ang + math.pi
        if ci == 0 or rng.random() < 0.5:
            sg = rng.choice([-1, 1])                                                  # 縦樋は桁側の横引き管(中心線の左右)へつなぐ
            lx = cx + sg * (cw / 2 - 0.5)
            put("ex_downpipe", lx, face * (cl / 2 + 0.07), zg, rot_f, 1.0, max(0.3, (hcol - 0.6) / 10.0))
            arm = abs(sg * (hw - 0.72) - lx)
            if arm > 0.6:
                a_rot = ang if sg < 0 else ang + math.pi
                put("ex_downpipe_cross", lx, (cl / 2 + 0.07) if sg < 0 else -(cl / 2 + 0.07), zdeck - th - 0.18, a_rot, arm / 1.2)
        if rng.random() < 0.45:
            put("ex_pier_ladder", cx, -face * (cl / 2 + 0.07), zg + 0.0, ang + (math.pi if face > 0 else 0), 1.0, max(0.3, (hcol + 0.4) / 12.0))
        if rng.random() < 0.7:
            put("ex_pier_plate", cx, face * (cl / 2 + 0.05), zg + 2.2, rot_f)
        if hcol > 5 and rng.random() < 0.6:
            put("ex_scaffold_bracket", cx, face * (cl / 2 + 0.03), zg + hcol * 0.62, rot_f)
            put("ex_scaffold_bracket", cx, face * (cl / 2 + 0.03), zg + hcol * 0.25, rot_f)
    if on_land and rng.random() < 0.3:
        side = rng.choice([-1, 1])
        put("ex_sos_box", side * (max(abs(q) for q in cols) + cw / 2 + 1.5), 0.0, zg, ang - side * math.pi / 2)
    if rng.random() < 0.25:
        for sy in (1, -1):
            put("ex_bird_net", 0.0, sy * 0.9, zdeck - th - 0.02, ang + (0 if sy > 0 else math.pi))
    for sx in (-1, 1):
        put("ex_fall_prevent", sx * hw * 0.65, 0.0, top - 0.1, ang, 1.0, 0.3)
    if rng.random() < 0.3:
        put("ex_underdeck_lamp", 0.0, cl / 2 + 0.6, zdeck - th, ang)
    return out


def deck_details(e, pts, S, zs, hws, ths, ws, zf, land, steel):
    """1本の高架道路(edge)に沿う細部。戻り値=Instリスト"""
    rng = random.Random(e.id * 131 + 7)
    n = len(pts) - 1
    L = S[-1]
    fr = frames(pts)
    out = []

    def idx(s):
        return min(n, max(0, int(round(s / (L / n)))))

    def at(i, lat, z, rot_extra=0.0, name="", sx=1.0, sz=1.0, face_in=False):
        x, y, tx, ty, nx, ny = fr[i]
        h = math.atan2(ty, tx)
        out.append(Inst(name, x + nx * lat, y + ny * lat, z, h + rot_extra, sx, 1.0, sz))
    motorway = e.tags.get("highway") in ("motorway", "motorway_link", "trunk")
    if not motorway:
        return out
    # 照明柱: 30m毎の高欄ベースの片側ずつに。外側(+y)=路外
    for k, s in enumerate(range(20, int(L) - 10, 30)):
        i = idx(s)
        if ws[i] > 0.9 or k % 2:
            continue
        sg = 1 if (k // 2) % 2 == 0 else -1
        at(i, sg * (hws[i] - 0.21), zs[i] + 0.82, 0.0 if sg > 0 else math.pi, "ex_lightpole_hw")
    # 非常電話(250m毎)・CCTV(320m毎)・案内標識/情報板(500m毎)
    for k, s in enumerate(range(140, int(L) - 60, 250)):
        i = idx(s)
        if ws[i] < 0.5:
            at(i, hws[i] - 0.85, zs[i], math.pi, "ex_sos_box")
    for k, s in enumerate(range(220, int(L) - 60, 320)):
        i = idx(s)
        if ws[i] < 0.5:
            at(i, -(hws[i] - 0.4), zs[i] + 0.82, math.pi, "ex_cctv_pole")
    for k, s in enumerate(range(260, int(L) - 120, 520)):
        i = idx(s)
        if ws[i] < 0.5:
            at(i, -(hws[i] - 0.5), zs[i], math.pi / 2, "ex_vms" if k % 3 == 2 else "ex_sign_gantry")
    # 桁下のケーブルトレイ(6m毎)。橋脚付近を除く
    if rng.random() < 0.55:
        side = rng.choice([-0.3, 0.3])
        for s in range(12, int(L) - 12, 6):
            i = idx(s)
            if ws[i] > 0.3 or zs[i] - zf(*pts[i]) < 4.0:
                continue
            at(i, side * hws[i], zs[i] - ths[i], 0.0, "ex_cable_tray")
    # 伸縮装置の下の遮水カバー(90m毎)
    for s in sorted({*range(90, int(L) - 40, 90)}):
        i = idx(s)
        if ws[i] < 0.3:
            at(i, 0.0, zs[i] - ths[i], math.pi / 2, "ex_joint_cover", (2 * hws[i] - 1.0) / 3.8)
    # 非常階段: 陸上で桁下が4.5〜15mの所に(おおよそ500mに1基)
    cand = [i for i in range(4, n - 4) if ws[i] < 0.2 and land.contains(Point(*pts[i])) and 4.5 < zs[i] - zf(*pts[i]) < 15.0]
    if cand:
        for _ in range(max(1, int(L // 500))):
            i = rng.choice(cand)
            clear = zs[i] - zf(*pts[i])
            nst = max(1, round(clear / STAIR_H))
            sg = rng.choice([-1, 1])
            for k in range(nst):
                z0 = zf(*pts[i]) + k * clear / nst
                at(i, sg * (hws[i] + 4.9), z0, math.pi if sg > 0 else 0.0, "ex_emerg_stair", 1.0, clear / nst / STAIR_H)
    return out
