"""
GEMINI JSON BATCH PROCESSOR + LIVE VALIDATOR  (v6)
  • Timeout API call (default 120s) — does not get stuck forever
  • Exponential backoff retry: 503 / timeout / empty response
  • Auto-repair STATIC_KEY_CHANGED from original input
  • PROHIBITED_CONTENT → fallback per-item (blocked items → original text preserved)
  • Safety settings BLOCK_NONE — 18+ content is not censored
  • Smart batch splitting by payload size
"""

import asyncio, json, os, re, sys, time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import aiofiles
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ═══════════════════════════════════════════════════════════════
# KONFIGURASI
# ═══════════════════════════════════════════════════════════════

INPUT_FOLDER   = Path("2_json_formatted_translation_todo")
OUTPUT_FOLDER  = Path("2.5_json_formatted_translation_done")
ERROR_LOG_FILE = Path("processor_error_log.txt")

GEMINI_MODEL      = "gemini-2.5-flash-lite"
BATCH_SIZE        = 30        # File per request (dipecah otomatis jika payload besar)
BATCH_DELAY       = 3.0       # Detik jeda antar batch
MAX_RETRIES       = 2         # Retry per file untuk error biasa
API_TIMEOUT       = 150       # Detik maks per API call sebelum timeout
                              # (lebih besar dari total retry sleep: 10+30+60=100s)
API_RETRY_DELAYS  = [10, 30, 60]  # Backoff: retry ke-1, ke-2, ke-3
MAX_PAYLOAD_CHARS = 50_000    # Batas payload JSON per batch (~50 KB)

SKIP_EXISTING = True      # True = lewati file yang sudah ada di output_json/ (resume-friendly)

STATIC_KEYS  = ["id", "type", "speaker"]
MUTABLE_KEYS = ["text"]

# ═══════════════════════════════════════════════════════════════
# MASTER PROMPT
# ═══════════════════════════════════════════════════════════════

