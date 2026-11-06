# NotebookLM source brief — Hermes Discord Workforce

**Datum:** 6. novembar 2026.

## Istraživačko pitanje

Kako iskoristiti već instalirani Hermes Agent i povezani Discord bot da se napravi produktivan tim specijalizovanih AI agenata, bez neproduktivne debate između botova i bez uvođenja nepotrebnog dodatnog framework-a?

## Glavni zaključak

Koristiti jedan postojeći Discord Hermes bot kao korisničku ulaznu tačku. Više Hermes profila obavljaju različite uloge, a Hermes Kanban je zajednički sloj za trajne zadatke, dodelu, zavisnosti, komentare, handoff i review. Ne uvoditi bot-to-bot Discord poruke u prvoj iteraciji.

## Zašto Hermes Kanban

Zvanični Hermes Kanban koristi SQLite tablu koju profili dele unutar iste Hermes instalacije/home okruženja. Dodeljeni worker se pokreće kroz dispatcher. Task može imati zavisnosti i structured handoff. Gateway obično hostuje dispatcher, zato za prvu iteraciju treba jedan dispatcher owner i ne treba paralelno startovati drugi daemon.

## Predložene uloge

- Orchestrator: ulazni Discord profil, planira i raspodeljuje zadatke.
- Researcher: proverava primarne izvore i dokumentaciju.
- Analyst: sintetizuje nalaze i preporučuje odluke.
- Builder: izvršava konkretne implementacione zadatke.
- Verifier: nezavisno proverava kriterijume i dokaze.

Početi sa 3–5 profila i ponovo iskoristiti postojeće profile gde mogu kvalitetno pokriti ulogu.

## Tok rada

Discord zahtev → acceptance kriterijumi → Kanban task graph → specijalizovani workers → strukturisani handoff → nezavisna verifikacija → konačni rezultat u Discord-u.

Verdikti verifikatora: PASS, NEEDS_CHANGES ili BLOCKED. Nema otvorene debate; svaka primedba mora da pokaže konkretan nedostatak u odnosu na kriterijum.

## Discord pravila

Sačuvati postojeći bot token i dozvole. Zadržati mention/allowlist zaštitu. Ne menjati `DISCORD_ALLOW_BOTS` i ne uključivati bot-authored relay. Discord je kontrolni interfejs, a Kanban je kanal koordinacije između agenata.

## Važne implementacione provere

- Proveriti lokalnu Hermes verziju i dostupnost Kanban-a pre promena.
- Omogućiti `kanban` toolset na aktivnom Discord orchestrator profilu (toolset izbor je per platform).
- Proveriti da postojeći gateway pokreće dispatcher.
- Backup konfiguracije i skill direktorijuma pre promena.
- Testirati jedan researcher task, zatim zavisni verifier task, i dokazati da rezultat stiže nazad na Discord.
- Ako lokalna verzija nema Kanban, zaustaviti izmene i napraviti kompatibilan upgrade plan za odobrenje; ne menjati framework samostalno.

## Opcioni pravci kasnije

- A2A za udaljene agente ili agente iz različitih framework-a.
- LangGraph za prilagođene workflow grafove ako native Kanban postane nedovoljan.
- CrewAI kao alternativni orchestration framework samo ako Hermes ne može da ispuni konkretan zahtev.

Nijedan od ovih dodataka nije potreban za početni lokalni multi-profile workflow.

## Primarni izvori za NotebookLM

- https://github.com/NousResearch/hermes-agent
- https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban
- https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-tutorial
- https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord
- https://hermes-agent.nousresearch.com/docs/user-guide/features/bot-mode
- https://hermes-agent.nousresearch.com/docs/user-guide/skills
- https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation
- https://hermes-agent.nousresearch.com/docs/user-guide/features/a2a
- https://github.com/agentskills/agentskills
- https://github.com/langchain-ai/langgraph
- https://github.com/crewAIInc/crewAI
- https://github.com/a2aproject/A2A

## Pitanja za dodatnu analizu

1. Koja je minimalna Hermes verzija koja podržava sve Kanban mogućnosti koje lokalna instalacija treba?
2. Koji postojeći Hermes profili već odgovaraju predloženim ulogama?
3. Koji modeli su trenutno dodeljeni profilima i koji zadaci zahtevaju skuplji model?
4. Da li Discord gateway već šalje Kanban terminalne notifikacije u izvorni thread?
5. Koji je najbezbedniji način za testiranje dispatch-a u konkretnom lokalnom okruženju?
