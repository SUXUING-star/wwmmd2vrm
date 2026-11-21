
# Wuthering Waves MMD to VRM 1.0 Converter

A Blender Python pipeline for converting MMD models exported from into VRM 1.0 avatars.

The repository is target to Wuthering Waves MMD Models Structure.It's for personal, educational, and non-commercial purposes.([related work](https://github.com/SUXUING-star/umammd2vrm))

---

## Requirements

1. **Blender** (4 ~ 5.2)
2. **Required Add-ons:**
   * **[mmd_tools](https://github.com/powup333/blender_mmd_tools)**
   * **[VRM Add-on for Blender](https://vrm-addon-for-blender.info/en/)**

---

## Model Configuration (`config.json`)

Each character directory in `public/` requires a `config.json` next to the `.blend` file.

```json
{
  "jp_name": "达妮娅",
  "en_name": "Dania",
  "texture_dir": "TEX",
  "vrma_path": "",
  "sparse_morphs": false,
  "fix_high_heel_rig": true,
  "metadata": {
    "vrm_name": "Dania",
    "version": "1.0.0",
    "author": "kuro games",
    "copyright": "",
    "contact": "",
    "reference": "",
    "third_party_licenses": "None",
    "other_license_url": "",
    "thumbnail_path": "",
    "avatar_permission": "onlyAuthor",
    "allow_excessively_violent_usage": false,
    "allow_excessively_sexual_usage": false,
    "commercial_usage": "personalNonProfit",
    "allow_political_or_religious_usage": false,
    "allow_antisocial_or_hate_usage": false,
    "credit_notation": "required",
    "allow_redistribution": false,
    "modification": "prohibited"
  }
}
```

---

## Usage

1. **Import PMX:** Import the `.pmx` model into Blender using `mmd_tools` and convert materials to Principled BSDF. Save the `.blend` file.
2. **Verify Setup:** Ensure `config.json` and `Texture2D/`(or other name) are in the same folder as the `.blend` file.
3. **Run Pipeline:** Open `blender.py` in Text Editor and edit the code path(the repsitory clone path),then you just copy the `blender.py` into the Blender's Text Editor,and click **Run Script** (`Alt + P`).
4. **Export VRM:** Check mappings in the VRM tab on the Blender sidebar (`N`), then click **Export VRM 1.0**.

---

## Pipeline Overview

1. Extract Spring Bones (Extract MMD rigid bodies & convert to VRM Spring Bones)
   ↓
2. Clean Mesh & Bones (Fix normals, remove unused rigid bodies, joints, and auxiliary bones)
   ↓
3. Bind Expressions (Normalize shape key names and bind to VRM Expressions)
   ↓
4. Bake Textures (Composite eye highlights & pack UV textures)
   ↓
5. Setup Materials (Configure VRM MToon shaders)
   ↓
6. Write Metadata (Set VRM 1.0 metadata)
   ↓
7. (Optional) Inject Animation (Import & attach animation files)
