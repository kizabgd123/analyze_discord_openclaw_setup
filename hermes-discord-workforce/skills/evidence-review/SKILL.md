---
name: evidence-review
description: Independently verify a completed Hermes Kanban task against acceptance criteria, tests, source evidence, and output artifacts. Use for review or verification tasks.
---

# Evidence Review

## Mission

Determine whether the assigned deliverable meets its explicit acceptance criteria. This is verification, not a debate or a general redesign exercise.

## Review procedure

1. Read the original task, acceptance criteria, parent task summaries, worker handoff and attached evidence.
2. Inspect the actual changed files/artifacts or open the cited primary sources. Do not rely only on the worker's self-report.
3. Re-run safe, relevant checks when practical. Record exact commands and observed outcomes.
4. Check that claims are supported by the evidence and that no important failure or limitation is hidden.
5. Check for scope violations, unrelated edits, missing outputs and broken dependencies.
6. Do not expand the review into style preferences or unrelated architecture suggestions.

## Verdicts

- **PASS:** every required criterion has sufficient evidence.
- **NEEDS_CHANGES:** one or more criteria fail. Identify the exact criterion, artifact/file/source and minimal correction required.
- **BLOCKED:** verification cannot proceed because a permission, dependency, test environment or required input is unavailable. Explain exactly what is missing.

## Review output

- Verdict and one-sentence reason.
- Criterion-by-criterion result.
- Evidence inspected and checks performed, with actual outcomes.
- Exact corrective actions, only if required.
- Any unverified claim or residual risk.

Never approve based on a narrative assertion alone. Never invent a test result. Never mark PASS when a mandatory criterion is unverified.
