import json
import math
import uuid

import bpy
from mathutils import Vector

from step1_bone_map import is_physics_or_spring_bone

SNAPSHOT_PROP = "ww_mmd_spring_snapshot"


def _call_vrm_op(op_name, **kwargs):
    op_ns = getattr(bpy.ops, "vrm", None)
    op = getattr(op_ns, op_name, None) if op_ns else None
    if op is None:
        return False
    try:
        valid_props = {p.identifier for p in op.get_rna_type().properties}
        filtered = {k: v for k, v in kwargs.items() if k in valid_props}
        return op("EXEC_DEFAULT", False, **filtered) == {"FINISHED"}
    except Exception:
        return False


def _get_sb1(armature_obj):
    return armature_obj.data.vrm_addon_extension.spring_bone1


def _set_enum_ci(prop_owner, prop_name, target):
    if not prop_owner or not hasattr(prop_owner, prop_name):
        return
    try:
        prop = prop_owner.bl_rna.properties.get(prop_name)
        if prop and prop.type == "ENUM":
            t_low = target.lower()
            for item in prop.enum_items:
                if item.identifier.lower() == t_low:
                    setattr(prop_owner, prop_name, item.identifier)
                    return
    except Exception:
        pass
    try:
        setattr(prop_owner, prop_name, target)
    except Exception:
        pass


def _ensure_uuid(item):
    if hasattr(item, "uuid"):
        cur = getattr(item, "uuid", "")
        if not cur:
            item.uuid = uuid.uuid4().hex
        return item.uuid
    return ""


def _collect_weighted_bones(armature_obj):
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


def _remap_mmd_collider_bone(bone_name, bones, weighted_bones):
    d_pairs = {
        "左足": "左足D",
        "左ひざ": "左ひざD",
        "左足首": "左足首D",
        "右足": "右足D",
        "右ひざ": "右ひざD",
        "右足首": "右足首D",
        "左腕": "左腕D",
        "左ひじ": "左ひじD",
        "左手首": "左手首D",
        "右腕": "右腕D",
        "右ひじ": "右ひじD",
        "右手首": "右手首D",
    }
    d_name = d_pairs.get(bone_name)
    if d_name and d_name in bones:
        if weighted_bones.get(d_name, 0) >= weighted_bones.get(bone_name, 0):
            return d_name
    return bone_name


def _get_mmd_rigid_dimensions(rb_obj):
    rb = getattr(rb_obj, "mmd_rigid", None)
    shape = str(getattr(rb, "shape", "SPHERE")).upper()
    rb_scale = rb_obj.matrix_world.to_scale()
    sx, sy, sz = abs(rb_scale.x), abs(rb_scale.y), abs(rb_scale.z)
    avg_scale = max(1e-5, (sx + sy + sz) / 3.0)

    if rb_obj.type == "MESH" and rb_obj.data and len(rb_obj.data.vertices) > 0:
        max_x = max(abs(v.co.x) for v in rb_obj.data.vertices) * sx
        max_y = max(abs(v.co.y) for v in rb_obj.data.vertices) * sy
        max_z = max(abs(v.co.z) for v in rb_obj.data.vertices) * sz
        if shape == "SPHERE":
            return "SPHERE", (max(max_x, max_y, max_z), 0.0, 0.0), (sx, sy, sz)
        if shape == "CAPSULE":
            r = max(max_x, max_y)
            half_h = max(0.0, max_z - r)
            return "CAPSULE", (r, half_h * 2.0, 0.0), (sx, sy, sz)
        return "BOX", (max_x, max_y, max_z), (sx, sy, sz)

    size = tuple(getattr(rb, "size", (0.05, 0.05, 0.05)))
    if shape == "SPHERE":
        return "SPHERE", (abs(size[0]) * avg_scale, 0.0, 0.0), (sx, sy, sz)
    if shape == "CAPSULE":
        return (
            "CAPSULE",
            (abs(size[0]) * max(sx, sy), abs(size[1]) * sz, 0.0),
            (sx, sy, sz),
        )
    return (
        "BOX",
        (abs(size[0]) * sx, abs(size[1]) * sy, abs(size[2]) * sz),
        (sx, sy, sz),
    )


