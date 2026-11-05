# Discord OpenClaw Modular Backend — Read-Only Audit Report

**Date:** 2026-11-05 23:05 CET  
**Auditor:** Verification Agent (Antigravity)  
**Execution Mode:** Read-Only Audit (Zero Modifications, Zero Git Commits)

---

## 1. Target Metadata & Location (Step 0)

| Attribute | Verified Value | Evidence |
| :--- | :--- | :--- |
| **Workspace Path** | `/home/kizamladjanijebac/Desktop/discord-openclaw` | `pwd` |
| **Git Branch** | `master` | `git branch --show-current` |
| **Last Commit Hash** | `7279c7563129bb6cda13615621952181537abc41` | `git rev-parse HEAD` |
| **Last Commit Message** | `checkpoint: fix dynamic youtube discovery, topic chapter synchronization, domain grounding, clean typography and quiz certificate gate` | `git log -1 --pretty=%B` |
| **Commit Author / Date** | Zoran Stojanovic <kiza101288@gmail.com> • Thu Nov 5 12:11:14 2026 +0100 | `git log -1` |

---

## 2. Section-by-Section Audit

### Section 1: Architecture (Law 5)
**Verdict: FAIL (Partial Implementation / Leftover Monolith Active)**

#### Evidence & Analysis:
1. **Layered Structure in `src/`:**
   The refactored modular structure exists under `src/`:
   - **Routes:** `src/routes/slash_routes.py` (82 lines)
   - **Controllers:** `src/controllers/base_controller.py` (116 lines), `nlm_controller.py` (95 lines), `debate_controller.py` (74 lines), `system_controller.py` (69 lines)
   - **Services:** `src/services/nlm_service.py` (150 lines), `judge_guard_service.py` (72 lines), `orchestration_service.py` (52 lines)
   - **Repositories:** `src/repositories/rag_repository.py` (122 lines), `state_repository.py` (85 lines)
   - **Config & Validators:** `src/config/unified_config.py` (160 lines), `src/validators/` (102 lines total)
   - **Entrypoint:** `src/main.py` (69 lines)

2. **Import Direction & Layer Boundaries:**
   - **Routes:** Only imports from `src.controllers` (`slash_routes.py:12-14`). Zero imports from services or repositories.
   - **Controllers:** Import from `src.controllers.base_controller`, `src.services`, `src.validators`, and `src.config`. No controller touches repositories directly.
   - **Services:** Import from `src.repositories`, `src.validators`, `src.config`, and `src.instrument`.
   - **Repositories:** Import only standard library (`sqlite3`, `json`, `pathlib`) and `src.config.unified_config`.
   - **Strict Hierarchical Rule:** No upward, reverse, or cyclic imports exist inside `src/`.

3. **Leftover Monolithic Files (Critical Finding):**
   - **The 1,825-line monolithic file `discord_bot.py` is STILL PRESENT in the project root** (`wc -l discord_bot.py` -> `1825`).
   - The production background service (`systemd --user discord-openclaw.service`) and the launch script (`start_discord_bot.sh`) **both execute `discord_bot.py`**, NOT `src/main.py`.
   - Additional monolithic modules remain in root:
     - `debate_engine.py`: 966 lines
     - `brain_core.py`: 434 lines
     - `adk_orchestration.py`: 357 lines
     - `agent_sanity_audit.py`: 314 lines
     - `a2tools_runtime.py`: 231 lines
     - `judge_guard.py`: 196 lines
     - `gemini_client.py`: 181 lines
   - `src/services/orchestration_service.py:41` still relies on an external lazy import from the root monolith:
     `from adk_orchestration import adk_manager`.
   - `src/routes/slash_routes.py` only defines **6 slash commands** (`/ask`, `/notebooks`, `/note`, `/addurl`, `/debate start`, `/status`, `/sh`), whereas `discord_bot.py` contains **13 slash commands** plus text prefix commands (`/use`, `/sources`, `/newchat`, `/current`, `/help`, `/execute`, `/debate pause/resume/next/stop/status/personas`).

---

### Section 2: Configuration
**Verdict: FAIL (Hardcoded Defaults & Root Scripts Bypass)**

#### Evidence & Analysis:
1. **Unified Pydantic Single Source of Truth:**
   - `src/config/unified_config.py` defines `UnifiedConfig` containing `DiscordConfig`, `NLMConfig`, `AgyConfig`, `DatabaseConfig`, `SentryObservabilityConfig`, and `JudgeGuardConfig`.
   - Inside `src/`: Zero calls to `os.getenv` or `os.environ` exist in any controller, route, service, or repository (only `nlm_service.py:30` copies `os.environ` for subprocess inheritance).

