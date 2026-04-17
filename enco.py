import subprocess
import pathlib

vntextpatch_path = r"VNTextPatch.exe"

input_folder = pathlib.Path("scene-cst")
json_folder = pathlib.Path("json_translated")
patched_folder = pathlib.Path("scene-cst-patched")

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