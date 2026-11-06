# Kaggle Competition Integration in Discord Bot (`/kaggle`) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a dedicated, admin-only Discord command (`/kaggle start <competition>`) separate from `/debate`, which pulls real Kaggle telemetry, runs a grounded NotebookLM agent debate producing an actionable pipeline plan, validates performance via remote Kaggle compute (or labels as `[EXPERIMENT]`), and provides interactive Discord buttons to safely submit via Kaggle CLI only on user confirmation.

**Architecture:**
1. **`KaggleService` (`src/services/kaggle_service.py`)** [COMPLETED & VERIFIED]: Executes parameterized `kaggle` CLI subprocesses (`asyncio.create_subprocess_exec`, no shell injection). Fetches live submissions via `--csv` and limits via `--json`. Validates competition slug with `^[a-zA-Z0-9_-]+$`. Computes `best_score` (0.604), `latest_score` (0.348), and `remaining_today` (5) dynamically without hardcoding.
2. **`A2ToolsRuntime` (`a2tools_runtime.py`)** [COMPLETED & VERIFIED]: Exposes `get_kaggle_context(competition)` to agent runtimes alongside `query_notebooklm`.
3. **Admin-Only Slash Command (`src/controllers/kaggle_controller.py` & hook in `discord_bot.py`)** [APPROVED - Task 3]:
   - Dedicated module `src/controllers/kaggle_controller.py` with minimal hook in `discord_bot.py`.
   - Access control strictly enforced from `unified_config.admin_user_id` (fail-closed if unset or non-admin, no hardcoded fallback).
   - Admin gate checked on command invocation AND inside EVERY interaction callback (all buttons, select menus, modals).
   - Starts debate workflow only; does not execute code or submit anything.
4. **Grounded Kaggle Debate Engine (`src/services/kaggle_debate_service.py`)** [REVISED - Task 4]:
   - Filters NotebookLM queries using native `--source-ids` flag in `nlm notebook query` to prevent cross-competition contamination.
   - 2-Round minimal debate protocol (Round 1: Opening positions; Round 2: Direct cross-examination answering specific points).
   - Produces a structured PLAN + standalone code file.
   - Anchor-CV comparison dropped because 0.604 kernel has no CV code/logs. Validation proves the kernel runs, completes, and outputs a valid `submission.parquet`. Anything not proven on LB is labeled `[EKSPERIMENT: <hipoteza>]`.
5. **Kaggle Compute Execution & Safe Submission Action Row (`src/views/kaggle_action_view.py`)** [REVISED - Task 5]:
   - Runs validation remotely on Kaggle compute via `kaggle kernels push/status/output`.
   - Generates `kernel-metadata.json` from a fixed template (internet strictly off, GPU from allowlist: `NvidiaTeslaT4` / `NvidiaTeslaP100`; agents never write it).
   - Pre-push button gate displays live quota (`kaggle quota` remaining GPU hours). GPU cost shown only from measured difference (`remaining_before - remaining_after`), otherwise marked `unknown`.
   - Stop/Pause notice: Kaggle CLI cannot abort remote running kernels; pressing Stop cancels local monitoring while notifying that the remote kernel continues running on Kaggle.
   - Confirm button displays kernel slug, exact version (`-v VERSION`), SHA-256 of pushed source, and dynamic remaining submissions.

**Tech Stack:** Python 3.12, asyncio, Pydantic, Kaggle CLI (v2.2.4+), Google ADK 2.0, Discord.py.

---

### Task 1: Kaggle Telemetry Service (`src/services/kaggle_service.py`) [COMPLETED & PASSED]
- **Status**: PASSED (5/5 unit & integration tests passed).
- **Features**: Parameterized subprocess execution, regex slug validation, live CLI parsing against independent reference, fixture parsing on real CSV, explicit error on missing comp.

### Task 2: Expose Kaggle Grounding in `a2tools_runtime.py` [COMPLETED & PASSED]
- **Status**: PASSED (3/3 integration tests passed).
- **Features**: `tools_runtime.get_kaggle_context(comp)` returns verified metadata and formatted markdown.

---

### Task 3: Admin-Only Slash Command Module (`src/controllers/kaggle_controller.py`) [APPROVED FOR IMPLEMENTATION]

**Files:**
- Create: `src/controllers/kaggle_controller.py`
- Modify: `discord_bot.py` (registers `/kaggle` command group hook; leaves `/debate` and `!debate` untouched)
- Create: `tests/test_kaggle_command_auth.py`

**Design & Security Boundaries:**
1. **Access Control**:
   - `admin_id = unified_config.admin_user_id`
   - If `admin_id is None` or `str(interaction.user.id) != str(admin_id)`:
     - Return ephemeral rejection: `"⛔ Pristup odbijen: Niste autorizovani admin za /kaggle komande."`
     - Fail closed: zero execution, zero hardcoded fallback IDs.
   - **Crucial**: The exact same check runs in EVERY interaction callback (all buttons, select menus, and modals).
