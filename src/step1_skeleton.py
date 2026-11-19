import re

import bpy


def to_snake_case(name: str) -> str:
    return re.sub(r"([A-Z])", r"_\1", name).lower()


def collect_weighted_bone_names(armature_obj):
    """统计所有网格中真正有蒙皮权重 (>0) 的顶点组名称"""
    weighted = set()
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data:
            continue
        bound = obj.parent == armature_obj or any(
            m.type == "ARMATURE" and m.object == armature_obj for m in obj.modifiers
        )
        if not bound or not obj.vertex_groups:
            continue

        idx_to_name = {vg.index: vg.name for vg in obj.vertex_groups}
        used_indices = set()
        for v in obj.data.vertices:
            for g in v.groups:
                if g.weight > 0.0001:
                    used_indices.add(g.group)
        for idx in used_indices:
            if idx in idx_to_name:
                weighted.add(idx_to_name[idx])
    return weighted


def build_vrm_humanoid_mappings():
    base = {
        "hips": ["Hips", "Hip", "腰", "下半身", "LowerBody", "pelvis", "Bip001 Pelvis"],
        "spine": ["Spine", "上半身", "UpperBody", "spine_01", "Bip001 Spine"],
        "chest": ["Chest", "上半身2", "UpperBody2", "胸", "spine_02", "Bip001 Spine1"],
        "upperChest": [
            "UpperChest",
            "上半身1",
            "上半身3",
            "UpperBody3",
            "spine_03",
            "Bip001 Spine2",
        ],
        "neck": ["Neck", "首", "脖子", "neck_01", "Bip001 Neck"],
        "head": ["Head", "頭", "头", "head", "Bip001 Head"],
        "leftEye": ["LeftEye", "EyeL", "Eye_L", "左目", "左眼", "eye_l"],
        "rightEye": ["RightEye", "EyeR", "Eye_R", "右目", "右眼", "eye_r"],
        "leftShoulder": [
            "ShoulderL",
            "Shoulder_L",
            "左肩",
            "clavicle_l",
            "Bip001 L Clavicle",
        ],
        "leftUpperArm": [
            "UpperArmL",
            "Arm_L",
            "左腕D",
            "左腕",
            "upperarm_l",
            "Bip001 L UpperArm",
        ],
        "leftLowerArm": [
            "LowerArmL",
            "Elbow_L",
            "左ひじD",
            "左ひじ",
            "lowerarm_l",
            "Bip001 L Forearm",
        ],
        "leftHand": [
            "HandL",
            "Wrist_L",
            "Hand_L",
            "左手首D",
            "左手首",
            "hand_l",
            "Bip001 L Hand",
        ],
        "rightShoulder": [
            "ShoulderR",
            "Shoulder_R",
            "右肩",
            "clavicle_r",
            "Bip001 R Clavicle",
        ],
        "rightUpperArm": [
            "UpperArmR",
            "Arm_R",
            "右腕D",
            "右腕",
            "upperarm_r",
            "Bip001 R UpperArm",
        ],
        "rightLowerArm": [
            "LowerArmR",
            "Elbow_R",
            "右ひじD",
            "右ひじ",
            "lowerarm_r",
            "Bip001 R Forearm",
        ],
        "rightHand": [
            "HandR",
            "Wrist_R",
            "Hand_R",
            "右手首D",
            "右手首",
            "hand_r",
            "Bip001 R Hand",
        ],
        "leftUpperLeg": [
            "UpperLegL",
            "Leg_L",
            "左足D",
            "左足",
            "thigh_l",
            "Bip001 L Thigh",
        ],
        "leftLowerLeg": [
            "LowerLegL",
            "Knee_L",
            "左ひざD",
            "左ひざ",
            "calf_l",
            "Bip001 L Calf",
        ],
        "leftFoot": [
            "FootL",
            "Ankle_L",
            "左足首D",
            "左足首",
            "foot_l",
            "Bip001 L Foot",
        ],
        "leftToes": [
            "ToesL",
            "Toe_L",
            "左足先EX",
            "左つま先",
            "ball_l",
            "Bip001 L Toe0",
        ],
        "rightUpperLeg": [
            "UpperLegR",
            "Leg_R",
            "右足D",
            "右足",
            "thigh_r",
            "Bip001 R Thigh",
        ],
        "rightLowerLeg": [
            "LowerLegR",
            "Knee_R",
            "右ひざD",
            "右ひざ",
            "calf_r",
            "Bip001 R Calf",
        ],
        "rightFoot": [
            "FootR",
            "Ankle_R",
            "右足首D",
            "右足首",
            "foot_r",
            "Bip001 R Foot",
        ],
        "rightToes": [
            "ToesR",
            "Toe_R",
            "右足先EX",
            "右つま先",
            "ball_r",
            "Bip001 R Toe0",
        ],
    }

    fingers_common = {
        "leftIndexProximal": [
            "IndexProximalL",
            "左人指１",
            "左人差指１",
            "左人指1",
            "IndexFinger1_L",
            "index_01_l",
            "Bip001 L Finger1",
        ],
        "leftIndexIntermediate": [
            "IndexIntermediateL",
            "左人指２",
            "左人差指２",
            "左人指2",
            "IndexFinger2_L",
            "index_02_l",
            "Bip001 L Finger11",
        ],
        "leftIndexDistal": [
            "IndexDistalL",
            "左人指３",
            "左人差指３",
            "左人指3",
            "IndexFinger3_L",
            "index_03_l",
            "Bip001 L Finger12",
        ],
        "leftMiddleProximal": [
            "MiddleProximalL",
            "左中指１",
            "左中指1",
            "MiddleFinger1_L",
            "middle_01_l",
            "Bip001 L Finger2",
        ],
        "leftMiddleIntermediate": [
            "MiddleIntermediateL",
            "左中指２",
            "左中指2",
            "MiddleFinger2_L",
            "middle_02_l",
            "Bip001 L Finger21",
        ],
        "leftMiddleDistal": [
            "MiddleDistalL",
            "左中指３",
            "左中指3",
            "MiddleFinger3_L",
            "middle_03_l",
            "Bip001 L Finger22",
        ],
        "leftRingProximal": [
            "RingProximalL",
            "左薬指１",
            "左薬指1",
            "RingFinger1_L",
            "ring_01_l",
            "Bip001 L Finger3",
        ],
        "leftRingIntermediate": [
            "RingIntermediateL",
            "左薬指２",
            "左薬指2",
            "RingFinger2_L",
            "ring_02_l",
            "Bip001 L Finger31",
        ],
        "leftRingDistal": [
            "RingDistalL",
            "左薬指３",
            "左薬指3",
            "RingFinger3_L",
            "ring_03_l",
            "Bip001 L Finger32",
        ],
        "leftLittleProximal": [
            "LittleProximalL",
            "左小指１",
            "左小指1",
            "LittleFinger1_L",
            "pinky_01_l",
            "Bip001 L Finger4",
        ],
        "leftLittleIntermediate": [
            "LittleIntermediateL",
            "左小指２",
            "左小指2",
            "LittleFinger2_L",
            "pinky_02_l",
            "Bip001 L Finger41",
        ],
        "leftLittleDistal": [
            "LittleDistalL",
            "左小指３",
            "左小指3",
            "LittleFinger3_L",
            "pinky_03_l",
            "Bip001 L Finger42",
        ],
        "rightIndexProximal": [
            "IndexProximalR",
            "右人指１",
            "右人差指１",
            "右人指1",
            "IndexFinger1_R",
            "index_01_r",
            "Bip001 R Finger1",
        ],
        "rightIndexIntermediate": [
            "IndexIntermediateR",
            "右人指２",
            "右人差指２",
            "右人指2",
            "IndexFinger2_R",
            "index_02_r",
            "Bip001 R Finger11",
        ],
        "rightIndexDistal": [
            "IndexDistalR",
            "右人指３",
            "右人差指３",
            "右人指3",
            "IndexFinger3_R",
            "index_03_r",
            "Bip001 R Finger12",
        ],
        "rightMiddleProximal": [
            "MiddleProximalR",
            "右中指１",
            "右中指1",
            "MiddleFinger1_R",
            "middle_01_r",
            "Bip001 R Finger2",
        ],
        "rightMiddleIntermediate": [
            "MiddleIntermediateR",
            "右中指２",
            "右中指2",
            "MiddleFinger2_R",
            "middle_02_r",
            "Bip001 R Finger21",
        ],
        "rightMiddleDistal": [
            "MiddleDistalR",
            "右中指３",
            "右中指3",
            "MiddleFinger3_R",
            "middle_03_r",
            "Bip001 R Finger22",
        ],
        "rightRingProximal": [
            "RingProximalR",
            "右薬指１",
            "右薬指1",
            "RingFinger1_R",
            "ring_01_r",
            "Bip001 R Finger3",
        ],
        "rightRingIntermediate": [
            "RingIntermediateR",
            "右薬指２",
            "右薬指2",
            "RingFinger2_R",
            "ring_02_r",
            "Bip001 R Finger31",
        ],
        "rightRingDistal": [
            "RingDistalR",
            "右薬指３",
            "右薬指3",
            "RingFinger3_R",
            "ring_03_r",
            "Bip001 R Finger32",
        ],
        "rightLittleProximal": [
            "LittleProximalR",
            "右小指１",
            "右小指1",
            "LittleFinger1_R",
            "pinky_01_r",
            "Bip001 R Finger4",
        ],
        "rightLittleIntermediate": [
            "LittleIntermediateR",
            "右小指２",
            "右小指2",
            "LittleFinger2_R",
            "pinky_02_r",
            "Bip001 R Finger41",
        ],
        "rightLittleDistal": [
            "LittleDistalR",
            "右小指３",
            "右小指3",
            "LittleFinger3_R",
            "pinky_03_r",
            "Bip001 R Finger42",
        ],
    }

    thumb_0 = [
        "Thumb0L",
        "左親指０",
        "左親指0",
        "Thumb0_L",
        "thumb_01_l",
        "Bip001 L Finger0",
    ]
    thumb_1 = [
        "Thumb1L",
        "左親指１",
        "左親指1",
        "Thumb1_L",
        "thumb_02_l",
        "Bip001 L Finger01",
    ]
    thumb_2 = [
        "Thumb2L",
        "左親指２",
        "左親指2",
        "Thumb2_L",
        "thumb_03_l",
        "Bip001 L Finger02",
    ]
    r_thumb_0 = [
        "Thumb0R",
        "右親指０",
        "右親指0",
        "Thumb0_R",
        "thumb_01_r",
        "Bip001 R Finger0",
    ]
    r_thumb_1 = [
        "Thumb1R",
        "右親指１",
        "右親指1",
        "Thumb1_R",
        "thumb_02_r",
        "Bip001 R Finger01",
    ]
    r_thumb_2 = [
        "Thumb2R",
        "右親指２",
        "右親指2",
        "Thumb2_R",
        "thumb_03_r",
        "Bip001 R Finger02",
    ]

    map_vrm0 = {
        **base,
        **fingers_common,
        "leftThumbProximal": thumb_0,
        "leftThumbIntermediate": thumb_1,
        "leftThumbDistal": thumb_2,
        "rightThumbProximal": r_thumb_0,
        "rightThumbIntermediate": r_thumb_1,
        "rightThumbDistal": r_thumb_2,
    }
    map_vrm1 = {
        **base,
        **fingers_common,
        "leftThumbMetacarpal": thumb_0,
        "leftThumbProximal": thumb_1,
        "leftThumbDistal": thumb_2,
        "rightThumbMetacarpal": r_thumb_0,
        "rightThumbProximal": r_thumb_1,
        "rightThumbDistal": r_thumb_2,
    }
    return map_vrm0, map_vrm1