def _compute_collider_local_spec(armature_obj, target_bone_name, rb_obj):
    bone = armature_obj.data.bones.get(target_bone_name)
    if not bone:
        return None

    shape, dims, (sx, sy, sz) = _get_mmd_rigid_dimensions(rb_obj)
    bone_world_mat = armature_obj.matrix_world @ bone.matrix_local
    bone_world_inv = bone_world_mat.inverted()
    b_scale = bone_world_mat.to_scale()
    avg_bone_scale = max(1e-5, (abs(b_scale.x) + abs(b_scale.y) + abs(b_scale.z)) / 3.0)

    if shape == "SPHERE":
        radius = max(0.005, dims[0] / avg_bone_scale)
        offset = bone_world_inv @ rb_obj.matrix_world.translation
        return {
            "bone": target_bone_name,
            "shape": "Sphere",
            "offset": [float(offset.x), float(offset.y), float(offset.z)],
            "radius": float(radius),
        }

    if shape == "CAPSULE":
        radius = max(0.005, dims[0] / avg_bone_scale)
        half_h_world = dims[1] * 0.5
        if half_h_world < 0.003:
            offset = bone_world_inv @ rb_obj.matrix_world.translation
            return {
                "bone": target_bone_name,
                "shape": "Sphere",
                "offset": [float(offset.x), float(offset.y), float(offset.z)],
                "radius": float(radius),
            }
        local_z = half_h_world / max(1e-5, sz)
        p_a = bone_world_inv @ (rb_obj.matrix_world @ Vector((0.0, 0.0, -local_z)))
        p_b = bone_world_inv @ (rb_obj.matrix_world @ Vector((0.0, 0.0, local_z)))
        return {
            "bone": target_bone_name,
            "shape": "Capsule",
            "offset": [float(p_a.x), float(p_a.y), float(p_a.z)],
            "tail": [float(p_b.x), float(p_b.y), float(p_b.z)],
            "radius": float(radius),
        }

    # BOX -> 近似为胶囊体或球体
    hx, hy, hz = dims
    axes = [(hx, 0, sx), (hy, 1, sy), (hz, 2, sz)]
    axes.sort(key=lambda x: x[0], reverse=True)
    longest, idx_max, s_max = axes[0]
    mid, smallest = axes[1][0], axes[2][0]

    if longest > mid * 1.35 and longest > 0.01:
        r_world = max(0.005, (mid + smallest) * 0.5)
        half_len_world = max(0.0, longest - r_world)
        local_vec = [0.0, 0.0, 0.0]
        local_vec[idx_max] = half_len_world / max(1e-5, s_max)
        v_pos = Vector(local_vec)
        p_a = bone_world_inv @ (rb_obj.matrix_world @ (-v_pos))
        p_b = bone_world_inv @ (rb_obj.matrix_world @ v_pos)
        return {
            "bone": target_bone_name,
            "shape": "Capsule",
            "offset": [float(p_a.x), float(p_a.y), float(p_a.z)],
            "tail": [float(p_b.x), float(p_b.y), float(p_b.z)],
            "radius": float(r_world / avg_bone_scale),
        }

    r_world = max(0.005, (hx + hy + hz) / 3.0)
    offset = bone_world_inv @ rb_obj.matrix_world.translation
    return {
        "bone": target_bone_name,
        "shape": "Sphere",
        "offset": [float(offset.x), float(offset.y), float(offset.z)],
        "radius": float(r_world / avg_bone_scale),
    }


def _compute_joint_params(bone_name, rb_obj, joint_obj):
    low = bone_name.lower()
    hit_radius = 0.025
    stiffness = 0.85
    drag_force = 0.45
    gravity_power = 0.35

    if rb_obj is not None:
        shape, dims, _ = _get_mmd_rigid_dimensions(rb_obj)
        hit_radius = (
            dims[0]
            if shape in ("SPHERE", "CAPSULE")
            else min(dims[0], dims[1], dims[2])
        )
        hit_radius = max(0.008, min(0.12, float(hit_radius)))
        ang_damp = float(getattr(rb_obj.mmd_rigid, "angular_damping", 0.5))
        drag_force = max(0.25, min(0.75, 0.30 + ang_damp * 0.40))

    if joint_obj is not None:
        mmd_j = getattr(joint_obj, "mmd_joint", None)
        if mmd_j and hasattr(mmd_j, "spring_angular"):
            avg_sp = sum(abs(float(x)) for x in mmd_j.spring_angular) / 3.0
            if avg_sp > 0.0:
                stiffness = min(3.2, max(0.35, 0.45 + 0.65 * math.log10(1.0 + avg_sp)))

    if any(k in low for k in ("胸", "bust", "boob", "oppai")):
        stiffness = max(stiffness, 1.8)
        drag_force = max(drag_force, 0.55)
        gravity_power = 0.15
    elif any(
        k in low for k in ("前髪", "bangs", "ahoge", "アホ毛", "sideburn", "もみあげ")
    ):
        stiffness = max(stiffness, 1.05)
        gravity_power = 0.25
    elif any(k in low for k in ("スカート", "skirt", "マント", "cape", "裾", "裙")):
        stiffness = min(max(stiffness, 0.55), 1.35)
        gravity_power = 0.45

    return float(hit_radius), float(stiffness), float(drag_force), float(gravity_power)


