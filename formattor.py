import json
import glob
import os

# =========================
# CONFIG
# =========================
INPUT_FOLDER_RAW = r"raw"
OUTPUT_FOLDER_JSON = r"json"
INPUT_FOLDER_JSON = r"fixed_json"
OUTPUT_FOLDER_RAW = r"raw2"

os.makedirs(OUTPUT_FOLDER_RAW, exist_ok=True)
os.makedirs(INPUT_FOLDER_RAW, exist_ok=True)
os.makedirs(OUTPUT_FOLDER_JSON, exist_ok=True)
os.makedirs(INPUT_FOLDER_JSON, exist_ok=True)

# =========================
# TEXT CLEANER
# =========================
def clean_text(text):
    text = text.replace("\r\n ", "<BR> ")
    text = text.replace("\r\n", "<BR>")
    text = text.replace("\n", "<BRn>")
    text = text.replace("\r", "<BRr>")
    text = text.replace("\u3000", "<FWSP>")
    return text

# =========================
# CONVERT TO JSON STYLE
# =========================
def convert_to_style():
    json_files = glob.glob(os.path.join(INPUT_FOLDER_RAW, "*.json"))

    for file_path in json_files:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        base_name = os.path.splitext(os.path.basename(file_path))[0]

        converted = []
        line_id = 1

        # Dialog state
        in_dialog_block = False
        current_speaker = None

        for item in raw_data:
            raw_message = item.get("message", "")
            message = clean_text(raw_message)
            name = item.get("name", "").strip()

            if message == "":
                continue

            # Detect dialog start
            if "「" in message:
                in_dialog_block = True
                if name:
                    current_speaker = name

            # Determine type and speaker
            if in_dialog_block:
                entry_type = "dialog"
                speaker = current_speaker
            else:
                if name:
                    entry_type = "dialog"
                    speaker = name
                else:
                    entry_type = "narration"
                    speaker = None

            # Save entry
            converted.append({
                "id": line_id,
                "type": entry_type,
                "speaker": speaker,
                "text": clean_text(message)
            })

            line_id += 1

            # Detect dialog end
            if "」" in message:
                in_dialog_block = False
                current_speaker = None

        output_path = os.path.join(OUTPUT_FOLDER_JSON, base_name + ".json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(converted, f, ensure_ascii=False, indent=2)

        print(f"✅ Converted: {output_path}")

# =========================
# REVERT TO ORIGINAL FORMAT (STRICT SYMBOL BASED)
# =========================
def revert_to_original():
    json_files = glob.glob(os.path.join(INPUT_FOLDER_JSON, "*.json"))

    for file_path in json_files:
        with open(file_path, "r", encoding="utf-8") as f:
            translated_data = json.load(f)

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        reverted = []

        in_dialog_block = False

        for item in translated_data:
            text = item.get("translated_text") or item.get("text", "")
            # text = text.replace("<BR> ", "\r\n ")
            # text = text.replace("<BR>", "\r\n")
            # text = text.replace("<BRn>", "\n")
            # text = text.replace("<BRr>", "\r")
            text = text.replace("<BR>", "")
            text = text.replace("<FWSP>", "\u3000")

            speaker = item.get("speaker")

            has_open = "「" in text
            has_close = "」" in text

            # ===== START OF MULTI-LINE DIALOG =====
            if has_open and not has_close:
                if speaker:
                    reverted.append({
                        "name": speaker,
                        "message": text
                    })
                else:
                    reverted.append({
                        "message": text
                    })
                in_dialog_block = True
                continue

            # ===== END OF MULTI-LINE DIALOG =====
            if in_dialog_block:
                reverted.append({
                    "message": text
                })

                if has_close:
                    in_dialog_block = False
                continue

            # ===== SINGLE LINE DIALOG =====
            if has_open and has_close:
                if speaker:
                    reverted.append({
                        "name": speaker,
                        "message": text
                    })
                else:
                    reverted.append({
                        "message": text
                    })
                continue

            # ===== NARRATION OR NON-QUOTED LINE =====
            if speaker:
                reverted.append({
                    "name": speaker,
                    "message": text
                })
            else:
                reverted.append({
                    "message": text
                })

        output_path = os.path.join(OUTPUT_FOLDER_RAW, base_name + ".json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(reverted, f, ensure_ascii=False, indent=2)

        print(f"✅ Reverted: {output_path}")

# =========================
# MAIN MENU
# =========================
def main():
    print("=================================")
    print(" JSON Processing Tool")
    print("=================================")
    print("1. Convert to JSON style")
    print("2. Revert to original format")
    print("3. Cancel")
    print("=================================")

    choice = input("Select an option (1/2/3): ").strip()

    if choice == "1":
        convert_to_style()
    elif choice == "2":
        revert_to_original()
    elif choice == "3":
        print("Operation cancelled.")
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()