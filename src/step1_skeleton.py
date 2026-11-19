import re

import bpy

from step1_bone_map import (
    BASE_BONE_RENAME_MAP,
    FLATTEN_CONTROL_BONES,
    GARBAGE_BONE_KEYWORDS,
    build_vrm_humanoid_mappings,
    translate_non_ascii_bone_name,
)


def to_snake_case(name: str) -> str:
    return re.sub(r"([A-Z])", r"_\1", name).lower()


def is_ancestor(bone, maybe_ancestor):
    cur = bone.parent
    while cur:
        if cur == maybe_ancestor:
            return True
        cur = cur.parent
    return False


def collect_weighted_bone_names(armature_obj):
    weighted = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data or not obj.vertex_groups:
            continue
        bound = obj.parent == armature_obj or any(
            m.type == "ARMATURE" and m.object == armature_obj for m in obj.modifiers
        )
        if not bound:
            continue
        idx_to_name = {vg.index: vg.name for vg in obj.vertex_groups}
        for v in obj.data.vertices:
            for g in v.groups:
                if g.weight > 0.0001 and g.group in idx_to_name:
                    bname = idx_to_name[g.group]
                    weighted[bname] = weighted.get(bname, 0) + 1
    return weighted


def find_first_bone(bones_dict, candidates):
    for c in candidates:
        if c in bones_dict:
            return bones_dict[c]
    return None


def resolve_torso_chain(edit_bones, hips_b, neck_or_head_b, arm_l_b, arm_r_b):
    """从 Neck/Head 向上追溯到 Hips 的真实直线链，保证 Spine -> Chest -> UpperChest 严格合规"""
    if not hips_b or not neck_or_head_b:
        return {}

    chain = []
    cur = neck_or_head_b.parent
    while cur and cur != hips_b:
        chain.append(cur)
        cur = cur.parent
    if cur != hips_b:
        return {}
    chain.reverse()  # 从下到上：[Spine候选, ..., Neck下方]

    # 筛选同时是左右大臂与脖子祖先的躯干骨
    valid_torso = [
        b
        for b in chain
        if (not arm_l_b or b == arm_l_b or is_ancestor(arm_l_b, b))
        and (not arm_r_b or b == arm_r_b or is_ancestor(arm_r_b, b))
    ]
    if not valid_torso:
        valid_torso = chain

    res = {}
    if len(valid_torso) >= 1:
        res[valid_torso[0].name] = "Spine"
    if len(valid_torso) >= 2:
        res[valid_torso[1].name] = "Chest"
    if len(valid_torso) >= 3:
        res[valid_torso[-1].name] = "UpperChest"
    return res


def safe_rename_bone(armature_obj, bone, new_name, existing_names):
    old_name = bone.name
    if old_name == new_name or new_name in existing_names:
        return False
    bone.name = new_name
    existing_names.discard(old_name)
    existing_names.add(bone.name)
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.vertex_groups:
            continue
        bound = obj.parent == armature_obj or any(
            m.type == "ARMATURE" and m.object == armature_obj for m in obj.modifiers
        )
        if (
            bound
            and old_name in obj.vertex_groups
            and bone.name not in obj.vertex_groups
        ):
            obj.vertex_groups[old_name].name = bone.name
    return True


