# Operativni zadatak za Antigravity

## Cilj

Postaviti postojeći Hermes Discord bot kao korisnički ulaz u produktivan multi-agent tim. Hermes profili izvršavaju zadatke, a Hermes Kanban obezbeđuje trajnu dodelu, zavisnosti, komentare, handoff i review. Ne praviti bot-to-bot debate.

## Pravila izvršenja

- Postojeći Hermes i Discord konektor su već instalirani. Ne reinstalirati ih.
- Ne menjati, prikazivati ili kopirati bot tokene, API ključeve ili druge tajne.
- Ne kreirati nove Discord bot naloge ili tokene.
- Ne menjati `DISCORD_ALLOW_BOTS`; ne uključivati bot-authored message relay.
- Ne pokretati drugi Kanban dispatcher ako ga postojeći gateway već hostuje.
- Ne resetovati niti brisati Kanban bazu, profile ili memoriju.
- Ne praviti upgrade instalacije bez odobrenja. Ako lokalna verzija nema traženu funkciju, zaustaviti promene i dostaviti dokaz.
- Koristiti postojeće profile kad god je moguće; kreirati samo nedostajuće.
- Napraviti backup pre svake izmene konfiguracije ili skill fajlova.
- Izvršavati komande sekvencijalno kada menjaju isto stanje; posle svake promene proveriti rezultat.

## Korak 1 — Inventar, samo čitanje

Prikupi i zabeleži:

1. Hermes verziju i putanju izvršne komande.
2. Postojeće Hermes home/profile direktorijume i listu profila.
3. Koji profil koristi postojeći Discord gateway/bot.
4. Da li je gateway aktivan i da li već radi Kanban dispatcher.
5. Da li postoji Kanban CLI/toolset i koje komande su dostupne.
6. Da li postoji Kanban baza; proveri veličinu/vreme izmene, ne menjaj je.
7. Koji toolset-i su uključeni za Discord na orchestrator profilu.
8. Postojeće profile role/description i instalirane skills.
9. Postojeće `review_dispatch`, `auto_decompose` i dispatcher opcije, ako su dostupne.

Koristi lokalni `hermes --help`, podkomandne `--help` izlaze i čitanje konfiguracije. Ne zaključuj iz web dokumentacije da je feature prisutan u lokalnoj verziji.

## Korak 2 — Plan minimalnih promena

Pre promene napiši kratku tabelu:

| Nalaz | Trenutno stanje | Potrebna promena | Rizik |
|---|---|---|---|

Ako je Kanban dostupan, nastavi. Ako nije, stani i pripremi kompatibilan plan; ne menjaj framework.

## Korak 3 — Backup i aktivacija Kanban-a

1. Napravi vremenski označen backup relevantnih konfiguracionih fajlova i postojećih skill direktorijuma. Ne kopiraj tajne u izveštaj.
2. Ako Kanban baza nedostaje, proveri dokumentovanu `hermes kanban init` komandu i njene lokalne help opcije; inicijalizuj samo ako je bezbedno i ako nema postojećih podataka.
3. Omogući `kanban` toolset za aktivni Discord orchestrator profil. Dokumentovani obrazac je `hermes -p <ACTIVE_PROFILE> tools enable kanban --platform discord`; prvo proveri lokalnu CLI sintaksu.
4. Ne uključuj toolset globalno svim profilima bez razloga.
5. Ako konfiguracija zahteva novu sesiju da bi se toolset učitao, otvori novu Discord konverzaciju posle potvrde izmene.
6. Osiguraj da postoji tačno jedan dispatcher owner (postojeći gateway). Ne startuj dodatni `hermes kanban daemon` ako gateway već dispatchuje.

## Korak 4 — Profili

Mapiraj postojeće profile na ove funkcionalne uloge:

- Orchestrator: jedini Discord ulaz i Kanban koordinator.
- Researcher: primarni izvori, dokumentacija, aktuelne činjenice.
- Analyst: sinteza, poređenje, tehničke odluke i rizici.
- Builder: konkretna implementacija u dodeljenom opsegu.
- Verifier: nezavisna provera kriterijuma, testova i dokaza.

Ne mora svaka uloga imati zaseban profil ako postojeći profil već kvalitetno pokriva ulogu. Počni sa 3–5 profila. Opisi profila moraju jasno iskazivati šta profil radi da bi Kanban usmeravanje bilo korisno.

## Korak 5 — Instalacija skill-ova

Pregledaj:

- `skills/hermes-kanban-orchestrator/SKILL.md`
- `skills/productive-team-worker/SKILL.md`
- `skills/evidence-review/SKILL.md`
- `skills/discord-workflow/SKILL.md`

Kopiraj ih u odgovarajuće Hermes skill kategorije pod aktivnim Hermes home-om (u skladu sa lokalnom strukturom, tipično `~/.hermes/skills/<category>/<skill-name>/SKILL.md`). Ne prepisuj postojeće skill-ove istih imena. Ako postoji konflikt, sačuvaj postojeći i prijavi ga.

Dodeli:

- orchestrator skill → Orchestrator profilu;
- worker skill → Researcher, Analyst i Builder profilima;
- evidence-review skill → Verifier profilu;
- discord-workflow skill → Orchestrator profilu.

Ako Hermes koristi drugačiji mehanizam instalacije/registracije, koristi lokalni zvanični mehanizam. Potvrdi da su skill-ovi vidljivi odgovarajućim profilima.

## Korak 6 — Provera Kanban mogućnosti

Proveri dostupnost i očekivano ponašanje:

- orchestrator može da vidi tablu i kreira zadatak;
- kartica može da se dodeli odgovarajućem profilu;
- zavisni zadatak čeka završetak roditelja;
- worker može da komentariše i preda sažetak/metadata;
- blocked/review statusi rade;
- gateway šalje notifikaciju o terminalnom ishodu u Discord sesiju koja je inicirala zadatak.

Ne pretpostavljaj da dashboard pristup znači da chat agent ima Kanban alate — proveri sam toolset.

## Korak 7 — End-to-end test

Koristi bezopasan test, bez izmene projekta i bez spoljnih objava:

1. U Discord-u pošalji orchestratoru zadatak: „Istraži zvaničnu Hermes dokumentaciju za Kanban i vrati tri proverene funkcije sa izvorima.“
2. Orchestrator napravi researcher karticu.
3. Nakon završetka, napravi verifier karticu sa zavisnošću od researcher kartice.
4. Verifier potvrdi da svaki nalaz ima zvaničan URL i da se ne tvrdi više od izvora.
5. Orchestrator objavi sažetak u Discord-u.

Proveri stvarni zapis u Kanban-u, worker handoff, zavisnost, verifier rezultat i Discord notifikaciju. Sačuvaj dokazne putanje/log reference, uz uklanjanje tajni.

## Korak 8 — Završni izveštaj

Dostavi:

- Hermes verziju i aktivni profil (bez tajni);
- postojeću i završnu konfiguraciju na nivou relevantnih opcija;
- profile i njihove uloge;
- instalirane skill putanje;
- potvrdu da je `kanban` aktivan u Discord toolset-u;
- dispatcher/gateway stanje;
- testni Kanban task ID-jeve i status svakog;
- tačan rezultat end-to-end testa;
- backup putanje;
- promene koje nisu urađene i razlog;
- preostale blokade/rizike.

Ne koristi „success“ ili „ready“ bez stvarnog prolaska end-to-end testa. Ako neki korak nije mogao biti proveren, jasno ga označi kao NEPROVEREN.
