---
name: discord-workflow
description: Handle user requests and progress reporting through the existing Hermes Discord bot while Kanban workers execute tasks. Use for Discord control-plane conversations.
---

# Discord Workflow

## Mission

Keep Discord as a clear control surface for the user. The orchestrator owns the conversation; worker-to-worker coordination belongs in Hermes Kanban.

## Intake

- Treat direct user requests and explicit bot mentions as instructions for the orchestrator.
- Summarize the intended outcome before creating multi-step tasks when it materially improves clarity.
- Use the existing guild/channel/user access controls. Never loosen them to make a test easier.

## Progress updates

- Send concise updates only at meaningful milestones: task plan created, a material blocker found, review started, or final result ready.
- Do not post every worker thought, tool call or intermediate message.
- Include task IDs only when they help the user track the work.
- Never expose internal secrets, private configuration or raw credentials.

## Agent coordination

- Create and monitor Kanban tasks through the orchestrator profile.
- Do not ask workers to message each other in Discord.
- Do not enable bot-to-bot admission or mention relays as a substitute for Kanban.
- Use task dependencies and structured handoffs to pass context.

## Final response

Return the outcome, what was verified, where the artifacts/results are, important limitations and the next action needed from the user. Clearly mark any unverified part. Avoid claiming success before the Kanban worker and verifier evidence is available.