def auto_assign_vrm_humanoid(armature_obj):
    ext = getattr(armature_obj.data, "vrm_addon_extension", None)
    if not ext:
        return

    map_vrm0, map_vrm1 = build_vrm_humanoid_mappings()

    if hasattr(ext, "vrm0") and hasattr(ext.vrm0, "humanoid"):
        for hb in ext.vrm0.humanoid.human_bones:
            vrm_key = hb.bone
            if vrm_key in map_vrm0:
                for candidate in map_vrm0[vrm_key]:
                    if candidate in armature_obj.data.bones:
                        hb.node.bone_name = candidate
                        break

    if hasattr(ext, "vrm1") and hasattr(ext.vrm1, "humanoid"):
        h_bones = ext.vrm1.humanoid.human_bones
        for attr_name, candidates in map_vrm1.items():
            snake_attr = to_snake_case(attr_name)
            target_attr = (
                attr_name
                if hasattr(h_bones, attr_name)
                else (snake_attr if hasattr(h_bones, snake_attr) else None)
            )
            if not target_attr:
                continue
            hb_item = getattr(h_bones, target_attr)
            for candidate in candidates:
                if candidate in armature_obj.data.bones:
                    if hasattr(hb_item, "node"):
                        hb_item.node.bone_name = candidate
                    break


