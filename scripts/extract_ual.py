"""Quaternius UAL(CC0)の glb から、各ボーンのワールド回転・位置をクリップごとに取り出す(bpy 使用)。
uv run python scripts/extract_ual.py [glb] -> data/humans/mocap/ual_clips.npz"""
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
GLB = sys.argv[1] if len(sys.argv) > 1 else str(next((ROOT / "data/humans/mocap/ual").glob("*/Unreal-Godot/UAL1_Standard.glb")))
CLIPS = ["A_TPose", "Idle_Loop", "Idle_Talking_Loop", "Walk_Loop", "Walk_Formal_Loop", "Jog_Fwd_Loop", "Sprint_Loop", "Sitting_Idle_Loop", "Sitting_Talking_Loop",
         "Idle_Torch_Loop", "Interact", "PickUp_Table", "Push_Loop", "Dance_Loop", "Driving_Loop", "Crouch_Idle_Loop"]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
names = [b.name for b in arm.pose.bones]
out = dict(bones=np.array(names))
for cn in CLIPS:
    act = bpy.data.actions.get(cn)
    if act is None:
        print("missing", cn)
        continue
    arm.animation_data.action = act
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    rot, head = [], []
    for f in range(f0, f1 + 1):
        bpy.context.scene.frame_set(f)
        M = [arm.matrix_world @ pb.matrix for pb in arm.pose.bones]
        rot.append([np.array(m.to_3x3()) for m in M])
        head.append([np.array(m.translation) for m in M])
    out[cn + "/rot"] = np.array(rot, dtype=np.float32)
    out[cn + "/head"] = np.array(head, dtype=np.float32)
    print(cn, len(rot), "frames")
(ROOT / "data/humans/mocap").mkdir(parents=True, exist_ok=True)
np.savez_compressed(ROOT / "data/humans/mocap/ual_clips.npz", **out)
