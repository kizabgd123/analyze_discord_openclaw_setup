# Izvori i GitHub projekti

Pregledano 6. novembra 2026. Prednost imaju zvanična dokumentacija i primarni repozitorijumi.

## Primarni Hermes izvori

1. **Hermes Agent — zvanični GitHub**  
   https://github.com/NousResearch/hermes-agent  
   Glavni repozitorijum. Dokumentacija i kod za profile, gateway, Discord, tools, skills i Kanban.

2. **Hermes Kanban — Multi-Agent Task Board**  
   https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban  
   Zajednička SQLite tabla, kartice, dodela radnika, zavisnosti, dispatch, komentari, handoff i review.

3. **Hermes Kanban — Tutorial**  
   https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-tutorial  
   Konkretan primer PM → worker → reviewer → promene → re-review. Koristan kao obrazac produktivnog toka.

4. **Hermes Discord Gateway**  
   https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord  
   Discord konfiguracija, mention pravila, thread-ovi, channel/user allowlist i bot-authored message pravila.

5. **Hermes Bot Mode**  
   https://hermes-agent.nousresearch.com/docs/user-guide/features/bot-mode  
   Profili kao botovi, njihove uloge, podešavanja i lokalni grupni razgovori. Odvojiti od Discord gateway ponašanja.

6. **Hermes Skills**  
   https://hermes-agent.nousresearch.com/docs/user-guide/skills  
   On-demand `SKILL.md` instrukcije, instaliranje i upravljanje veštinama.

7. **Hermes Delegation**  
   https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation  
   `delegate_task` za kratke izolovane paralelne podzadatke; Kanban za trajan rad.

8. **Hermes A2A**  
   https://hermes-agent.nousresearch.com/docs/user-guide/features/a2a  
   Opciona integracija za agente na različitim framework-ovima/mašinama; nije potrebna za lokalne Hermes profile.

## Standard za skill fajlove

9. **Agent Skills — otvoreni standard**  
   https://github.com/agentskills/agentskills  
   Specifikacija formata `SKILL.md` sa YAML frontmatter poljima kao što su `name` i `description`.

## GitHub kandidati koje vredi pratiti, ali ne uvoditi sada

10. **LangGraph**  
    https://github.com/langchain-ai/langgraph  
    Kandidat ako kasnije bude potreban prilagođen, eksplicitan workflow/state-machine sistem. Duplirao bi deo Hermes orkestracije u prvoj iteraciji.

11. **CrewAI**  
    https://github.com/crewAIInc/crewAI  
    Alternativni multi-agent framework. Nije potreban samo da bi se Hermes profili raspoređivali kroz Kanban.

12. **A2A Protocol**  
    https://github.com/a2aproject/A2A  
    Otvoreni protokol za komunikaciju između nezavisnih agenata. Uvesti tek ako se pojavi potreba za udaljenim/heterogenim agentima.

## Važna napomena o verifikaciji

Spoljašnji GitHub kandidati nisu predstavljeni kao instalirani, testirani ili kompatibilni sa konkretnom mašinom. Primarni implementacioni oslonac je zvanični Hermes repo. Antigravity treba da proveri lokalnu Hermes verziju i stvarni CLI/API pre bilo kakve promene.
