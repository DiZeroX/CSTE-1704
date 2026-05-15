import subprocess
import pathlib

vntextpatch_path = r"D:\Projects\Grisaia Remaster Translation\VNTranslationTools\VNTextPatch\VNTextPatch.exe"

input_folder = pathlib.Path("0_scene_cst_input_decompiled")
json_folder = pathlib.Path("4_json_reverted_to_decompiled")
patched_folder = pathlib.Path("5_scene_cst_patch_output_compiled")

patched_folder.mkdir(exist_ok=True)

for json_file in json_folder.glob("*.json"):
    cst_name = json_file.stem + ".cst"
    cst_path = input_folder / cst_name
    output_cst = patched_folder / cst_name

    print(f"Menyisipkan {json_file.name} ke {cst_name}")

    subprocess.run([
        vntextpatch_path,
        "insertlocal",
        str(cst_path),
        str(json_file),
        str(output_cst)
    ], check=True)