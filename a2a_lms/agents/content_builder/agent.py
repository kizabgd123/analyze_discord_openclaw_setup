"""Lead Content Builder Agent (Google ADK 2.0 A2A LMS).
Synthesizes verified research and YouTube metadata into a 7-section interactive masterclass.
"""

import re
import json
import logging
from typing import List, Dict, Any, Tuple
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
from gemini_client import query_llm

logger = logging.getLogger("a2a_lms.content_builder")


class LeadContentBuilderAgent:
    """Agent that builds the complete 7-section curriculum and interactive widgets."""

    def build_course(
        self,
        findings: ResearchFindings,
        judge_feedback: JudgeFeedback,
        youtube_meta: YouTubeMetadata,
    ) -> CoursePayload:
        logger.info(f"Lead Content Builder constructing curriculum for: '{findings.topic}'")

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
            verification_hash=f"ADK-VERIFIED-{h}",
            created_at=now_ts,
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

        # Extract flashcards block first if present
        fc_block = ""
        if "FLEŠ-KARTICE:" in llm_text:
            parts = llm_text.split("FLEŠ-KARTICE:")
            llm_text = parts[0]
            fc_block = parts[1]

        # Parse flashcards
        fc_pairs = re.findall(r"P:\s*([^\n\r]+)[\n\r]+\s*O:\s*([^\n\r]+)", fc_block)
        for q, a in fc_pairs:
            flashcards.append(Flashcard(front=q.strip(), back=a.strip()))

        if not flashcards:
            # Fallback flashcards from mental models and principles
            for model in findings.mental_models[:3]:
                flashcards.append(Flashcard(front=f"Šta podrazumeva {model}?", back=f"Temeljni koncept koji definiše {findings.topic}."))
            if findings.traps_and_pitfalls:
                flashcards.append(Flashcard(front="Koja je glavna zabluda?", back=findings.traps_and_pitfalls[0]))

        # Split sections
        for idx, title in sec_patterns:
            header_regex = re.compile(rf"(?:##\s*|#\s*)?{idx}\.\s*[^\n\r]+", re.IGNORECASE)
            match = header_regex.search(llm_text)
            content = ""
            if match:
                start_pos = match.end()
                # Find next section or end
                next_match = None
                for next_idx, _ in sec_patterns:
                    if next_idx > idx:
                        nm = re.compile(rf"(?:##\s*|#\s*)?{next_idx}\.\s*[^\n\r]+", re.IGNORECASE).search(llm_text, start_pos)
                        if nm:
                            next_match = nm
                            break
                end_pos = next_match.start() if next_match else len(llm_text)
                content = llm_text[start_pos:end_pos].strip()

            if not content:
                content = f"Detaljna razrada teme {title} u domenu {findings.topic}."
            sections.append(CourseSection(index=idx, title=title, content_markdown=content))

        # Parse Quiz Questions from Section 6
        sec6_text = next((s.content_markdown for s in sections if s.index == 6), "")
        quiz_matches = re.finditer(
            r"Pitanje\s*\d*:\s*([^\n\r]+)[\n\r]+"
            r"\[([ xX])\]\s*A\)\s*([^\n\r]+)[\n\r]+"
            r"\[([ xX])\]\s*B\)\s*([^\n\r]+)[\n\r]+"
            r"\[([ xX])\]\s*C\)\s*([^\n\r]+)[\n\r]+"
            r"\[([ xX])\]\s*D\)\s*([^\n\r]+)[\n\r]+"
            r"(?:Objašnjenje:\s*([^\n\r]+))?",
            sec6_text,
        )

        for m in quiz_matches:
            q_txt = m.group(1).strip()
            ch_a, opt_a = m.group(2).lower(), m.group(3).strip()
            ch_b, opt_b = m.group(4).lower(), m.group(5).strip()
            ch_c, opt_c = m.group(6).lower(), m.group(7).strip()
            ch_d, opt_d = m.group(8).lower(), m.group(9).strip()
            expl = m.group(10).strip() if m.group(10) else "Tačan odgovor prema zvaničnoj specifikaciji."

            corr = 0
            if "x" in ch_b:
                corr = 1
            elif "x" in ch_c:
                corr = 2
            elif "x" in ch_d:
                corr = 3

            quiz_questions.append(
                QuizQuestion(
                    question=q_txt,
                    options=[opt_a, opt_b, opt_c, opt_d],
                    correct_index=corr,
                    explanation=expl,
                )
            )

        if not quiz_questions:
            # Deterministic default quiz question
            quiz_questions.append(
                QuizQuestion(
                    question=f"Koji je primarni cilj učenja teme {findings.topic}?",
                    options=[
                        "Potpuno razumevanje principa i praktična primena bez prečica",
                        "Korišćenje zastarelih sintetičkih alata",
                        "Nasumično testiranje bez evaluacije",
                        "Isključivo teorijsko memorisanje bez vežbi"
                    ],
                    correct_index=0,
                    explanation="Temeljno savladavanje gradiva zahteva aktivno učenje i validiranu primenu."
                )
            )

        return sections, flashcards, quiz_questions
