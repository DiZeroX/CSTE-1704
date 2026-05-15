import os
import glob
import json

# =========================
# CONFIG
# =========================
original_folder = r"2_json_formatted_translation_todo"
translated_folder = r"2.5_json_formatted_translation_done"

# =========================
# HELPER
# =========================
def get_bracket_info(text):
    return {
        "starts_with_quote": text.startswith('"'),
        "ends_with_quote": text.endswith('"'),
        "starts_with_bracket": text.startswith('「'),
        "ends_with_bracket": text.endswith('」'),
    }

# =========================
# MAIN CHECK
# =========================
original_files = glob.glob(os.path.join(original_folder, "*.json"))

total_files = 0
files_with_issues = 0
total_issues = 0

print("=================================")
print(" JSON Bracket Validation Tool")
print("=================================")

for orig_path in original_files:
    base_name = os.path.basename(orig_path)
    trans_path = os.path.join(translated_folder, base_name)

    if not os.path.exists(trans_path):
        print(f"⚠ Skip {base_name} (translated file not found)")
        continue

    total_files += 1

    with open(orig_path, "r", encoding="utf-8") as f:
        original_data = json.load(f)

    with open(trans_path, "r", encoding="utf-8") as f:
        translated_data = json.load(f)

    min_len = min(len(original_data), len(translated_data))
    file_issue_count = 0

    for i in range(min_len):
        o_text = original_data[i].get("text", "")
        t_text = translated_data[i].get("text", "")

        o_bracket = get_bracket_info(o_text)
        t_bracket = get_bracket_info(t_text)

        if o_bracket != t_bracket:
            file_issue_count += 1
            total_issues += 1

            print(f"\n❌ Bracket mismatch in {base_name} (index {i})")
            print(f"Original : {o_text}")
            print(f"Translated: {t_text}")

    if file_issue_count > 0:
        files_with_issues += 1
        print(f"\n⚠ {base_name} has {file_issue_count} bracket issue(s).")
    else:
        print(f"✅ {base_name} has no bracket issues.")

# =========================
# SUMMARY
# =========================
print("\n=================================")
print(" SUMMARY")
print("=================================")
print(f"Total files checked      : {total_files}")
print(f"Files with bracket issue : {files_with_issues}")
print(f"Total bracket mismatches : {total_issues}")
print("=================================")