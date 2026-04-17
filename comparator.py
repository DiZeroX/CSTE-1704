import os
import json
import glob

# =========================
# CONFIG
# =========================
INPUT_FOLDER = "raw"
PROCESS_FOLDER = "raw2"

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
def compare_folders():
    input_files = glob.glob(os.path.join(INPUT_FOLDER, "*.json"))

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
        process_path = os.path.join(PROCESS_FOLDER, file_name)

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
    compare_folders()