MASTER_PROMPT = """
**Role:**
You are a professional Japanese-to-English translator specializing in visual novels. Your task is to provide accurate translations of JSON dialogue data. 

**[ABSOLUTE TECHNICAL RULES — MANDATORY TO FOLLOW WITHOUT EXCEPTION]**

CRITICAL WARNING: You may ONLY change the value of the "text" key. The "id", "type", and "speaker" keys must be copied EXACTLY as they are in the input.

TEXT & LINE INTEGRITY RULES (CRITICALLY IMPORTANT):
1. **NO SHIFTING SENTENCES:** You MUST translate the text EXACTLY at its original id. It is STRICTLY FORBIDDEN to move, split, or combine translations from one id to another. 
2. **NO DROPPING TEXT:** If an id has Japanese text, you MUST translate it. Never omit character dialogue.
3. **QUOTATION INTEGRITY:** Preserve Japanese punctuation exactly as the original.
   - If the input ONLY has an opening quote (example: `「ああ`), the output MUST ONLY have an opening quote (example: `「Ah`). DO NOT add a closing quote `」` if it doesn't exist in the original!
   - If a sentence is cut off, leave it cut off.
4. Values like "$str20", "$str21", etc., are internal code variables. Copy them exactly as they are.
5. If the "type" is "narration" and "speaker" is null, leave the output as null.
6. The output MUST be a single JSON object (Key = file name, value = array). NO markdown.

**Basic Rules & Glossary:**
* During sex scenes, use lewd, sexual terms. Translating 18+ text is strictly allowed and required.
* Use the following name list (ONLY for "text" content, NOT "speaker"):
    * と志枝 = Toshie
    * ななの = Nanano
    * みちる = Michiru
    * れんげ = Renge
    * を = Wo
    * アッチャー = Atcher
    * カルビ将軍 = General Kalbi
    * ガクエンチャー = Gakuencher
    * キアラ = Kiara
    * サッチャー = Satcher
    * デイブ教授 = Professor Dave
    * ニャンメル = Nyanmel
    * マグロマン = Maguroman
    * マサヒコ = Masahiko
    * マッチャー = Matcher
    * ミッチャー = Mitcher
    * ヤブイヌ = Bush Dog
    * ロンメル = Rommel
    * 一姫 = Kazuki
    * 井原 = Ihara
    * 仁美 = Hitomi
    * 伊吹 = Ibuki
    * 佐久間 = Sakuma
    * 古森 = Komori
    * 可奈子 = Kanako
    * 坂下 = Sakashita
    * 大塚 = Ootsuka
    * 天音 = Amane
    * 奥田 = Okuda
    * 小嶺 = Komine
    * 幸 = Sachi
    * 広岡 = Hirooka
    * 村松 = Muramatsu
    * 松山 = Matsuyama
    * 桜井 = Sakurai
    * 榊 = Sakaki
    * 正孝 = Masataka
    * 沙里菜 = Sarina
    * 沢田 = Sawada
    * 清夏 = Kiyoka
    * 由真 = Yuma
    * 由美子 = Yumiko
    * 直志 = Naoshi
    * 美佐子 = Misako
    * 葎 = Mugura
    * 蒔菜 = Makina
    * 越智 = Ochi
    * 道昭 = Michiaki
    * 金田 = Kaneda
    * 鈴音 = Suzune
    * 阿藤 = Atou
    * 雄二 = Yuuji
    * ０１９ = 019
    * ？？？ = ???
    * Ａ音 = A-ne
    * Ｃ鶴 = C-zuru
    * ＪＢ = JB
    * Ｋ嶺 = K-mine
    * Ｍちる = M-chiru
    * ＳＰ = SP
    * ＳＰ２ = SP2
    * ＳＰ３ = SP3
    * Ｙ美子 = Y-miko
    * センパイ = Senpai

**Style Guide:**
* **Casual & Natural:** Use fluent, everyday conversational English for most translations. Use military jargon when appropriate. 
* **Pronouns:** Use "I" for the first person. Use "Senpai" to translate センパイ and 先輩.
* **Onomatopoeia:** Translate spoken sound effects (example: "Fua...", "Uuu...", "Ahaha").
* **Tag Formatting:** Maintain HTML tags (such as `<BR>` dan `<FWSP>`) EXACTLY in their original positions. Do not delete or move them to other lines/ids.

**JSON data to be translated:**
{json_content}
"""

# ═══════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════

class ProhibitedContentError(Exception):
    """Prompt blocked by PROHIBITED_CONTENT — do not retry, go directly per-item."""
    pass

# ═══════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════

@dataclass
class ValidationError:
    filename: str; error_type: str; detail: str
    def __str__(self): return f"[{self.error_type}] {self.filename}: {self.detail}"

@dataclass
class FileValidationResult:
    filename: str
    is_valid: bool = True
    errors: list[ValidationError] = field(default_factory=list)

    def add_error(self, error_type: str, detail: str):
        self.errors.append(ValidationError(self.filename, error_type, detail))
        self.is_valid = False

    def has_error_type(self, t: str) -> bool:
        return any(e.error_type == t for e in self.errors)

    def only_static_key_errors(self) -> bool:
        return bool(self.errors) and all(e.error_type == "STATIC_KEY_CHANGED" for e in self.errors)

# ═══════════════════════════════════════════════════════════════
# INIT
# ═══════════════════════════════════════════════════════════════

load_dotenv()

def init_gemini() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not found in .env!")
        sys.exit(1)
    return genai.Client(api_key=api_key)

# ═══════════════════════════════════════════════════════════════
# I/O
# ═══════════════════════════════════════════════════════════════

async def read_json_file(filepath: Path) -> list[dict]:
    async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
        return json.loads(await f.read())

async def write_json_file(filepath: Path, data: list[dict]):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))

# ═══════════════════════════════════════════════════════════════
# AUTO-REPAIR
# ═══════════════════════════════════════════════════════════════

