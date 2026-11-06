#!/usr/bin/env python3
"""
scripts/check_sources.py
Validator for Kaggle agentic research sources and reading notes.

Verifies:
1. Each listed source file exists and is non-empty.
2. Each source file contains the recorded command and comment count.
3. research/discoveries/reading_notes.md exists and is non-empty.
4. Every quote labeled [QUOTED] is under 25 words.
5. Every quote labeled [QUOTED] appears literally in its referenced source file.
"""

import sys
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SOURCES = [
    {
        "path": BASE_DIR / "research" / "sources" / "s6e11_756276.md",
        "command": "kaggle competitions topics show playground-series-s6e11 756276",
        "comment_count": "6",
        "label": "READ"
    },
    {
        "path": BASE_DIR / "research" / "sources" / "s6e9_745013.md",
        "command": "kaggle competitions topics show playground-series-s6e9 745013",
        "comment_count": "26",
        "label": "READ"
    },
    {
        "path": BASE_DIR / "research" / "sources" / "s6e8_738592.md",
        "command": "kaggle competitions topics show playground-series-s6e8 738592",
        "comment_count": "78",
        "label": "READ"
    },
    {
        "path": BASE_DIR / "research" / "sources" / "s6e5_703615.md",
        "command": "kaggle competitions topics show playground-series-s6e5 703615",
        "comment_count": "26",
        "label": "READ"
    },
    {
        "path": BASE_DIR / "research" / "sources" / "s6e3_686686.md",
        "command": "kaggle competitions topics show playground-series-s6e3 686686",
        "comment_count": "101",
        "label": "READ"
    },
    {
        "path": BASE_DIR / "research" / "sources" / "kgmon_playbook.md",
        "command": "curl -s \"https://raw.githubusercontent.com/cdeotte/KGMON-Playbook-2026/main/README.md\"",
        "comment_count": "0",
        "label": "READ"
    }
]

READING_NOTES_PATH = BASE_DIR / "research" / "discoveries" / "reading_notes.md"


def main() -> int:
    errors = []
    print("=== Running Source & Notes Verification ===")

    # 1. Check each source file
    for src in SOURCES:
        p = src["path"]
        rel = p.relative_to(BASE_DIR)
        print(f"\nChecking source: {rel}")
        if not p.exists():
            errors.append(f"Missing source file: {rel}")
            continue

        content = p.read_text(encoding="utf-8")
        if not content.strip():
            errors.append(f"Source file is empty: {rel}")
            continue

        # Check recorded command
        cmd = src["command"]
        if cmd not in content:
            errors.append(f"Source {rel} does not contain recorded command: {cmd}")
        else:
            print(f"  [OK] Found command: {cmd}")

        # Check comment count (e.g., 'Comments: 26' or 'comment_count: 26')
        cc = src["comment_count"]
        cc_patterns = [
            rf"Comments:\s*{cc}\b",
            rf"Comment Count\**:\s*{cc}\b",
            rf"comment_count\**:\s*{cc}\b",
            rf"Comments count\**:\s*{cc}\b",
            rf"\b{cc}\s+comments\b"
        ]
        if not any(re.search(pat, content, re.IGNORECASE) for pat in cc_patterns):
            errors.append(f"Source {rel} does not contain comment count '{cc}'")
        else:
            print(f"  [OK] Found comment count: {cc}")

        # Check status label
        lbl = src["label"]
        if lbl not in content:
            errors.append(f"Source {rel} does not contain status label: {lbl}")
        else:
            print(f"  [OK] Found status label: {lbl}")

    # 2. Check reading notes
    print(f"\nChecking reading notes: {READING_NOTES_PATH.relative_to(BASE_DIR)}")
    if not READING_NOTES_PATH.exists():
        errors.append(f"Missing reading notes: {READING_NOTES_PATH.relative_to(BASE_DIR)}")
        return fail(errors)

    notes_content = READING_NOTES_PATH.read_text(encoding="utf-8")
    if not notes_content.strip():
        errors.append(f"Reading notes file is empty: {READING_NOTES_PATH.relative_to(BASE_DIR)}")
        return fail(errors)

    # 3. Parse quotes from reading notes
    # Structure expected:
    # - **Status**: [QUOTED]
    # - **Location**: `research/sources/s6e9_745013.md` (or similar)
    # - **Quote**: "..."
    #
    # We will parse entries with regex or line-by-line block matching.
    quote_blocks = re.findall(
        r"-\s*\*\*Status\*\*:\s*\[QUOTED\].*?"
        r"-\s*\*\*Location\*\*:\s*`?([^`\n\(\)]+)`?.*?"
        r"-\s*\*\*Quote\*\*:\s*\"([^\"]+)\"",
        notes_content,
        re.DOTALL
    )

    if not quote_blocks:
        errors.append("No [QUOTED] blocks found in reading notes matching expected format!")

    print(f"\nFound {len(quote_blocks)} [QUOTED] entries in reading notes:")

    for idx, (loc_str, quote_str) in enumerate(quote_blocks, 1):
        loc_str = loc_str.strip()
        quote_str = quote_str.strip()
        word_count = len(quote_str.split())
        print(f"  Quote #{idx} ({word_count} words): \"{quote_str[:40]}...\"")

        # Check word count
        if word_count >= 25:
            errors.append(f"Quote #{idx} exceeds word limit (<25 words): got {word_count} words: \"{quote_str}\"")

        # Resolve location path
        loc_path = BASE_DIR / loc_str
        if not loc_path.exists():
            errors.append(f"Quote #{idx} location does not exist: {loc_str}")
            continue

        src_text = loc_path.read_text(encoding="utf-8")
        if quote_str not in src_text:
            errors.append(f"Quote #{idx} does not appear literally in {loc_str}!\nQuote: \"{quote_str}\"")
        else:
            print(f"    [OK] Literal match confirmed in {loc_str}")

    if errors:
        return fail(errors)

    print("\n✅ ALL CHECKS PASSED: All source files and quotes verified successfully!")
    return 0


def fail(errors):
    print("\n❌ VERIFICATION FAILED:")
    for err in errors:
        print(f"  - {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
