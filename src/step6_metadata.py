import os

import bpy


def run(config):
    print(">>> [步骤 6] 写入 VRM 1.0 元数据并导出 VRM...")

    armature = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    if not armature:
        return

    armature.data.vrm_addon_extension.spec_version = "1.0"
    meta = armature.data.vrm_addon_extension.vrm1.meta

    d = config.get("metadata", {})

    meta.vrm_name = d.get("vrm_name", config["en_name"])
    meta.version = d.get("version", "1.0.0")
    meta.copyright_information = d.get("copyright_information", "")
    meta.contact_information = d.get("contact_information", "")
    meta.third_party_licenses = d.get("third_party_licenses", "")
    meta.other_license_url = d.get("other_license_url", "")

    meta.authors.clear()
    meta.authors.add().value = d.get("author", "Unknown")

    meta.references.clear()
    ref_val = d.get("reference", "")
    if ref_val:
        meta.references.add().value = ref_val

    meta.avatar_permission = d.get("avatar_permission", "everyone")
    meta.allow_excessively_violent_usage = d.get(
        "allow_excessively_violent_usage", False
    )
    meta.allow_excessively_sexual_usage = d.get("allow_excessively_sexual_usage", False)
    meta.commercial_usage = d.get("commercial_usage", "personalNonProfit")
    meta.allow_political_or_religious_usage = d.get(
        "allow_political_or_religious_usage", False
    )
    meta.allow_antisocial_or_hate_usage = d.get("allow_antisocial_or_hate_usage", False)
    meta.credit_notation = d.get("credit_notation", "required")
    meta.allow_redistribution = d.get("allow_redistribution", False)
    meta.modification = d.get("modification", "allowModification")

    tp = d.get("thumbnail_path", "")
    if tp and os.path.exists(tp):
        img = bpy.data.images.get(os.path.basename(tp)) or bpy.data.images.load(tp)
        meta.thumbnail_image = img

    print("✅ [步骤 6] 元数据写入完成。")

    models_dir = config.get("models_dir")
    if models_dir:
        os.makedirs(models_dir, exist_ok=True)
        out_vrm = os.path.join(models_dir, f"{config['en_name']}.vrm")
        has_vrma = bool(
            config.get("vrma_path")
            or (
                isinstance(config.get("vrma_paths"), list)
                and any(config.get("vrma_paths"))
            )
        )
        res = bpy.ops.export_scene.vrm(
            filepath=out_vrm,
            armature_object_name=armature.name,
            enable_advanced_preferences=has_vrma,
            export_gltf_animations=has_vrma,
        )
        if res == {"FINISHED"} and os.path.exists(out_vrm):
            size_mb = os.path.getsize(out_vrm) / (1024 * 1024)
            total_verts = sum(
                len(o.data.vertices)
                for o in bpy.data.objects
                if o.type == "MESH" and o.data
            )
            print(
                f"✅ [步骤 6] VRM 已导出至: {out_vrm} "
                f"(体积: {size_mb:.2f} MB | 骨骼: {len(armature.data.bones)} | 顶点: {total_verts} | 图像数据块: {len(bpy.data.images)} | 内嵌动画: {has_vrma})"
            )
        else:
            print(f"⚠️ [步骤 6] VRM 导出失败: {res}")
