"""人物モーション: Quaternius UAL(CC0)を Anny スケルトンへリターゲット+手続きクリップ。
クリップ = 各ボーンの局所回転(Anny の local-ref パラメータ、クォータニオン xyzw)+骨盤の平行移動。assets/humans/anim/<name>.npz に保存する。"""
import math
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as Rot

from . import humans as H

ROOT = H.ROOT
ANIM = ROOT / "assets/humans/anim"
MOCAP = ROOT / "data/humans/mocap/ual_clips.npz"
FPS = 24

# (出力名, UAL クリップ, 時間倍率, 振幅, ループ)
UAL_CLIPS = [("walk", "Walk_Loop", 1.0, 1.0, True), ("walk_slow", "Walk_Loop", 0.75, 0.7, True), ("walk_formal", "Walk_Formal_Loop", 1.0, 1.0, True),
             ("jog", "Jog_Fwd_Loop", 1.0, 1.0, True), ("run", "Sprint_Loop", 1.0, 1.0, True), ("idle", "Idle_Loop", 1.0, 1.0, True),
             ("talk", "Idle_Talking_Loop", 1.0, 1.0, True), ("sit", "Sitting_Idle_Loop", 1.0, 1.0, True), ("sit_talk", "Sitting_Talking_Loop", 1.0, 1.0, True),
             ("interact", "Interact", 1.0, 1.0, False), ("push", "Push_Loop", 1.0, 1.0, True)]


def _model():
    return H.model("anny")


def _parents():
    return list(_model().bone_parents)


def _mats(Q):
    return Rot.from_quat(Q.reshape(-1, 4)).as_matrix().reshape(Q.shape[:-1] + (3, 3))


def retarget_ual(clip, speed=1.0, amp=1.0, npz=None):
    """UAL の1クリップ → (Q[F,B,4], T[F,3])。ワールド回転の差分(A-pose 基準)を Anny の局所回転に直す"""
    z = npz if npz is not None else np.load(MOCAP)
    m = _model()
    L = m.bone_labels
    ub = [str(s) for s in z["bones"]]
    umap = {n.lower(): i for i, n in enumerate(ub)}
    idx = [umap[n.lower()] for n in L]
    ref, ref_h = z["A_TPose/rot"][0][idx], z["A_TPose/head"][0][idx]
    R, Hd = z[clip + "/rot"][:, idx], z[clip + "/head"][:, idx]
    r = H.run(dict(gender=0.5, age=0.5, muscle=0.5, weight=0.5, height=0.5, proportions=0.5, african=0.5, asian=0.5, caucasian=0.5, cupsize=0.5, firmness=0.5), "anny")
    ah = r["rest_bone_poses"][:, :3, 3]
    fu = (ref_h[L.index("ball_l")] - ref_h[L.index("foot_l")])[:2]
    fa = (ah[L.index("ball_l")] - ah[L.index("foot_l")])[:2]
    yaw = math.atan2(fa[1], fa[0]) - math.atan2(fu[1], fu[0])
    Yc = Rot.from_euler("z", yaw).as_matrix()
    D = np.einsum("fbij,bjk->fbik", R, np.linalg.inv(ref))
    D = Yc @ D @ Yc.T
    for side in ("l", "r"):
        a0 = ah[L.index("lowerarm_" + side)] - ah[L.index("upperarm_" + side)]
        u0 = Yc @ (ref_h[L.index("lowerarm_" + side)] - ref_h[L.index("upperarm_" + side)])
        a0, u0 = a0 / np.linalg.norm(a0), u0 / np.linalg.norm(u0)
        ax = np.cross(a0, u0)
        S = Rot.from_rotvec(ax / max(np.linalg.norm(ax), 1e-9) * math.acos(np.clip(a0 @ u0, -1, 1))).as_matrix()
        for i, n in enumerate(L):
            if n.endswith("_" + side) and n.split("_")[0] in ("upperarm", "lowerarm", "hand", "index", "middle", "ring", "pinky", "thumb"):
                D[:, i] = D[:, i] @ S
    if amp != 1.0:
        D = Rot.from_rotvec(Rot.from_matrix(D.reshape(-1, 3, 3)).as_rotvec() * amp).as_matrix().reshape(D.shape)
    par = _parents()
    P = np.empty_like(D)
    for b, p in enumerate(par):
        P[:, b] = D[:, b] if p < 0 else np.einsum("fji,fjk->fik", D[:, p], D[:, b])
    scale = (ah[L.index("head")][2] - ah[L.index("foot_l")][2]) / max(ref_h[L.index("head")][2] - ref_h[L.index("foot_l")][2], 1e-6)
    T = (Hd[:, L.index("pelvis")] - ref_h[L.index("pelvis")]) * scale
    T = (Yc @ T.T).T
    n = len(P)
    if clip not in ("Interact",) and n > 4:
        dots = np.abs((Rot.from_matrix(P[0].reshape(-1, 3, 3)).as_quat() * Rot.from_matrix(P[-1].reshape(-1, 3, 3)).as_quat()).sum(-1))
        if dots.min() > 0.999:        # 末尾フレームが先頭と同じ(ループ素材の重複)なら捨てて、ループの継ぎ目の止まりを無くす
            P, T, n = P[:-1], T[:-1], n - 1
    if speed != 1.0:
        k = max(2, int(round(n / speed)))
        src = np.linspace(0, n - 1, k)
        i0 = np.floor(src).astype(int)
        i1 = np.minimum(i0 + 1, n - 1)
        w = (src - i0)[:, None]
        q = Rot.from_matrix(P.reshape(-1, 3, 3)).as_quat().reshape(n, len(L), 4)
        q1 = q[i0]
        q2 = q[i1] * np.where((q1 * q[i1]).sum(-1, keepdims=True) < 0, -1, 1)
        Q = q1 * (1 - w[:, None]) + q2 * w[:, None]
        Q /= np.linalg.norm(Q, axis=-1, keepdims=True)
        return Q, T[i0] * (1 - w) + T[i1] * w
    return Rot.from_matrix(P.reshape(-1, 3, 3)).as_quat().reshape(n, len(L), 4), T


