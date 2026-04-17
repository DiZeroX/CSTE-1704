import os
import glob
import json

# =========================
# CONFIG
# =========================
original_folder = r"json"
translated_folder = r"output_json"
output_folder = r"fixed_json"

os.makedirs(output_folder, exist_ok=True)

# =========================
# PROCESS FILES
# =========================
original_files = glob.glob(os.path.join(original_folder, "*.json"))

for orig_path in original_files:
    base_name = os.path.basename(orig_path)
    trans_path = os.path.join(translated_folder, base_name)

    if not os.path.exists(trans_path):
        print(f"Skip {base_name}, translated file not found.")
        continue

    with open(orig_path, "r", encoding="utf-8") as f:
        original_data = json.load(f)

    with open(trans_path, "r", encoding="utf-8") as f:
        translated_data = json.load(f)

    fixed_data = []
    min_len = min(len(original_data), len(translated_data))

    for i in range(min_len):
        o_item = original_data[i]
        t_item = translated_data[i]

        o_text = o_item.get("text", "")
        t_text = t_item.get("text", "")

        new_text = t_text

        # detect original format
        starts_with_quote = o_text.startswith('"')
        ends_with_quote = o_text.endswith('"')
        starts_with_bracket = o_text.startswith('「')
        ends_with_bracket = o_text.endswith('」')

        # sync "
        if starts_with_quote and not new_text.startswith('"'):
            new_text = '"' + new_text
        if not starts_with_quote and new_text.startswith('"'):
            new_text = new_text.lstrip('"')

        if ends_with_quote and not new_text.endswith('"'):
            new_text = new_text + '"'
        if not ends_with_quote and new_text.endswith('"'):
            new_text = new_text.rstrip('"')

        # sync 「」
        if starts_with_bracket and not new_text.startswith('「'):
            new_text = '「' + new_text
        if not starts_with_bracket and new_text.startswith('「'):
            new_text = new_text.lstrip('「')

        if ends_with_bracket and not new_text.endswith('」'):
            new_text = new_text + '」'
        if not ends_with_bracket and new_text.endswith('」'):
            new_text = new_text.rstrip('」')

        # rebuild object (preserve structure)
        fixed_item = t_item.copy()
        fixed_item["text"] = new_text

        fixed_data.append(fixed_item)

    # append remaining lines if different length
    if len(translated_data) > min_len:
        fixed_data.extend(translated_data[min_len:])

    output_path = os.path.join(output_folder, base_name)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(fixed_data, f, ensure_ascii=False, indent=2)

    print(f"Fixed JSON saved to: {output_path}")