def is_ancestor(bone, maybe_ancestor):
    cur = bone.parent
    while cur:
        if cur == maybe_ancestor:
            return True
        cur = cur.parent
    return False


def remove_bone_and_reparent_children(edit_bones, bone):
    parent = bone.parent
    for child in list(bone.children):
        child.parent = parent
    edit_bones.remove(bone)


def translate_non_ascii_bone_name(orig_name, mmd_name_e=""):
    if orig_name.isascii():
        return orig_name

    if mmd_name_e and mmd_name_e.isascii():
        clean_e = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", mmd_name_e).strip("_")
        if clean_e:
            return clean_e

    trans = orig_name.translate(str.maketrans("０１２３４５６７８９", "0123456789"))

    TOKEN_MAP = [
        ("腰キャンセル", "WaistCancel"),
        ("下半身", "Pelvis"),
        ("上半身", "UpperBody"),
        ("スカート", "Skirt"),
        ("リボン", "Ribbon"),
        ("マント", "Cape"),
        ("フリル", "Frill"),
        ("ネクタイ", "Tie"),
        ("ピアス", "Earring"),
        ("マフラー", "Scarf"),
        ("ツインテ", "TwinTail"),
        ("ポニー", "PonyTail"),
        ("アホ毛", "Ahoge"),
        ("もみあげ", "Sideburn"),
        ("前髪", "Bangs"),
        ("横髪", "SideHair"),
        ("後髪", "BackHair"),
        ("後ろ髪", "BackHair"),
        ("髪", "Hair"),
        ("发", "Hair"),
        ("頭花", "HeadFlower"),
        ("辮子", "Braid"),
        ("辫子", "Braid"),
        ("袖", "Sleeve"),
        ("尻尾", "Tail"),
        ("尾", "Tail"),
        ("耳", "Ear"),
        ("翼", "Wing"),
        ("羽", "Feather"),
        ("胸", "Bust"),
        ("肩", "Shoulder"),
        ("腕捩", "ArmTwist"),
        ("手捩", "HandTwist"),
        ("親指", "Thumb"),
        ("人差指", "Index"),
        ("人指", "Index"),
        ("中指", "Middle"),
        ("薬指", "Ring"),
        ("小指", "Little"),
        ("両目", "BothEyes"),
        ("目", "Eye"),
        ("眼", "Eye"),
        ("眉", "Brow"),
        ("口", "Mouth"),
        ("舌", "Tongue"),
        ("花", "Flower"),
        ("紐", "String"),
        ("帯", "Belt"),
        ("鎖", "Chain"),
        ("飾り", "Accessory"),
        ("飾", "Accessory"),
        ("左", "L_"),
        ("右", "R_"),
        ("前", "F_"),
        ("後", "B_"),
        ("横", "S_"),
        ("中", "M_"),
        ("上", "Up_"),
        ("下", "Dn_"),
        ("先", "Tip"),
        ("補助", "Aux"),
        ("ダミー", "Dummy"),
    ]
    for jp, en in TOKEN_MAP:
        trans = trans.replace(jp, en)

    trans = re.sub(r"[^\x00-\x7F]+", "_", trans)
    trans = re.sub(r"_+", "_", trans).strip("_")
    return trans or "AuxBone"


