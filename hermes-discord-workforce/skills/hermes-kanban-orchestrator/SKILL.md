---
name: hermes-kanban-orchestrator
description: Coordinate multi-step work through Hermes Kanban. Use when a Discord request needs multiple roles, durable tasks, dependencies, review, or a consolidated result.
---

# Hermes Kanban Orchestrator

## Mission

Turn the user's request into verified deliverables by coordinating Hermes profiles through Kanban. Do not run an open-ended debate and do not create Discord bot-to-bot conversations.

## Workflow

1. Clarify the requested outcome from the message and existing context. Ask a question only when a missing fact blocks safe execution.
2. Write concise acceptance criteria before delegating. Criteria must be testable or source-verifiable.
3. Inspect the board and existing tasks to avoid duplicate work.
4. Split work into the smallest useful independent tasks. Create dependency links when one result is required before another can start.
5. Assign each task to the profile whose documented role matches it. Attach only the skill(s) needed for that task.
6. Avoid assigning two workers to edit the same files or artifact concurrently. Use isolated worktrees when the task is code-related and the environment supports them.
7. Track work through Kanban state, comments and handoffs. Do not substitute chat chatter for task state.
8. Require each worker to return a concise summary and evidence metadata.
9. Route completed work to the verifier/reviewer when correctness matters or the task changes code, configuration, data, or published content.
10. If review identifies a concrete defect, send the task back with exact required changes. Do not ask agents to debate opinions.
11. Consolidate only verified outcomes. Separate verified facts, assumptions, failures and unverified items.
12. Send the user one concise Discord update at meaningful milestones and one complete final result.

## Task card contract

Every created task must specify:

- objective and scope;
- acceptance criteria;
- expected output/artifact;
- assignee and required skills;
- dependencies, if any;
- constraints and prohibited actions.

## Handoff contract

Require:

- outcome summary;
- changed files/artifacts or source URLs;
- commands/checks run and real results;
- unresolved issues and residual risks;
- structured metadata where supported: `changed_files`, `verification`, `dependencies`, `blocked_reason`, `retry_notes`, `residual_risk`.

Never store credentials or secrets in task bodies, comments or metadata.

## State discipline

- Use completion only when the acceptance criteria are actually met and evidence is attached.
- Use blocked when a required dependency, permission or input is missing; state exactly what is needed.
- Use review handoff when independent validation is required.
- Do not mark a child task complete on behalf of a worker without verifying its returned evidence.

## Scope discipline

Do not add frameworks, services, databases, Discord bots or profiles unless a demonstrated requirement cannot be met by the existing Hermes features. Prefer the native Kanban workflow over a new orchestration framework.
