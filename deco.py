import subprocess
import pathlib

# lokasi VNTextPatch.exe
vntextpatch_path = r"D:\Projects\Grisaia Remaster Translation\VNTranslationTools\VNTextPatch\VNTextPatch.exe"

# folder berisi file .cst
input_folder = pathlib.Path(r"0_scene_cst_input_decompiled")

# folder output hasil xlsx
output_folder = pathlib.Path(r"1_json_decompiled")
output_folder.mkdir(exist_ok=True)

# loop semua file .cst
for cst_file in input_folder.glob("*.cst"):
    output_json = output_folder / f"{cst_file.stem}.json"
    print(f"Extracting {cst_file.name} → {output_json.name}")
    subprocess.run([
        vntextpatch_path,
        "extractlocal",
        str(cst_file),   # file .cst
        str(output_json) # nama file xlsx hasil
    ], check=True)

print("Finished.")