def repair_static_keys(input_data: list[dict], output_data: list[dict]) -> list[dict]:
    repaired = []
    for idx, out_item in enumerate(output_data):
        new_item = dict(out_item)
        if idx < len(input_data):
            in_item = input_data[idx]
            for key in STATIC_KEYS:
                if key in in_item:
                    new_item[key] = in_item[key]
                elif key in new_item:
                    del new_item[key]
        repaired.append(new_item)
    return repaired

# ═══════════════════════════════════════════════════════════════
# JSON EXTRACTOR
# ═══════════════════════════════════════════════════════════════

def _extract_json_from_text(raw: str) -> str:
    text = raw.strip()
    fence = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    m = fence.search(text)
    if m:
        candidate = m.group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            text = candidate

    for open_c, close_c in [('{', '}'), ('[', ']')]:
        start = text.find(open_c)
        if start == -1:
            continue
        depth, end_idx, in_str, esc = 0, -1, False, False
        for i, ch in enumerate(text[start:], start):
            if esc: esc = False; continue
            if ch == '\\' and in_str: esc = True; continue
            if ch == '"': in_str = not in_str; continue
            if in_str: continue
            if ch == open_c: depth += 1
            elif ch == close_c:
                depth -= 1
                if depth == 0: end_idx = i; break
        if end_idx != -1:
            candidate = text[start:end_idx + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass
    return text

# ═══════════════════════════════════════════════════════════════
# GEMINI API — with timeout, retry, safety settings
# ═══════════════════════════════════════════════════════════════

def _is_retryable(e: Exception) -> bool:
    msg = str(e).lower()
    return any(k in msg for k in ["503", "unavailable", "overload", "resource exhausted",
                                   "429", "too many requests", "timeout", "empty", "invalid json"])

def call_gemini_api(client: genai.Client, batch_data: dict[str, list]) -> dict[str, list]:
    """Send batch to Gemini. Auto-retry for temporary errors. Raise ProhibitedContentError if blocked."""
    prompt      = MASTER_PROMPT.replace("{json_content}", json.dumps(batch_data, ensure_ascii=False, indent=2))
    last_error  = None

    for attempt_idx, delay in enumerate([0] + API_RETRY_DELAYS, start=1):
        if delay > 0:
            print(f"  [RETRY-API {attempt_idx}/{len(API_RETRY_DELAYS)+1}] Pause for {delay}s...")
            time.sleep(delay)

        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=131072,
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,  threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,        threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,         threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,  threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ],
                ),
            )
        except Exception as e:
            last_error = e
            if _is_retryable(e) and attempt_idx < len([0] + API_RETRY_DELAYS):
                print(f"  [!] API error (retry): {str(e)[:100]}")
                continue
            raise

        # ── Cek PROHIBITED_CONTENT di prompt_feedback ──
        pf = getattr(response, "prompt_feedback", None)
        block_reason = getattr(pf, "block_reason", None)
        if block_reason is not None:
            block_name = getattr(block_reason, "name", str(block_reason))
            if block_name and block_name not in ("0", "BLOCK_REASON_UNSPECIFIED", "UNSPECIFIED"):
                raise ProhibitedContentError(block_name)

        # ── Cek candidate kosong ──
        raw_text = (getattr(response, "text", None) or "").strip()
        if not raw_text:
            # Candidate kosong bisa karena overload/timeout — retry dulu, bukan per-item
            last_error = ValueError("Empty response from API (empty candidate)")
            if attempt_idx < len([0] + API_RETRY_DELAYS):
                print(f"  [!] Empty response (retry)...")
                continue
            raise last_error

        # ── Parse JSON ──
        cleaned = _extract_json_from_text(raw_text)
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError as e:
            last_error = ValueError(f"Invalid JSON: {e}\n{raw_text[:300]}")
            if attempt_idx < len([0] + API_RETRY_DELAYS):
                print(f"  [!] JSON invalid (retry): {e}")
                continue
            raise last_error

        # ── Auto-wrap list → dict jika 1 file ──
        if isinstance(result, list):
            filenames = list(batch_data.keys())
            if len(filenames) == 1:
                result = {filenames[0]: result}
            else:
                last_error = ValueError(f"Response is a list even though there are {len(filenames)} files")
                if attempt_idx < len([0] + API_RETRY_DELAYS):
                    continue
                raise last_error

        if not isinstance(result, dict):
            raise ValueError(f"Response is not a dict: {type(result).__name__}")

        return result

    raise last_error or RuntimeError("All API retries exhausted")


