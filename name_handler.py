import os
import glob
import json

# =========================
# CONFIG
# =========================
TARGET_FOLDER = r"1_json_decompiled"
OUTPUT_FOLDER = r"1.5_name_processed"
NAME_LIST_FILE = "speaker_list.json"
PROCESSED_NAME_LIST_FILE = "speaker_processed.json"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

OUTPUT_PATH = os.path.join(OUTPUT_FOLDER, NAME_LIST_FILE)
PROCESSED_INPUT_PATH = os.path.join(OUTPUT_FOLDER, PROCESSED_NAME_LIST_FILE)

# =========================
# STEP 1 - COLLECT ORIGINAL NAMES
# =========================
def collect_speakers():
    speakers = set()

    json_files = glob.glob(os.path.join(TARGET_FOLDER, "**", "*.json"), recursive=True)

    for path in json_files:
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"⚠️ Skip invalid JSON: {path}")
                continue

        for item in data:
            name = item.get("name")
            if name:
                speakers.add(name.strip())

    speakers = sorted(speakers)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(speakers, f, ensure_ascii=False, indent=2)

    print(f"✅ Original speaker list saved to: {NAME_LIST_FILE}")
    print("👉 Edit this file and create a mapping file for replacement.")


# =========================
# STEP 2 - APPLY PROCESSED NAMES
# =========================
def apply_name_mapping():
    if not os.path.exists(OUTPUT_PATH):
        print("❌ speaker_list.json not found.")
        return

    if not os.path.exists(PROCESSED_INPUT_PATH):
        print("❌ speaker_processed.json not found.")
        return

    # Load original list
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        original_list = json.load(f)

    # Load processed list
    with open(PROCESSED_INPUT_PATH, "r", encoding="utf-8") as f:
        processed_list = json.load(f)

    # Safety check
    if len(original_list) != len(processed_list):
        print("❌ ERROR: List length mismatch!")
        print(f"Original: {len(original_list)}")
        print(f"Processed: {len(processed_list)}")
        return

    # Create mapping dictionary
    name_map = dict(zip(original_list, processed_list))

    print("✅ Mapping created successfully.")
    print("Applying name replacements...")

    json_files = glob.glob(os.path.join(TARGET_FOLDER, "**", "*.json"), recursive=True)

    for path in json_files:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        changed = False

        for item in data:
            old_name = item.get("name")

            if old_name in name_map:
                item["name"] = name_map[old_name]
                changed = True

        if changed:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"✅ Updated: {path}")

    print("🎉 Done applying processed names.")


# =========================
# MAIN MENU
# =========================
def main():
    print("=================================")
    print(" Name Processing Tool")
    print("=================================")
    print("1. Extract original speaker names")
    print("2. Apply processed name mapping")
    print("3. Cancel")
    print("=================================")

    choice = input("Select an option (1/2/3): ").strip()

    if choice == "1":
        collect_speakers()
    elif choice == "2":
        apply_name_mapping()
    elif choice == "3":
        print("Operation cancelled.")
    else:
        print("Invalid choice.")


if __name__ == "__main__":
    main()