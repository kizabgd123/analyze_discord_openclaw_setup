# Discord Bot Memory
Ovaj fajl se koristi za beleženje lokalnih informacija o korisnicima i zadacima. Bot koristi Google NotebookLM kao glavni izvor memorije.

## Lokalna pravila:
- Komunikacija sa NLM CLI se vrši za svaku dolaznu poruku (mentions & DMs).
- NLM odgovori se dele na 1900 karaktera ako su predugački za Discord limit od 2000.
- Svaka operacija izmene stanja i pokretanja komandi prolazi kroz JudgeGuard HMAC-SHA256 quorum verifikaciju.

## Aktivne Google NotebookLM Sveske (Vratiće se rode Multi-Agent Engine):
- **Švaba (Moderator):** `06da0502-7e35-4d6f-bf28-3de316dc0437` — OpenClaw Sovereign AI OS & Multi-Agent Orchestration 2026
- **Ekser (Arhitekta):** `e07782d0-7a66-4c12-a348-70ca1b2fdb8c` — Discord Bot MCP & FastMCP Architecture 2026
- **Pikac (Kritičar):** `2ac2015f-51dd-44f8-9210-521499f0c953` — Sistemski Promptovi i Bezbednost LLM-ova
- **Dule Pacov (Strategist):** `1f53f9ad-bae3-45b9-aec0-0ab0450a6b48` — AI Agent Monetization, GEO & Growth Strategy 2026
- **Babac (Evaluator):** `98d5b107-3c1b-4345-b8d5-1825dbfe4084` — Agentic AI: Human Oversight & Generative UI Patterns
