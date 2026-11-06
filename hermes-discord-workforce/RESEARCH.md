# Istraživanje: produktivan Hermes multi-agent tim preko Discorda

**Datum provere:** 6. novembar 2026.  
**Primarni izvor:** zvanični `NousResearch/hermes-agent` repozitorijum i zvanična Hermes dokumentacija. Dokumentacija se razvija brzo; Antigravity mora prvo da proveri šta je dostupno u lokalno instaliranoj verziji.

## 1. Sažetak odluke

Preporuka je da se koristi postojeći Hermes Discord bot kao jedina korisnička ulazna tačka, a da se rad raspoređuje na zasebne Hermes profile preko ugrađenog Hermes Kanban sistema.

Ne preporučuje se Discord bot swarm u kome više botova odgovara jedan drugom u zajedničkom kanalu. Takav režim postoji kao opcionalna mogućnost u Hermes Discord integraciji, ali nije potreban za željeni rezultat. On donosi dodatnu kontrolu dozvola, mention pravila, rizik od petlji i više buke. Zadatke, međurezultate i handoff treba čuvati u Kanban tabli, a ne u neformalnom Discord razgovoru.

### Ciljni tok

1. Korisnik pošalje zadatak postojećem Hermes botu u privatnom/odobrenom Discord kanalu.
2. Orchestrator razume cilj, napiše kriterijume prihvatanja i podeli posao na nezavisne ili zavisne kartice.
3. Hermes Kanban dodeli kartice specijalizovanim profilima.
4. Radnici izvršavaju svaki svoj zadatak, prijavljuju blokade i predaju strukturisan rezultat sa dokazima.
5. Zavisni rad počinje tek kada su roditeljski zadaci završeni.
6. Reviewer/verifier proverava ispunjenost kriterijuma, testove i dokaze. Ne vodi raspravu niti iznosi neodređeno mišljenje.
7. Orchestrator objedini potvrđene rezultate i pošalje kratak, upotrebljiv izveštaj na Discord.

## 2. Šta Hermes već nudi

### 2.1 Hermes profili i Bot Mode nisu isto

Hermes profili omogućavaju odvojene konfiguracije i uloge. Svaki profil može imati sopstveni model, memoriju i izbor veština/alata. Zvanični Bot Mode u Hermes Desktop-u dodatno predstavlja profile kao imenovane botove i podržava lokalne grupne razgovore od 2 do 6 botova.

Važno razgraničenje: **Hermes Desktop Bot Mode grupni razgovor nije isto što i Discord gateway.** Za ovaj projekat ne treba pretpostaviti da se Desktop group chat automatski preslikava u Discord. Koristimo Hermes profile + Kanban dispatch; Discord je korisnički interfejs.

### 2.2 Hermes Kanban je centralna komponenta

Zvanična dokumentacija opisuje Kanban kao trajan multi-agent sistem zasnovan na SQLite bazi (podrazumevana putanja u dokumentaciji: `~/.hermes/kanban.db`) i zajednički dostupan Hermes profilima u istoj Hermes instalaciji/home okruženju.

Kanban obezbeđuje:

- trajne task kartice i statusni tok;
- dodelu zadataka konkretnim Hermes profilima;
- linkovanje roditeljskih/zavisnih zadataka;
- komentarе i napomene;
- predaju zadatka sa sažetkom i metapodacima;
- nastavak/retry i prijavu blokade;
- automatsko pokretanje dodeljenih radnika preko dispatcher-a;
- opcionalno automatsko slanje zadatka na review.

Zvanični alati uključuju (tačna dostupnost zavisi od verzije i aktivnog toolset-a): `kanban_show`, `kanban_list`, `kanban_create`, `kanban_link`, `kanban_comment`, `kanban_complete`, `kanban_request_review`, `kanban_request_changes`, `kanban_block`, `kanban_unblock`, `kanban_heartbeat`, `kanban_attach` i `kanban_attachments`.

Desktop Kanban dashboard prikazuje tablu, ali samo otvaranje dashboard-a ne daje chat agentu pravo da upravlja karticama. Orchestrator mora imati omogućen `kanban` toolset na platformi na kojoj prima zadatke.

### 2.3 Dispatcher i gateway

U dokumentaciji je gateway dispatcher uključen po podrazumevanim podešavanjima. Kada je gateway aktivan, on periodično proverava spremne kartice i pokreće radnike. Zbog toga u prvoj verziji treba zadržati **jedan vlasnički gateway/dispatcher**. Ne pokretati paralelno stari/odvojeni Kanban daemon ako gateway već obavlja dispatch — dva dispatchera mogu da se nadmeću za iste zadatke.

`hermes kanban init` je dokumentovan kao inicijalizacija Kanban baze. Antigravity treba prvo da proveri da li je već inicijalizovana i da li komanda postoji u instaliranoj verziji; ne sme da briše ili resetuje postojeću tablu.

## 3. Preporučena podela uloga

Ne praviti desetine profila. Početi sa najmanjim timom koji ima jasnu podelu odgovornosti:

