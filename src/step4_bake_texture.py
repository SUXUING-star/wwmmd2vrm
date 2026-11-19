import hashlib
import json
import os
import re

import bpy
import numpy as np
from PIL import Image


def extract_material_base_image(mat):
    if not mat or not mat.use_nodes or not mat.node_tree:
        return None
    nodes = mat.node_tree.nodes

    base_node = nodes.get("mmd_base_tex")
    if base_node and base_node.type == "TEX_IMAGE" and base_node.image:
        return base_node.image

    mmd_shader = nodes.get("mmd_shader")
    if mmd_shader and "Base Tex" in mmd_shader.inputs:
        inp = mmd_shader.inputs["Base Tex"]
        if inp.is_linked:
            src = inp.links[0].from_node
            if src.type == "TEX_IMAGE" and src.image:
                return src.image

    for node in nodes:
        if node.type == "BSDF_PRINCIPLED":
            inp = node.inputs.get("Base Color")
            if inp and inp.is_linked:
                src = inp.links[0].from_node
                if src.type == "TEX_IMAGE" and src.image:
                    return src.image

    for node in nodes:
        if node.type == "TEX_IMAGE" and node.image:
            if node.name in ("mmd_toon_tex", "mmd_sphere_tex"):
                continue
            img_low = node.image.name.lower()
            if any(
                kw in img_low
                for kw in (
                    "spa",
                    "sph",
                    "toon",
                    "hair hi light",
                    "alphamc",
                    "bodymc",
                    "mc12",
                )
            ):
                continue
            return node.image
    return None


def classify_role(mat_name: str, img_name: str) -> str:
    m_low = mat_name.lower()
    s = f"{mat_name} {img_name}".lower()

    if any(
        kw in s
        for kw in (
            "eyehi",
            "eye hi",
            "eyelight",
            "emo",
            "cheek",
            "heng",
            "boli",
            "glass",
            "yeti",
            "liquid",
            "fx",
            "玻璃",
            "液体",
            "特效",
            "腮红",
        )
    ) or re.search(r"(^|[_\-\s])hi\d*($|[_\-\s])", m_low):
        return "fx_overlay"

    if any(kw in m_low for kw in ("lash", "mayu", "brow", "eyeline", "睫", "眉")):
        return "lash_brow"

    if (
        "eye" in m_low
        or "bai" in m_low
        or "瞳" in m_low
        or "目" in m_low
        or "眼" in m_low
    ):
        return "eye"

    if any(kw in s for kw in ("face", "kao", "顔", "脸")):
        return "face"

    if any(kw in s for kw in ("skin", "hada", "sink", "肌", "素体", "皮肤")):
        return "skin"

    if any(kw in s for kw in ("hair", "bangs", "kami", "髪", "刘海")):
        return "hair"

    return "cloth"


def resolve_disk_path(img, texture_dir):
    if img and img.filepath:
        abs_p = bpy.path.abspath(img.filepath)
        if os.path.exists(abs_p) and os.path.isfile(abs_p):
            return abs_p
    if img and texture_dir and os.path.exists(texture_dir):
        base = os.path.basename(bpy.path.abspath(img.filepath or img.name))
        cand = os.path.join(texture_dir, base)
        if os.path.exists(cand):
            return cand
        stem = re.sub(r"\.\d{3}$", "", img.name)
        for f in os.listdir(texture_dir):
            if (
                f.lower() == stem.lower()
                or os.path.splitext(f)[0].lower() == stem.lower()
            ):
                return os.path.join(texture_dir, f)
    return None


def image_to_pil_rgba(img_obj, disk_path):
    if disk_path and os.path.exists(disk_path):
        return Image.open(disk_path).convert("RGBA")
    if img_obj and img_obj.has_data and img_obj.size[0] > 0 and img_obj.size[1] > 0:
        w, h = img_obj.size[0], img_obj.size[1]
        px = np.array(img_obj.pixels[:], dtype=np.float32).reshape((h, w, 4))
        px = np.flipud(px)  # Blender 像素自底向上，PIL 自顶向下
        return Image.fromarray(
            np.clip(px * 255.0, 0, 255).astype(np.uint8), mode="RGBA"
        )
    return None


def find_emissive_counterpart(disk_path, texture_dir):
    if not disk_path or not texture_dir or not os.path.exists(texture_dir):
        return None
    stem = os.path.splitext(os.path.basename(disk_path))[0]
    candidates_prefix = []
    for suffix in ("_D_noalpha2", "_D_noalpha", "_D1", "_D2", "_D"):
        if stem.endswith(suffix):
            base_prefix = stem[: -len(suffix)]
            candidates_prefix.extend(
                [
                    f"{base_prefix}_E",
                    f"{base_prefix}_Emissive",
                    f"{base_prefix}_EMI",
                    f"{base_prefix}_Glow",
                ]
            )
            break
    if not candidates_prefix:
        return None

    files = os.listdir(texture_dir)
    for cand in candidates_prefix:
        for f in files:
            if os.path.splitext(f)[0].lower() == cand.lower():
                return os.path.join(texture_dir, f)
    return None


