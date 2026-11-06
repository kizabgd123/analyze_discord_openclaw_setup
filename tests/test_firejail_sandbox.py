"""
test_firejail_sandbox.py — Rigorous Verification Suite for Hardened Firejail Sandbox.
=====================================================================================
Covers Deliverables 1 through 4 under the Evidence Protocol:
  - Test 1 (Minimal Env): PATH, LANG, HOME set to run_dir only. No secrets/tokens/keys. Names only.
  - Test 2 (Default-Deny FS): $HOME hidden, --whitelist for run_dir, data_dir, venv_dir.
                            Probe lists $HOME contents (names only), tries sensitive paths (OK/DENIED only).
  - Test 3 (Functional): train.csv readable, sklearn/lightgbm/xgboost/catboost import, write only in run_dir,
                         secrets DENIED, network fails.
  - Test 4 (Fail-Closed): Wrong firejail path => runner refuses immediately, zero unsandboxed fallback.
"""

import os
import sys
import tempfile
import asyncio
from pathlib import Path
import pytest

from src.services.kaggle2.runner import LocalRunner


@pytest.mark.asyncio
async def test_1_minimal_explicit_environment():
    """
    Deliverable 1: Launch sandbox with minimal explicit environment (env -i style).
    SSH_AUTH_SOCK, DISCORD_BOT_TOKEN, GEMINI_API_KEY, JUDGE_HMAC_SECRET and every
    *TOKEN*/*KEY*/*SECRET* must be completely absent. Prove it by printing names only.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        probe_script = run_dir / "env_probe.py"
        probe_script.write_text(
            "import os, re\n"
            "env_names = sorted(os.environ.keys())\n"
            "print('=== ENVIRONMENT VARIABLE NAMES (NAMES ONLY) ===')\n"
            "for name in env_names:\n"
            "    print(f'VAR_NAME: {name}')\n"
            "\n"
            "forbidden_exact = ['SSH_AUTH_SOCK', 'DISCORD_BOT_TOKEN', 'GEMINI_API_KEY', 'JUDGE_HMAC_SECRET', 'MOCK_AUTH0', 'MOCK_GEMINI_JUDGE']\n"
            "found_forbidden = [k for k in env_names if k in forbidden_exact]\n"
            "print('FORBIDDEN_EXACT_FOUND:', found_forbidden)\n"
            "assert len(found_forbidden) == 0, f'Found forbidden exact vars: {found_forbidden}'\n"
            "\n"
            "# Check any *TOKEN*, *KEY*, *SECRET* pattern (case-insensitive)\n"
            "pattern = re.compile(r'(TOKEN|KEY|SECRET)', re.IGNORECASE)\n"
            "found_pattern = [k for k in env_names if pattern.search(k)]\n"
            "print('PATTERN_MATCH_FOUND:', found_pattern)\n"
            "assert len(found_pattern) == 0, f'Found sensitive pattern vars: {found_pattern}'\n"
            "print('ENV_PROBE_RESULT: PASSED')\n"
        )

        runner = LocalRunner(run_dir=run_dir, timeout_seconds=30)
        result = await runner.execute_script(probe_script)

        print("\n--- TEST 1 RUNNER STDOUT ---")
        print(result["stdout"])
        if result["stderr"]:
            print("--- TEST 1 RUNNER STDERR ---")
            print(result["stderr"])

        assert result["status"] in ("PASSED", "UNVERIFIED"), f"Runner execution failed: {result}"
        assert result["exit_code"] == 0, f"Exit code non-zero: {result['exit_code']}"
        assert "ENV_PROBE_RESULT: PASSED" in result["stdout"]
        assert "FORBIDDEN_EXACT_FOUND: []" in result["stdout"]
        assert "PATTERN_MATCH_FOUND: []" in result["stdout"]


@pytest.mark.asyncio
async def test_2_default_deny_filesystem_probe():
    """
    Deliverable 2: Switch to default-deny for filesystem: hide $HOME via --whitelist
    plus --nonewprivs, --caps.drop=all, --seccomp, --noroot, --private-tmp, and --quiet.
    Probe lists visible contents of $HOME (names only) and tries:
    ~/.gemini, ~/.config, ~/.bash_history, other projects' .env, /run/user/*/ sockets (OK/DENIED only).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        probe_script = run_dir / "fs_probe.py"
        probe_script.write_text(
            "import os, glob\n"
            "from pathlib import Path\n"
            "\n"
            "print('=== HOME DIRECTORY VISIBLE CONTENTS (NAMES ONLY) ===')\n"
            "home_path = os.environ.get('HOME', '')\n"
            "print('HOME_ENV_VALUE:', home_path)\n"
            "if os.path.exists(home_path):\n"
            "    for item in sorted(os.listdir(home_path)):\n"
            "        print(f'HOME_ENTRY: {item}')\n"
            "\n"
            "print('=== SENSITIVE PATH PROBE (OK/DENIED ONLY) ===')\n"
            "test_targets = [\n"
            "    '~/.gemini',\n"
            "    '~/.config',\n"
            "    '~/.bash_history',\n"
            "    '/home/kizamladjanijebac/.gemini',\n"
            "    '/home/kizamladjanijebac/.config',\n"
            "    '/home/kizamladjanijebac/.bash_history',\n"
            "    '/home/kizamladjanijebac/.env',\n"
            "    '/home/kizamladjanijebac/Desktop/discord-openclaw/.env',\n"
            "    '/home/kizamladjanijebac/Desktop/openclaw/.env',\n"
            "    '/home/kizamladjanijebac/.kaggle/kaggle.json',\n"
            "    '/home/kizamladjanijebac/.nlm/env',\n"
            "    '/run/user/1001/bus',\n"
            "    '/run/user/1001/keyring',\n"
            "    '/run/user/1001/pulse',\n"
            "]\n"
            "# Also check any /run/user socket glob\n"
            "run_user_matches = glob.glob('/run/user/*/*')\n"
            "print('RUN_USER_MATCHES_COUNT:', len(run_user_matches))\n"
            "assert len(run_user_matches) == 0, f'Leaked /run/user sockets: {run_user_matches}'\n"
            "\n"
            "denied_count = 0\n"
            "for target in test_targets:\n"
            "    expanded = os.path.expanduser(target)\n"
            "    try:\n"
            "        exists = os.path.exists(expanded)\n"
            "        if exists:\n"
            "            status = 'OK'\n"
            "        else:\n"
            "            status = 'DENIED'\n"
            "    except PermissionError:\n"
            "        status = 'DENIED'\n"
            "    except Exception:\n"
            "        status = 'DENIED'\n"
            "    print(f'{target} -> {status}')\n"
            "    if status == 'DENIED':\n"
            "        denied_count += 1\n"
            "\n"
            "assert denied_count == len(test_targets), f'Expected all {len(test_targets)} to be DENIED, but got {denied_count}'\n"
            "print('FS_PROBE_RESULT: ALL_SENSITIVE_PATHS_DENIED')\n"
        )

        runner = LocalRunner(run_dir=run_dir, timeout_seconds=30)
        result = await runner.execute_script(probe_script)

        print("\n--- TEST 2 RUNNER STDOUT ---")
        print(result["stdout"])
        if result["stderr"]:
            print("--- TEST 2 RUNNER STDERR ---")
            print(result["stderr"])

        assert result["status"] in ("PASSED", "UNVERIFIED"), f"Runner execution failed: {result}"
        assert result["exit_code"] == 0, f"Exit code non-zero: {result['exit_code']}"
        assert "FS_PROBE_RESULT: ALL_SENSITIVE_PATHS_DENIED" in result["stdout"]


