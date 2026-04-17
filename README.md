# CSTE-1704 — CatSystem2 Transcompiler Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Gemini API](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-4285F4?logo=google)](https://ai.google.dev/)
[![Engine](https://img.shields.io/badge/Engine-CatSystem2-critical)](https://cs2.suki.jp/manual/)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen)]()

> An automated pipeline and transcompiler engine for extracting, decompiling, translating, and recompiling visual novel data built on the **CatSystem2** engine.

---

## Table of Contents

1. [Overview](#overview)
2. [Pipeline Architecture](#pipeline-architecture)
3. [Prerequisites & Dependencies](#prerequisites--dependencies)
4. [Directory Structure](#directory-structure)
5. [Stage 1 — Extraction](#stage-1--extraction)
6. [Stage 2 — Decompilation](#stage-2--decompilation)
7. [Stage 3 — Pre-Processing](#stage-3--pre-processing)
8. [Stage 4 — Translation Processing](#stage-4--translation-processing)
9. [Stage 5 — Post-Processing](#stage-5--post-processing)
10. [Stage 6 — Compilation](#stage-6--compilation)
11. [Stage 7 — Compression & Patching](#stage-7--compression--patching)
12. [Configuration Reference](#configuration-reference)
13. [Script Reference](#script-reference)
14. [Contributing](#contributing)
15. [License](#license)

---

## Overview

CSTE-1704 is a modular, end-to-end transcompiler pipeline purpose-built for localizing visual novels running on the [CatSystem2](https://cs2.suki.jp/manual/) engine. It handles the full lifecycle of a translation project: from raw archive extraction through AI-assisted translation to final archive repackaging — all while preserving game engine compatibility.

The pipeline is designed to be **resume-friendly**, **fault-tolerant**, and **non-destructive** to the original game assets.

---

## Pipeline Architecture

```
[ scene.int ]
     │
     ▼  GARbro
[ .cst files ]  ←── Shift-JIS encoded
     │
     ▼  deco.py (VNTextPatch)
[ raw .json ]  ←── name / message attributes
     │
     ▼  formattor.py
[ formatted .json ]  ←── id / type / speaker / text
     │
     ▼  name_handler.py
[ speaker_list.json ]  ──► manual translation ──► speaker_processed.json
     │
     ▼  processor.py (Gemini API)
[ translated .json ]
     │
     ├──► bracket_handler.py   (fix dialogue brackets)
     ├──► check_line.py        (verify line counts)
     ├──► comparator.py        (detect duplicate files)
     ├──► validator.py         (audit bracket integrity)
     └──► wrapper.py           (apply CRLF line wrapping)
          │
          ▼  formattor.py (revert)
     [ reverted .json ]
          │
          ▼  enco.py (VNTextPatch)
     [ patched .cst files ]
          │
          ▼  GARbro
     [ update01.int ]
```

---

## Prerequisites & Dependencies

### External Tools

| Tool | Purpose | Link |
|---|---|---|
| **GARbro** | Extract and repack `.int` game archives | [GitHub Releases](https://github.com/morkt/GARbro/releases) |
| **VNTranslationTools** (`VNTextPatch.exe`) | Decompile `.cst` → `.json` and recompile back | [GitHub Releases](https://github.com/arcusmaximus/VNTranslationTools/releases) |
| **Sermone** | Optional: view and verify Shift-JIS encoded `.cst` files | [GitHub Releases](https://github.com/marcussacana/SacanaWrapper/releases) |

### Python Requirements

```bash
pip install google-generativeai aiofiles python-dotenv
```

A Python version of **3.10 or higher** is required for dataclass and type hint compatibility.

### API Keys

Create a `.env` file in the project root with the following variables:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## Directory Structure

```
project-root/
│
├── .env                    # API key and runtime configuration
│
├── scene-cst/              # Input: decompiled .cst files
├── json/                   # Decompiled raw JSON (name/message format)
├── input_json/             # Formatted JSON ready for translation
├── json_id/                # Translated JSON output from processor.py
├── fixed_json/             # Bracket-corrected JSON
├── raw/                    # Pre-revert formatted JSON
├── raw2/                   # Wrapper-processed JSON
├── raw3/                   # Final post-processed JSON
├── scene-cst-patched/      # Recompiled .cst files
│
├── speaker_list.json       # Extracted speaker names (auto-generated)
├── speaker_processed.json  # Manually translated speaker names
├── error_log.txt           # Auto-generated error log from processor.py
│
├── deco.py                 # CST decompiler wrapper
├── enco.py                 # CST compiler wrapper
├── formattor.py            # JSON format converter / reverter
├── name_handler.py         # Speaker name extractor and mapper
├── processor.py            # Gemini API batch translation engine
├── bracket_handler.py      # Dialogue bracket fixer
├── check_line.py           # Line count validator
├── comparator.py           # File duplication checker
├── validator.py            # Bracket integrity auditor
└── wrapper.py              # CRLF line wrapper
```

---

## Stage 1 — Extraction

**Tool:** [GARbro](https://github.com/morkt/GARbro/releases)

Open GARbro and extract the game's `.int` archive — specifically `scene.int`, which contains all in-game dialogues and narrations. The extraction output is a collection of `.cst` (Cat Scene Editor) files.

> **Important:** At this stage, all `.cst` files use **Shift-JIS** encoding. You can inspect their contents using [Sermone](https://github.com/marcussacana/SacanaWrapper/releases) to verify extraction integrity before proceeding.

Place the extracted `.cst` files into the `scene-cst/` directory.

---

## Stage 2 — Decompilation

**Script:** `deco.py` | **Depends on:** `VNTextPatch.exe`

`deco.py` is a wrapper around `VNTextPatch.exe` from [VNTranslationTools](https://github.com/arcusmaximus/VNTranslationTools/releases). It iterates over all `.cst` files in the input folder and decompiles each one into a structured `.json` file.

**Usage:**

Configure the paths at the top of `deco.py`:

```python
vntextpatch_path = r"VNTextPatch.exe"   # path to VNTextPatch
input_folder     = pathlib.Path(r"scene-cst")  # folder with .cst files
output_folder    = pathlib.Path(r"json")       # output folder for .json
```

Then run:

```bash
python deco.py
```

**Output format (raw JSON):**

Each `.json` file contains entries with two primary attributes:

```json
[
  { "name": "キャラクター名", "message": "セリフの内容" },
  { "message": "ナレーションのテキスト" }
]
```

---

## Stage 3 — Pre-Processing

Before translation, raw JSON is restructured into a richer, semantically clear format that distinguishes between spoken dialogue and internal narrations.

### `formattor.py`

A dual-mode processor that handles format conversion and reversion.

**Mode 1 — Convert to structured format:**

Reads from `raw/` and writes to `json/`. Transforms `name`/`message` attributes into a normalized schema:

```json
[
  {
    "id": 1,
    "type": "dialog",
    "speaker": "キャラクター名",
    "text": "セリフ「内容」"
  },
  {
    "id": 2,
    "type": "narration",
    "speaker": null,
    "text": "ナレーションのテキスト"
  }
]
```

The converter applies special encoding for control characters to prevent data loss:

| Original | Encoded |
|---|---|
| `\r\n ` | `<BR> ` |
| `\r\n` | `<BR>` |
| `\n` | `<BRn>` |
| `\r` | `<BRr>` |
| `\u3000` (full-width space) | `<FWSP>` |

It also uses bracket detection logic (`「`/`」`) to correctly identify multi-line dialogue blocks, ensuring that speaker names are assigned only once per consecutive dialogue sequence.

**Mode 2 — Revert to original format:**

Reads from `fixed_json/` and writes to `raw2/`. Used after translation is complete to restore the `name`/`message` structure required by `VNTextPatch.exe` for recompilation.

**Usage:**

```bash
python formattor.py
# Select option 1 (Convert) or 2 (Revert) from the interactive menu
```

---

### `name_handler.py`

A dual-mode utility for batch translation of character/speaker names separately from the main dialogue content.

**Mode 1 — Extract speaker names:**

Scans all `.json` files in the target folder, collects all unique `name` values, and outputs them to `speaker_list.json` for manual or batch translation.

**Mode 2 — Apply translated names:**

Maps translated names from `speaker_processed.json` back into all JSON files. The two lists must be index-aligned: entry `N` in `speaker_processed.json` replaces entry `N` in `speaker_list.json` across all files.

**Usage:**

```bash
python name_handler.py
# Select option 1 (Extract) or 2 (Apply) from the interactive menu
```

**Workflow:**

```
[Mode 1] → speaker_list.json  →  manually create speaker_processed.json  →  [Mode 2]
```

---

## Stage 4 — Translation Processing

**Script:** `processor.py` | **Depends on:** Gemini API, `.env` configuration

`processor.py` is the core of the translation pipeline. It is an asynchronous, batch-aware engine that sends structured JSON dialogue files to the Gemini API and writes validated translations back to disk.

### Key Features

- **Batch processing** with configurable file count per API request
- **Smart payload splitting** — automatically divides oversized batches into sub-batches if `MAX_PAYLOAD_CHARS` is exceeded
- **Exponential backoff retry** on `503` errors, timeouts, or empty responses
- **Per-file fallback** — if a batch fails, each file is retried individually
- **Auto-repair** — automatically restores corrupted static keys (`id`, `type`, `speaker`) from the original input
- **SKIP_EXISTING** mode — safely resume interrupted sessions without reprocessing completed files
- **Live validation** — every output file is validated immediately after writing
- **Error logging** — all failures are written to `error_log.txt`

### Configuration (`.env`)

```env
GEMINI_API_KEY=your_api_key_here
```

The following constants are configured directly in `processor.py`:

```python
GEMINI_MODEL      = "gemini-2.5-flash-lite"
BATCH_SIZE        = 30          # Files per API request
MAX_RETRIES       = 2           # Retry attempts for failed files
API_TIMEOUT       = 150         # Max seconds per API call
MAX_PAYLOAD_CHARS = 50_000      # Max characters per batch (~50 KB)
BATCH_DELAY       = 3.0         # Seconds between batches
SKIP_EXISTING     = True        # Resume mode: skip already-translated files
```

### The Master Prompt (`MASTER_PROMPT`)

The core instruction set passed to the AI model on every request. It defines:

- Translator role and target language
- Absolute technical rules (key immutability, line integrity, bracket preservation)
- Internal variable passthrough (e.g., `$str20`, `$str21`)
- Character name glossary
- Style guide (casual register, pronoun conventions, onomatopoeia handling, HTML tag preservation)

The prompt uses `{json_content}` as the injection point for the batch payload.

### Usage

```bash
python processor.py
```

---

## Stage 5 — Post-Processing

After translation, a suite of quality-assurance scripts ensures formatting correctness and game engine compatibility before recompilation.

### `bracket_handler.py`

Automatically fixes Japanese dialogue bracket mismatches between the original and translated JSON files.

Compares each `text` field in the translated output against its original counterpart. If a bracket (`「`, `」`) or double-quote (`"`) is present in the original but missing in the translation (or vice versa), it is added or stripped automatically.

```bash
# Configure paths at the top of the script, then run:
python bracket_handler.py
```

Output is written to the `fixed_json/` directory, leaving the translated source untouched.

---

### `check_line.py`

Compares the total line count of each translated JSON file against its original counterpart to detect missing lines or structural corruption.

```bash
python check_line.py
```

**Example output:**

```
✅ scene001.json: Line count matches (312 lines)
⚠️ scene002.json: Line count mismatch! Original=200, Translated=198
```

A final summary lists all files with detected issues.

---

### `comparator.py`

Detects full-file content duplication between two folders (e.g., `raw/` vs. `raw2/`). Useful for identifying files that may have been overwritten without modification or skipped during processing.

```bash
python comparator.py
```

**Example output:**

```
✅ IDENTICAL: scene001.json
❌ DIFFERENT: scene002.json
⚠ Missing in process folder: scene003.json
```

---

### `validator.py`

A **read-only** bracket integrity auditor. Unlike `bracket_handler.py`, it does not modify any files. It reports all bracket mismatches in detail, providing the exact index, original text, and translated text for each issue.

```bash
python validator.py
```

**Example output:**

```
❌ Bracket mismatch in scene001.json (index 42)
Original  : 「ああ、そうか
Translated: Ah, begitu ya」
```

Use this script before `bracket_handler.py` to assess the scope of issues, or after it to confirm all corrections were applied.

---

### `wrapper.py`

Appends `\r\n` (CRLF) line breaks to `message` values that exceed the maximum character limit per line. This prevents text overflow and awkward mid-word line cuts within the game engine's dialogue UI.

The default limit is **56 characters per line**, configurable via `MAX_CHAR` at the top of the script.

```bash
python wrapper.py
```

---

## Stage 6 — Compilation

**Script:** `enco.py` | **Depends on:** `VNTextPatch.exe`

Before running `enco.py`, first revert the translated JSON back to the original `name`/`message` format using `formattor.py` (Mode 2).

`enco.py` then iterates over all `.json` files in `json_translated/`, pairs each one with its corresponding `.cst` source file, and calls `VNTextPatch.exe insertlocal` to inject the translated text and recompile the binary. The encoding is automatically restored to what the game engine expects.

**Usage:**

First, configure the paths in `enco.py`:

```python
vntextpatch_path = r"VNTextPatch.exe"
input_folder     = pathlib.Path("scene-cst")          # original .cst files
json_folder      = pathlib.Path("json_translated")     # translated .json files
patched_folder   = pathlib.Path("scene-cst-patched")  # output patched .cst files
```

Then run:

```bash
python enco.py
```

---

## Stage 7 — Compression & Patching

**Tool:** [GARbro](https://github.com/morkt/GARbro/releases)

Repack the contents of `scene-cst-patched/` back into an `.int` archive using GARbro.

> **Critical:** Do **not** overwrite `scene.int`. The CatSystem2 engine supports a patch priority system based on archive naming. Archives with higher numerical suffixes take precedence over lower ones at runtime.

**Naming convention:**

```
update01.int   ← first translation patch (lowest priority)
update02.int   ← second patch (overrides update01)
update03.int   ← and so on...
```

Place the resulting `updateXX.int` file in the game's root directory alongside the original `scene.int`. The engine will automatically load the highest-priority version of each scene.

---

## Configuration Reference

| Parameter | Script | Default | Description |
|---|---|---|---|
| `GEMINI_MODEL` | `processor.py` | `gemini-2.5-flash-lite` | Gemini model version |
| `BATCH_SIZE` | `processor.py` | `30` | Files per API request |
| `MAX_RETRIES` | `processor.py` | `2` | Max retries on error |
| `API_TIMEOUT` | `processor.py` | `150` | Seconds before API call times out |
| `MAX_PAYLOAD_CHARS` | `processor.py` | `50000` | Max characters per batch before splitting |
| `BATCH_DELAY` | `processor.py` | `3.0` | Seconds between batch requests |
| `SKIP_EXISTING` | `processor.py` | `True` | Skip already-translated files (resume mode) |
| `MAX_CHAR` | `wrapper.py` | `56` | Max characters per dialogue line |

---

## Script Reference

| Script | Stage | Description |
|---|---|---|
| `deco.py` | Decompilation | Wraps `VNTextPatch.exe extractlocal` for batch `.cst` → `.json` |
| `enco.py` | Compilation | Wraps `VNTextPatch.exe insertlocal` for batch `.json` → `.cst` |
| `formattor.py` | Pre/Post-Processing | Converts between raw and structured JSON formats |
| `name_handler.py` | Pre-Processing | Extracts and remaps speaker names |
| `processor.py` | Translation | Async Gemini API batch translation engine with live validation |
| `bracket_handler.py` | Post-Processing | Auto-fixes dialogue bracket mismatches |
| `check_line.py` | Post-Processing | Validates line counts between original and translated files |
| `comparator.py` | Post-Processing | Detects full-file content duplication across folders |
| `validator.py` | Post-Processing | Read-only bracket integrity audit with detailed reporting |
| `wrapper.py` | Post-Processing | Applies CRLF line wrapping to prevent UI text overflow |

---

## Contributing

Contributions are welcome. Please open an issue to discuss proposed changes before submitting a pull request. Ensure all scripts are tested against valid CatSystem2 game data before submission.

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

> This tool is intended for legitimate fan translation and personal archival use only. Respect the intellectual property rights of the original game developers.