| Profil | Odgovornost | Šta ne radi |
|---|---|---|
| `orchestrator` | Prima zahtev, definiše kriterijume, deli posao, prati Kanban, sklapa konačni odgovor | Ne izmišlja rezultate radnika i ne označava zadatak završenim bez predaje |
| `researcher` | Pronalazi primarne izvore, proverava datume/verzije, izdvaja činjenice i citate | Ne implementira kod osim ako je to eksplicitno dodeljeno |
| `analyst` | Sređuje nalaze, poredi opcije, identifikuje rizike i odluke | Ne prepisuje istraživačke izvore kao da ih je sam proverio |
| `builder` | Izvršava konkretan implementacioni zadatak u dodeljenom opsegu | Ne menja tuđe fajlove ili arhitekturu bez dogovora |
| `verifier` | Nezavisno proverava kriterijume, testove, tragove i izlazne artefakte | Ne ulazi u opštu debatu; navodi konkretan dokaz ili konkretan nedostatak |

Profili mogu biti spojeni u manjem okruženju: researcher i analyst mogu u početku biti jedan profil. Builder se uključuje samo kada zahtev zaista traži implementaciju.

### Opis profila je važan

Hermes Kanban može koristiti opise profila kao signal za usmeravanje zadataka. Opisi treba da budu funkcionalni i uski (na primer: „proverava zvaničnu dokumentaciju i primarne izvore“), a ne marketinške biografije.

## 4. `delegate_task` ili Kanban?

Koristiti oba, ali za različite vrste posla:

- **Kanban:** trajni zadaci, više faza, rad između profila, zavisnosti, ponovni pokušaji, review ili potreba da čovek vidi i prati stanje.
- **`delegate_task`:** kratak, izolovan podzadatak sa jasnim ulazom i izlazom, bez dugoročnog statusa ili potrebe da se nastavlja posle restarta.

Ne praviti dodatni LangGraph/CrewAI sloj samo da bi se postigla osnovna delegacija. Hermes već ima native Kanban i delegation.

## 5. Discord integracija: preporučena podešavanja

### Koristiti postojeći bot

- Sačuvati postojeći bot token i konfiguraciju.
- Zadržati dozvole za korisnike/uloge/kanale koje već postoje; proveriti da nisu šire od potrebnog.
- Koristiti jedan kontrolni kanal ili thread workflow, po mogućnosti zatvoren za neodobrene korisnike.
- Ostaviti zahtev za mention uključenim u server kanalima.
- Uključiti automatsko pravljenje threada samo ako je već podržano i korisno u lokalnoj verziji.
- Orchestrator preko Kanban-a pokreće radnike i dobija završne notifikacije u Discord konverzaciji.

### Ne uključivati bot-to-bot chat u prvoj iteraciji

Hermes Discord dokumentacija opisuje `DISCORD_ALLOW_BOTS` kao opt-in; podrazumevana vrednost je `none`. Kada se dozvoli bot-authored poruka, postoje i dodatna pravila za literalne mention-e i zaštite od petlji. Ostaviti podešavanje na postojećoj vrednosti (najčešće `none`) i ne menjati ga za ovaj dizajn.

Ako se kasnije pojavi realan zahtev za komunikaciju sa drugim nezavisnim Discord botom, to treba projektovati kao zasebnu integraciju sa jasnim allowlist-om, jednim smerom handoff-a, ograničenjem poruka i testom loop-prevention — ne kao podrazumevani način rada tima.

### Platform toolset

Zvanična dokumentacija navodi da je izbor toolset-a po platformi nezavisan. Potrebno je omogućiti `kanban` toolset baš za aktivni profil i Discord platformu. Dokumentovan primer obrasca komande je:

```bash
hermes -p <ACTIVE_PROFILE> tools enable kanban --platform discord
```

Antigravity mora proveriti `hermes --help`, `hermes tools --help` i aktivni profil pre pokretanja. Ne pretpostavljati da je primer potpuno isti u svakoj starijoj verziji. Nakon promene platform toolset-a otvoriti novu Discord sesiju/konverzaciju da se ažurirani alati učitaju.

## 6. Handoff ugovor i dokazivanje

Svaki worker treba da preda:

- kratak rezultat u običnom jeziku;
- šta je tačno urađeno;
- koje fajlove/artefakte je promenio ili kreirao;
- koje komande/testove je pokrenuo i njihov stvarni izlazni status;
- izvore, URL-ove i datume kada je zadatak istraživački;
- šta nije provereno;
- blokade i preostale rizike.

Predloženi strukturisani metapodaci:

```json
{
  "changed_files": [],
  "verification": [],
  "dependencies": [],
  "blocked_reason": null,
  "retry_notes": null,
  "residual_risk": []
}
```

Ovo je primer strukture, a ne obaveza da se polja šalju kao tekst ako lokalni alat očekuje mapu/JSON objekat. Ne upisivati tokene, lozinke, privatne ključeve ili druge tajne u kartice, komentare ili metadata.

**Pravilo završetka:** status `completed` samo kada je rad stvarno izvršen i sažetak sadrži dokaz. Ako postoji prepreka, koristiti `blocked` i objasniti šta tačno nedostaje. Ako je potreban review, koristiti review handoff, ne lažno „done“.