2. **Bypasses in Root Codebase:**
   The files running in production bypass `unified_config.py` and read directly from environment:
   - `discord_bot.py:38`: `TOKEN = os.getenv("DISCORD_BOT_TOKEN")`
   - `discord_bot.py:39`: `DEFAULT_NOTEBOOK_ID = os.getenv("NLM_NOTEBOOK_ID", ...)`
   - `discord_bot.py:273`: `_JUDGE_SECRET = os.getenv("JUDGE_HMAC_SECRET", "openclaw-dev-secret")`
   - `brain_core.py:99`: `os.getenv("NLM_NOTEBOOK_ID", ...)`
   - `judge_guard.py:32, 179`: `os.getenv("JUDGE_HMAC_SECRET", ...)`
   - `agy_client.py:21`: `os.getenv("AGY_BIN", ...)`
   - `gemini_client.py:20, 24, 108, 109, 114`: `os.getenv` for `GEMINI_CLI_BIN`, `GEMINI_MODEL`, `OLLAMA_API_BASE`, `OLLAMA_MODEL`, `OLLAMA_API_KEY`.

3. **Hardcoded Values in `src/config/unified_config.py`:**
   - `orchestration_notebook_id` (line 53): Hardcoded UUID `"3bd81caf-9396-4593-ad18-4a98dc1a2115"` without environment override.
   - `admin_user_id` (line 34): Fallback default `"1500206682192744569"`.
   - `accounts` (lines 68-73): Hardcoded list of 4 personal email addresses.
   - `secret` (line 138): Insecure fallback `"openclaw-dev-secret-change-me"`.

---

### Section 3: Observability
**Verdict: FAIL (Architecturally Structured, but Disabled & Dependency Missing at Runtime)**

#### Evidence & Analysis:
1. **BaseController Integration:**
   - `src/controllers/base_controller.py` provides `handle_error` (lines 73-116), which delegates to `src.instrument.capture_exception`.
   - All 3 modular controllers inherit from `BaseController`:
     - `src/controllers/nlm_controller.py:17`: `class NotebookLMController(BaseController)`
     - `src/controllers/debate_controller.py:17`: `class DebateController(BaseController)`
     - `src/controllers/system_controller.py:19`: `class SystemController(BaseController)`
   - `src/main.py:9` executes `import src.instrument` as its first import boundary.

2. **Sentry Configuration & Reality:**
   - In `src/instrument.py:24-35`, DSN is sourced dynamically via `config.observability.dsn` (`SENTRY_DSN` env var), not hardcoded.
   - **Failure 1 (Missing Dependency):** `sentry_sdk` is NOT installed in `venv` (`venv/bin/python3 -c "import sentry_sdk"` returns `ModuleNotFoundError: No module named 'sentry_sdk'`).
   - **Failure 2 (Missing Configuration):** Neither `SENTRY_DSN` nor `SENTRY_ENABLED` are present in `.env`.
   - `src/instrument.py:40-42` catches the missing module and falls back to standard Python `logging`.
   - Active running service `discord_bot.py` has no Sentry integration whatsoever.

---

### Section 4: Safety Gates
**Verdict: FAIL (Severe Bypass in Active Service)**

#### Evidence & Analysis:
1. **Implementation Locations:**
   - Modular layer: `src/validators/system_schemas.py` (`ShellCommandSchema`) and `src/services/judge_guard_service.py` (`JudgeGuardService`).
   - Standalone gate: `judge_guard.py` (`JudgeGuard`).

2. **Fail-Closed Verification:**
   - Both `judge_guard.py` and `src/services/judge_guard_service.py` fail closed:
     - If command matches blocked regex -> returns `BLOCKED` / `False`.
     - If `WORK_LOG.md` mtime is older than 300 seconds -> returns `BLOCKED` / `False`.
     - If `WORK_LOG.md` cannot be stat-checked -> returns `BLOCKED` / `False`.

3. **Operations Passing Through Safety Gates:**
   - In `src/controllers/system_controller.py:53-69`: `/sh` validates via `ShellCommandSchema` and calls `judge_service.verify_action`. (Note: `execute_command` only acknowledges authorization; it does not actually spawn a process).
   - In `discord_bot.py:1232-1234`: The `/execute` slash command evaluates `judge.verify(proposed_action)`.

4. **CRITICAL BYPASSES (Vulnerabilities):**
   - **Live Production Shell Bypass:** In `discord_bot.py:503-539` (`class ExecApprovalView`) and `discord_bot.py:1132-1139` (`/sh`), as well as `discord_bot.py:1755` (`!sh`):
     - Commands sent via `/sh` or `!sh` are presented to the user with an interactive "Approve" button.
     - When the user clicks "Approve", line 518 executes:
       `proc = await asyncio.create_subprocess_shell(self.command, cwd="/home/kizamladjanijebac/Desktop/openclaw")`
     - **This completely bypasses `judge_guard.py`, `JudgeGuardService`, and all blacklist pattern checks.**
     - In addition, the check `if interaction.user.id != self.user_id:` allows the user who invoked the command to self-approve the destructive action.
   - **Blacklist Discrepancy:** `judge_guard.py` blocks `eval\s*\(` and `base64\s+-d.*\|\s*sh`, but `src/validators/system_schemas.py` omitted both patterns from `_BLOCKED_COMMAND_PATTERNS`.

