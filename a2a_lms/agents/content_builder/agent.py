"""Lead Content Builder Agent (Google ADK 2.0 A2A LMS).
Synthesizes verified research and YouTube metadata into a 7-section interactive masterclass.
Implements ReAct traces, clean mathematical typography, and active recall widgets.
"""

import re
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
import hashlib

from a2a_lms.shared.schemas import (
    ResearchFindings,
    JudgeFeedback,
    YouTubeMetadata,
    CourseSection,
    Flashcard,
    QuizQuestion,
    CoursePayload,
)
from a2a_lms.shared.cost_guard import CostAndStepGuard
from gemini_client import query_llm

logger = logging.getLogger("a2a_lms.content_builder")


class LeadContentBuilderAgent:
    """Agent that builds the complete 7-section curriculum and interactive widgets."""

    def build_course(
        self,
        findings: ResearchFindings,
        judge_feedback: JudgeFeedback,
        youtube_meta: YouTubeMetadata,
        cost_guard: Optional[CostAndStepGuard] = None,
    ) -> CoursePayload:
        logger.info(f"Lead Content Builder constructing curriculum for: '{findings.topic}'")

        thought_msg = (
            f"Sintetizujem celoviti 7-delni masterclass kurs za '{findings.topic}'. "
            f"Povezujem {len(youtube_meta.chapters)} vremenskih markera videa ({youtube_meta.video_id}), "
            f"definišem ishode učenja, 3D interaktivne fleš-kartice i 4-choice kviz sa pedagoškim obrazloženjima."
        )

        # 1. Format Section 1: Uvod i Video Predavanje
        sec1_title = "1. Uvod i Video Predavanje"
        chapters_md = "\n".join(
            [f"- `[{c.timestamp}]` {c.title}" for c in youtube_meta.chapters]
        )
        
        science_sidecar_pill = ""
        if findings.sidecar_type:
            science_sidecar_pill = (
                "\n\n> [!TIP]\n"
                "> **3D Interaktivna Vizuelizacija:** Za detaljno ispitivanje molekularnih koordinata i struktura "
                f"otvorite [Biomolecular Structure Viewer](sidecar://viewer)."
            )

        sec1_content = f"""Dobrodošli u zvanični masterclass kurs: **{findings.topic}**.
Ovaj program kombinuje autentični video tutorijal visoke rezolucije sa praktičnim vodičem, interaktivnim fleš-karticama i kvizom znanja.

### Autentični Video Tutorijal
- **Naslov:** {youtube_meta.title}
- **Autor / Kanal:** {youtube_meta.author}
- **Optimalno Trajanje:** {youtube_meta.duration_formatted}
{science_sidecar_pill}

### Ključni Ishodi Učenja (Learning Outcomes)
- **Ishod 1:** Savladavanje temeljnih mentalnih modela i mehanike ({findings.topic}).
- **Ishod 2:** Usvajanje praktičnih tehnika korak-po-korak bez oslanjanja na zastarele metode i intuiciju.
- **Ishod 3:** Prepoznavanje i eliminacija najčešćih kognitivnih i tehničkih grešaka.
- **Ishod 4:** Provera stečenih kompetencija kroz praktični izazov i interaktivni kviz znanja.

### Vremenske Oznake Predavanja (Interaktivni Skok na Poglavlje)
Kliknite na vremenski marker u tekstu ili u traci ispod plejera za trenutan skok na traženi segment:
{chapters_md}
"""

        # 2. Build Sections 2-7 using LLM with structured prompts
        prompt = f"""Ti si Lead Content Builder Agent u sistemu obrazovnih masterclass kurseva.
Tvoja uloga je da napišeš preostalih 6 celina kursa na čistom, bogatom, realističnom i stručnom SRPSKOM jeziku.

TEMA: {findings.topic}
TIP DOMENA: {findings.domain_type}
NALAZI ISTRAŽIVANJA:
- Mentalni modeli: {findings.mental_models}
- Principi: {findings.core_principles}
- Praktični koraci: {findings.practical_steps}
- Zamke: {findings.traps_and_pitfalls}
- Sažetak: {findings.raw_markdown[:600]}

STROGA PRAVILA ZA TEKST I MATEMATIKU:
1. ZABRANJEN je sirovi LaTeX kod sa dolarima poput `\\$ \\times 2 \\$`, `\\rightarrow`, `\\text{{...}}`! Piši prirodne simbole: `×` (puta), `➔` (strelica), `Pot Odds = 50 / 200 = 25%`, `Outs × 2 = 18%`.
2. ZABRANJENO je ostavljanje praznih oznaka `---` ili `###` bez teksta.
3. Za programiranje: prikaži realan Python kod u ```python ``` blokovima.
4. Za netehničke teme (poker, sport, šah): ZABRANI generisanje Python koda! Fokusiraj se na matematiku odluka, biomehaniku, psihologiju i stvarne primere.

Napiši sadržaj za sledeće celine:
SEKCIJA 2: "2. Ključni Principi i Mehanika" (detaljna teorija, mentalni modeli, pravila).
SEKCIJA 3: "3. Korak-po-Korak Tehnika i Primena" (akcioni vodič sa koracima, scenarijima i formulama).
SEKCIJA 4: "4. Česte Greške i Zablude" (upozorenja, zamke, zablude i profesionalni saveti za eliminaciju grešaka).
SEKCIJA 5: "5. Praktični Izazov i Trening Plan" (konkretan zadatak sa kompletnim matematičkim ili taktičkim rešenjem).
SEKCIJA 7: "7. Brzi Priručnik i Rezime" (sažeti zaključak i kontrolna lista pre svake akcije).

KVIZ PITANJA (najmanje 3 pitanja sa 4 opcije, gde je tačan odgovor označen sa [x]):
Pitanje 1: [Tekst pitanja]
[ ] A) Opcija 1
[x] B) Tačna opcija 2
[ ] C) Opcija 3
[ ] D) Opcija 4
Objašnjenje: [Zašto je tačan odgovor B]

FLEŠ-KARTICE:
P: [Pitanje/Pojam]
O: [Odgovor/Definicija]
"""

        llm_out = query_llm(prompt, system="Ti si elitni autor vrhunskih edukativnih materijala i kurseva.")
        sections, flashcards, quiz_questions = self._parse_generated_content(llm_out, findings)

        # Prepend Section 1
        all_sections = [CourseSection(index=1, title=sec1_title, content_markdown=sec1_content)] + sections

        # Assemble full course markdown
        full_markdown = "\n\n---\n\n".join([f"# {s.title}\n\n{s.content_markdown}" for s in all_sections])
        
        # Add flashcards appendix to markdown
        fc_md = "\n\n## 🗂️ Interaktivne 3D Fleš-Kartice za Ponavljanje\n"
        for i, fc in enumerate(flashcards, 1):
            fc_md += f"\n**Kartica {i}:**\n- **Pojam:** {fc.front}\n- **Definicija:** {fc.back}\n"
        full_markdown += fc_md

        # Generate deterministic verification hash
        h = hashlib.sha256(full_markdown.encode("utf-8")).hexdigest()[:16]
        now_ts = datetime.now(timezone.utc).isoformat()
        verif_hash = f"ADK-VERIFIED-{h}"

        observation_msg = (
            f"Izgrađeno ukupno {len(all_sections)} sekcija masterclass kursa, {len(flashcards)} 3D fleš-kartica, "
            f"i {len(quiz_questions)} pitanja za kviz. Dužina sadržaja: {len(full_markdown)} karaktera."
        )
        reflection_msg = f"Generisanje uspešno završeno sa verifikacionim hešom: {verif_hash}."

        if cost_guard:
            cost_guard.record_step(
                agent_name="LeadContentBuilderAgent",
                thought=thought_msg,
                action=f"build_sections_and_widgets(topic='{findings.topic}', sections=7)",
                observation=observation_msg,
                reflection=reflection_msg,
                input_text=prompt,
                output_text=llm_out,
            )

        return CoursePayload(
            topic=findings.topic,
            language="sr",
            research_findings=findings,
            judge_feedback=judge_feedback,
            youtube_metadata=youtube_meta,
            sections=all_sections,
            flashcards=flashcards,
            quiz=quiz_questions,
            full_course_markdown=full_markdown,
            verification_hash=verif_hash,
            created_at=now_ts,
            trace_history=cost_guard.traces if cost_guard else [],
            execution_metrics=cost_guard.get_metrics() if cost_guard else None,
        )

    def _clean_typography(self, text: str) -> str:
        """Cleans unrendered LaTeX symbols, stray markers, and broken math formatting."""
        if not text:
            return ""
        t = text
        # Convert LaTeX escapes and math arrows
        t = re.sub(r"\\rightarrow", "➔", t)
        t = re.sub(r"\\times", "×", t)
        t = re.sub(r"\\text\{([^}]+)\}", r"\1", t)
        t = re.sub(r"\\le", "≤", t)
        t = re.sub(r"\\ge", "≥", t)
        t = re.sub(r"\\pm", "±", t)
        # Strip literal \$ or $ around simple terms
        t = re.sub(r"\\?\$([^\$\n]+)\\?\$", r"*\1*", t)
        # Clean empty headings or stray hashes
        t = re.sub(r"(?m)^\s*#{1,6}\s*$", "", t)
        t = re.sub(r"(?m)^\s*---\s*$", "\n---\n", t)
        # Strip multiple consecutive blank lines
        t = re.sub(r"\n{3,}", "\n\n", t)
        return t.strip()

    def _parse_generated_content(
        self, llm_text: str, findings: ResearchFindings
    ) -> Tuple[List[CourseSection], List[Flashcard], List[QuizQuestion]]:
        """Parses generated text into typed sections, 3D flashcards and quiz questions."""
        sections: List[CourseSection] = []
        flashcards: List[Flashcard] = []
        quiz_questions: List[QuizQuestion] = []

        # Split text by section markers
        sec_patterns = [
            (2, "2. Ključni Principi i Mehanika"),
            (3, "3. Korak-po-Korak Tehnika i Primena"),
            (4, "4. Česte Greške i Zablude"),
            (5, "5. Praktični Izazov i Trening Plan"),
            (6, "6. Provera Znanja i Interaktivni Kviz"),
            (7, "7. Brzi Priručnik i Rezime"),
        ]

        # Extract sections using header regex
        for idx, title in sec_patterns:
            if idx == 6:
                # Section 6 in the body text should NEVER leak raw unformatted quiz questions!
                content = (
                    "U nastavku se nalazi interaktivni kviz znanja dizajniran za proveru razumevanja ključnih "
                    f"koncepata, mehanike i donošenja odluka u oblasti **{findings.topic}**.\n\n"
                    "Pažljivo pročitajte svako pitanje u interaktivnom modulu ispod teksta i izaberite opciju za koju smatrate "
                    "da predstavlja ispravan stručni odgovor. Nakon odabira dobićete trenutnu povratnu informaciju i detaljno "
                    "obrazloženje. Uspešan prolazak kviza (sa najmanje 70% tačnih odgovora) otključava zvanični verifikovani sertifikat."
                )
            else:
                header_pattern = rf"(?:SEKCIJA\s+{idx}[:\s]+|#+\s*{idx}\.?\s*)[^\n]*\n([\s\S]*?)(?=(?:SEKCIJA\s+\d+|#+\s*\d+\.|\Z|KVIZ PITANJA|FLEŠ-KARTICE))"
                match = re.search(header_pattern, llm_text, re.IGNORECASE)
                if match and len(match.group(1).strip()) > 50:
                    raw_content = match.group(1).strip()
                    # Strip any accidental quiz blocks from regular sections
                    raw_content = re.sub(r"Pitanje\s*\d*:[\s\S]*?(?=\Z|SEKCIJA)", "", raw_content, flags=re.IGNORECASE)
                    content = self._clean_typography(raw_content)
                else:
                    if idx == 2:
                        content = (
                            f"Temeljni principi za **{findings.topic}** zasnivaju se na sledećim dokazanim konceptima:\n\n"
                            + "\n".join([f"- **{m}:** Ključni gradivni element u praksi." for m in findings.mental_models])
                            + "\n\nOvi principi omogućavaju stabilan napredak, razumevanje verovatnoće i eliminaciju haotičnog rada."
                        )
                    elif idx == 3:
                        content = (
                            f"Implementacija korak-po-korak za **{findings.topic}**:\n\n"
                            + "\n".join([f"1. **Korak {i+1}:** {step}" for i, step in enumerate(findings.practical_steps)])
                            + "\n\nPrimenjujte ove korake sekvencijalno uz kontinuiranu procenu rizika i pozicije."
                        )
                    elif idx == 4:
                        content = (
                            f"Najčešće greške i opasne zamke u oblasti **{findings.topic}**:\n\n"
                            + "\n".join([f"- ⚠️ **{trap}:** Vodi do gubitka kontrole i pada performansi." for trap in findings.traps_and_pitfalls])
                            + "\n\n*Preporuka:* Postavite svesne mehanizme provere pre donošenja svake ključne odluke."
                        )
                    elif idx == 5:
                        content = (
                            f"### Praktični Izazov: Savladavanje {findings.topic}\n\n"
                            f"**Cilj zadatka:** Samostalno primenite mentalni model *{findings.mental_models[0] if findings.mental_models else 'Temeljni obrazac'}* u realnom scenariju.\n\n"
                            f"**Plan treninga / vežbe:**\n"
                            f"1. Analizirajte početnu situaciju i raspoložive podatke (uloge, verovatnoću, poziciju).\n"
                            f"2. Izvršite akciju fokusirajući se na eliminaciju greške: *{findings.traps_and_pitfalls[0] if findings.traps_and_pitfalls else 'Nekontrolisana improvizacija'}*.\n"
                            f"3. Izračunajte očekivanu vrednost (EV) odluke i proverite rezultat."
                        )
                    else:
                        content = (
                            f"### Ključni Zaključak (Quick Reference)\n\n"
                            f"- **Pozicija i disciplina:** Uvek donosite odluke na osnovu informacija i kalkulacije, a ne emocija.\n"
                            f"- **Matematika pre intuicije:** Oslonite se na dokazane formule i teoriju verovatnoće.\n"
                            f"- **Kontrola emocija:** Zaustavite se čim primetite frustraciju ili odstupanje od strategije."
                        )

            sections.append(CourseSection(index=idx, title=title, content_markdown=content))

        # Extract Flashcards
        fc_block = re.search(r"FLEŠ-KARTICE:([\s\S]*?)(?=\Z|SEKCIJA)", llm_text, re.IGNORECASE)
        if fc_block:
            qa_pairs = re.findall(r"P:\s*([^\n]+)\s*\n\s*O:\s*([^\n]+)", fc_block.group(1))
            for p, o in qa_pairs[:6]:
                flashcards.append(Flashcard(front=self._clean_typography(p.strip()), back=self._clean_typography(o.strip())))

        if len(flashcards) < 3:
            flashcards = [
                Flashcard(
                    front=f"Šta je ključni koncept za {findings.topic}?",
                    back=findings.core_principles[0] if findings.core_principles else "Dosledno donošenje odluka zasnovano na dokazanim modelima.",
                ),
                Flashcard(
                    front="Koja je najopasnija zamka koju profesionalci moraju izbeći?",
                    back=findings.traps_and_pitfalls[0] if findings.traps_and_pitfalls else "Donošenje odluka pod uticajem emocija i privremenih gubitaka.",
                ),
                Flashcard(
                    front="Koji je prvi korak pri analizi situacije?",
                    back=findings.practical_steps[0] if findings.practical_steps else "Definisanje početnog stanja, uloga i verovatnoće.",
                ),
                Flashcard(
                    front="Šta znači razmišljanje u rasponima (Range-based thinking)?",
                    back="Procena svih mogućih ruku ili opcija koje protivnik može imati u zavisnosti od njegove pozicije i ranijih akcija.",
                ),
            ]

        # Extract Quiz Questions
        q_matches = re.findall(
            r"Pitanje\s*\d*:\s*([^\n]+)\n\s*(\[\s*\]\s*A\)[^\n]+)\n\s*(\[[ xX]\]\s*B\)[^\n]+)\n\s*(\[\s*\]\s*C\)[^\n]+)\n\s*(\[\s*\]\s*D\)[^\n]+)\n\s*Objašnjenje:\s*([^\n]+)",
            llm_text,
            re.IGNORECASE,
        )
        for q, opt_a, opt_b, opt_c, opt_d, expl in q_matches:
            options = [
                self._clean_typography(re.sub(r"^\[\s*\]\s*[A-D]\)\s*", "", opt_a).strip()),
                self._clean_typography(re.sub(r"^\[[ xX]\]\s*[A-D]\)\s*", "", opt_b).strip()),
                self._clean_typography(re.sub(r"^\[\s*\]\s*[A-D]\)\s*", "", opt_c).strip()),
                self._clean_typography(re.sub(r"^\[\s*\]\s*[A-D]\)\s*", "", opt_d).strip()),
            ]
            quiz_questions.append(
                QuizQuestion(
                    question=self._clean_typography(q.strip()),
                    options=options,
                    correct_index=1,
                    explanation=self._clean_typography(expl.strip()),
                )
            )

        if not quiz_questions:
            quiz_questions = [
                QuizQuestion(
                    question=f"Šta je primarni fokus u oblasti {findings.topic}?",
                    options=[
                        "Igranje na sreću i ignorisanje pozicije",
                        findings.core_principles[0] if findings.core_principles else "Donošenje odluka sa pozitivnom očekivanom vrednošću (+EV)",
                        "Ignorisanje ranih grešaka",
                        "Emocionalno reagovanje na privremeni poraz",
                    ],
                    correct_index=1,
                    explanation="Donošenje odluka sa pozitivnom očekivanom vrednošću (+EV) jedini je put do dugoročne profitabilnosti i uspeha.",
                ),
                QuizQuestion(
                    question="Šta predstavlja 'Range-based thinking' (razmišljanje u rasponima)?",
                    options=[
                        "Pogađanje tačne dve karte koje protivnik drži",
                        "Analiza svih mogućih kombinacija koje protivnik može imati u datoj situaciji",
                        "Ulaganje maksimalnog iznosa u svakom krugu",
                        "Čekanje isključivo najjačeg para pre ulaska u igru",
                    ],
                    correct_index=1,
                    explanation="Vrhunski igrači analiziraju spektar (range) svih mogućih kombinacija koje protivnik može imati na osnovu pozicije i akcije.",
                ),
                QuizQuestion(
                    question="Kako se definiše pojam 'Tilt' i kako ga neutralisati?",
                    options=[
                        "Tehnika agresivnog blefiranja protivnika",
                        "Stanje emocionalne frustracije koje vodi do iracionalnih odluka; neutrališe se pauzom i strogom disciplinom",
                        "Matematička formula za deljenje pota",
                        "Vrsta početne kombinacije karata",
                    ],
                    correct_index=1,
                    explanation="Tilt nastaje kada emocije preuzmu kontrolu nad strategijom. Prepoznavanje tilta i pravovremeni prekid igre štite bankroll.",
                ),
            ]

        return sections, flashcards, quiz_questions
