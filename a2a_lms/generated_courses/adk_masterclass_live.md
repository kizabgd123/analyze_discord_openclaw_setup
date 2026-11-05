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

Sistem funkcioniše kroz četiri specijalizovane uloge:
1.  **Principal Researcher:** Koristi `GoogleSearch Grounding` za ekstrakciju činjeničnih podataka.
2.  **Senior Judge:** Validira podatke koristeći **Pydantic šeme** (npr. `JudgeFeedback` klasa) kako bi osigurao objektivnost.

---

# 3. Korak-po-Korak Tehnika i Primena

Detaljna razrada teme 3. Korak-po-Korak Tehnika i Primena u domenu Google ADK A2A Multi-Agent Sistemi 2026.

---

# 4. Česte Greške i Zablude

---

### SEKCIJA 3: Korak-po-Korak Tehnika i Primena
**Implementacija A2A Multi-Agent sistema**

Za implementaciju ovog sistema, fokusiramo se na Python okruženje sa Pydantic validacijom i integracijom Google API-ja.

#### Tehnički vodič za implementaciju:

**Korak 1: Definisanje Pydantic šeme za audit**
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class JudgeFeedback(BaseModel):
    score: int = Field(..., ge=1, le=10, description="Kvalitet istraživanja od 1 do 10")
    missing_points: List[str] = Field(default=[], description="Lista nedostajućih informacija")
    is_approved: bool = Field(..., description="Da li sadržaj prolazi prag od 7/10")
    suggestions: Optional[str] = None
```

**Korak 2: Implementacija Head Entity Extraction-a za YouTube API**
Da bismo izbegli prazne rezultate, čistimo upite pre slanja:
```python
def clean_youtube_query(raw_title: str) -> str:
    # Uklanjanje šuma (npr. "Detaljan vodič za...", "Masterclass o...")
    noise_words = ["detaljan vodič", "masterclass", "tutorial", "kako koristiti"]
    query = raw_title.lower()
    for word in noise_words:
        query = query.replace(word, "")
    return query.strip()