---

### Section 5: Tests
**Verdict: FAIL (Full Suite 28/30; Mocks Detected in BaseController Tests)**

#### Evidence & Analysis:
1. **Real Execution Results:**
   - **Claimed 25 Unit Tests (`test_base_controller.py`, `test_bfri_compliance.py`, `test_layered_services.py`, `test_unified_config.py`, `test_validators.py`):**
     - Command: `PYTHONPATH=. python3 -m pytest tests/test_base_controller.py tests/test_bfri_compliance.py tests/test_layered_services.py tests/test_unified_config.py tests/test_validators.py`
     - **Result:** `25 passed in 1.22s` (matches the 25/25 claim).
   - **Full Test Directory (`pytest tests`):**
     - Total Collected: **30 tests**.
     - **Result:** **28 passed, 2 failed in 2.12s**.
     - Failure 1: `tests/test_adk_pipeline.py::test_adk_imports` -> `ModuleNotFoundError: No module named 'google.adk'` (line 27).
     - Failure 2: `tests/test_adk_pipeline.py::test_notebooklm_live_query` -> `Failed: async def functions are not natively supported` (line 89, missing pytest-asyncio integration).

2. **Zero-Mocks Policy Audit:**
   - **Mocks Detected in `tests/test_base_controller.py`:**
     - Line 8: `from unittest.mock import AsyncMock, MagicMock`
     - Lines 35-37: `mock_interaction = MagicMock()`, `mock_interaction.response.is_done.return_value = True`, `mock_interaction.followup.send = AsyncMock()`
     - Lines 47-49: `mock_interaction = MagicMock()`, `mock_interaction.response.is_done.return_value = True`, `mock_interaction.followup.send = AsyncMock()`
     - Lines 44 & 57: `mock_interaction.followup.send.assert_awaited_once()`
   - **Test Claim Contradiction:**
     - `tests/test_bfri_compliance.py:35` explicitly scores `testability = 5` citing "mockable services".
     - This conflicts with the strict project mandate: *"Zero mocks / zero simulations: report only real results from real execution."*

---

### Section 6: Runtime
**Verdict: FAIL (Running Monolith, Not Modular Backend; Startup Exceptions)**

#### Evidence & Analysis:
1. **Service Inspection:**
   - Service Unit: `/home/kizamladjanijebac/.config/systemd/user/discord-openclaw.service`
   - Command: `systemctl --user status discord-openclaw.service`
   - Status: `active (running)` since Thu 2026-11-05 20:52:10 CET (PID 4004, Memory ~92.2 MB).

2. **Binary & Script Being Executed:**
   - Unit definition:
     `ExecStart=/home/kizamladjanijebac/Desktop/discord-openclaw/venv/bin/python discord_bot.py`
   - **The active service executes the un-refactored monolithic `discord_bot.py`, NOT `src/main.py`.**
   - The modular architecture in `src/` is completely dormant in production.

3. **Journal Log Excerpts (`journalctl --user -u discord-openclaw.service --no-pager -n 50`):**
   - Startup Warnings:
     - `WARNING: PyNaCl is not installed, voice will NOT be supported`
     - `WARNING: davey is not installed, voice will NOT be supported`
   - Startup Errors:
     - `Nov 05 20:54:59 kizabgd python[4004]: 2026-11-05 20:54:59,747 [JudgeGuard] ERROR: Izuzetak u list_notebooks:`
     - `Nov 05 20:54:59 kizabgd python[4004]: 2026-11-05 20:54:59,747 [JudgeGuard] INFO: Keširano 0 NotebookLM svezaka.`
   - Operations:
     - Heartbeat running on 30-minute intervals (`💓 HEARTBEAT aktiviran`).
     - Gateway connected as `PokerOrchestrator#7220`.

---

### Section 7: Repo Hygiene
**Verdict: FAIL (Tracked Logs & SQLite Databases in Git)**

#### Evidence & Analysis:
1. **Git Working Tree Status:**
   - Uncommitted modifications in `WORK_LOG.md` and `discord_bot.log.bak`.

2. **Tracked Files Violations:**
   - `discord_bot.log.bak` (502,906 bytes, ~6,700 lines of rotating logs) is tracked in git (`git ls-files discord_bot.log.bak`).
   - `antigravity_rag.db` (40,960 bytes binary SQLite database) is tracked in git (`git ls-files antigravity_rag.db`).
   - `.gitignore` ignores `*.log` and `venv/`, but omits `*.log.bak`, `*.db`, `*.sqlite`.