def call_gemini_api_per_item(client: genai.Client, filename: str, items: list[dict]) -> list[dict]:
    """
    Fallback when file is blocked by PROHIBITED_CONTENT.
    Translate each item one by one with a per-item timeout.
    Blocked items → original text is maintained, the number of items remains the same.
    One ThreadPoolExecutor is used for all items — do not create/destroy per item.
    """
    import concurrent.futures as _cf
    results = []
    blocked = 0

    # Satu executor untuk semua items — jauh lebih efisien untuk file 100+ dialog
    with _cf.ThreadPoolExecutor(max_workers=1) as pool:
        for i, item in enumerate(items):
            if not (item.get("text") or "").strip():
                results.append(item)
                continue
            try:
                future = pool.submit(call_gemini_api, client, {filename: [item]})
                try:
                    api_result = future.result(timeout=API_TIMEOUT)
                except _cf.TimeoutError:
                    print(f"  [!] Per-item timeout index {i} — original text preserved")
                    results.append(item)
                    continue
                translated = api_result.get(filename, [item])
                out = translated[0] if translated else item
                for key in STATIC_KEYS:
                    if key in item:
                        out[key] = item[key]
                results.append(out)
            except ProhibitedContentError:
                blocked += 1
                results.append(item)  # pertahankan teks asli
            except Exception:
                results.append(item)

    if blocked:
        print(f"  [INFO] {blocked}/{len(items)} items blocked — original text preserved")
    return results

# ═══════════════════════════════════════════════════════════════
# VALIDATOR
# ═══════════════════════════════════════════════════════════════

def load_json_safe(filepath: Path) -> tuple[list | None, str | None]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return None, f"Not an array (type: {type(data).__name__})"
        return data, None
    except json.JSONDecodeError as e: return None, f"Invalid JSON: {e}"
    except FileNotFoundError:         return None, "File not found"
    except Exception as e:            return None, f"Error: {e}"


def validate_file_pair(filename: str) -> FileValidationResult:
    result = FileValidationResult(filename=filename)
    in_data,  err = load_json_safe(INPUT_FOLDER  / filename)
    if err: result.add_error("INPUT_JSON_INVALID", err);  return result
    # FILE_MISSING harus dicek SEBELUM load_json_safe output,
    # karena load_json_safe mengembalikan "File tidak ditemukan" sebagai OUTPUT_JSON_INVALID
    if not (OUTPUT_FOLDER / filename).exists():
        result.add_error("FILE_MISSING", "Output file does not exist"); return result
    out_data, err = load_json_safe(OUTPUT_FOLDER / filename)
    if err: result.add_error("OUTPUT_JSON_INVALID", err); return result

    len_in, len_out = len(in_data), len(out_data)
    if len_in != len_out:
        result.add_error("COUNT_MISMATCH",
            f"Item count mismatch: input={len_in}, output={len_out} (difference {abs(len_in-len_out)})")

    for idx in range(min(len_in, len_out)):
        in_item, out_item = in_data[idx], out_data[idx]
        if not isinstance(in_item, dict):
            result.add_error("ITEM_FORMAT_INVALID", f"Index {idx} INPUT is not a dict"); continue
        if not isinstance(out_item, dict):
            result.add_error("ITEM_FORMAT_INVALID", f"Index {idx} OUTPUT is not a dict"); continue
        for key in STATIC_KEYS:
            in_v, out_v = in_item.get(key), out_item.get(key)
            if key not in out_item:
                result.add_error("STATIC_KEY_MISSING", f"Index {idx}: '{key}' is missing (input={repr(in_v)})")
            elif in_v != out_v:
                result.add_error("STATIC_KEY_CHANGED", f"Index {idx}: '{key}' changed! {repr(in_v)} -> {repr(out_v)}")
        for key in MUTABLE_KEYS:
            if key not in out_item:
                result.add_error("MUTABLE_KEY_MISSING", f"Index {idx}: key '{key}' is missing")
        unexpected = set(out_item.keys()) - set(in_item.keys())
        if unexpected:
            result.add_error("UNEXPECTED_KEYS", f"Index {idx}: new key: {unexpected}")
    return result


