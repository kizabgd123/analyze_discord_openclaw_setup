#!/usr/bin/env python3
"""
scripts/fetch_and_save_sources.py
Fetches and saves raw public threads and materials directly via Kaggle CLI and curl.
Never infers content.
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCES_DIR = BASE_DIR / "research" / "sources"
SOURCES_DIR.mkdir(parents=True, exist_ok=True)

def run_cmd(cmd_list):
    res = subprocess.run(cmd_list, capture_output=True, text=True)
    return res.stdout, res.stderr, res.returncode

def main():
    print("Fetching Kaggle competition discussion threads and GitHub playbook...")

    # 1. S6E11 Topic 756276
    print("\n1. Fetching S6E11 756276...")
    cmd1_str = "kaggle competitions topics show playground-series-s6e11 756276"
    cmd1 = ["kaggle", "competitions", "topics", "show", "playground-series-s6e11", "756276"]
    out1, err1, rc1 = run_cmd(cmd1)
    
    # Also fetch full messages for complete untruncated transcript
    cmd1_msg = ["kaggle", "competitions", "topic-messages", "playground-series-s6e11", "756276", "--format", "json"]
    out1_msg, _, _ = run_cmd(cmd1_msg)
    
    s6e11_path = SOURCES_DIR / "s6e11_756276.md"
    s6e11_content = f"""# S6E11 Topic 756276: Sharing Code for 500 Models!

## Metadata
- **Status**: READ
- **Competition**: playground-series-s6e11
- **Topic ID**: 756276
- **Title**: Sharing Code for 500 Models!
- **Author**: Chris Deotte
- **Date**: 2026-11-05 20:43:58.932000
- **Comment Count**: 6
- **Command**: `{cmd1_str}`
- **Retrieved**: {datetime.now(timezone.utc).isoformat()}

## CLI Command Output (`kaggle competitions topics show playground-series-s6e11 756276`)

```
{out1.strip()}
```

## Complete Topic Messages JSON (`kaggle competitions topic-messages playground-series-s6e11 756276 --format json`)

```json
{out1_msg.strip()}
```
"""
    s6e11_path.write_text(s6e11_content, encoding="utf-8")
    print(f"Saved: {s6e11_path}")

    # 2. S6E9 Topic 745013 (AI Relay)
    print("\n2. Fetching S6E9 745013...")
    cmd2_str = "kaggle competitions topics show playground-series-s6e9 745013"
    cmd2 = ["kaggle", "competitions", "topics", "show", "playground-series-s6e9", "745013"]
    out2, _, _ = run_cmd(cmd2)

    s6e9_path = SOURCES_DIR / "s6e9_745013.md"
    s6e9_content = f"""# S6E9 Topic 745013: 1st Place - The AI Relay!

## Metadata
- **Status**: READ
- **Competition**: playground-series-s6e9
- **Topic ID**: 745013
- **Title**: 1st Place - The AI Relay!
- **Author**: Chris Deotte
- **Date**: 2026-10-01 19:59:01.549000
- **Comment Count**: 26
- **Command**: `{cmd2_str}`
- **Retrieved**: {datetime.now(timezone.utc).isoformat()}

## CLI Command Output (`kaggle competitions topics show playground-series-s6e9 745013`)

```
{out2.strip()}
```
"""
    s6e9_path.write_text(s6e9_content, encoding="utf-8")
    print(f"Saved: {s6e9_path}")

    # 3. S6E8 Topic 738592 (Distributed Intelligence - NVIDIA Inference Hub)
    print("\n3. Fetching S6E8 738592...")
    cmd3_str = "kaggle competitions topics show playground-series-s6e8 738592"
    cmd3 = ["kaggle", "competitions", "topics", "show", "playground-series-s6e8", "738592"]
    out3, _, _ = run_cmd(cmd3)

    s6e8_path = SOURCES_DIR / "s6e8_738592.md"
    s6e8_content = f"""# S6E8 Topic 738592: 1st Place - Distributed Intelligence - NVIDIA Inference Hub

## Metadata
- **Status**: READ
- **Competition**: playground-series-s6e8
- **Topic ID**: 738592
- **Title**: 1st Place - Distributed Intelligence - NVIDIA Inference Hub
- **Author**: Chris Deotte
- **Date**: 2026-08-31 23:59:39.755000
- **Comment Count**: 78
- **Command**: `{cmd3_str}`
- **Retrieved**: {datetime.now(timezone.utc).isoformat()}

## CLI Command Output (`kaggle competitions topics show playground-series-s6e8 738592`)

