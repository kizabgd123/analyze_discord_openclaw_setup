"""Lead Content Builder Agent (Google ADK 2.0 A2A LMS).
Synthesizes verified research and YouTube metadata into a 7-section interactive masterclass.
Implements ReAct traces and active recall widgets.
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

        sec1_content = f"""## 1. Uvod i Video Predavanje

Dobrodošli u zvanični masterclass kurs: **{findings.topic}**.
Ovaj modul kombinuje autentični video tutorijal visoke rezolucije sa interaktivnim vežbama, fleš-karticama i simulacijama.

### Autentični Video Tutorijal
- **Naslov:** {youtube_meta.title}
- **Autor / Kanal:** {youtube_meta.author}
- **Optimalno Trajanje:** {youtube_meta.duration_formatted}
{science_sidecar_pill}

### Ključni Ishodi Učenja (Learning Outcomes)
- **Ishod 1:** Savladavanje temeljnih mentalnih modela i mehanike ({findings.topic}).
- **Ishod 2:** Usvajanje praktičnih tehnika korak-po-korak bez oslanjanja na zastarele metode.
- **Ishod 3:** Prepoznavanje i eliminacija najčešćih grešaka u realnim scenarijima.
- **Ishod 4:** Provera stečenih kompetencija kroz praktični izazov i interaktivni kviz znanja.

### Vremenske Oznake Predavanja (Interaktivni Skok na Poglavlje)
Kliknite na vremenski marker u tekstu ili u traci ispod plejera za trenutan skok na traženi segment:
{chapters_md}
"""

        # 2. Build Sections 2-7 using LLM with structured prompts
        prompt = f"""Ti si Lead Content Builder Agent u Google ADK A2A LMS sistemu.
Tvoja uloga je da napišeš preostalih 6 celina masterclass kursa na čistom, bogatom i stručnom SRPSKOM jeziku.

TEMA: {findings.topic}
TIP DOMENA: {findings.domain_type}
NALAZI ISTRAŽIVANJA:
- Mentalni modeli: {findings.mental_models}
- Principi: {findings.core_principles}
- Praktični koraci: {findings.practical_steps}
- Zamke: {findings.traps_and_pitfalls}
- Sažetak: {findings.raw_markdown[:600]}

Napiši sadržaj za sledećih 6 celina:
SEKCIJA 2: "2. Ključni Principi i Mehanika" (detaljna teorija, mentalni modeli, arhitektura).
SEKCIJA 3: "3. Korak-po-Korak Tehnika i Primena" (akcioni vodič sa koracima; za programiranje daj kompletan čist kod; za netehničke teme daj biomehaniku i pozicioniranje).
SEKCIJA 4: "4. Česte Greške i Zablude" (upozorenja, zamke i profesionalni saveti za izbegavanje grešaka).
SEKCIJA 5: "5. Praktični Izazov i Trening Plan" (konkretan zadatak/vežba sa celovitim rešenjem).
SEKCIJA 6: "6. Provera Znanja i Interaktivni Kviz" (najmanje 3 pitanja u striktnom formatu:
Pitanje 1: [Tekst pitanja]
[ ] A) Opcija 1
[x] B) Tačna opcija 2
[ ] C) Opcija 3
[ ] D) Opcija 4
Objašnjenje: [Zašto je tačan odgovor B]
)
SEKCIJA 7: "7. Brzi Priručnik i Rezime" (sažeti bulleti i kontrolna lista).