def print_validation_inline(result: FileValidationResult):
    if result.is_valid:
        print(f"       OK  VALIDATION SUCCESSFUL")
    else:
        print(f"       !!  VALIDATION FAILED  ({len(result.errors)} issues):")
        for err in result.errors:
            print(f"            -> [{err.error_type}] {err.detail}")

# ═══════════════════════════════════════════════════════════════
# PER-FILE PROCESSOR (dengan retry + repair + per-item fallback)
# ═══════════════════════════════════════════════════════════════

async def process_file_with_repair(
    client: genai.Client,
    filepath: Path,
    global_failed: list[FileValidationResult],
) -> tuple[int, int]:
    fname = filepath.name
    input_data, err = load_json_safe(filepath)
    if err:
        print(f"  [FAILED] {fname}  (failed to read input: {err})")
        return 0, 1

    async def _run_api(data):
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, call_gemini_api, client, {fname: data}),
            timeout=API_TIMEOUT,
        )

    async def _run_per_item():
        loop = asyncio.get_event_loop()
        # Timeout flat API_TIMEOUT * 3 = 450s (~7.5 menit).
        # Tidak dikali jumlah item — file 200 dialog tidak boleh jalan 8+ jam.
        # Tiap item sudah punya timeout internal sendiri (future.result(timeout=API_TIMEOUT)),
        # jadi ini hanya safety net untuk kasus executor leak.
        return await asyncio.wait_for(
            loop.run_in_executor(None, call_gemini_api_per_item, client, fname, input_data),
            timeout=API_TIMEOUT * 3,
        )

    async def _save_validate_repair(out_data) -> tuple[bool, FileValidationResult]:
        out_path = OUTPUT_FOLDER / fname
        await write_json_file(out_path, out_data)
        val = validate_file_pair(fname)
        if not val.is_valid and val.only_static_key_errors():
            print(f"  [AUTO-REPAIR] {fname}  → {len(val.errors)} static keys fixed")
            repaired = repair_static_keys(input_data, out_data)
            await write_json_file(out_path, repaired)
            val = validate_file_pair(fname)
        return val.is_valid, val

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            api_result = await _run_api(input_data)
        except asyncio.TimeoutError:
            if attempt <= MAX_RETRIES:
                delay = API_RETRY_DELAYS[min(attempt-1, len(API_RETRY_DELAYS)-1)]
                print(f"  [TIMEOUT {attempt}/{MAX_RETRIES}] {fname}  — retry in {delay}s...")
                await asyncio.sleep(delay)
                continue
            print(f"  [FAILED] {fname}  (all retries timed out)")
            return 0, 1
        except ProhibitedContentError as e:
            print(f"  [BLOCKED] {fname}  (PROHIBITED_CONTENT: {e}) — per-item fallback...")
            try:
                out_data = await _run_per_item()
            except Exception as ex:
                print(f"  [FAILED] {fname}  (per-item failed: {ex})")
                return 0, 1
            ok, val = await _save_validate_repair(out_data)
            if ok:
                print(f"  [OK]    {fname}  (via per-item)")
            else:
                print(f"  [FAILED] {fname}  (per-item: validation failed)")
                global_failed.append(val)
            print_validation_inline(val)
            return (1, 0) if ok else (0, 1)
        except Exception as e:
            msg = str(e).split("\n")[0][:100]
            if attempt <= MAX_RETRIES:
                delay = API_RETRY_DELAYS[min(attempt-1, len(API_RETRY_DELAYS)-1)]
                print(f"  [RETRY {attempt}/{MAX_RETRIES}] {fname}  → {msg}  (delay {delay}s)")
                await asyncio.sleep(delay)
                continue
            print(f"  [FAILED] {fname}  (all retries exhausted: {msg})")
            return 0, 1

        if fname not in api_result:
            if attempt <= MAX_RETRIES:
                delay = API_RETRY_DELAYS[min(attempt-1, len(API_RETRY_DELAYS)-1)]
                print(f"  [RETRY {attempt}/{MAX_RETRIES}] {fname}  → not in response (delay {delay}s)")
                await asyncio.sleep(delay)
                continue
            print(f"  [FAILED] {fname}  (not in API response)")
            return 0, 1

        out_data = api_result[fname]
        ok, val = await _save_validate_repair(out_data)

        if not ok and val.has_error_type("COUNT_MISMATCH"):
            if attempt <= MAX_RETRIES:
                delay = API_RETRY_DELAYS[min(attempt-1, len(API_RETRY_DELAYS)-1)]
                print(f"  [RETRY {attempt}/{MAX_RETRIES}] {fname}  → COUNT_MISMATCH (jeda {delay}s)")
                await asyncio.sleep(delay)
                continue

        if ok:
            print(f"  [OK]    {fname}")
        else:
            print(f"  [FAILED] {fname}  (validation failed)")
            global_failed.append(val)
        print_validation_inline(val)
        return (1, 0) if ok else (0, 1)

    print(f"  [FAILED] {fname}  (exhausted all attempts)")
    return 0, 1