def _collect_linear_chains(roots, physics_bones):
    chains = []

    def walk(b, current_chain):
        current_chain.append(b)
        phys_children = [ch for ch in b.children if ch.name in physics_bones]
        if len(phys_children) == 1:
            walk(phys_children[0], current_chain)
        elif len(phys_children) > 1:
            walk(phys_children[0], current_chain)
            for extra_ch in phys_children[1:]:
                walk(extra_ch, [])
        else:
            tip_children = [
                ch
                for ch in b.children
                if ch.name not in physics_bones and not ch.children
            ]
            if len(tip_children) == 1:
                current_chain.append(tip_children[0])
            elif len(b.children) == 1 and b.children[0].name not in physics_bones:
                current_chain.append(b.children[0])
            if len(current_chain) >= 2:
                chains.append(current_chain)

    for r in roots:
        walk(r, [])
    return chains


def snapshot_mmd_physics_to_armature(armature_obj=None, overwrite=False):
    """
    在清理 MMD 刚体/关节之前，将物理链与碰撞体参数拍成轻量化 JSON 快照保存在骨骼上。
    这样 step1_skeleton 改名/合并骨骼时不会频繁触发 VRM 插件回调导致卡顿。
    """
    armature_obj = armature_obj or next(
        (o for o in bpy.data.objects if o.type == "ARMATURE"), None
    )
    if not armature_obj:
        return False
    if not overwrite and SNAPSHOT_PROP in armature_obj:
        return True

    bones = armature_obj.data.bones
    center_bone = next(
        (
            bones[c]
            for c in ("Root", "全ての親", "全ての亲", "Position", "ParentNode")
            if c in bones
        ),
        None,
    )
    center_bone_name = center_bone.name if center_bone else ""

    rigid_bodies = [
        o for o in bpy.data.objects if getattr(o, "mmd_type", "NONE") == "RIGID_BODY"
    ]
    joints = [o for o in bpy.data.objects if getattr(o, "mmd_type", "NONE") == "JOINT"]

    if not rigid_bodies:
        core_exclude = (
            "hips",
            "spine",
            "chest",
            "upperchest",
            "neck",
            "head",
            "pelvis",
            "root",
            "全ての親",
            "センター",
            "腰",
            "下半身",
            "上半身",
            "首",
            "頭",
            "头",
            "目",
            "eye",
            "指",
            "thumb",
            "index",
            "middle",
            "ring",
            "little",
            "腕",
            "ひじ",
            "手首",
            "足",
            "ひざ",
            "足首",
            "shoulder",
            "arm",
            "hand",
            "leg",
            "foot",
            "toe",
        )
        physics_bones = {
            b.name
            for b in bones
            if is_physics_or_spring_bone(b.name)
            and not any(ex in b.name.lower() for ex in core_exclude)
        }
        if not physics_bones:
            return False

        cols_by_group = {"0": []}
        for cands, rad, off in (
            (("Head", "頭", "头"), 0.095, [0.0, 0.08, 0.0]),
            (("UpperChest", "Chest", "上半身2", "上半身"), 0.11, [0.0, 0.06, 0.0]),
            (("Hips", "下半身", "腰", "Pelvis"), 0.11, [0.0, 0.0, 0.0]),
        ):
            b = next((bones[c] for c in cands if c in bones), None)
            if b:
                cols_by_group["0"].append(
                    {"bone": b.name, "shape": "Sphere", "offset": off, "radius": rad}
                )

        roots = [
            b
            for b in bones
            if b.name in physics_bones
            and (b.parent is None or b.parent.name not in physics_bones)
        ]
        chains = _collect_linear_chains(roots, physics_bones)
        springs = []
        for idx, ch in enumerate(chains):
            springs.append(
                {
                    "name": f"Spring_{ch[0].name}_{idx}",
                    "groups": ["0"] if cols_by_group["0"] else [],
                    "joints": [
                        {
                            "bone": b.name,
                            "params": list(_compute_joint_params(b.name, None, None)),
                        }
                        for b in ch
                    ],
                }
            )
        snap = {
            "mode": "heuristic",
            "center_bone": center_bone_name,
            "collider_groups": cols_by_group,
            "springs": springs,
        }
        armature_obj[SNAPSHOT_PROP] = json.dumps(snap, ensure_ascii=False)
        print(
            f"   🌸 [SpringBone 快照(启发式)] 已缓存 {len(springs)} 条弹簧链、"
            f"{len(cols_by_group['0'])} 个碰撞体，将在骨骼规整后写入 VRM。"
        )
        return True

    weighted_bones = _collect_weighted_bones(armature_obj)
    joint_by_rigid = {}
    for j_obj in joints:
        rbc = getattr(j_obj, "rigid_body_constraint", None)
        if rbc and rbc.object2:
            joint_by_rigid[rbc.object2] = j_obj

    cols_by_group = {}
    bone_to_rigid = {}
    col_count = 0

    for rb_obj in rigid_bodies:
        mmd_rb = getattr(rb_obj, "mmd_rigid", None)
        if not mmd_rb:
            continue
        raw_bone_name = getattr(mmd_rb, "bone", "")
        if not raw_bone_name or raw_bone_name not in bones:
            continue
        rb_type = str(getattr(mmd_rb, "type", "0"))
        if rb_type == "0":
            target_bone = _remap_mmd_collider_bone(raw_bone_name, bones, weighted_bones)
            spec = _compute_collider_local_spec(armature_obj, target_bone, rb_obj)
            if spec is not None:
                grp_key = str(int(getattr(mmd_rb, "collision_group_number", 0)))
                cols_by_group.setdefault(grp_key, []).append(spec)
                col_count += 1
        else:
            prev = bone_to_rigid.get(raw_bone_name)
            if prev is None or (
                str(getattr(prev.mmd_rigid, "type", "1")) == "1" and rb_type == "2"
            ):
                bone_to_rigid[raw_bone_name] = rb_obj

    humanoid_core = {
        "Hips",
        "Spine",
        "Chest",
        "UpperChest",
        "Neck",
        "Head",
        "全ての親",
        "全ての亲",
        "センター",
        "下半身",
        "上半身",
        "上半身2",
        "首",
        "頭",
        "头",
    }
    physics_bones = {b for b in bone_to_rigid if b not in humanoid_core}
    roots = [
        b
        for b in bones
        if b.name in physics_bones
        and (b.parent is None or b.parent.name not in physics_bones)
    ]
    chains = _collect_linear_chains(roots, physics_bones)

    springs = []
    total_joints = 0
    for idx, ch in enumerate(chains):
        active_grps = set()
        joint_specs = []
        for b in ch:
            rb_obj = bone_to_rigid.get(b.name)
            j_obj = joint_by_rigid.get(rb_obj) if rb_obj else None
            joint_specs.append(
                {
                    "bone": b.name,
                    "params": list(_compute_joint_params(b.name, rb_obj, j_obj)),
                }
            )
            if rb_obj:
                mask = getattr(rb_obj.mmd_rigid, "collision_group_mask", None)
                if mask is None:
                    active_grps.update(cols_by_group.keys())
                else:
                    for g_key in cols_by_group:
                        g_num = int(g_key)
                        if g_num < len(mask) and not mask[g_num]:
                            active_grps.add(g_key)
        total_joints += len(joint_specs)
        springs.append(
            {
                "name": f"Spring_{ch[0].name}_{idx}",
                "groups": sorted(active_grps, key=lambda x: int(x)),
                "joints": joint_specs,
            }
        )

    snap = {
        "mode": "mmd",
        "center_bone": center_bone_name,
        "collider_groups": cols_by_group,
        "springs": springs,
    }
    armature_obj[SNAPSHOT_PROP] = json.dumps(snap, ensure_ascii=False)
    print(
        f"   🌸 [SpringBone 快照] 已从 MMD 刚体/关节缓存：{len(springs)} 条弹簧链"
        f"（{total_joints} 个关节），{col_count} 个碰撞体（{len(cols_by_group)} 组），"
        f"将在骨骼规整后写入 VRM。"
    )
    return True