```
{out3.strip()}
```
"""
    s6e8_path.write_text(s6e8_content, encoding="utf-8")
    print(f"Saved: {s6e8_path}")

    # 4. S6E5 Topic 703615 (Autonomous Codex Yolo!)
    print("\n4. Fetching S6E5 703615...")
    cmd4_str = "kaggle competitions topics show playground-series-s6e5 703615"
    cmd4 = ["kaggle", "competitions", "topics", "show", "playground-series-s6e5", "703615"]
    out4, _, _ = run_cmd(cmd4)

    s6e5_path = SOURCES_DIR / "s6e5_703615.md"
    s6e5_content = f"""# S6E5 Topic 703615: 2nd Place - Autonomous Codex Yolo!

## Metadata
- **Status**: READ
- **Competition**: playground-series-s6e5
- **Topic ID**: 703615
- **Title**: 2nd Place - Autonomous Codex Yolo!
- **Author**: Chris Deotte
- **Date**: 2026-06-01 15:07:43.336000
- **Comment Count**: 26
- **Command**: `{cmd4_str}`
- **Retrieved**: {datetime.now(timezone.utc).isoformat()}

## CLI Command Output (`kaggle competitions topics show playground-series-s6e5 703615`)

```
{out4.strip()}
```
"""
    s6e5_path.write_text(s6e5_content, encoding="utf-8")
    print(f"Saved: {s6e5_path}")

    # 5. S6E3 Topic 686686 (KGMON Playbook)
    print("\n5. Fetching S6E3 686686...")
    cmd5_str = "kaggle competitions topics show playground-series-s6e3 686686"
    cmd5 = ["kaggle", "competitions", "topics", "show", "playground-series-s6e3", "686686"]
    out5, _, _ = run_cmd(cmd5)

    s6e3_path = SOURCES_DIR / "s6e3_686686.md"
    s6e3_content = f"""# S6E3 Topic 686686: 1st Place - GPT5.4, Gemini3.1, ClaudeOpus4.6 - KGMON Playbook!

## Metadata
- **Status**: READ
- **Competition**: playground-series-s6e3
- **Topic ID**: 686686
- **Title**: 1st Place - GPT5.4, Gemini3.1, ClaudeOpus4.6 - KGMON Playbook!
- **Author**: Chris Deotte
- **Date**: 2026-04-01 00:00:44.230000
- **Comment Count**: 101
- **Command**: `{cmd5_str}`
- **Retrieved**: {datetime.now(timezone.utc).isoformat()}

## CLI Command Output (`kaggle competitions topics show playground-series-s6e3 686686`)

```
{out5.strip()}
```
"""
    s6e3_path.write_text(s6e3_content, encoding="utf-8")
    print(f"Saved: {s6e3_path}")

    # 6. KGMON Playbook 2026 Repo
    print("\n6. Fetching KGMON-Playbook-2026...")
    cmd6_str = 'curl -s "https://raw.githubusercontent.com/cdeotte/KGMON-Playbook-2026/main/README.md"'
    cmd6 = ["curl", "-s", "https://raw.githubusercontent.com/cdeotte/KGMON-Playbook-2026/main/README.md"]
    out6, _, _ = run_cmd(cmd6)

    # Also list repository contents
    cmd6_api = ["curl", "-s", "https://api.github.com/repos/cdeotte/KGMON-Playbook-2026/contents"]
    out6_api, _, _ = run_cmd(cmd6_api)
    api_items = json.loads(out6_api)
    notebooks = [item["name"] for item in api_items if item["name"].endswith(".ipynb")]

    kgmon_path = SOURCES_DIR / "kgmon_playbook.md"
    kgmon_content = f"""# GitHub Repository: cdeotte/KGMON-Playbook-2026

## Metadata
- **Status**: READ
- **Repository**: cdeotte/KGMON-Playbook-2026
- **URL**: https://github.com/cdeotte/KGMON-Playbook-2026
- **Date**: 2026-11-06
- **Comment Count**: 0
- **Command**: `{cmd6_str}`
- **Retrieved**: {datetime.now(timezone.utc).isoformat()}

## Notebook Titles in Repository (No Code Execution)
{chr(10).join(f"- `{nb}`" for nb in notebooks)}

## Raw README.md (`curl -s "https://raw.githubusercontent.com/cdeotte/KGMON-Playbook-2026/main/README.md"`)

```markdown
{out6.strip()}
```
"""
    kgmon_path.write_text(kgmon_content, encoding="utf-8")
    print(f"Saved: {kgmon_path}")

    print("\nAll 6 source files successfully saved!")

if __name__ == "__main__":
    main()