# ═══════════════════════════════════════════════════════════════
# BATCH SPLITTER
# ═══════════════════════════════════════════════════════════════

def split_batch_by_payload(files: list[Path], contents: dict[str, list]) -> list[list[Path]]:
    batches, current, size = [], [], 0
    for fp in files:
        fsize = len(json.dumps(contents.get(fp.name, []), ensure_ascii=False))
        if current and size + fsize > MAX_PAYLOAD_CHARS:
            batches.append(current)
            current, size = [fp], fsize
        else:
            current.append(fp)
            size += fsize
    if current:
        batches.append(current)
    return batches

# ═══════════════════════════════════════════════════════════════
# BATCH PROCESSOR
# ═══════════════════════════════════════════════════════════════

async def process_and_validate_batch(
    client: genai.Client,
    batch_files: list[Path],
    global_failed: list[FileValidationResult],
) -> tuple[int, int]:
    ok_total = fail_total = 0

    # Skip file yang sudah ada di output (jika SKIP_EXISTING=True)
    if SKIP_EXISTING:
        skipped = [f for f in batch_files if (OUTPUT_FOLDER / f.name).exists()]
        if skipped:
            # Cache hasil validasi — hindari double disk I/O per file
            skip_val_cache: dict[str, FileValidationResult] = {
                sf.name: validate_file_pair(sf.name) for sf in skipped
            }
            for sf in skipped:
                val = skip_val_cache[sf.name]
                if val.is_valid:
                    print(f"  [SKIP] {sf.name}  (valid output, skipping)")
                    ok_total += 1
                else:
                    print(f"  [SKIP-INVALID] {sf.name}  (output exists but is invalid, reprocessing)")
        else:
            skip_val_cache = {}
        # Gunakan cache — tidak perlu validate_file_pair ulang
        batch_files = [
            f for f in batch_files
            if not (OUTPUT_FOLDER / f.name).exists()
            or not skip_val_cache.get(f.name, FileValidationResult(f.name, False)).is_valid
        ]
        if not batch_files:
            return ok_total, fail_total

    # Baca semua file input paralel
    file_contents = await asyncio.gather(*[read_json_file(f) for f in batch_files], return_exceptions=True)
    input_cache: dict[str, list] = {}
    valid_files: list[Path] = []

    for fp, content in zip(batch_files, file_contents):
        if isinstance(content, Exception):
            print(f"  [FAILED] {fp.name}  (read failed: {content})")
            fail_total += 1
        else:
            input_cache[fp.name] = content
            valid_files.append(fp)

    if not valid_files:
        return ok_total, fail_total

    # Smart split jika payload besar
    sub_batches = split_batch_by_payload(valid_files, input_cache)
    if len(sub_batches) > 1:
        total_c = sum(len(json.dumps(v, ensure_ascii=False)) for v in input_cache.values())
        print(f"  [SPLIT] {total_c:,} char → {len(sub_batches)} sub-batch")

    for sb_idx, sub_batch in enumerate(sub_batches, 1):
        if len(sub_batches) > 1:
            print(f"  [SUB {sb_idx}/{len(sub_batches)}] {', '.join(f.name for f in sub_batch)}")
        sub_payload = {f.name: input_cache[f.name] for f in sub_batch}
        ok, fail = await _send_and_process(client, sub_batch, sub_payload, input_cache, global_failed)
        ok_total += ok; fail_total += fail
        if sb_idx < len(sub_batches):
            await asyncio.sleep(1.5)

    return ok_total, fail_total


