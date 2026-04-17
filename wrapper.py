import os
import json
import textwrap
import pathlib

MAX_CHAR = 56

INPUT_FOLDER = "raw2"
OUTPUT_FOLDER = "raw3"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def smart_wrap(text):
    wrapped = textwrap.fill(
        text,
        width=MAX_CHAR,
        break_long_words=False,
        replace_whitespace=False
    )
    return wrapped.replace("\n", "\r\n")

for file in pathlib.Path(INPUT_FOLDER).glob("*.json"):
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    changes = 0

    for item in data:
        if "message" in item:
            original = item["message"]
            wrapped = smart_wrap(original)

            if wrapped != original:
                item["message"] = wrapped
                changes += 1

    out_path = pathlib.Path(OUTPUT_FOLDER) / file.name
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"{file.name} | Wrapped: {changes}")