def run(jp_model_name, en_model_name):
    GARBAGE_BONE_KEYWORDS = [
        "Pole",
        "Target",
        "Handle",
        "mmd_shadow",
        "mmd_dummy",
        "dummy",
        "shadow",
        "IK_parent",
        "eye_control",
        "_end",
        "ＩＫ",
        "_IK",
        "IK_",
        "足IK",
        "つま先IK",
        "操作中心",
        "ビュー中心",
        "指先",
    ]

    FLATTEN_CONTROL_BONES = {
        "センター",
        "グルーブ",
        "グルーブ2",
        "グルーブ２",
        "腰キャンセル左",
        "腰キャンセル右",
        "腰キャンセルL",
        "腰キャンセルR",
        "Center",
        "Groove",
        "Groove2",
    }

    print(">>> [步骤 1] 规整鸣潮 MMD 骨骼命名、D-Bone 识别与层级拍平...")
    armature_obj = next(
        (obj for obj in bpy.data.objects if obj.type == "ARMATURE"), None
    )
    if armature_obj:
        weighted_bones = collect_weighted_bone_names(armature_obj)

        # 先记录 PMX 英文名并彻底清空全部 mmd_tools 骨骼约束，防止删 _shadow_/_dummy_ 时依赖图刷屏报错
        mmd_name_e_map = {}
        for pbone in armature_obj.pose.bones:
            mmd_b = getattr(pbone, "mmd_bone", None)
            if mmd_b and getattr(mmd_b, "name_e", ""):
                mmd_name_e_map[pbone.name] = mmd_b.name_e
            for c in list(pbone.constraints):
                pbone.constraints.remove(c)

        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode="EDIT")
        edit_bones = armature_obj.data.edit_bones

        has_left_leg_d = "左足D" in edit_bones
        has_right_leg_d = "右足D" in edit_bones
        has_left_arm_d = "左腕D" in edit_bones
        has_right_arm_d = "右腕D" in edit_bones

        bones_to_remove = {
            b.name
            for b in edit_bones
            if any(kw in b.name for kw in GARBAGE_BONE_KEYWORDS)
            or b.name.endswith("IK")
        }

        if has_left_leg_d:
            for drv in ("左足", "左ひざ", "左足首", "左つま先"):
                if drv in edit_bones and drv not in weighted_bones:
                    bones_to_remove.add(drv)
        if has_right_leg_d:
            for drv in ("右足", "右ひざ", "右足首", "右つま先"):
                if drv in edit_bones and drv not in weighted_bones:
                    bones_to_remove.add(drv)

        for ctrl_name in FLATTEN_CONTROL_BONES:
            if ctrl_name in edit_bones and ctrl_name not in weighted_bones:
                bones_to_remove.add(ctrl_name)

        for b_name in list(bones_to_remove):
            if b_name in edit_bones:
                remove_bone_and_reparent_children(edit_bones, edit_bones[b_name])

        root_b = (
            edit_bones.get("Root")
            or edit_bones.get("全ての親")
            or edit_bones.get("全ての亲")
            or edit_bones.get("Position")
            or edit_bones.get("ParentNode")
        )
        hips_b = (
            edit_bones.get("Hips")
            or edit_bones.get("Hip")
            or edit_bones.get("pelvis")
            or edit_bones.get("Bip001 Pelvis")
            or edit_bones.get("腰")
            or edit_bones.get("下半身")
            or edit_bones.get("LowerBody")
        )
        spine_b = (
            edit_bones.get("Spine")
            or edit_bones.get("上半身")
            or edit_bones.get("UpperBody")
            or edit_bones.get("spine_01")
            or edit_bones.get("Bip001 Spine")
        )

        if hips_b and root_b and hips_b != root_b:
            hips_b.parent = root_b

        if hips_b and spine_b and not is_ancestor(spine_b, hips_b):
            spine_b.parent = hips_b

        upper1_b = edit_bones.get("上半身1")
        upper2_b = edit_bones.get("上半身2")
        upper3_b = edit_bones.get("上半身3")
        chest_orig_name = None
        upper_chest_orig_name = None
        if upper2_b and upper1_b:
            if is_ancestor(upper1_b, upper2_b):
                chest_orig_name = "上半身2"
                upper_chest_orig_name = "上半身1"
            else:
                chest_orig_name = "上半身1"
                upper_chest_orig_name = "上半身2"
        elif upper2_b:
            chest_orig_name = "上半身2"
            if upper3_b:
                upper_chest_orig_name = "上半身3"

        hips_orig_name = hips_b.name if hips_b else None

        CUSTOM_BONE_MAP = {
            "Position": "Root",
            "全ての親": "Root",
            "全ての亲": "Root",
            "ParentNode": "Root",
            "root": "Root",
            "Hip": "Hips",
            "hips": "Hips",
            "pelvis": "Hips",
            "Bip001 Pelvis": "Hips",
            "Spine": "Spine",
            "上半身": "Spine",
            "UpperBody": "Spine",
            "spine": "Spine",
            "spine_01": "Spine",
            "Bip001 Spine": "Spine",
            "Chest": "Chest",
            "UpperBody2": "Chest",
            "胸": "Chest",
            "chest": "Chest",
            "spine_02": "Chest",
            "Bip001 Spine1": "Chest",
            "UpperBody3": "UpperChest",
            "upperChest": "UpperChest",
            "spine_03": "UpperChest",
            "Bip001 Spine2": "UpperChest",
            "Neck": "Neck",
            "首": "Neck",
            "脖子": "Neck",
            "neck": "Neck",
            "neck_01": "Neck",
            "Bip001 Neck": "Neck",
            "Head": "Head",
            "頭": "Head",
            "头": "Head",
            "head": "Head",
            "Bip001 Head": "Head",
            "左目": "LeftEye",
            "左眼": "LeftEye",
            "Eye_L": "LeftEye",
            "eye_l": "LeftEye",
            "右目": "RightEye",
            "右眼": "RightEye",
            "Eye_R": "RightEye",
            "eye_r": "RightEye",
            "Shoulder_L": "ShoulderL",
            "左肩": "ShoulderL",
            "leftShoulder": "ShoulderL",
            "clavicle_l": "ShoulderL",
            "Bip001 L Clavicle": "ShoulderL",
            "Shoulder_R": "ShoulderR",
            "右肩": "ShoulderR",
            "rightShoulder": "ShoulderR",
            "clavicle_r": "ShoulderR",
            "Bip001 R Clavicle": "ShoulderR",
            "Arm_L": "UpperArmL",
            "UpperArm_L": "UpperArmL",
            "leftUpperArm": "UpperArmL",
            "upperarm_l": "UpperArmL",
            "Bip001 L UpperArm": "UpperArmL",
            "Elbow_L": "LowerArmL",
            "LowerArm_L": "LowerArmL",
            "leftLowerArm": "LowerArmL",
            "lowerarm_l": "LowerArmL",
            "Bip001 L Forearm": "LowerArmL",
            "Wrist_L": "HandL",
            "Hand_L": "HandL",
            "leftHand": "HandL",
            "hand_l": "HandL",
            "Bip001 L Hand": "HandL",
            "Arm_R": "UpperArmR",
            "UpperArm_R": "UpperArmR",
            "rightUpperArm": "UpperArmR",
            "upperarm_r": "UpperArmR",
            "Bip001 R UpperArm": "UpperArmR",
            "Elbow_R": "LowerArmR",
            "LowerArm_R": "LowerArmR",
            "rightLowerArm": "LowerArmR",
            "lowerarm_r": "LowerArmR",
            "Bip001 R Forearm": "LowerArmR",
            "Wrist_R": "HandR",
            "Hand_R": "HandR",
            "rightHand": "HandR",
            "hand_r": "HandR",
            "Bip001 R Hand": "HandR",
            "Thigh_L": "UpperLegL",
            "Leg_L": "UpperLegL",
            "leftUpperLeg": "UpperLegL",
            "thigh_l": "UpperLegL",
            "Bip001 L Thigh": "UpperLegL",
            "Knee_L": "LowerLegL",
            "leftLowerLeg": "LowerLegL",
            "calf_l": "LowerLegL",
            "Bip001 L Calf": "LowerLegL",
            "Ankle_L": "FootL",
            "Foot_L": "FootL",
            "leftFoot": "FootL",
            "foot_l": "FootL",
            "Bip001 L Foot": "FootL",
            "Toe_L": "ToesL",
            "leftToes": "ToesL",
            "ball_l": "ToesL",
            "Bip001 L Toe0": "ToesL",
            "Thigh_R": "UpperLegR",
            "Leg_R": "UpperLegR",
            "rightUpperLeg": "UpperLegR",
            "thigh_r": "UpperLegR",
            "Bip001 R Thigh": "UpperLegR",
            "Knee_R": "LowerLegR",
            "rightLowerLeg": "LowerLegR",
            "calf_r": "LowerLegR",
            "Bip001 R Calf": "LowerLegR",
            "Ankle_R": "FootR",
            "Foot_R": "FootR",
            "rightFoot": "FootR",
            "foot_r": "FootR",
            "Bip001 R Foot": "FootR",
            "Toe_R": "ToesR",
            "rightToes": "ToesR",
            "ball_r": "ToesR",
            "Bip001 R Toe0": "ToesR",
            "左親指０": "Thumb0L",
            "左親指0": "Thumb0L",
            "Thumb0_L": "Thumb0L",
            "thumb_01_l": "Thumb0L",
            "左親指１": "Thumb1L",
            "左親指1": "Thumb1L",
            "Thumb1_L": "Thumb1L",
            "thumb_02_l": "Thumb1L",
            "左親指２": "Thumb2L",
            "左親指2": "Thumb2L",
            "Thumb2_L": "Thumb2L",
            "thumb_03_l": "Thumb2L",
            "左人指１": "IndexProximalL",
            "左人差指１": "IndexProximalL",
            "左人指1": "IndexProximalL",
            "IndexFinger1_L": "IndexProximalL",
            "index_01_l": "IndexProximalL",
            "左人指２": "IndexIntermediateL",
            "左人差指２": "IndexIntermediateL",
            "左人指2": "IndexIntermediateL",
            "IndexFinger2_L": "IndexIntermediateL",
            "index_02_l": "IndexIntermediateL",
            "左人指３": "IndexDistalL",
            "左人差指３": "IndexDistalL",
            "左人指3": "IndexDistalL",
            "IndexFinger3_L": "IndexDistalL",
            "index_03_l": "IndexDistalL",
            "左中指１": "MiddleProximalL",
            "左中指1": "MiddleProximalL",
            "MiddleFinger1_L": "MiddleProximalL",
            "middle_01_l": "MiddleProximalL",
            "左中指２": "MiddleIntermediateL",
            "左中指2": "MiddleIntermediateL",
            "MiddleFinger2_L": "MiddleIntermediateL",
            "middle_02_l": "MiddleIntermediateL",
            "左中指３": "MiddleDistalL",
            "左中指3": "MiddleDistalL",
            "MiddleFinger3_L": "MiddleDistalL",
            "middle_03_l": "MiddleDistalL",
            "左薬指１": "RingProximalL",
            "左薬指1": "RingProximalL",
            "RingFinger1_L": "RingProximalL",
            "ring_01_l": "RingProximalL",
            "左薬指２": "RingIntermediateL",
            "左薬指2": "RingIntermediateL",
            "RingFinger2_L": "RingIntermediateL",
            "ring_02_l": "RingIntermediateL",
            "左薬指３": "RingDistalL",
            "左薬指3": "RingDistalL",
            "RingFinger3_L": "RingDistalL",
            "ring_03_l": "RingDistalL",
            "左小指１": "LittleProximalL",
            "左小指1": "LittleProximalL",
            "LittleFinger1_L": "LittleProximalL",
            "pinky_01_l": "LittleProximalL",
            "左小指２": "LittleIntermediateL",
            "左小指2": "LittleIntermediateL",
            "LittleFinger2_L": "LittleIntermediateL",
            "pinky_02_l": "LittleIntermediateL",
            "左小指３": "LittleDistalL",
            "左小指3": "LittleDistalL",
            "LittleFinger3_L": "LittleDistalL",
            "pinky_03_l": "LittleDistalL",
            "右親指０": "Thumb0R",
            "右親指0": "Thumb0R",
            "Thumb0_R": "Thumb0R",
            "thumb_01_r": "Thumb0R",
            "右親指１": "Thumb1R",
            "右親指1": "Thumb1R",
            "Thumb1_R": "Thumb1R",
            "thumb_02_r": "Thumb1R",
            "右親指２": "Thumb2R",
            "右親指2": "Thumb2R",
            "Thumb2_R": "Thumb2R",
            "thumb_03_r": "Thumb2R",
            "右人指１": "IndexProximalR",
            "右人差指１": "IndexProximalR",
            "右人指1": "IndexProximalR",
            "IndexFinger1_R": "IndexProximalR",
            "index_01_r": "IndexProximalR",
            "右人指２": "IndexIntermediateR",
            "右人差指２": "IndexIntermediateR",
            "右人指2": "IndexIntermediateR",
            "IndexFinger2_R": "IndexIntermediateR",
            "index_02_r": "IndexIntermediateR",
            "右人指３": "IndexDistalR",
            "右人差指３": "IndexDistalR",
            "右人指3": "IndexDistalR",
            "IndexFinger3_R": "IndexDistalR",
            "index_03_r": "IndexDistalR",
            "右中指１": "MiddleProximalR",
            "右中指1": "MiddleProximalR",
            "MiddleFinger1_R": "MiddleProximalR",
            "middle_01_r": "MiddleProximalR",
            "右中指２": "MiddleIntermediateR",
            "右中指2": "MiddleIntermediateR",
            "MiddleFinger2_R": "MiddleIntermediateR",
            "middle_02_r": "MiddleIntermediateR",
            "右中指３": "MiddleDistalR",
            "右中指3": "MiddleDistalR",
            "MiddleFinger3_R": "MiddleDistalR",
            "middle_03_r": "MiddleDistalR",
            "右薬指１": "RingProximalR",
            "右薬指1": "RingProximalR",
            "RingFinger1_R": "RingProximalR",
            "ring_01_r": "RingProximalR",
            "右薬指２": "RingIntermediateR",
            "右薬指2": "RingIntermediateR",
            "RingFinger2_R": "RingIntermediateR",
            "ring_02_r": "RingIntermediateR",
            "右薬指３": "RingDistalR",
            "右薬指3": "RingDistalR",
            "RingFinger3_R": "RingDistalR",
            "ring_03_r": "RingDistalR",
            "右小指１": "LittleProximalR",
            "右小指1": "LittleProximalR",
            "LittleFinger1_R": "LittleProximalR",
            "pinky_01_r": "LittleProximalR",
            "右小指２": "LittleIntermediateR",
            "右小指2": "LittleIntermediateR",
            "LittleFinger2_R": "LittleIntermediateR",
            "pinky_02_r": "LittleIntermediateR",
            "右小指３": "LittleDistalR",
            "右小指3": "LittleDistalR",
            "LittleFinger3_R": "LittleDistalR",
            "pinky_03_r": "LittleDistalR",
        }

        if hips_orig_name:
            CUSTOM_BONE_MAP[hips_orig_name] = "Hips"
        if chest_orig_name:
            CUSTOM_BONE_MAP[chest_orig_name] = "Chest"
        if upper_chest_orig_name:
            CUSTOM_BONE_MAP[upper_chest_orig_name] = "UpperChest"

        if has_left_arm_d:
            CUSTOM_BONE_MAP.update(
                {"左腕D": "UpperArmL", "左ひじD": "LowerArmL", "左手首D": "HandL"}
            )
        else:
            CUSTOM_BONE_MAP.update(
                {"左腕": "UpperArmL", "左ひじ": "LowerArmL", "左手首": "HandL"}
            )
        if has_right_arm_d:
            CUSTOM_BONE_MAP.update(
                {"右腕D": "UpperArmR", "右ひじD": "LowerArmR", "右手首D": "HandR"}
            )
        else:
            CUSTOM_BONE_MAP.update(
                {"右腕": "UpperArmR", "右ひじ": "LowerArmR", "右手首": "HandR"}
            )

        if has_left_leg_d:
            CUSTOM_BONE_MAP.update(
                {
                    "左足D": "UpperLegL",
                    "左ひざD": "LowerLegL",
                    "左足首D": "FootL",
                    "左足先EX": "ToesL",
                }
            )
        else:
            CUSTOM_BONE_MAP.update(
                {
                    "左足": "UpperLegL",
                    "左ひざ": "LowerLegL",
                    "左足首": "FootL",
                    "左つま先": "ToesL",
                }
            )
        if has_right_leg_d:
            CUSTOM_BONE_MAP.update(
                {
                    "右足D": "UpperLegR",
                    "右ひざD": "LowerLegR",
                    "右足首D": "FootR",
                    "右足先EX": "ToesR",
                }
            )
        else:
            CUSTOM_BONE_MAP.update(
                {
                    "右足": "UpperLegR",
                    "右ひざ": "LowerLegR",
                    "右足首": "FootR",
                    "右つま先": "ToesR",
                }
            )

        protected_vrm_orig = set(CUSTOM_BONE_MAP.keys()) | set(CUSTOM_BONE_MAP.values())
        pruned_leaf_cnt = 0
        while True:
            to_prune = [
                b.name
                for b in edit_bones
                if len(b.children) == 0
                and b.name not in weighted_bones
                and b.name not in protected_vrm_orig
                and not any(
                    k in b.name
                    for k in (
                        "指",
                        "Thumb",
                        "Index",
                        "Middle",
                        "Ring",
                        "Little",
                        "Finger",
                        "目",
                        "Eye",
                    )
                )
            ]
            if not to_prune:
                break
            for bn in to_prune:
                if bn in edit_bones:
                    edit_bones.remove(edit_bones[bn])
                    pruned_leaf_cnt += 1

        bpy.ops.object.mode_set(mode="OBJECT")

        existing_bone_names = {b.name for b in armature_obj.data.bones}
        applied_renames = {}

        for bone in list(armature_obj.data.bones):
            target = CUSTOM_BONE_MAP.get(bone.name)
            if not target or target == bone.name:
                continue
            if target in existing_bone_names:
                occupant = armature_obj.data.bones.get(target)
                if occupant and occupant.name not in CUSTOM_BONE_MAP:
                    tmp_name = f"Aux_{target}_old"
                    occupant.name = tmp_name
                    existing_bone_names.discard(target)
                    existing_bone_names.add(tmp_name)
                    applied_renames[target] = tmp_name
            if target not in existing_bone_names:
                old_name = bone.name
                bone.name = target
                existing_bone_names.discard(old_name)
                existing_bone_names.add(target)
                applied_renames[old_name] = target

        for bone in list(armature_obj.data.bones):
            if bone.name.isascii():
                continue
            old_name = bone.name
            base_en = translate_non_ascii_bone_name(
                old_name, mmd_name_e_map.get(old_name, "")
            )
            cand = base_en
            idx = 1
            while cand in existing_bone_names and cand != old_name:
                cand = f"{base_en}_{idx}"
                idx += 1
            if cand != old_name:
                bone.name = cand
                existing_bone_names.discard(old_name)
                existing_bone_names.add(cand)
                applied_renames[old_name] = cand

        for child in bpy.data.objects:
            if child.type == "MESH" and (
                child.parent == armature_obj
                or any(
                    m.type == "ARMATURE" and m.object == armature_obj
                    for m in child.modifiers
                )
            ):
                for vg in child.vertex_groups:
                    if vg.name in applied_renames:
                        vg.name = applied_renames[vg.name]

        auto_assign_vrm_humanoid(armature_obj)
        print(
            f"   🦴 骨骼处理完成：保留 {len(armature_obj.data.bones)} 根骨骼，"
            f"清理 {len(bones_to_remove)} 根控制/IK骨 + {pruned_leaf_cnt} 根零权重末端骨，"
            f"完成 {len(applied_renames)} 个骨骼与顶点组英文化。"
        )

    for obj in bpy.data.objects:
        if jp_model_name in obj.name and not re.search(r"\.\d+$", obj.name):
            obj.name = obj.name.replace(jp_model_name, en_model_name)
    for mesh in bpy.data.meshes:
        if jp_model_name in mesh.name:
            mesh.name = mesh.name.replace(jp_model_name, en_model_name)
    for arm in bpy.data.armatures:
        if jp_model_name in arm.name:
            arm.name = arm.name.replace(jp_model_name, en_model_name)
    for coll in bpy.data.collections:
        if jp_model_name in coll.name:
            coll.name = coll.name.replace(jp_model_name, en_model_name)
    print("✅ [步骤 1] 骨骼与命名处理完成！")