def validate_and_assign_vrm_humanoid(armature_obj):
    ext = getattr(armature_obj.data, "vrm_addon_extension", None)
    if not ext:
        return {}

    bones = armature_obj.data.bones
    map_vrm0, map_vrm1 = build_vrm_humanoid_mappings()

    # 严格按父子关系过滤，防止任何非法层级导致 VRM 导出崩溃
    resolved = {}
    for key, cands in map_vrm1.items():
        for c in cands:
            if c in bones:
                resolved[key] = c
                break

    hips = bones.get(resolved.get("hips", ""))
    spine = bones.get(resolved.get("spine", ""))
    chest = bones.get(resolved.get("chest", ""))
    upper_chest = bones.get(resolved.get("upperChest", ""))
    neck = bones.get(resolved.get("neck", ""))
    head = bones.get(resolved.get("head", ""))
    arm_l = bones.get(resolved.get("leftUpperArm", ""))
    arm_r = bones.get(resolved.get("rightUpperArm", ""))

    # 校验 UpperChest：必须是 Chest 后代，且是 Neck/Head/双臂的祖先
    if upper_chest:
        ok = (
            chest is not None
            and is_ancestor(upper_chest, chest)
            and (neck is None or is_ancestor(neck, upper_chest))
            and (head is None or is_ancestor(head, upper_chest))
            and (arm_l is None or is_ancestor(arm_l, upper_chest))
            and (arm_r is None or is_ancestor(arm_r, upper_chest))
        )
        if not ok:
            resolved.pop("upperChest", None)
            upper_chest = None

    top_torso = upper_chest or chest or spine or hips
    for side, uarm in (("left", arm_l), ("right", arm_r)):
        sh = bones.get(resolved.get(f"{side}Shoulder", ""))
        if sh and (
            not top_torso
            or not is_ancestor(sh, top_torso)
            or not uarm
            or not is_ancestor(uarm, sh)
        ):
            resolved.pop(f"{side}Shoulder", None)
        foot = bones.get(resolved.get(f"{side}Foot", ""))
        toes = bones.get(resolved.get(f"{side}Toes", ""))
        if toes and (not foot or not is_ancestor(toes, foot)):
            resolved.pop(f"{side}Toes", None)

    for eye_key in ("leftEye", "rightEye"):
        eye = bones.get(resolved.get(eye_key, ""))
        if eye and (not head or not is_ancestor(eye, head)):
            resolved.pop(eye_key, None)

    if hasattr(ext, "vrm0") and hasattr(ext.vrm0, "humanoid"):
        for hb in ext.vrm0.humanoid.human_bones:
            hb.node.bone_name = ""
            if hb.bone in resolved:
                hb.node.bone_name = resolved[hb.bone]
            elif hb.bone == "leftThumbProximal" and "leftThumbMetacarpal" in resolved:
                hb.node.bone_name = resolved["leftThumbMetacarpal"]
            elif hb.bone == "leftThumbIntermediate" and "leftThumbProximal" in resolved:
                hb.node.bone_name = resolved["leftThumbProximal"]
            elif hb.bone == "rightThumbProximal" and "rightThumbMetacarpal" in resolved:
                hb.node.bone_name = resolved["rightThumbMetacarpal"]
            elif (
                hb.bone == "rightThumbIntermediate" and "rightThumbProximal" in resolved
            ):
                hb.node.bone_name = resolved["rightThumbProximal"]

    if hasattr(ext, "vrm1") and hasattr(ext.vrm1, "humanoid"):
        h_bones = ext.vrm1.humanoid.human_bones
        for attr_name in map_vrm1:
            snake_attr = to_snake_case(attr_name)
            target_attr = (
                attr_name
                if hasattr(h_bones, attr_name)
                else (snake_attr if hasattr(h_bones, snake_attr) else None)
            )
            if not target_attr:
                continue
            hb_item = getattr(h_bones, target_attr)
            if hasattr(hb_item, "node"):
                hb_item.node.bone_name = resolved.get(attr_name, "")

    return resolved