def maybe_synthesize_black_bg_alpha(arr, role):
    if role != "fx_overlay":
        return arr
    alpha = arr[:, :, 3]
    if np.any(alpha < 250):
        return arr

    luma = np.max(arr[:, :, :3], axis=2)
    if float(np.mean(luma < 25.0)) > 0.30:
        new_alpha = np.clip((luma - 12.0) * (255.0 / 243.0), 0.0, 255.0)
        arr = arr.copy()
        arr[:, :, 3] = new_alpha
    return arr


def detect_alpha_mode(rgba_arr, role, mat_or_img_name):
    name_low = mat_or_img_name.lower()
    if role == "fx_overlay":
        return True, "BLEND"
    if "noalpha" in name_low and "alpha" not in name_low.replace("noalpha", ""):
        return False, "OPAQUE"

    alpha = rgba_arr[:, :, 3]
    non_opaque = alpha < 250
    if not np.any(non_opaque):
        return False, "OPAQUE"

    semi = (alpha > 10) & (alpha < 245)
    semi_ratio = float(np.sum(semi)) / max(1, int(np.sum(non_opaque)))
    if semi_ratio > 0.35 and role != "lash_brow":
        return True, "BLEND"
    return True, "MASK"


def resize_if_needed(pil_img, max_size):
    if max_size <= 0:
        return pil_img
    w, h = pil_img.size
    if max(w, h) <= max_size:
        return pil_img
    scale = max_size / float(max(w, h))
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)


def run(texture_dir, max_tex_size=1024):
    print(
        f">>> [步骤 4] 优化鸣潮 TEX 贴图（全图上限 {max_tex_size}px + 不透明转JPEG）..."
    )

    if not texture_dir:
        return
    temp_dir = os.path.join(texture_dir, "vrm_temp_baked")
    os.makedirs(temp_dir, exist_ok=True)

    image_jobs = {}
    for mat in bpy.data.materials:
        if not mat or getattr(mat, "users", 0) == 0:
            continue
        base_img = extract_material_base_image(mat)
        if not base_img:
            continue
        role = classify_role(mat.name, base_img.name)
        if base_img.name not in image_jobs:
            image_jobs[base_img.name] = (base_img, role, f"{mat.name} {base_img.name}")

    manifest = {}

    for img_name, (img_obj, role, combined_name) in image_jobs.items():
        disk_path = resolve_disk_path(img_obj, texture_dir)
        try:
            pil_img = image_to_pil_rgba(img_obj, disk_path)
            if pil_img is None:
                print(
                    f"   ⚠️ 无法读取贴图 [{img_name}]（既无磁盘文件也无像素数据），跳过。"
                )
                continue

            pil_img = resize_if_needed(pil_img, max_tex_size)

            arr = np.array(pil_img, dtype=np.float32)
            arr = maybe_synthesize_black_bg_alpha(arr, role)
            has_alpha, alpha_mode = detect_alpha_mode(arr, role, combined_name)

            short_hash = hashlib.md5(img_name.encode("utf-8")).hexdigest()[:6]
            raw_base = os.path.basename(disk_path) if disk_path else img_name
            safe_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", os.path.splitext(raw_base)[0])
            key_prefix = f"ww_{safe_stem}_{short_hash}"

            if has_alpha:
                lit_fname = f"{key_prefix}_lit.png"
                lit_path = os.path.join(temp_dir, lit_fname)
                Image.fromarray(
                    np.clip(arr, 0, 255).astype(np.uint8), mode="RGBA"
                ).save(lit_path, format="PNG", optimize=True, compress_level=9)
            else:
                lit_fname = f"{key_prefix}_lit.jpg"
                lit_path = os.path.join(temp_dir, lit_fname)
                Image.fromarray(
                    np.clip(arr[:, :, :3], 0, 255).astype(np.uint8), mode="RGB"
                ).save(
                    lit_path, format="JPEG", quality=90, subsampling=0, optimize=True
                )

            emi_fname = None
            emi_disk = find_emissive_counterpart(disk_path, texture_dir)
            if emi_disk and os.path.exists(emi_disk):
                emi_img = resize_if_needed(
                    Image.open(emi_disk).convert("RGB"), max_tex_size
                )
                emi_fname = f"{key_prefix}_emi.jpg"
                emi_img.save(
                    os.path.join(temp_dir, emi_fname),
                    format="JPEG",
                    quality=88,
                    subsampling=0,
                    optimize=True,
                )

            manifest[img_name] = {
                "role": role,
                "lit": lit_fname,
                "emissive": emi_fname,
                "has_alpha": has_alpha,
                "alpha_mode": alpha_mode,
            }
            size_kb = os.path.getsize(lit_path) // 1024
            print(
                f"   ✅ [贴图压缩] {raw_base} -> {lit_fname} ({size_kb} KB, {pil_img.size[0]}x{pil_img.size[1]}, alpha={alpha_mode})"
            )
        except Exception as e:
            print(f"   ⚠️ 贴图 [{img_name}] 处理失败: {e}")

    manifest_path = os.path.join(temp_dir, "ww_bake_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"✅ [步骤 4] 贴图优化完成！共处理 {len(manifest)} 张底图。")