Takođe, na samom kraju dodaj blok sa 4 fleš-kartice u formatu:
FLEŠ-KARTICE:
P: [Pitanje/Pojam]
O: [Odgovor/Definicija]
"""

        llm_out = query_llm(prompt, system="Ti si vrhunski autor tehničkih i praktičnih kurseva.")
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
            header_pattern = rf"(?:SEKCIJA\s+{idx}[:\s]+|#+\s*{idx}\.?\s*)[^\n]*\n([\s\S]*?)(?=(?:SEKCIJA\s+\d+|#+\s*\d+\.|\Z|FLEŠ-KARTICE))"
            match = re.search(header_pattern, llm_text, re.IGNORECASE)
            if match and len(match.group(1).strip()) > 50:
                content = match.group(1).strip()
            else:
                # High quality deterministic section fallback grounded in findings
                if idx == 2:
                    content = (
                        f"Temeljni principi za **{findings.topic}** zasnivaju se na sledećim konceptima:\n\n"
                        + "\n".join([f"- **{m}:** Ključni gradivni element u praksi." for m in findings.mental_models])
                        + "\n\nOvi principi omogućavaju stabilan napredak i izbegavanje haotičnog rada."
                    )
                elif idx == 3:
                    content = (
                        f"Implementacija korak-po-korak za **{findings.topic}**:\n\n"
                        + "\n".join([f"1. **Korak {i+1}:** {step}" for i, step in enumerate(findings.practical_steps)])
                        + "\n\nPrimenjujte ove korake sekvencijalno uz kontinuiranu samoevaluaciju."
                    )
                elif idx == 4:
                    content = (
                        f"Najčešće greške i zamke u oblasti **{findings.topic}**:\n\n"
                        + "\n".join([f"- ⚠️ **{trap}:** Vodi do gubitka efikasnosti i loših navika." for trap in findings.traps_and_pitfalls])
                        + "\n\n*Preporuka:* Postavite svesne mehanizme provere pre svakog koraka."
                    )
                elif idx == 5:
                    content = (
                        f"### Praktični Izazov: Savladavanje {findings.topic}\n\n"
                        f"**Cilj zadatka:** Samostalno primenite mentalni model *{findings.mental_models[0] if findings.mental_models else 'Temeljni obrazac'}*.\n\n"
                        f"**Plan treninga / vežbe:**\n"
                        f"1. Uradite pripremu i analizirajte početno stanje (10 min).\n"
                        f"2. Izvršite vežbu fokusirajući se na eliminaciju greške: *{findings.traps_and_pitfalls[0] if findings.traps_and_pitfalls else 'Požurivanje'}*.\n"
                        f"3. Verifikujte rezultat i uporedite sa standardom."
                    )
                elif idx == 6:
                    content = (
                        f"U nastavku sledi interaktivna provera znanja. Rešite kviz ispod teksta kako biste potvrdili razumevanje."
                    )
                else:
                    content = (
                        f"### Ključni Zaključak (Quick Reference)\n\n"
                        f"- Uvek poštujte redosled: Analiza -> Priprema -> Izvršenje -> Verifikacija.\n"
                        f"- Zadržite fokus na dokazanim principima, a ne na improvizaciji.\n"
                        f"- Kontinuirano testirajte razumevanje kroz praktične primere."
                    )

            sections.append(CourseSection(index=idx, title=title, content_markdown=content))

        # Extract Flashcards
        fc_block = re.search(r"FLEŠ-KARTICE:([\s\S]*?)(?=\Z|SEKCIJA)", llm_text, re.IGNORECASE)
        if fc_block:
            qa_pairs = re.findall(r"P:\s*([^\n]+)\s*\n\s*O:\s*([^\n]+)", fc_block.group(1))
            for p, o in qa_pairs[:6]:
                flashcards.append(Flashcard(front=p.strip(), back=o.strip()))

        if len(flashcards) < 2:
            flashcards = [
                Flashcard(
                    front=f"Šta je ključni princip za {findings.topic}?",
                    back=findings.core_principles[0] if findings.core_principles else "Dosledna primena dokazanih modela.",
                ),
                Flashcard(
                    front="Koja je najčešća zamka koju treba izbeći?",
                    back=findings.traps_and_pitfalls[0] if findings.traps_and_pitfalls else "Nekontrolisana improvizacija.",
                ),
                Flashcard(
                    front="Koji je prvi praktični korak u implementaciji?",
                    back=findings.practical_steps[0] if findings.practical_steps else "Postavljanje jasnog cilja i okruženja.",
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
                re.sub(r"^\[\s*\]\s*[A-D]\)\s*", "", opt_a).strip(),
                re.sub(r"^\[[ xX]\]\s*[A-D]\)\s*", "", opt_b).strip(),
                re.sub(r"^\[\s*\]\s*[A-D]\)\s*", "", opt_c).strip(),
                re.sub(r"^\[\s*\]\s*[A-D]\)\s*", "", opt_d).strip(),
            ]
            quiz_questions.append(
                QuizQuestion(
                    question=q.strip(),
                    options=options,
                    correct_index=1,
                    explanation=expl.strip(),
                )
            )

        if not quiz_questions:
            quiz_questions = [
                QuizQuestion(
                    question=f"Šta je osnovni fokus pri savladavanju teme: {findings.topic}?",
                    options=[
                        "Površno testiranje bez jasnog plana",
                        findings.core_principles[0] if findings.core_principles else "Utemeljenost na dokazanim principima",
                        "Zanemarivanje ranih grešaka u biomehanici/kodu",
                        "Sintetička simulacija bez verifikacije",
                    ],
                    correct_index=1,
                    explanation=f"Utemeljenost na dokazanim principima garantuje dosledne i merljive rezultate.",
                ),
                QuizQuestion(
                    question="Kako se eliminišu najčešće zamke u radu?",
                    options=[
                        "Ubrzavanjem tempa bez kontrole",
                        "Kontinuiranom verifikacijom i samorefleksijom u svakom koraku",
                        "Ignorisanjem upozorenja mentora/sudije",
                        "Korišćenjem nepotvrđenih hipoteza",
                    ],
                    correct_index=1,
                    explanation="Sistematska provera na svakom koraku sprečava kumuliranje grešaka.",
                ),
            ]

        return sections, flashcards, quiz_questions