def _clip_from_pose_fn(fn, frames):
    """fn(phase 0..1) -> dict(ボーン名 -> 4x4(world軸回転)), 骨盤移動(3,) を frames 枚並べて Q,T にする"""
    L = _model().bone_labels
    Q = np.zeros((frames, len(L), 4)); Q[..., 3] = 1.0
    T = np.zeros((frames, 3))
    for f in range(frames):
        d, t = fn(f / frames)
        for n, M in d.items():
            Q[f, L.index(n)] = Rot.from_matrix(M[:3, :3]).as_quat()
        T[f] = t
    return Q, T


R = H._R


def _both(d, name, rots_l, extra=None):
    M = np.eye(4)
    for ax, deg in rots_l:
        M = M @ R(ax, deg)
    d[name + "_l"] = M @ d.get(name + "_l", np.eye(4))
    Mr = np.eye(4)
    for ax, deg in rots_l:
        Mr = Mr @ R(ax, -deg if ax in "yz" else deg)
    d[name + "_r"] = Mr @ d.get(name + "_r", np.eye(4))


def _base(d, arm=42, elbow=-12, fingers=True):
    _both(d, "upperarm", [("y", arm)])
    _both(d, "lowerarm", [("x", elbow)])
    if fingers:
        for fn in ("index", "middle", "ring", "pinky", "thumb"):
            for i, a in ((1, 12), (2, 20), (3, 16)):
                _both(d, f"{fn}_0{i}", [("x", -a)])


_REST = {}


def _rest_dirs():
    """中立体型の腕のレスト方向(upper→lower, lower→hand)。Anny座標(前=-y, 左腕=+x)"""
    if not _REST:
        r = H.run(dict(gender=0.5, age=0.5, muscle=0.5, weight=0.5, height=0.5, proportions=0.5, african=0.5, asian=0.5, caucasian=0.5, cupsize=0.5, firmness=0.5), "anny")
        L = _model().bone_labels
        h = r["rest_bone_poses"][:, :3, 3]
        for s_ in ("l", "r"):
            u = h[L.index("lowerarm_" + s_)] - h[L.index("upperarm_" + s_)]
            f = h[L.index("hand_" + s_)] - h[L.index("lowerarm_" + s_)]
            _REST[s_] = (u / np.linalg.norm(u), f / np.linalg.norm(f))
    return _REST