def get_snapshot_spring_bone_names(armature_obj):
    if not armature_obj or SNAPSHOT_PROP not in armature_obj:
        return set()
    try:
        snap = json.loads(armature_obj[SNAPSHOT_PROP])
    except Exception:
        return set()

    names = set()
    if snap.get("center_bone"):
        names.add(snap["center_bone"])
    for cols in snap.get("collider_groups", {}).values():
        for c in cols:
            if c.get("bone"):
                names.add(c["bone"])
    for sp in snap.get("springs", []):
        for j in sp.get("joints", []):
            if j.get("bone"):
                names.add(j["bone"])
    return names


def _create_vrm1_collider_entry(armature_obj, bone_name):
    before_len = len(_get_sb1(armature_obj).colliders)
    ok = _call_vrm_op(
        "add_spring_bone1_collider",
        armature_object_name=armature_obj.name,
        armature_name=armature_obj.name,
        bone_name=bone_name,
    )
    sb1 = _get_sb1(armature_obj)
    col = (
        sb1.colliders[-1]
        if (ok and len(sb1.colliders) > before_len)
        else sb1.colliders.add()
    )
    _ensure_uuid(col)

    if hasattr(col, "bpy_object") and col.bpy_object is None:
        empty = bpy.data.objects.new(f"VRM_Collider_{bone_name}", None)
        empty.empty_display_type = "SPHERE"
        empty.hide_render = True
        bpy.context.scene.collection.objects.link(empty)
        empty.parent = armature_obj
        empty.parent_type = "BONE"
        empty.parent_bone = bone_name
        col.bpy_object = empty

    if hasattr(col, "node") and hasattr(col.node, "bone_name"):
        col.node.bone_name = bone_name
    return col