@pytest.mark.asyncio
async def test_3_functional_pipeline_in_sandbox():
    """
    Deliverable 3: Re-run earlier functional test through real runner:
      - train.csv readable
      - sklearn, lightgbm, xgboost, catboost import
      - write only in the run folder (read-only in data folder, writes blocked outside)
      - secrets DENIED
      - network fails (--net=none)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        func_script = run_dir / "functional_test.py"
        func_script.write_text(
            "import os, sys, socket\n"
            "from pathlib import Path\n"
            "import pandas as pd\n"
            "\n"
            "# 1. Read train.csv\n"
            "data_path = Path('/home/kizamladjanijebac/Desktop/discord-openclaw/artifacts/kaggle/s6e11/data/train.csv')\n"
            "assert data_path.is_file(), f'train.csv not found at {data_path}'\n"
            "df = pd.read_csv(data_path, nrows=50)\n"
            "assert len(df) == 50, f'Expected 50 rows, got {len(df)}'\n"
            "print(f'TRAIN_CSV: OK (rows={len(df)}, cols={len(df.columns)})')\n"
            "\n"
            "# 2. Import ML libraries\n"
            "import sklearn\n"
            "import lightgbm\n"
            "import xgboost\n"
            "import catboost\n"
            "print('ML_IMPORTS: OK (sklearn, lightgbm, xgboost, catboost)')\n"
            "\n"
            "# 3. Write inside run folder -> OK\n"
            "run_out = Path('model_output.txt')\n"
            "run_out.write_text('Model training checkpoint complete')\n"
            "assert run_out.is_file() and run_out.read_text() == 'Model training checkpoint complete'\n"
            "print('RUN_DIR_WRITE: OK')\n"
            "\n"
            "# 4. Write inside data folder -> DENIED (read-only filesystem)\n"
            "data_write_blocked = False\n"
            "try:\n"
            "    (data_path.parent / 'illegal_write.tmp').write_text('illegal')\n"
            "except (OSError, PermissionError):\n"
            "    data_write_blocked = True\n"
            "assert data_write_blocked, 'Write into data_dir must be DENIED'\n"
            "print('DATA_DIR_WRITE: DENIED')\n"
            "\n"
            "# 5. Secrets DENIED\n"
            "secrets_blocked = not os.path.exists('/home/kizamladjanijebac/Desktop/discord-openclaw/.env') and \\\n"
            "                  not os.path.exists('/home/kizamladjanijebac/.kaggle/kaggle.json')\n"
            "assert secrets_blocked, 'Secrets access must be DENIED'\n"
            "print('SECRETS_ACCESS: DENIED')\n"
            "\n"
            "# 6. Network fails\n"
            "network_blocked = False\n"
            "try:\n"
            "    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
            "    s.settimeout(1.0)\n"
            "    s.connect(('8.8.8.8', 53))\n"
            "except (OSError, socket.error):\n"
            "    network_blocked = True\n"
            "finally:\n"
            "    try: s.close()\n"
            "    except Exception: pass\n"
            "assert network_blocked, 'Network access must fail under --net=none'\n"
            "print('NETWORK_ACCESS: FAILS (DENIED)')\n"
            "\n"
            "# Emit dummy CV score for runner status verification\n"
            "print('CV_ROC_AUC: 0.95250')\n"
            "print('FUNCTIONAL_TEST_RESULT: PASSED')\n"
        )

        runner = LocalRunner(run_dir=run_dir, timeout_seconds=60)
        result = await runner.execute_script(func_script)

        print("\n--- TEST 3 RUNNER STDOUT ---")
        print(result["stdout"])
        if result["stderr"]:
            print("--- TEST 3 RUNNER STDERR ---")
            print(result["stderr"])

        assert result["status"] == "PASSED", f"Expected PASSED status, got {result['status']} (error: {result['error']})"
        assert result["cv_score"] == 0.95250
        assert "TRAIN_CSV: OK" in result["stdout"]
        assert "ML_IMPORTS: OK" in result["stdout"]
        assert "RUN_DIR_WRITE: OK" in result["stdout"]
        assert "DATA_DIR_WRITE: DENIED" in result["stdout"]
        assert "SECRETS_ACCESS: DENIED" in result["stdout"]
        assert "NETWORK_ACCESS: FAILS (DENIED)" in result["stdout"]


@pytest.mark.asyncio
async def test_4_fail_closed_on_invalid_firejail_path():
    """
    Deliverable 4: Fail-closed test: wrong firejail path => runner refuses, no unsandboxed fallback.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        canary_file = run_dir / "unsandboxed_leak.txt"
        dangerous_script = run_dir / "exploit.py"
        dangerous_script.write_text(
            f"from pathlib import Path\n"
            f"Path('{canary_file}').write_text('EXECUTED_UNSANDBOXED')\n"
        )

        # Deliberately invalid Firejail path
        invalid_path = "/usr/local/bin/nonexistent_firejail_binary_12345"
        runner = LocalRunner(run_dir=run_dir, firejail_path=invalid_path, timeout_seconds=10)

        result = await runner.execute_script(dangerous_script)

        print("\n--- TEST 4 RUNNER RESULT ---")
        print("Status:", result["status"])
        print("Exit code:", result["exit_code"])
        print("Error:", result["error"])

        # 1. Runner must return FAILED
        assert result["status"] == "FAILED"
        assert result["exit_code"] == 127
        assert "SecurityError" in result["error"]
        assert "fail-closed" in result["error"].lower()

        # 2. Canary file must NOT exist (strictly no fallback execution)
        assert not canary_file.exists(), "CRITICAL FAULT: Script executed unsandboxed when Firejail was missing!"
        print("FAIL_CLOSED_VERIFIED: No unsandboxed fallback executed.")