# Primer: "Detaljan vodič za Google ADK A2A" -> "Google ADK A2A"
```

**Korak 3: SSE Strimovanje i HTML5 Sinhronizacija**
Za interaktivni plejer, koristimo `postMessage` API kako bi tekstualni modul znao tačno koji deo videa se prikazuje:
```javascript
// Frontend sinhronizacija
window.addEventListener("message", (event) => {
    if (event.data.type === "YOUTUBE_TIMESTAMP") {
        player.seekTo(event.data.seconds);
        highlightTextSection(event.data.sectionId);
    }
});
```

---

### SEKCIJA 4: Česte Greške i Zablude
**Analiza zamki i profesionalni saveti**

U radu sa Multi-Agent sistemima, najopasnije su greške koje izgledaju kao uspeh (halucinacije koje zvuče ubedljivo).

1.  **Zamka "Ukrašenih Naslova":** Slanje naslova poput *"Vrhunski vodič za napredne koncepte A2A sistema"* u YouTube API često vraća nula rezultata. 
    *   **Savet:** Koristite samo ključne imenice i tehničke termine.
2.  **Kognitivni Razmak (Cognitive Gap):** Generisanje teksta lekcije nezavisno od pretrage videa. Rezultat je situacija gde tekst objašnjava koncept X, a video prikazuje koncept Y.
    *   **Savet:** Video metapodaci moraju biti deo `ctx.session.state` pre nego što Content Builder započne pisanje.
3.  **Simulacija Materijala:** Kreiranje "veštačkih slajdova" ili nepostojećih URL-ova.
    *   **Savet:** Strogo primenjujte **Zero-Simulation Mandate**. Ako API ne vrati validan link, sistem mora prijaviti nedostatak resursa, a ne izmisliti ga.

---

### SEKCIJA 5: Praktični Izazov i Trening Plan
**Zadatak: Izgradnja "Mini-A2A" Modula**

**Izazov:** Kreirajte automatizovani tok koji istražuje temu "Google Gemini 1.5 Pro Context Window", validira podatke i pronalazi jedan embed-abilan YouTube video.

**Trening Plan:**
1.  **Faza 1 (Istraživanje):** Konfigurišite `Principal Researcher` da izvuče 3 ključne činjenice o 2M token prozoru.
2.  **Faza 2 (Audit):** Kreirajte `JudgeFeedback` instancu. Ako je score < 7, vratite agenta na Fazu 1.
3.  **Faza 3 (Integracija):** Primenite `clean_youtube_query` i povežite video ID sa tekstom.

**Rešenje (Checklist):**
- [ ] Da li je `ctx.session.state` korišćen za prenos podataka?
- [ ] Da li je Pydantic šema validirala ocenu?
- [ ] Da li je YouTube link stvaran i funkcionalan (embeddable=true)?
- [ ] Da li je izbegnuta robotska sinteza govora u finalnom izlazu?

---

### SEKCIJA 6: Provera Znanja i Interaktivni Kviz

Pitanje 1: Šta je primarna svrha `ctx.session.state` objekta u A2A sistemu?
[ ] A) Brže renderovanje HTML stranica
[x] B) Služenje kao jedinstveni izvor istine za asinhronu razmenu podataka
[ ] C) Zamena za Google Search API
[ ] D) Skladištenje korisničkih lozinki
Objašnjenje: `ctx.session.state` eliminiše gubitak konteksta tako što omogućava svim agentima pristup istom, strogo tipiziranom setu podataka.

Pitanje 2: Koji mehanizam sprečava generisanje sadržaja na osnovu neproverenih podataka?
[ ] A) Head Entity Extraction
[ ] B) SSE Strimovanje
[x] C) Research-Audit Loop (RAL)
[ ] D) Query Relaxation Hierarchy
Objašnjenje: RAL blokira napredak kursa dok Senior Judge Agent ne potvrdi da je kvalitet istraživanja $\ge 7/10$.

Pitanje 3: Šta predstavlja kršenje "Zero-Simulation Mandate" principa?
[ ] A) Korišćenje engleskog jezika u upitima
[x] B) Generisanje nepostojećih URL-ova ili veštačkih slajdova
[ ] C) Primena Pydantic validacije
[ ] D) Korišćenje YouTube API v3
Objašnjenje: Zero-Simulation Mandate strogo zabranjuje bilo koji oblik simuliranog ili izmišljenog sadržaja radi očuvanja integriteta sistema.

---

### SEKCIJA 7: Brzi Priručnik i Rezime

**Kontrolna lista za implementaciju:**
*   [ ] **Arhitektura:** Da li su definisane sve 4 uloge (Researcher, Judge, Loop, Builder)?
*   [ ] **Validacija:** Da li svaki prelazak faze prolazi kroz Pydantic `JudgeFeedback`?
*   [ ] **Pretraga:** Da li se koristi *Query Relaxation* za izbegavanje praznih rezultata?
*   [ ] **Sadržaj:** Da li je primenjen *Zero-Simulation Mandate* (nema lažnih linkova)?
*   [ ] **UX:** Da li su video i tekst sinhronizovani putem `postMessage` API-ja?

**Ključni zaključak:** Google ADK A2A 2026 nije samo alat za generisanje teksta, već sistem za **garantovanu tačnost** kroz iterativni audit i strogu tehničku validaciju.

---

**

---

# 5. Praktični Izazov i Trening Plan

Detaljna razrada teme 5. Praktični Izazov i Trening Plan u domenu Google ADK A2A Multi-Agent Sistemi 2026.

---

# 6. Provera Znanja i Interaktivni Kviz

Detaljna razrada teme 6. Provera Znanja i Interaktivni Kviz u domenu Google ADK A2A Multi-Agent Sistemi 2026.

---

# 7. Brzi Priručnik i Rezime

Detaljna razrada teme 7. Brzi Priručnik i Rezime u domenu Google ADK A2A Multi-Agent Sistemi 2026.

## 🗂️ Interaktivne 3D Fleš-Kartice za Ponavljanje

**Kartica 1:**
- **Pojam:** **Zero-Simulation Mandate**
- **Definicija:** Stroga zabrana generisanja nepostojećih linkova, biblioteka ili veštačkih materijala; svaki element mora biti realan i verifikovan.

**Kartica 2:**
- **Pojam:** **Research-Audit Loop (RAL)**
- **Definicija:** Iterativni proces gde Senior Judge Agent blokira produkciju sadržaja dok istraživanje ne dostigne prag kvaliteta $\ge 7/10$.

**Kartica 3:**
- **Pojam:** **Query Relaxation Hierarchy**
- **Definicija:** Strategija postepenog širenja kriterijuma pretrage (od striktnog ka širem) kako bi se izbegli prazni odgovori API-ja.

**Kartica 4:**
- **Pojam:** **`ctx.session.state`**
- **Definicija:** Strogo tipiziran objekat koji služi kao jedinstveni izvor istine (SSOT) za razmenu podataka između agenata.