def apply_mmd_spring_snapshot_to_vrm(armature_obj, rename_map=None, overwrite=True):
    """将步骤 0 缓存的物理快照（按最终骨骼名重映射后）一次性写入 VRM spring_bone1。"""
    if not armature_obj or SNAPSHOT_PROP not in armature_obj:
        return 0, 0
    ext = getattr(armature_obj.data, "vrm_addon_extension", None)
    if not ext or not hasattr(ext, "spring_bone1"):
        return 0, 0

    try:
        snap = json.loads(armature_obj[SNAPSHOT_PROP])
    except Exception:
        return 0, 0

    rename_map = rename_map or {}
    bones = armature_obj.data.bones
    ext.spec_version = "1.0"
    sb1 = _get_sb1(armature_obj)
    if overwrite:
        sb1.springs.clear()
        sb1.collider_groups.clear()
        sb1.colliders.clear()

    try:
        bpy.context.view_layer.objects.active = armature_obj
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
    except Exception:
        pass

    def resolve_bone(bname):
        return rename_map.get(bname, bname)

    # 1. 创建全部碰撞体（仅保存 uuid, name）
    group_to_col_refs = {}
    col_count = 0
    for grp_key, col_specs in sorted(
        snap.get("collider_groups", {}).items(), key=lambda x: int(x[0])
    ):
        for spec in col_specs:
            bname = resolve_bone(spec["bone"])
            if bname not in bones:
                continue
            col = _create_vrm1_collider_entry(armature_obj, bname)
            if spec["shape"] == "Capsule":
                _set_enum_ci(col, "shape_type", "Capsule")
                col.shape.capsule.offset = tuple(spec["offset"])
                col.shape.capsule.tail = tuple(spec["tail"])
                col.shape.capsule.radius = float(spec["radius"])
            else:
                _set_enum_ci(col, "shape_type", "Sphere")
                col.shape.sphere.offset = tuple(spec["offset"])
                col.shape.sphere.radius = float(spec["radius"])
            group_to_col_refs.setdefault(grp_key, []).append(
                (_ensure_uuid(col), getattr(col, "name", ""))
            )
            col_count += 1

    # 2. 通过 .add() 创建 ColliderGroups
    sb1 = _get_sb1(armature_obj)
    group_to_cg_ref = {}
    for grp_key, col_refs in sorted(group_to_col_refs.items(), key=lambda x: int(x[0])):
        cg = sb1.collider_groups.add()
        cg_uuid = _ensure_uuid(cg)
        cg_name = f"MMD_Group_{grp_key}"
        if hasattr(cg, "vrm_name"):
            cg.vrm_name = cg_name
        elif hasattr(cg, "name"):
            cg.name = cg_name
        for col_uuid, col_name in col_refs:
            ref = cg.colliders.add()
            if hasattr(ref, "collider_uuid"):
                ref.collider_uuid = col_uuid
            elif hasattr(ref, "collider_name"):
                ref.collider_name = col_name
        group_to_cg_ref[grp_key] = (
            cg_uuid,
            getattr(cg, "vrm_name", getattr(cg, "name", cg_name)),
        )

    # 3. 通过 .add() 创建 Springs
    raw_center = snap.get("center_bone", "")
    center_bone = resolve_bone(raw_center) if raw_center else ""
    if center_bone not in bones:
        center_bone = "Root" if "Root" in bones else ""

    created_springs = 0
    total_joints = 0
    for idx, sp_spec in enumerate(snap.get("springs", [])):
        valid_joints = []
        seen_b = set()
        for j_spec in sp_spec.get("joints", []):
            bname = resolve_bone(j_spec["bone"])
            if bname in bones and bname not in seen_b:
                seen_b.add(bname)
                valid_joints.append((bname, j_spec["params"]))
        if len(valid_joints) < 2:
            continue

        sp = sb1.springs.add()
        sp_name = f"Spring_{valid_joints[0][0]}_{idx}"
        if hasattr(sp, "vrm_name"):
            sp.vrm_name = sp_name
        elif hasattr(sp, "name"):
            sp.name = sp_name

        if center_bone and center_bone not in seen_b:
            if hasattr(sp, "center") and hasattr(sp.center, "bone_name"):
                sp.center.bone_name = center_bone

        sp.joints.clear()
        for bname, params in valid_joints:
            j = sp.joints.add()
            if hasattr(j, "node") and hasattr(j.node, "bone_name"):
                j.node.bone_name = bname
            hit_radius, stiffness, drag_force, gravity_power = params
            if hasattr(j, "hit_radius"):
                j.hit_radius = hit_radius
            if hasattr(j, "stiffness"):
                j.stiffness = stiffness
            if hasattr(j, "drag_force"):
                j.drag_force = drag_force
            if hasattr(j, "gravity_power"):
                j.gravity_power = gravity_power
            total_joints += 1

        sp.collider_groups.clear()
        for grp_key in sp_spec.get("groups", []):
            cg_ref = group_to_cg_ref.get(grp_key)
            if not cg_ref:
                continue
            ref = sp.collider_groups.add()
            if hasattr(ref, "collider_group_uuid"):
                ref.collider_group_uuid = cg_ref[0]
            elif hasattr(ref, "collider_group_name"):
                ref.collider_group_name = cg_ref[1]
        created_springs += 1

    try:
        del armature_obj[SNAPSHOT_PROP]
    except Exception:
        pass

    print(
        f"   🌸 [SpringBone 写入] 已写入 VRM：springs={created_springs} 条（joints={total_joints} 个），"
        f"colliders={col_count} 个，colliderGroups={len(group_to_cg_ref)} 组。"
    )
    return created_springs, col_count


def extract_mmd_spring_bones_to_vrm(armature_obj=None, overwrite=False):
    """兼容直接调用：拍取 MMD 物理快照并立即写入 VRM spring_bone1。"""
    armature_obj = armature_obj or next(
        (o for o in bpy.data.objects if o.type == "ARMATURE"), None
    )
    if not armature_obj:
        return 0, 0
    ext = getattr(armature_obj.data, "vrm_addon_extension", None)
    if not ext or not hasattr(ext, "spring_bone1"):
        return 0, 0
    if not overwrite and len(getattr(ext.spring_bone1, "springs", [])) > 0:
        return len(ext.spring_bone1.springs), len(
            getattr(ext.spring_bone1, "colliders", [])
        )

    if snapshot_mmd_physics_to_armature(armature_obj, overwrite=overwrite):
        return apply_mmd_spring_snapshot_to_vrm(armature_obj, overwrite=overwrite)
    return 0, 0
