# SDD Workflow & Master Orchestration

This repository operates under the immutable governance of `~/.gemini/MASTER_ORCHESTRATION.md` and `judge_guard.py`.

## Preflight Defaults

- **Pace**: Interactive (validate every plan step with the user).
- **Delivery Strategy**: Atomic commits with verifiable pre-action checkpoints.
- **Max Open Tasks**: 5 concurrent tasks (`MAX_TASKS_PER_TRACK = 5`).
- **Freshness Window**: 300 seconds (5 minutes) on `WORK_LOG.md`.

## Immutable Orchestration Laws

1. **User Sovereignty**: The user is the ultimate authority. Actions require explicit consent.
2. **No Destructive Operations Without Verification**: Any deletion or critical modification must pass JudgeGuard quorum check.
3. **Research First**: Validate assumptions against source code and Google NotebookLM before changing implementations.
4. **Transparency**: Stream thoughts and actions; record decisions in `WORK_LOG.md`.
5. **Modularity**: Maintain clean separation across Discord gateway, cognitive brain, debate engine, and safety gates.
6. **Work Log Mandatory**: `WORK_LOG.md` must be updated BEFORE and AFTER every major action.
7. **Security Enforcement**: Strictly prohibited commands: `sudo`, `rm -rf /`, `rm -rf /*`, `chmod -R 777`.
8. **Quality Standards**: Anti-stub, anti-mock, full AST and dynamic contract verification required.

## Mandatory Pre-Action Verification Workflow

BEFORE executing any of:
- Starting a new phase or feature track
- Database or schema changes
- Modifications to core safety logic or bot commands
- Major git commits or deployments

You MUST execute the 7-step cycle:

```bash
# Step 1: Record start in log
echo "🟡 Starting [ACTION_NAME]" >> WORK_LOG.md

# Step 2: Run JudgeGuard Pre-Check
./venv/bin/python3 judge_guard.py "Start [ACTION_NAME]"

# Step 3: Evaluate Verdict
# EXIT 0 (PASSED)  -> Proceed
# EXIT 1 (BLOCKED) -> STOP immediately, address failure, return to Step 1

# Step 4: Execute the action in codebase

# Step 5: Record completion in log
echo "✅ Completed [ACTION_NAME]" >> WORK_LOG.md

# Step 6: Post-Check verification
./venv/bin/python3 judge_guard.py "Verify [ACTION_NAME] Complete"

# Step 7: Checkpoint commit (only if user instructed)
git add . && git commit -m "checkpoint: [ACTION_NAME]"
```

## Atomic Task Chunking

- No agent may open more than 5 concurrent `🟡 Starting` tasks without completing (`✅ Completed`) or abandoning (`⚠️ Abandoned`) previous tasks.
- If stale open tasks exist from crashed sessions, explicitly mark them `⚠️ Abandoned` before initiating new work.

## Post-Apply Verification

After completing changes, always run the full verification pipeline:

```bash
./venv/bin/python3 -m py_compile *.py
./venv/bin/python3 .githooks/verify_sanity.py
./venv/bin/python3 scratch/test_pipeline.py
```