## 7. Review bez debate

Reviewer ne ocenjuje stil ili „ko je u pravu“. Proverava unapred dogovorene acceptance kriterijume:

- PASS — svi kriterijumi imaju odgovarajući dokaz;
- NEEDS_CHANGES — konkretan kriterijum nije ispunjen; navesti tačan fajl/test/činjenicu i potreban ispravak;
- BLOCKED — provera nije moguća zbog nedostajućeg pristupa, izvora ili zavisnosti.

Hermes dokumentacija navodi ugrađeni `sdlc-review` skill i `review_dispatch` opciju za automatsko slanje zadataka na review. Antigravity treba proveriti da li je review dispatch uključen i kakva je lokalna konfiguracija; ne menjati ga ako već radi.

## 8. Skill paket

Ovaj paket sadrži četiri fokusa:

1. `hermes-kanban-orchestrator` — planiranje, dekompozicija, raspodela, zavisnosti i objedinjavanje.
2. `productive-team-worker` — izvršenje jedne dodeljene kartice i strukturisana predaja.
3. `evidence-review` — provera na osnovu kriterijuma i dokaza.
4. `discord-workflow` — način komunikacije sa korisnikom preko Discord-a.

Skill-ovi su namerno odvojeni da se ne učitava sve instrukcije svakom profilu. Instalirati ih samo profilima kojima su potrebni. Uputstva koriste Hermes `SKILL.md` princip sa frontmatter `name` i `description`; dodatne reference ili skripte dodavati samo kada postoji jasan slučaj.

## 9. Plan uvođenja

### Faza 0 — Read-only inventar

Antigravity proverava verziju, aktivni profil, profile listu, gateway status, Discord platformu, toolsets, Kanban komande/bazu i postojeće skill-ove. Bez promena.

### Faza 1 — Minimalna aktivacija

Ako je Kanban podržan i nije već aktivan: sačuvati konfiguraciju, inicijalizovati samo ako nedostaje, omogućiti `kanban` toolset za aktivni Discord orchestrator profil. Ne dirati bot token, dozvole i bot-to-bot opcije.

### Faza 2 — Role profili i skill-ovi

Koristiti postojeće profile gde je moguće. Kreirati samo uloge koje nedostaju. Kopirati naše skill-ove u Hermes skill direktorijum uz backup i potvrditi da ih namenjeni profili vide.

### Faza 3 — Testni zadatak

Napraviti mali, bezopasan test zadatak koji ne menja projekat: jedan researcher zadatak, jedan zavisni verifier zadatak, zatim objedinjavanje u Discord thread-u. Proveriti da se zadaci čuvaju, dispatchuju, završavaju i da Discord dobija notifikaciju.

### Faza 4 — Praktični pilot

Pustiti jedan stvarni zadatak sa jasnim kriterijumima i ograničenim opsegom. Proveriti logove, kartice i dokaze. Tek onda razmotriti dodatne profile ili optimizaciju modela.

## 10. Ograničenja i fallback

- Dokumentacija na webu može biti novija od lokalne instalacije. Lokalni `--help`, verzija, konfiguracioni fajlovi i dostupni tool-ovi imaju prednost.
- Ako Kanban nije podržan, ne instalirati naslepo najnoviji Hermes i ne prebacivati sistem na CrewAI/LangGraph. Napraviti izveštaj o verziji i kompatibilnosti pa predložiti minimalan upgrade plan za odobrenje.
- Ako postojeći Hermes setup koristi više home okruženja ili gateway procesa, prvo utvrditi da li dele Kanban bazu i ko je dispatcher owner. Ne spajati home/profile baze naslepo.
- Kanban tabla i dashboard mogu sadržati osetljive promptove, projektne detalje i putanje fajlova. Dashboard držati na loopback-u osim ako postoji eksplicitno obezbeđen pristup.

## 11. Šta svesno ne uvodimo u prvoj verziji

- LangGraph, CrewAI ili Agno kao još jedan orkestracioni sloj.
- Više Discord bot tokena.
- `DISCORD_ALLOW_BOTS=mentions/all`.
- A2A ili remote agent protokol za lokalne profile.
- Novi dashboard, web servis ili zasebna baza.
- Automatski merge/commit/deploy bez eksplicitnih kriterijuma i postojećih zaštita.

A2A je zanimljiv za kasnije povezivanje nezavisnih agenata na različitim mašinama ili drugim framework-ovima, ali nije potreban za više Hermes profila u istoj instalaciji.

## 12. Konačna preporuka

Prvo aktivirati i pravilno podesiti Hermes Kanban za već postojeći Discord bot i postojeći gateway. Izgraditi mali tim od 3–5 profila uz jasne opise i ciljane skill-ove. Uspostaviti strukturisanu predaju i nezavisnu proveru. Ovaj pristup koristi ono što Hermes već podržava, smanjuje dodatnu infrastrukturu i daje trajno, proverljivo stanje rada umesto neproduktivnog razgovora botova.
