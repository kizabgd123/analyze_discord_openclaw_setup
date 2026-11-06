# Antigravity — kratak zadatak

U postojećem Hermes okruženju, koje je već povezano sa Discordom, implementiraj produktivan multi-agent workflow koristeći **Hermes Kanban**, ne bot-to-bot debatu.

Prvo pregledaj `antigravity/TASK.md`, checklist i `skills/`. Zatim read-only proveri Hermes verziju, profile, aktivni Discord/gateway profil, toolsets, Kanban podršku i postojeće skill-ove. Sačuvaj backup konfiguracije. Ne reinstaliraj Hermes/Discord, ne pravi nove bot naloge/tokenе i ne menjaj postojeću autentikaciju.

Ako je Kanban kompatibilan, omogući ga za postojeći Discord orchestrator profil, dodaj samo nedostajuće role profile i ciljane skill-ove, pa testiraj ceo tok malim bezopasnim zadatkom: Discord → orchestrator → Kanban workers → verifier → rezultat u Discord. Ne uključuj bot-to-bot poruke (`DISCORD_ALLOW_BOTS` ostaje postojeći/default `none`). Ne pokreći drugi dispatcher pored gateway-a.

Radi iterativno, proveravaj svaki korak stvarnim CLI izlazom i logovima. Ne tvrdi uspeh bez dokaza. Ne radi upgrade, reset baze ili promenu arhitekture ako lokalna verzija ne podržava Kanban — stani, priloži nalaze i predloži minimalan kompatibilan plan. Završno prikaži promene, backup putanju, testove, rezultate i preostale blokade.
