# Testing Strategy

## Runner & Verification Tooling

Testing in `discord-openclaw` relies on an automated verification pipeline executing under Python 3.12 (`./venv/bin/python3`).

| Command | Purpose |
| ------- | ------- |
| `./venv/bin/python3 -m py_compile *.py` | Fast bytecode compilation and syntax validation across all modules |
| `./venv/bin/python3 .githooks/verify_sanity.py` | AST semantic integrity, import contracts, and notebook ID consistency |
| `./venv/bin/python3 .githooks/verify_sanity.py --strict` | Strict verification gate (promotes warnings to blocking errors) |
| `./venv/bin/python3 scratch/test_pipeline.py` | Full E2E test: JudgeGuard + BrainCore NLM + Persona Turn Execution |
| `./venv/bin/python3 agent_sanity_audit.py` | Deep 5-pillar audit: anti-stub, AST, runtime imports, tests, and Babac AI gate |

## Test Structure

```text
scratch/
└── test_pipeline.py           # 5-stage live integration and E2E verification
.githooks/
├── verify_sanity.py           # Deep semantic, AST, UUID, and schema consistency checker
└── pre-commit                 # Automated hook running compilation, syntax, and sanity
agent_sanity_audit.py          # Standalone 5-pillar verification script
```

## E2E Pipeline Stages (`scratch/test_pipeline.py`)

1. **JudgeGuard Verification**: Asserts safety gate passes valid action descriptions and correctly evaluates Quorum Verdict.
2. **BrainCore NLM Query**: Verifies live execution of `nlm notebook query` against the default notebook without mocks.
3. **Debate Engine Personas Configuration**: Validates persona UUIDs, titles, and prompts across the 5 personas.
4. **Moderator (Švaba) Turn Generation**: Generates live grounded turn and verifies non-empty response and citation parsing.
5. **Architect (Ekser) Turn Generation**: Passes context turn to second persona and verifies conversational grounding.

## Verification Cycle

After modifying cognitive modules, bot handlers, or database logic:

```bash
./venv/bin/python3 -m py_compile *.py
./venv/bin/python3 .githooks/verify_sanity.py
./venv/bin/python3 scratch/test_pipeline.py
./venv/bin/python3 judge_guard.py "Verification of changes"
```

## Rules for New Code & Tests

- **Zero Mock Policy**: Do not introduce fake or simulated responses for NotebookLM in production pathways. Real API responses via `nlm notebook query` are the source of truth.
- **Anti-Stub Gate**: Never submit functions with placeholder `pass`, `TODO`, or unpopulated return values. `agent_sanity_audit.py` will reject the commit.
- **Async Safety**: Every async function interacting with Discord or NLM subprocesses must handle timeouts and cancellations cleanly.