3. **Secrets Audit:**
   - **Plaintext Secret Leak Scan:** PASS (Zero raw tokens, private keys, or Discord bot tokens committed in git tracking or commit history).
   - `openclaw.json` correctly uses reference pointer `"SecretRef:env:DISCORD_BOT_TOKEN"`.
   - `.env` contains live credentials but is untracked and ignored by `.gitignore`.
   - **Minor issue:** Personal developer email addresses are hardcoded in `src/config/unified_config.py:68-73` and `test_adk_pipeline.py:38-41`.

---

## 3. Discrepancies Between Claims and Actual State

| Claim | Actual State | Severity |
| :--- | :--- | :--- |
| **"Monolithic 1,825-line Discord agent refactored into layered modules"** | Modular files exist in `src/`, but `discord_bot.py` (1,825 lines) remains untouched in root and continues to be the active entrypoint executed by systemd and `start_discord_bot.sh`. | **HIGH** |
| **"Zero raw os.getenv; unified_config is single source of truth"** | True only inside `src/`. Root files (`discord_bot.py`, `judge_guard.py`, `brain_core.py`, `gemini_client.py`, `agy_client.py`) have over 10 raw `os.getenv` calls. | **MEDIUM** |
| **"Sentry observability active via BaseController"** | Code structure exists, but `sentry_sdk` is not installed in `venv`, `SENTRY_DSN` is not in `.env`, and production monolith has no Sentry calls. | **MEDIUM** |
| **"Destructive token blacklist gates protect operations"** | In `discord_bot.py`, `/sh` and `!sh` bypass JudgeGuard and execute arbitrary shell commands via `ExecApprovalView` without blacklist checks. | **CRITICAL** |
| **"25/25 tests passing in ~1.5s"** | 25 backend tests pass in 1.22s, but the full suite has 30 tests (2 failing in `test_adk_pipeline.py`). Furthermore, `test_base_controller.py` uses `unittest.mock.MagicMock` and `AsyncMock`. | **MEDIUM** |
| **"Zero mocks / zero simulations"** | `tests/test_base_controller.py` uses `MagicMock` and `AsyncMock` to simulate Discord interaction responses and followups. | **LOW / AUDIT POLICY** |
| **"Clean repository hygiene"** | A 500 KB log file (`discord_bot.log.bak`) and a binary database (`antigravity_rag.db`) are actively tracked in git. | **LOW** |

---

## 4. Ordered List of Recommended Fixes (Do NOT Apply Automatically)

1. **[CRITICAL SECURITY] Fix `/sh` Shell Gate in `discord_bot.py` or Migrate Service to `src/main.py`:**
   - Replace `ExecApprovalView.approve` in `discord_bot.py` with mandatory `judge_guard.py` verification and blacklist checks before spawning any subprocess.
   - Restrict execution approval to `ADMIN_DISCORD_USER_ID` rather than allowing the command initiator to self-approve.
   - Synchronize blacklist patterns so `eval` and `base64 | sh` are present in `src/validators/system_schemas.py`.

2. **[HIGH ARCHITECTURE] Complete the Migration to `src/main.py`:**
   - Migrate remaining slash commands (`/use`, `/sources`, `/newchat`, `/current`, `/help`, `/execute`, debate subcommands) into `src/routes/slash_routes.py` and respective controllers.
   - Update `~/.config/systemd/user/discord-openclaw.service` and `start_discord_bot.sh` to execute `src/main.py` instead of `discord_bot.py`.
   - Once verified, decommission or archive the monolithic `discord_bot.py`.

3. **[HIGH OBSERVABILITY] Install and Configure Sentry SDK:**
   - Install `sentry-sdk` in `venv/`: `venv/bin/pip install sentry-sdk`.
   - Add `SENTRY_DSN` and `SENTRY_ENABLED=true` to `.env`.

4. **[MEDIUM TESTS] Resolve Failing Tests and Remove Mocks:**
   - Fix `tests/test_adk_pipeline.py`: either install the required package or mark optional integration suites appropriately; add `pytest-asyncio` for async tests.
   - Replace `MagicMock`/`AsyncMock` in `tests/test_base_controller.py` with lightweight protocol test doubles or dummy classes to adhere strictly to the zero-mocks rule.

5. **[MEDIUM REPO HYGIENE] Untrack Logs & Databases:**
   - Remove tracked log backup: `git rm --cached discord_bot.log.bak`.
   - Remove tracked SQLite database: `git rm --cached antigravity_rag.db`.
   - Update `.gitignore` to include `*.log.bak`, `*.db`, `*.sqlite`.

6. **[LOW CONFIGURATION] Externalize Hardcoded Configs:**
   - Move `orchestration_notebook_id` and personal emails in `src/config/unified_config.py` to environment variables or `openclaw.json`.
