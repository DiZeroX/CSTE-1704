import os
import json
import glob

# =========================
# LOAD JSON SAFELY
# =========================
def load_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        return None

# =========================
# COMPARE JSON CONTENT
# =========================
def compare_json(data1, data2):
    return data1 == data2

# =========================
# MAIN FUNCTION
# =========================
def compare_folders(input_folder, process_folder):
    input_files = glob.glob(os.path.join(input_folder, "*.json"))

    total_checked = 0
    identical_count = 0
    different_count = 0
    missing_count = 0

    print("=================================")
    print(" JSON Folder Comparison Tool")
    print("=================================")

    if not input_files:
        print("No JSON files found in input folder.")
        return

    for input_path in input_files:
        file_name = os.path.basename(input_path)
        process_path = os.path.join(process_folder, file_name)

        total_checked += 1

        if not os.path.exists(process_path):
            print(f"⚠ Missing in process folder: {file_name}")
            missing_count += 1
            continue

        json_input = load_json(input_path)
        json_process = load_json(process_path)

        if json_input is None or json_process is None:
            continue

        if compare_json(json_input, json_process):
            print(f"✅ IDENTICAL: {file_name}")
            identical_count += 1
        else:
            print(f"❌ DIFFERENT: {file_name}")
            different_count += 1

    # =========================
    # SUMMARY
    # =========================
    print("=================================")
    print(" SUMMARY")
    print("=================================")
    print(f"Total files checked : {total_checked}")
    print(f"Identical files     : {identical_count}")
    print(f"Different files     : {different_count}")
    print(f"Missing files       : {missing_count}")
    print("=================================")


if __name__ == "__main__":
    print("=================================")
    print(" COMPARISON TOOL")
    print("=================================")
    print(" Input folder: 1_json_decompiled")
    print(" Process folder: 2_json_formatted_translation_todo")
    print("=================================")
    compare_folders(r"1_json_decompiled", r"2_json_formatted_translation_todo")
    print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print("=================================")
    print(" Input folder: 2_json_formatted_translation_todo")
    print(" Process folder: 2.5_json_formatted_translation_done")
    print("=================================")
    compare_folders(r"2_json_formatted_translation_todo", r"2.5_json_formatted_translation_done")
    print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print("=================================")
    print(" Input folder: 2.5_json_formatted_translation_done")
    print(" Process folder: 3_json_post_processed_brackets")
    print("=================================")
    compare_folders(r"2.5_json_formatted_translation_done", r"3_json_post_processed_brackets")
    print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")