2. **Explicit Parameter**:
   - Signature: `/kaggle start <competition: str>`
   - Validated immediately with `kaggle_service.validate_slug(competition)`.
   - Autocomplete/choices supported for known active competitions (`name-that-llm`, `gemma-4-developer-agent`).
   - Zero keyword guessing or inferred parameters.
3. **Scope Enforcement**:
   - The command ONLY initiates the grounded debate workflow and sends the initial Discord embed.
   - It NEVER executes any generated code and NEVER calls `kaggle submit`.

---

### Task 4: Grounded Competition Debate & Real Validation Gate [REVISED]

**Files:**
- Create: `src/services/kaggle_debate_service.py`
- Create: `tests/test_kaggle_debate_protocol.py`

**Grounded Debate Design:**
1. **Native Source Filtering (`--source-ids`)**:
   - Notebook `3bd81caf-9396-4593-ad18-4a98dc1a2115` has 14 sources.
   - Verified via `nlm notebook query --help`: CLI natively supports `--source-ids <comma_separated_ids>`.
   - Moderator fetches source list via `nlm list sources <notebook_id> --json`, identifies source IDs matching the competition, and passes `--source-ids <id1,id2,...>`.
   - Query response is strictly bounded to the specified sources.
2. **Minimal 2-Round Protocol**:
   - **Round 1 (Opening)**:
     - *Strategist*: Metric decomposition (Balanced Accuracy over 18 classes) & runtime budgets.
     - *Engineer*: Pipeline architecture, token/stylegram features, and model ensemble.
     - *Skeptic*: Leakage vectors (prompt overlap, author clustering) and offline constraint checks.
   - **Round 2 (Cross-Examination)**:
     - Each agent must explicitly address points raised by the other two in Round 1.
   - **Deliverable**:
     - Discord summary with key decisions.
     - Full runnable code script saved to fixed path `/home/kizamladjanijebac/Desktop/discord-openclaw/artifacts/kaggle/<comp>/pipeline.py` and attached to Discord message.
     - Explicit list of disagreements and the deciding rationale behind each choice.
3. **Empirical Validation Gate (No Fictitious Anchor CV)**:
   - Verification confirmed: `ntl-0604-dual-lora-gaussian-hungarian` has zero CV code or logs.
   - Anchor-CV comparison is dropped.
   - Remote Kaggle run validates that:
     1. Kernel status becomes `KernelWorkerStatus.COMPLETE`.
     2. Output contains valid `submission.parquet` (columns `id`, `model`, 18 valid labels, no nulls).
     3. Informational CV is reported if the script computes one; otherwise marked `CV: Informational only / Uncomputed`.
   - Any approach not empirically proven on the Public Leaderboard is labeled **`[EKSPERIMENT: <hipoteza>]`**.

---

### Task 5: Remote Kaggle Compute Execution & Safe Submit Action Row [REVISED]

**Files:**
- Create: `src/views/kaggle_action_view.py`
- Create: `tests/test_kaggle_view.py`

**Kaggle Compute & Submission Gates:**
1. **Fixed Template `kernel-metadata.json`**:
   - Generated by backend from strict schema template:
     - `enable_internet: false`
     - `enable_gpu: true`
     - `machine_shape`: allowlisted (`NvidiaTeslaT4` or `NvidiaTeslaP100`)
     - `competition_sources: [competition]`
     - Attached datasets and models strictly taken from verified competition assets (e.g. Qwen, UltraBERT, DeBERTa-v3).
     - Agents NEVER write or modify metadata.
2. **Quota Gate & Remote Execution**:
   - Button `[🚀 Pokreni Validaciju na Kaggle]` runs `kaggle quota` and displays remaining GPU hours before user confirmation.
   - Pushes kernel via `kaggle kernels push -p <fixed_dir>`.
   - Monitors status via `kaggle kernels status <kernel_slug>`.
   - GPU usage reported as measured difference (`remaining_before - remaining_after`), or `unknown` if unmeasured.
   - **Stop/Pause Handling**: Kaggle CLI has no cancel command. Stop button cancels the local monitoring loop and explicitly informs the user that the remote kernel continues running on Kaggle.
3. **Pinned Version Submission (`[✅ Confirm Submission]`)**:
   - Validates via `kaggle kernels status <kernel_slug>` that status is `KernelWorkerStatus.COMPLETE`.
   - Obtains latest kernel version `V` and checks output files (`kaggle kernels files`).
   - Displays:
     - Kernel slug and exact version: e.g. `kiza123123/<slug>/versions/<V>`
     - SHA-256 hash of the notebook source
     - Remaining daily submissions dynamically from `KaggleService`
   - Executes pinned command:
     `kaggle competitions submit -c <comp> -k <kernel_slug> -v <V> -f submission.parquet -m "openclaw-<comp>-<timestamp>-<tag>"`
   - Post-submit: runs `kaggle competitions submissions <comp> --csv` and prints the newly created row.
