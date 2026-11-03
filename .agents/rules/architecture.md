# Architecture Rules

## Single App Structure (Autonomous Discord Bot & Cognitive OS)

OpenClaw / Antigravity 2.0 is an autonomous, self-improving agent service running on Python 3.12 with asynchronous Discord event handling, dual-tier cognitive retrieval, and multi-agent persona debates grounded in Google NotebookLM.

```text
discord-openclaw/
├── discord_bot.py            # Primary Discord gateway (Slash commands, UI components, events)
├── brain_core.py             # Cognitive engine (VSR funnel, dual-tier SQLite FTS5 + NLM retrieval)
├── debate_engine.py          # Multi-agent debate coordinator (5 personas, webhook dispatch, state machine)
├── debate_self_improve.py    # Autonomous Context Updating (ACU) & self-improvement loop
├── judge_guard.py            # HMAC-SHA256 Quorum safety gate & WORK_LOG freshness validator
├── agent_sanity_audit.py     # 5-pillar semantic & runtime sanity evaluator
├── openclaw.json             # Sovereign agent specification & persona notebook mapping
├── debate_state.json         # Active debate session state persistence
├── antigravity_rag.db        # Tier 1 SQLite3 database with FTS5 search
├── SOUL.md                   # Agent voice and persona behavioral contract
├── MEMORY.md                 # Working memory & notebook registry
├── WORK_LOG.md               # Audit log & sliding freshness record
├── DECISION_RECORD_EVIDENCE_LAYER.md # Evidence and provenance decision audit
├── manage_bot.sh             # Systemd service manager
├── start_discord_bot.sh      # Background process manager & log rotator
├── .githooks/                # Pre-commit, commit-msg, post-commit hooks & sanity verifier
├── scratch/                  # Test pipelines and scratch scripts
├── souls/                    # Extended persona prompt markdown files
└── venv/                     # Isolated Python 3.12 virtual environment
```

## Stack

| Layer | Technology | Version |
| ----- | ---------- | ------- |
| Runtime | CPython | 3.12.3 |
| Virtualenv | venv / pip | 24.0 |
| Bot Gateway | discord.py | 2.7.1 |
| Async HTTP | aiohttp | 3.14.1 |
| Environment Config | python-dotenv | 1.2.2 |
| Cryptography & Safety | PyNaCl / cffi / hmac | 1.6.2 / 2.1.1 / stdlib |
| Local Database | SQLite3 (FTS5 enabled) | 3.x (stdlib) |
| Grounding Engine | Google NotebookLM via `nlm` CLI | System binary (`nlm`) |
| Process Supervisor | Linux systemd (`discord-openclaw.service`) | Systemd |

## Commands & Interaction Endpoints

Native Discord Slash Commands registered in `discord_bot.py`:

| Command | Type | Purpose |
| ------- | ---- | ------- |
| `/ask <query>` | Slash Command | Query active NotebookLM notebook with grounded citation output |
| `/notebooks` | Slash Command | List all available Google NotebookLM notebooks with interactive select menu |
| `/use <notebook_id>` | Slash Command | Switch default working notebook for the current user/session |
| `/sources [notebook_id]` | Slash Command | List document sources grounded in the specified notebook |
| `/note <title> <content>` | Slash Command | Create a persistent note in the active notebook |
| `/debate <topic>` | Slash Command | Start a structured 5-persona multi-agent debate |
| `/execute <plan>` | Slash Command | Tier-2/Tier-3 state-changing action (requires DM admin approval & JudgeGuard) |
| `/status` | Slash Command | Real-time status of bot, memory, and cognitive modules |
| `/help` | Slash Command | Interactive guide for bot capabilities and commands |

## Persona Grounding Matrix

Every persona is grounded in a dedicated Google NotebookLM notebook:

| Persona | Character & Role | Notebook ID | Grounding Domain |
| ------- | ---------------- | ----------- | ---------------- |
| **Švaba** | Predrag Švabić — Moderator & Mozak | `06da0502-7e35-4d6f-bf28-3de316dc0437` | Sovereign AI OS, Orchestration |
| **Ekser** | Milorad Urošević — Kod-Kombinator & Arhitekta | `e07782d0-7a66-4c12-a348-70ca1b2fdb8c` | Discord Bot, FastMCP Architecture |
| **Pikac** | Momčilo Đorđević — QA & Bezbednosni Paranoik | `2ac2015f-51dd-44f8-9210-521499f0c953` | System Prompts, LLM Security |
| **Dule Pacov** | Dušan Krtolica — Biznis Strateg | `1f53f9ad-bae3-45b9-aec0-0ab0450a6b48` | Monetization, Growth, GEO Strategy |
| **Babac** | Ruža / Miki Nosonja — Vrhovni Sudija & Evaluator | `98d5b107-3c1b-4345-b8d5-1825dbfe4084` | AI Evaluation, Human Oversight |

## Data Flow

```text
User Input (Discord Slash / Mention / DM)
        │
        ▼
discord_bot.py (Command Router & Event Listener)
        │
        ├── [Read-only Query]
        │         │
        │         ▼
        │   BrainCore.retrieve_context()
        │         │
        │         ├── Tier 1: SQLite FTS5 (antigravity_rag.db)
        │         │
        │         └── Tier 2: `nlm notebook query <NOTEBOOK_ID> "<PROMPT>"`
        │                   │
        │                   ▼
        │         BrainCore.synthesize() (VSR Funnel)
        │                   │
        │                   ▼
        │         Formatted Discord Response (< 1900 chars chunks)
        │
        └── [State-Changing Action / Command Execution]
                  │
                  ▼
            JudgeGuard Quorum Verification
                  │
                  ├── Blacklist Pattern Scan
                  ├── WORK_LOG.md Freshness Check (< 300s)
                  └── HMAC-SHA256 Quorum Signing
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
          [PASSED]                    [BLOCKED]
              │                           │
              ▼                           ▼
      Execute Action               Halt & Alert Admin
              │
              ▼
      Update WORK_LOG.md (✅)
```

## Language and Voice Specification

- **Persona Output**: Cult Serbian ("Vratiće se rode") voice with street wit, cynical humor, but 100% technical accuracy. Output must be concise (2 to 4 paragraphs or bullet points, zero fluff).
- **System Documentation**: Strict technical English for code comments, logs, architecture documents, and git commits.
