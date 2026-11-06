# Hermes Discord Workforce

**Istraživačko-implementacioni paket za Antigravity**  
Istraženo: 6. novembar 2026.

## Svrha

Postaviti produktivan tim specijalizovanih Hermes profila kojim se upravlja kroz već povezani Discord Hermes bot. Ne praviti botove koji međusobno vode otvorene razgovore. Koristiti Hermes Kanban kao trajni sloj za zadatke, dodelu, zavisnosti, komentare, predaju i proveru rezultata.

## Šta je u paketu

- `RESEARCH.md` — detaljni nalazi, arhitektura, ograničenja i preporuke.
- `SOURCES.md` — primarni izvori i GitHub projekti.
- `ANTIGRAVITY_PROMPT.md` — kratak prompt za Antigravity.
- `antigravity/TASK.md` — operativni zadatak koji agent treba da izvrši.
- `antigravity/ACCEPTANCE_CHECKLIST.md` — kriterijumi završetka i dokazivanja.
- `skills/` — četiri Hermes `SKILL.md` instrukcije, fokusirane po ulozi.
- `templates/` — šablon zadatka i predaje rada.
- `notebooklm/NOTEBOOKLM_IMPORT.md` — sažetak spreman za ubacivanje u NotebookLM.

## Ciljna arhitektura

```text
Discord (postojeći Hermes bot)
          |
          v
Orchestrator profile (Discord ulaz + Kanban toolset)
          |
          v
Hermes Kanban (shared SQLite task board)
    |           |             |
    v           v             v
Researcher   Analyst       Builder
    |           |             |
    +-----------+-------------+
                |
                v
          Verifier / Reviewer
                |
                v
   Orchestrator → rezultat na Discord
```

Profili su Hermes radnici, ne dodatni Discord botovi. Jedan gateway/dispatcher obrađuje zajedničku Kanban tablu. `delegate_task` ostaje opcija za kratke, izolovane podzadatke; Kanban je primarni mehanizam za trajan, višekoračni rad.

## Važno

Ovaj paket nije instalacioni skript i ne sadrži pristupne tokene. Antigravity treba da ga koristi kao specifikaciju, pregleda postojeće stanje i primeni samo ono što nedostaje. Ako instalirana Hermes verzija nema Kanban funkcionalnost ili se šema konfiguracije razlikuje od dokumentacije, agent treba da prekine tu promenu, priloži dokaz i predloži kompatibilan sledeći korak — bez samostalnog upgrade-a ili zamene arhitekture.
