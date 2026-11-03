# Git Workflow

## Approval & Execution Rules

- **NO commits** without the user validating the code first — always present the diff and summary.
- **NO branches** unless explicitly instructed by the user.
- **NO git push** unless specifically authorized.
- Before editing code: explain the plan (files to touch and why).
- After changes: run the verification cycle and display the results.

## Commit Convention

Conventional Commits standard:

```text
feat: <brief description>
fix: <brief description>
refactor: <brief description>
test: <brief description>
chore: <brief description>
docs: <brief description>
checkpoint: <brief description>
```

Rules:
- One commit per logical unit of work.
- Imperative mood, lowercase, no trailing period.
- **Strictly NO "Co-Authored-By" or AI attribution headers.**
- English language for all commit messages.

### Concrete Examples from Repository History

- `feat(hooks): add pre-commit, commit-msg, post-commit hooks and deep sanity verifier`
- `fix(sync): synchronize strategist persona notebook ID and add discord bot startup guard`
- `checkpoint: complete goal - Vratiće se rode personas, short outputs and NotebookLM grounding`
- `checkpoint: fix NLM query syntax, setup verified personas notebooks, clean debate state`

## Pre-Commit Verification Hook

The repository utilizes an automated pre-commit hook in `.githooks/pre-commit`. Before committing, the hook verifies:

1. **Python compilation**: `py_compile` succeeds for all core modules.
2. **NLM syntax**: Verifies `nlm notebook query` is used (rejects old deprecated `nlm query notebook` syntax).
3. **Notebook ID consistency**: All persona notebook IDs match across `openclaw.json`, `debate_engine.py`, and `MEMORY.md`.
4. **JSON syntax**: Validates `openclaw.json` and `debate_state.json`.
5. **Secret leak scan**: Scans staged files for raw tokens or API keys.
6. **JudgeGuard gate**: Evaluates Quorum Verdict before commit is accepted.

To manually execute the pre-commit checks:

```bash
./venv/bin/python3 .githooks/verify_sanity.py
```
