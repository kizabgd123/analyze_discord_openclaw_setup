# 1. Uvod i Video Predavanje

## 1. Uvod i Video Predavanje

Dobrodošli u zvanični masterclass kurs: **Google ADK A2A Multi-Agent Sistemi 2026**.
Ovaj modul kombinuje autentični video tutorijal visoke rezolucije sa interaktivnim vežbama, fleš-karticama i simulacijama.

### Autentični Video Tutorijal
- **Naslov:** OpenClaw Tutorial for Beginners - Crash Course
- **Autor / Kanal:** Adrian Twarog
- **Optimalno Trajanje:** 07:58


### Ključni Ishodi Učenja (Learning Outcomes)
- **Ishod 1:** Savladavanje temeljnih mentalnih modela i mehanike (Google ADK A2A Multi-Agent Sistemi 2026).
- **Ishod 2:** Usvajanje praktičnih tehnika korak-po-korak bez oslanjanja na zastarele metode.
- **Ishod 3:** Prepoznavanje i eliminacija najčešćih grešaka u realnim scenarijima.
- **Ishod 4:** Provera stečenih kompetencija kroz praktični izazov i interaktivni kviz znanja.

### Vremenske Oznake Predavanja (Interaktivni Skok na Poglavlje)
Kliknite na vremenski marker u tekstu ili u traci ispod plejera za trenutan skok na traženi segment:
- `[00:00]` Uvod i postavljanje radnog okruženja
- `[02:30]` Ključni koncepti i mentalni model agenata
- `[05:15]` Korak-po-korak A2A demonstracija
- `[07:00]` Rezime i produkcijski saveti


---

# 2. Ključni Principi i Mehanika

U srcu Google ADK A2A sistema nije samo generisanje teksta, već **deterministička orkestracija**. Arhitektura se oslanja na četiri ključna mentalna modela:

**1. Stanje sesije kao jedinstveni izvor istine (`ctx.session.state`)**
Umesto da agenti razmenjuju neorganizovane poruke, sistem koristi tipiziranu magistralu podataka. Svaki agent (Researcher, Judge, Builder) čita i piše u zajednički objekat stanja. Ovo osigurava da `Lead Content Builder` ne može da generiše lekciju ako `Principal Researcher` nije prethodno popunio `research_findings` polje.

**2. Petlja istraživanja i audita (Research-Audit Loop)**
Sistem implementira strogu kontrolu kvaliteta. `Senior Judge Agent` ne daje samo sugestije, već deluje kao "gatekeeper". Ako nalazi ne dostignu prag od $\ge 7/10$ prema Pydantic šemi `JudgeFeedback`, `LoopAgent` automatski vraća proces na fazu istraživanja. Napredak je blokiran dok se kriterijumi tačnosti i dubine ne ispune.

**3. Hijerarhijsko opuštanje upita (Query Relaxation Hierarchy)**
Da bi se izbegli prazni rezultati pretrage, sistem primenjuje četiri nivoa pretrage:
*   **Nivo 1 (Striktan):** Specifičan tehnički entitet (npr. "Google ADK A2A Pydantic Validation").
*   **Nivo 2 (Tehnički):** Širi tehnički kontekst (npr. "Google ADK Multi-Agent Orchestration").
*   **Nivo 3 (Konceptualni):** Opšti koncept (npr. "LLM Agent Communication Protocols").
*   **Nivo 4 (Široki):** Domenska oblast (npr. "AI Agent Frameworks 2026").

**4. Harmonizacija teksta i medija**
Sistem odbacuje generičke AI slajdove. Umesto toga, koristi metapodatke iz autentičnih YouTube videa. Vremenske oznake $[mm:ss]$ služe kao sidra za tekstualni kurikulum, čime se postiže savršena sinhronizacija između onoga što korisnik čita i onoga što vidi na ekranu.

---

###

---

# 3. Korak-po-Korak Tehnika i Primena

Implementacija A2A sistema zahteva preciznu definiciju agenata i protokola. Ispod je kompletan tehnički okvir za inicijalizaciju sistema.

#### Tehnički Implementacioni Kod (Python/ADK)

```python
from google_adk import Agent, Session, types
from pydantic import BaseModel, Field
from typing import List, Optional

---

# 4. Česte Greške i Zablude

def run_masterclass_pipeline():
    session = Session()
    researcher = PrincipalResearcher()
    judge = SeniorJudge()
    
    # Research-Audit Loop
    while True:
        researcher.execute(session)
        result = judge.execute(session)
        if result.is_passed:
            break
        print(f"Audit failed: {result.improvement_suggestions}")

run_masterclass_pipeline()
```

**Biomehanika procesa:**
1. **Ekstrakcija:** `Head Entity Extraction` algoritam čisti šum iz upita.
2. **Filtriranje:** Video materijali se filtriraju po trajanju (12-18 min) kako bi se osigurala dubina bez gubitka pažnje.
3. **Strimovanje:** Napredak se emituje preko `FastAPI /api/chat_stream` za real-time frontend ažuriranje.