async def _send_and_process(
    client, valid_files, batch_payload, input_cache, global_failed
) -> tuple[int, int]:
    success_count = fail_count = 0

    payload_chars = len(json.dumps(batch_payload, ensure_ascii=False))
    print(f"  [SEND] {len(valid_files)} file | {payload_chars:,} char | {', '.join(f.name for f in valid_files)}")

    try:
        loop = asyncio.get_event_loop()
        api_result = await asyncio.wait_for(
            loop.run_in_executor(None, call_gemini_api, client, batch_payload),
            timeout=API_TIMEOUT,
        )
    except asyncio.TimeoutError:
        print(f"\n  [!] Timeout {API_TIMEOUT}s — fallback per-file...")
        for fp in valid_files:
            ok, fail = await process_file_with_repair(client, fp, global_failed)
            success_count += ok; fail_count += fail
        return success_count, fail_count
    except ProhibitedContentError:
        print(f"\n  [!] Batch PROHIBITED_CONTENT — fallback per-file...")
        for fp in valid_files:
            ok, fail = await process_file_with_repair(client, fp, global_failed)
            success_count += ok; fail_count += fail
        return success_count, fail_count
    except Exception as e:
        print(f"\n  [!] Batch error: {str(e).split(chr(10))[0][:120]}")
        print(f"  [FALLBACK] per-file...")
        for fp in valid_files:
            ok, fail = await process_file_with_repair(client, fp, global_failed)
            success_count += ok; fail_count += fail
        return success_count, fail_count

    for filepath in valid_files:
        fname   = filepath.name
        in_data = input_cache[fname]

        if fname not in api_result:
            print(f"  [RETRY-SINGLE] {fname}  → not in response")
            ok, fail = await process_file_with_repair(client, filepath, global_failed)
            success_count += ok; fail_count += fail
            continue

        out_data = api_result[fname]
        out_path = OUTPUT_FOLDER / fname
        try:
            await write_json_file(out_path, out_data)
        except Exception as e:
            print(f"  [FAILED] {fname}  (save failed: {e})")
            fail_count += 1; continue

        val = validate_file_pair(fname)

        if not val.is_valid and val.only_static_key_errors():
            print(f"  [AUTO-REPAIR] {fname}  → {len(val.errors)} static key")
            repaired = repair_static_keys(in_data, out_data)
            await write_json_file(out_path, repaired)
            val = validate_file_pair(fname)

        elif not val.is_valid and val.has_error_type("COUNT_MISMATCH"):
            print(f"  [RETRY-SINGLE] {fname}  → COUNT_MISMATCH")
            await asyncio.sleep(1.5)
            ok, fail = await process_file_with_repair(client, filepath, global_failed)
            success_count += ok; fail_count += fail
            continue

        elif not val.is_valid and val.has_error_type("OUTPUT_JSON_INVALID"):
            print(f"  [RETRY-SINGLE] {fname}  → JSON invalid")
            ok, fail = await process_file_with_repair(client, filepath, global_failed)
            success_count += ok; fail_count += fail
            continue

        if val.is_valid:
            print(f"  [OK]    {fname}")
            success_count += 1
        else:
            print(f"  [FAILED] {fname}  (validation failed)")
            fail_count += 1
            global_failed.append(val)
        print_validation_inline(val)

    return success_count, fail_count