def run(jp_model_name, en_model_name):
    print(">>> [步骤 1] 规整鸣潮 MMD 骨骼命名、校验躯干链路与层级拍平...")
    armature_obj = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    if armature_obj:
        weighted_bones = collect_weighted_bone_names(armature_obj)
        mmd_name_e_map = {}
        for pb in armature_obj.pose.bones:
            mmd_b = getattr(pb, "mmd_bone", None)
            if mmd_b and getattr(mmd_b, "name_e", ""):
                mmd_name_e_map[pb.name] = mmd_b.name_e
            for c in list(pb.constraints):
                pb.constraints.remove(c)

        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode="EDIT")
        eb = armature_obj.data.edit_bones

        use_leg_l_d = "左足D" in eb and weighted_bones.get(
            "左足D", 0
        ) >= weighted_bones.get("左足", 0)
        use_leg_r_d = "右足D" in eb and weighted_bones.get(
            "右足D", 0
        ) >= weighted_bones.get("右足", 0)
        use_arm_l_d = "左腕D" in eb and weighted_bones.get(
            "左腕D", 0
        ) >= weighted_bones.get("左腕", 0)
        use_arm_r_d = "右腕D" in eb and weighted_bones.get(
            "右腕D", 0
        ) >= weighted_bones.get("右腕", 0)

        to_remove = {
            b.name
            for b in eb
            if (
                any(kw in b.name for kw in GARBAGE_BONE_KEYWORDS)
                or b.name.endswith("IK")
            )
            and b.name not in weighted_bones
        }
        if use_leg_l_d:
            to_remove.update(
                d
                for d in ("左足", "左ひざ", "左足首", "左つま先")
                if d in eb and d not in weighted_bones
            )
        if use_leg_r_d:
            to_remove.update(
                d
                for d in ("右足", "右ひざ", "右足首", "右つま先")
                if d in eb and d not in weighted_bones
            )
        to_remove.update(
            c for c in FLATTEN_CONTROL_BONES if c in eb and c not in weighted_bones
        )

        for bn in list(to_remove):
            if bn in eb:
                p = eb[bn].parent
                for ch in list(eb[bn].children):
                    ch.parent = p
                eb.remove(eb[bn])

        root_b = find_first_bone(
            eb, ("Root", "全ての親", "全ての亲", "Position", "ParentNode")
        )
        hips_b = find_first_bone(
            eb, ("Hips", "Hip", "pelvis", "Bip001 Pelvis", "腰", "下半身", "LowerBody")
        )
        spine_b = find_first_bone(
            eb, ("Spine", "上半身", "UpperBody", "spine_01", "Bip001 Spine")
        )
        neck_b = find_first_bone(eb, ("Neck", "首", "脖子", "neck_01", "Bip001 Neck"))
        head_b = find_first_bone(eb, ("Head", "頭", "头", "head", "Bip001 Head"))
        arm_l_b = find_first_bone(
            eb,
            ("左腕D",)
            if use_arm_l_d
            else ("UpperArmL", "Arm_L", "左腕", "upperarm_l", "Bip001 L UpperArm"),
        )
        arm_r_b = find_first_bone(
            eb,
            ("右腕D",)
            if use_arm_r_d
            else ("UpperArmR", "Arm_R", "右腕", "upperarm_r", "Bip001 R UpperArm"),
        )

        if hips_b and root_b and hips_b != root_b:
            hips_b.parent = root_b
        if hips_b and spine_b and not is_ancestor(spine_b, hips_b):
            spine_b.parent = hips_b

        rename_map = dict(BASE_BONE_RENAME_MAP)
        if hips_b:
            rename_map[hips_b.name] = "Hips"
        rename_map.update(
            resolve_torso_chain(eb, hips_b, neck_b or head_b, arm_l_b, arm_r_b)
        )
        rename_map.update(
            {"左腕D": "UpperArmL", "左ひじD": "LowerArmL", "左手首D": "HandL"}
            if use_arm_l_d
            else {"左腕": "UpperArmL", "左ひじ": "LowerArmL", "左手首": "HandL"}
        )
        rename_map.update(
            {"右腕D": "UpperArmR", "右ひじD": "LowerArmR", "右手首D": "HandR"}
            if use_arm_r_d
            else {"右腕": "UpperArmR", "右ひじ": "LowerArmR", "右手首": "HandR"}
        )
        rename_map.update(
            {
                "左足D": "UpperLegL",
                "左ひざD": "LowerLegL",
                "左足首D": "FootL",
                "左足先EX": "ToesL",
            }
            if use_leg_l_d
            else {
                "左足": "UpperLegL",
                "左ひざ": "LowerLegL",
                "左足首": "FootL",
                "左つま先": "ToesL",
            }
        )
        rename_map.update(
            {
                "右足D": "UpperLegR",
                "右ひざD": "LowerLegR",
                "右足首D": "FootR",
                "右足先EX": "ToesR",
            }
            if use_leg_r_d
            else {
                "右足": "UpperLegR",
                "右ひざ": "LowerLegR",
                "右足首": "FootR",
                "右つま先": "ToesR",
            }
        )

        protected = set(rename_map.keys()) | set(rename_map.values())
        pruned_cnt = 0
        while True:
            leaves = [
                b.name
                for b in eb
                if len(b.children) == 0
                and b.name not in weighted_bones
                and b.name not in protected
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
            if not leaves:
                break
            for bn in leaves:
                eb.remove(eb[bn])
                pruned_cnt += 1

        bpy.ops.object.mode_set(mode="OBJECT")

        existing = {b.name for b in armature_obj.data.bones}
        renamed = 0
        for bone in list(armature_obj.data.bones):
            tgt = rename_map.get(bone.name)
            if not tgt or tgt == bone.name:
                continue
            if tgt in existing:
                occ = armature_obj.data.bones.get(tgt)
                if occ and occ.name not in rename_map:
                    tmp = f"Aux_{tgt}_old"
                    while tmp in existing:
                        tmp += "_"
                    if safe_rename_bone(armature_obj, occ, tmp, existing):
                        renamed += 1
            if safe_rename_bone(armature_obj, bone, tgt, existing):
                renamed += 1

        for bone in list(armature_obj.data.bones):
            if bone.name.isascii():
                continue
            old = bone.name
            base_en = translate_non_ascii_bone_name(old, mmd_name_e_map.get(old, ""))
            cand, idx = base_en, 1
            while cand in existing and cand != old:
                cand = f"{base_en}_{idx}"
                idx += 1
            if safe_rename_bone(armature_obj, bone, cand, existing):
                renamed += 1

        assigned = validate_and_assign_vrm_humanoid(armature_obj)
        final_w = collect_weighted_bone_names(armature_obj)
        core_check = {
            k: f"{assigned.get(k)}({final_w.get(assigned.get(k), 0)}v)"
            for k in (
                "hips",
                "spine",
                "chest",
                "upperChest",
                "head",
                "leftUpperArm",
                "rightUpperArm",
                "leftUpperLeg",
                "rightUpperLeg",
            )
            if k in assigned
        }
        print(
            f"   🦴 骨骼处理完成：保留 {len(armature_obj.data.bones)} 根，清理 {len(to_remove)}+{pruned_cnt} 根废骨，重命名 {renamed} 根。"
        )
        print(f"   ⚖️ [核心骨骼链路与权重] {core_check}")

    for coll_data in (
        bpy.data.objects,
        bpy.data.meshes,
        bpy.data.armatures,
        bpy.data.collections,
    ):
        for item in coll_data:
            if jp_model_name in item.name and not (
                coll_data is bpy.data.objects and re.search(r"\.\d+$", item.name)
            ):
                item.name = item.name.replace(jp_model_name, en_model_name)
    print("✅ [步骤 1] 骨骼与命名处理完成！")