---

###

---

# 5. Praktični Izazov i Trening Plan

**Zadatak:** Kreirati automatizovani modul za temu "Implementacija SSE Strimovanja u A2A sistemu".

**Trening Plan:**
1. **Faza 1 (Istraživanje):** Konfigurišite `PrincipalResearcher` da pronađe 3 videa trajanja 12-18 min o SSE (Server-Sent Events).
2. **Faza 2 (Audit):** Podesite `SeniorJudge` da odbije svaki rezultat koji nema konkretan kod primer u videu (Score < 7).
3. **Faza 3 (Sastavljanje):** Povežite vremensku oznaku $[04:20]$ (gde se objašnjava FastAPI `EventSourceResponse`) sa tekstualnim objašnjenjem u lekciji.

**Rešenje (Checklist):**
- [x] `ctx.session.state['research_findings']` sadrži validne YouTube ID-eve.
- [x] `JudgeFeedback` je `is_passed = True`.
- [x] Tekst lekcije sadrži barem 3 vremenske oznake koje odgovaraju sadržaju videa.
- [x] Nema generisanih nepostojećih biblioteka.

---

###

---

# 6. Provera Znanja i Interaktivni Kviz

Pitanje 1: Šta predstavlja `ctx.session.state` u Google ADK A2A arhitekturi?
[ ] A) Privremeni keš za čuvanje slika
[x] B) Tipizirana magistrala za asinhronu razmenu podataka i jedinstveni izvor istine
[ ] C) Metoda za brže generisanje teksta
[ ] D) Baza podataka za skladištenje korisničkih lozinki
Objašnjenje: `ctx.session.state` osigurava konzistentnost informacija između različitih agenata, sprečavajući gubitak konteksta.

Pitanje 2: Koji je prag kvaliteta koji `Senior Judge Agent` zahteva da bi dozvolio napredak u Research-Audit Loop-u?
[ ] A) $\ge 5/10$
[ ] B) $\ge 9/10$
[x] C) $\ge 7/10$
[ ] D) Nema praga, samo kvalitativna ocena
Objašnjenje: Prag od 7/10 je definisan kao minimalni standard za domensku tačnost i dubinu pre prelaska na fazu kreiranja sadržaja.

Pitanje 3: Šta je primarni cilj "Hijerarhijskog opuštanja upita" (Query Relaxation Hierarchy)?
[ ] A) Ubrzanje rada procesora
[x] B) Eliminacija praznih rezultata pretrage kroz postepeno širenje pojmova
[ ] C) Smanjenje troškova API poziva
[ ] D) Automatski prevod upita na više jezika
Objašnjenje: Strategija omogućava sistemu da pronađe relevantne informacije čak i kada striktni tehnički termini ne vrate rezultate.

---

###

---

# 7. Brzi Priručnik i Rezime

**Kontrolna lista za Lead Content Builder-a:**
*   **Validacija:** Da li je `Zero-Simulation Mandate` poštovan? (Nema lažnih linkova).
*   **Konzistentnost:** Da li su vremenske oznake $[mm:ss]$ sinhronizovane sa videom?
*   **Kvalitet:** Da li je `Senior Judge` potvrdio status `pass`?
*   **Struktura:** Da li je korišćen `ctx.session.state` umesto direktnog slanja poruka?

**Rezime u 3 tačke:**
1. **Sistem:** Google ADK A2A 2026 eliminiše halucinacije kroz strogu validaciju i audit petlje.
2. **Metoda:** Tekst prati video, a ne obrnuto (Harmonizacija medija).
3. **Tehnika:** Pydantic šeme i Query Relaxation osiguravaju tehničku preciznost i dostupnost podataka.

---

**

## 🗂️ Interaktivne 3D Fleš-Kartice za Ponavljanje

**Kartica 1:**
- **Pojam:** **Zero-Simulation Mandate**
- **Definicija:** Stroga zabrana generisanja nepostojećih softverskih biblioteka, lažnih YouTube linkova ili simuliranih podataka.

**Kartica 2:**
- **Pojam:** **Research-Audit Loop**
- **Definicija:** Iterativni proces gde `Senior Judge Agent` blokira napredak dok istraživački nalazi ne dostignu prag kvaliteta $\ge 7/10$.

**Kartica 3:**
- **Pojam:** **ctx.session.state**
- **Definicija:** Centralni, tipizirani objekat koji služi kao jedinstveni izvor istine za sve agente u A2A sistemu.

**Kartica 4:**
- **Pojam:** **Query Relaxation Hierarchy**
- **Definicija:** Strategija pretraživanja u četiri nivoa (od striktnog do širokog) radi eliminacije praznih rezultata pretrage.
