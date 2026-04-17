import os
import glob

input_folder = r"raw"        # original files folder
trans_folder = r"raw3"  # translated files folder

json_files = glob.glob(os.path.join(trans_folder, "*.json"))

errors = []

for trans_path in json_files:
    base_name = os.path.splitext(os.path.basename(trans_path))[0]
    input_path = os.path.join(input_folder, base_name + ".json")

    if not os.path.exists(input_path):
        print(f"⚠️ {base_name}.json: Original file not found")
        errors.append(f"⚠️ {base_name}.json: Original file not found")
        continue

    with open(trans_path, "r", encoding="utf-8") as f:
        trans_lines = [line.rstrip("\n") for line in f]

    with open(input_path, "r", encoding="utf-8") as f:
        orig_lines = [line.rstrip("\n") for line in f]

    len_trans = len(trans_lines)
    len_orig = len(orig_lines)

    if len_trans == len_orig:
        print(f"✅ {base_name}.json: Line count matches ({len_trans} lines)")
    else:
        print(f"⚠️ {base_name}.json: Line count mismatch! Original={len_orig}, Translated={len_trans}")
        errors.append(f"⚠️ {base_name}.json: Line count mismatch")

# Final summary
print("\n=== Summary of Issues ===")
if errors:
    for err in errors:
        print(err)
else:
    print("✅ All files are correct.")