# ═══════════════════════════════════════════════════════════════
# ERROR LOG
# ═══════════════════════════════════════════════════════════════

def write_error_log(failed: list[FileValidationResult], stats: dict):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ERROR_LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"VALIDATION ERROR LOG  |  {ts}\n")
        f.write(f"Total:{stats['total']}  OK:{stats['success']}  Failed:{stats['fail']}\n\n")
        for r in failed:
            f.write(f">> {r.filename}\n")
            for e in r.errors:
                f.write(f"  [{e.error_type}] {e.detail}\n")
            f.write("\n")

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    print("=" * 65)
    print("  GEMINI BATCH PROCESSOR + LIVE VALIDATOR  ")
    print("=" * 65)

    if not INPUT_FOLDER.exists():
        print(f"[ERROR] Folder '{INPUT_FOLDER}' not found!")
        sys.exit(1)

    json_files = sorted(INPUT_FOLDER.glob("*.json"))
    if not json_files:
        print(f"[INFO] No .json files in '{INPUT_FOLDER}'."); sys.exit(0)

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    total_files   = len(json_files)
    total_batches = (total_files + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"  Input   : {INPUT_FOLDER.resolve()}")
    print(f"  Output  : {OUTPUT_FOLDER.resolve()}")
    print(f"  File    : {total_files}  |  Batch: {total_batches}  |  Model: {GEMINI_MODEL}")
    print(f"  Timeout : {API_TIMEOUT}s  |  Retry: {MAX_RETRIES}x  |  Backoff: {API_RETRY_DELAYS}")
    print(f"  Payload : max {MAX_PAYLOAD_CHARS:,} chars/batch\n")

    client = init_gemini()
    batches = [json_files[i:i+BATCH_SIZE] for i in range(0, total_files, BATCH_SIZE)]
    total_success = total_fail = 0
    global_failed: list[FileValidationResult] = []
    start_time = time.time()

    # Hitung skip sebelum mulai (SKIP_EXISTING: file sudah ada + valid di output)
    if SKIP_EXISTING:
        total_skip = sum(
            1 for f in json_files
            if (OUTPUT_FOLDER / f.name).exists() and validate_file_pair(f.name).is_valid
        )
    else:
        total_skip = 0

    for batch_idx, batch in enumerate(batches, 1):
        print(f"+-- Batch {batch_idx}/{total_batches}  ({len(batch)} file) " + "-"*28)
        print(f"|   Sending to Gemini API...")
        t0 = time.time()
        ok, fail = await process_and_validate_batch(client, batch, global_failed)
        total_success += ok; total_fail += fail
        print(f"+-- Finished {time.time()-t0:.1f}s  |  OK: {ok}  Failed: {fail}\n")
        if batch_idx < total_batches:
            print(f"    Delay {BATCH_DELAY}s...\n")
            await asyncio.sleep(BATCH_DELAY)

    elapsed = time.time() - start_time
    print("=" * 65)
    skip_str = f"  Skip: {total_skip}  |" if SKIP_EXISTING and total_skip > 0 else ""
    print(f"  Duration: {elapsed:.0f}s  |  OK: {total_success}  Failed: {total_fail}  |{skip_str}  Total: {total_files}")
    if global_failed:
        write_error_log(global_failed, {"total": total_files, "success": total_success, "fail": total_fail})
        print(f"  {len(global_failed)} problematic files → {ERROR_LOG_FILE}")
    else:
        print("  All files passed validation!")
        if ERROR_LOG_FILE.exists(): ERROR_LOG_FILE.unlink()
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