def _swing(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    ax = np.cross(a, b)
    n = np.linalg.norm(ax)
    if n < 1e-9:
        return np.eye(4) if a @ b > 0 else R("z", 180)
    M = np.eye(4)
    M[:3, :3] = Rot.from_rotvec(ax / n * math.acos(np.clip(a @ b, -1, 1))).as_matrix()
    return M


def _aim(d, side, du, df):
    """腕の向きを世界方向で指定(左腕 +x 側の値を書き、右腕は x を反転して渡す)。upperarm/lowerarm の局所回転を d に入れる"""
    u0, f0 = _rest_dirs()[side]
    Du = _swing(u0, du)
    Df = _swing(f0, df)
    d["upperarm_" + side] = Du
    d["lowerarm_" + side] = np.linalg.inv(Du) @ Df


def _arm(d, side, du, df):
    sg = 1.0 if side == "l" else -1.0
    _aim(d, side, (du[0] * sg, du[1], du[2]), (df[0] * sg, df[1], df[2]))


RELAXED = dict(index=(18, 28, 20), middle=(22, 32, 24), ring=(26, 36, 26), pinky=(30, 38, 26), thumb=(8, 10, 8))
SPREAD = dict(index=4, middle=0, ring=-4, pinky=-9, thumb=0)


def _fingers(d, curl=1.0):
    """指を軽く握った自然な形(人差し指〜小指の曲げ量を段階的に、わずかに扇状)"""
    for fn, ang in RELAXED.items():
        for i, a in enumerate(ang, 1):
            _both(d, f"{fn}_0{i}", [("x", -a * curl), ("z", SPREAD[fn] if i == 1 else 0)])


def relax_fingers(Q):
    """取り込んだクリップの指の回転を、軽く握った形に置き換える(UAL の指は T/A ポーズ基準で崩れやすい)"""
    L = _model().bone_labels
    d = {}
    _fingers(d)
    for n, M in d.items():
        Q[:, L.index(n)] = Rot.from_matrix(M[:3, :3]).as_quat()
    return Q


def _p_idle_hands(ph):
    """手待ち: 体の前で両手を組む(横断待ちなど)"""
    d, s = {}, math.sin(2 * math.pi * ph)
    for sd in ("l", "r"):
        _arm(d, sd, (0.12, -0.25, -0.96), (-0.45, -0.85, -0.25))
    _fingers(d)
    d["spine_02"] = R("x", 1.5 * s)
    d["head"] = R("z", 3 * math.sin(2 * math.pi * ph * 2))
    return d, np.array([0, 0, 0.004 * s])


def _p_phone(ph):
    """スマホ: 右手を顔の前へ、左腕は下ろす。頭は少し下向き"""
    d, s = {}, math.sin(2 * math.pi * ph)
    _arm(d, "l", (0.15, 0.0, -0.99), (0.05, -0.25, -0.96))
    _arm(d, "r", (0.15, -0.45, -0.88), (-0.2, -0.65, 0.73))
    _fingers(d)
    d["head"] = R("x", -14 + 1.5 * s)
    d["neck_01"] = R("x", -6)
    return d, np.array([0, 0, 0.003 * s])


def _p_wave(ph):
    """手を振る: 右腕を横に上げ前腕を立てて左右に振る"""
    d, s = {}, math.sin(2 * math.pi * ph * 2)
    _arm(d, "l", (0.15, 0.0, -0.99), (0.05, -0.25, -0.96))
    _arm(d, "r", (0.95, -0.1, 0.25), (0.25 + 0.4 * s, -0.1, 0.9))
    _fingers(d, 0.2)
    d["head"] = R("z", 4 * math.sin(2 * math.pi * ph))
    return d, np.zeros(3)


def _p_carry(ph):
    """荷物を持つ: 右手を下げて重みで体をわずかに傾ける"""
    d, s = {}, math.sin(2 * math.pi * ph)
    _arm(d, "l", (0.15, 0.0, -0.99), (0.05, -0.25, -0.96))
    _arm(d, "r", (0.08, 0.0, -1.0), (0.0, -0.2, -0.98))
    _fingers(d)
    d["spine_02"] = R("y", 3) @ R("x", 1 * s)
    return d, np.array([0, 0, 0.003 * s])


def _p_bike(ph):
    """自転車こぎ: 前傾して両手を前へ、脚を逆位相で回す。骨盤を下げる"""
    d = {}
    a = 2 * math.pi * ph
    for sd in ("l", "r"):
        _arm(d, sd, (0.15, -0.8, -0.55), (0.1, -0.95, -0.2))
    _fingers(d)
    d["spine_01"] = R("x", -10); d["spine_02"] = R("x", -10)
    d["head"] = R("x", 12)
    th_l, th_r = -50 + 28 * math.sin(a), -50 - 28 * math.sin(a)
    d["thigh_l"] = R("x", th_l); d["thigh_r"] = R("x", th_r)
    d["calf_l"] = R("x", 70 - 30 * math.sin(a) + 8); d["calf_r"] = R("x", 70 + 30 * math.sin(a) + 8)
    d["foot_l"] = R("x", -15); d["foot_r"] = R("x", -15)
    return d, np.array([0, 0.05, -0.2])


PROCEDURAL = [("idle_hands", _p_idle_hands, 72), ("idle_phone", _p_phone, 72), ("wave", _p_wave, 48), ("carry", _p_carry, 72), ("bike", _p_bike, 36)]


def make_all(npz=True):
    clips = {}
    z = np.load(MOCAP) if MOCAP.exists() else None
    if z is not None:
        for name, src, sp, amp, loop in UAL_CLIPS:
            if src + "/rot" in z:
                q, t = retarget_ual(src, sp, amp, z)
                clips[name] = (relax_fingers(q), t)
    for name, fn, n in PROCEDURAL:
        clips[name] = _clip_from_pose_fn(fn, n)
    return clips


def save(clips):
    ANIM.mkdir(parents=True, exist_ok=True)
    for n, (Q, T) in clips.items():
        np.savez_compressed(ANIM / f"{n}.npz", Q=Q.astype(np.float16), T=T.astype(np.float32))


_C = {}


def load(name):
    if name not in _C:
        z = np.load(ANIM / f"{name}.npz")
        _C[name] = (z["Q"].astype(np.float64), z["T"].astype(np.float64))
    return _C[name]


def names():
    return sorted(p.stem for p in ANIM.glob("*.npz"))


def pose_at(name, phase, rng=None):
    """クリップの位相 0..1 から (1,B,4,4) の torch 姿勢(パラメータ)。隣接フレームを線形補間"""
    import torch
    Q, T = load(name)
    n = len(Q)
    x = (phase % 1.0) * n
    i0 = int(x) % n
    i1 = (i0 + 1) % n
    w = x - int(x)
    q2 = Q[i1] * np.where((Q[i0] * Q[i1]).sum(-1, keepdims=True) < 0, -1, 1)
    q = Q[i0] * (1 - w) + q2 * w
    q /= np.linalg.norm(q, axis=-1, keepdims=True)
    M = np.tile(np.eye(4), (len(q), 1, 1))
    M[:, :3, :3] = Rot.from_quat(q).as_matrix()
    M[_model().bone_labels.index("pelvis"), :3, 3] = T[i0] * (1 - w) + T[i1] * w
    return torch.tensor(M, dtype=torch.float32)[None]


def write_usd(name, path=None, spec=None):
    """クリップを UsdSkel アニメ(中立体型のスケルトン)として assets/humans/anim/<name>.usdc へ。ヒーロー USD の Skel と同じジョイント名"""
    import torch
    from pxr import Gf, Sdf, Usd, UsdSkel, Vt
    from . import humans_usd as U
    path = Path(path or ANIM / f"{name}.usdc")
    m = _model()
    Q, T = load(name)
    spec = spec or H.sample(900, "casual", female=False)
    base = H.run(spec["p"], "anny")
    g = float(base["rest_vertices"][:, 2].min()) - 0.007
    Tm = U._T(g)
    names_ = list(m.bone_labels)
    joints = U._joint_paths(m.bone_parents, names_)
    st = Usd.Stage.CreateNew(str(path))
    st.SetStartTimeCode(0); st.SetEndTimeCode(len(Q) - 1); st.SetTimeCodesPerSecond(FPS)
    an = UsdSkel.Animation.Define(st, f"/{name}")
    st.SetDefaultPrim(an.GetPrim())
    an.CreateJointsAttr(Vt.TokenArray(joints))
    for f in range(len(Q)):
        r = H.run(spec["p"], "anny", pose_at(name, f / len(Q)))
        Wm = np.einsum("ij,bjk->bik", Tm, r["bone_poses"])
        loc = [Wm[i] if m.bone_parents[i] < 0 else np.linalg.inv(Wm[m.bone_parents[i]]) @ Wm[i] for i in range(len(names_))]
        q = Rot.from_matrix(np.array([l[:3, :3] for l in loc])).as_quat()
        an.GetTranslationsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*l[:3, 3]) for l in loc]), f)
        an.GetRotationsAttr().Set(Vt.QuatfArray([Gf.Quatf(float(x[3]), float(x[0]), float(x[1]), float(x[2])) for x in q]), f)
        an.GetScalesAttr().Set(Vt.Vec3hArray([Gf.Vec3h(1, 1, 1)] * len(loc)), f)
    st.GetRootLayer().Save()
    return path
