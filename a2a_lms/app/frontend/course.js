/**
 * Google ADK A2A LMS Client Logic (2026).
 * Handles video seek synchronization, 3D flashcards, quiz evaluation,
 * strict certificate score gating, and ReAct traces rendering.
 */

// Global State
let currentCourseData = null;
let quizScore = 0;
let questionsAnswered = 0;

document.addEventListener("DOMContentLoaded", () => {
    initVideoPlayerControls();
    initFlashcards();
    initQuizEngine();
    initCertificateModal();
    loadCourseFromStorage();
});

/**
 * 1. Masterclass Video Player & HTML5 postMessage Seeking
 */
function initVideoPlayerControls() {
    document.addEventListener("click", (e) => {
        const target = e.target.closest(".chapter-chip, .inline-chapter-pill");
        if (!target) return;

        const seconds = parseInt(target.getAttribute("data-seconds"), 10);
        if (isNaN(seconds)) return;

        seekVideoTo(seconds);

        // Update active class
        document.querySelectorAll(".chapter-chip").forEach(el => el.classList.remove("active"));
        if (target.classList.contains("chapter-chip")) {
            target.classList.add("active");
        }
    });
}

function seekVideoTo(seconds) {
    const iframe = document.querySelector("#masterclass-iframe");
    if (!iframe || !iframe.contentWindow) return;

    iframe.contentWindow.postMessage(JSON.stringify({
        event: "command",
        func: "seekTo",
        args: [seconds, true]
    }), "*");

    iframe.contentWindow.postMessage(JSON.stringify({
        event: "command",
        func: "playVideo",
        args: []
    }), "*");

    console.log(`[LMS Video Player] Seeked to: ${seconds}s`);
}

/**
 * 2. Interactive 3D Active Recall Flashcards
 */
function initFlashcards() {
    document.addEventListener("click", (e) => {
        const card = e.target.closest(".flip-card");
        if (!card) return;
        card.classList.toggle("flipped");
    });
}

/**
 * 3. Robust Universal Quiz Engine & Strict Score Gating
 */
function initQuizEngine() {
    document.addEventListener("click", (e) => {
        const optionBtn = e.target.closest(".quiz-option-btn");
        if (!optionBtn) return;

        const card = optionBtn.closest(".quiz-question-card");
        if (!card || card.getAttribute("data-answered") === "true") return;

        card.setAttribute("data-answered", "true");
        questionsAnswered++;

        const isCorrect = optionBtn.getAttribute("data-correct") === "true";
        const feedbackDiv = card.querySelector(".quiz-feedback");

        if (isCorrect) {
            optionBtn.classList.add("correct");
            quizScore++;
            if (feedbackDiv) {
                feedbackDiv.style.display = "block";
                feedbackDiv.style.background = "rgba(34, 197, 94, 0.15)";
                feedbackDiv.style.color = "#86efac";
                feedbackDiv.innerHTML = `<strong>Tačno!</strong> ${optionBtn.getAttribute("data-explanation") || ""}`;
            }
        } else {
            optionBtn.classList.add("wrong");
            // Highlight the correct option
            const correctBtn = card.querySelector(".quiz-option-btn[data-correct='true']");
            if (correctBtn) correctBtn.classList.add("correct");

            if (feedbackDiv) {
                feedbackDiv.style.display = "block";
                feedbackDiv.style.background = "rgba(239, 68, 68, 0.15)";
                feedbackDiv.style.color = "#fca5a5";
                feedbackDiv.innerHTML = `<strong>Netačno.</strong> ${optionBtn.getAttribute("data-explanation") || ""}`;
            }
        }

        updateQuizScoreDisplay();

        // Check completion
        const totalCards = document.querySelectorAll(".quiz-question-card").length;
        if (questionsAnswered >= totalCards && totalCards > 0) {
            triggerCertificateEvaluation(quizScore, totalCards);
        }
    });
}

function updateQuizScoreDisplay() {
    const badge = document.querySelector("#quiz-score-badge");
    const totalCards = document.querySelectorAll(".quiz-question-card").length;
    if (badge) {
        badge.innerText = `Rezultat: ${quizScore} / ${totalCards}`;
    }
}

function triggerCertificateEvaluation(score, total) {
    const banner = document.querySelector("#cert-banner");
    if (!banner) return;

    const percentage = total > 0 ? (score / total) : 0;
    banner.style.display = "block";

    if (percentage >= 0.7) {
        // PASS (>= 70%)
        banner.style.background = "linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(56, 189, 248, 0.15))";
        banner.style.borderColor = "var(--accent-green)";
        banner.innerHTML = `
            <h3 style="color: #86efac; margin-bottom: 8px;">🎓 Čestitamo! Položili ste kviz znanja (${score}/${total} — ${Math.round(percentage * 100)}%)!</h3>
            <p style="color: var(--text-secondary); margin-bottom: 16px;">
                Uspešno ste zadovoljili pedagoške kriterijume Senior Judge agenta i savladali sve module.
            </p>
            <button onclick="openCertificateModal()" class="btn-generate" style="margin: 0 auto;">
                <span>📜 Preuzmi Zvanični Sertifikat</span>
            </button>
        `;
    } else {
        // FAIL (< 70%)
        banner.style.background = "rgba(239, 68, 68, 0.12)";
        banner.style.borderColor = "var(--accent-red)";
        banner.innerHTML = `
            <h3 style="color: #fca5a5; margin-bottom: 8px;">❌ Kviz nije položen (Rezultat: ${score}/${total} — ${Math.round(percentage * 100)}%)</h3>
            <p style="color: var(--text-secondary); margin-bottom: 14px;">
                Za sticanje zvaničnog sertifikata potrebno je najmanje 70% tačnih odgovora. Pročitajte objašnjenja i pokušajte ponovo.
            </p>
            <button onclick="resetQuiz()" class="chapter-chip" style="margin: 0 auto; display: inline-block; cursor: pointer;">
                🔄 Pokušaj ponovo
            </button>
        `;
    }
}

function resetQuiz() {
    quizScore = 0;
    questionsAnswered = 0;
    document.querySelectorAll(".quiz-question-card").forEach(card => {
        card.removeAttribute("data-answered");
        const fb = card.querySelector(".quiz-feedback");
        if (fb) {
            fb.style.display = "none";
            fb.innerHTML = "";
        }
    });
    document.querySelectorAll(".quiz-option-btn").forEach(btn => {
        btn.classList.remove("correct", "wrong");
    });
    updateQuizScoreDisplay();
    const banner = document.querySelector("#cert-banner");
    if (banner) banner.style.display = "none";
}

/**
 * 4. Verified Certificate Modal & Print System
 */
function initCertificateModal() {
    const modal = document.querySelector("#certificate-modal");
    const btnClose = document.querySelector("#btn-close-cert");
    const btnPrint = document.querySelector("#btn-print-cert");

    if (btnClose && modal) {
        btnClose.addEventListener("click", () => {
            modal.style.display = "none";
        });
    }

    if (btnPrint) {
        btnPrint.addEventListener("click", () => {
            window.print();
        });
    }
}

function openCertificateModal() {
    const modal = document.querySelector("#certificate-modal");
    if (!modal) return;

    let studentName = localStorage.getItem("lms_student_name");
    if (!studentName) {
        studentName = prompt("Unesite vaše ime i prezime za zvanični sertifikat:", "Polaznik Obrazovnog Programa");
        if (studentName) localStorage.setItem("lms_student_name", studentName);
        else studentName = "Polaznik Obrazovnog Programa";
    }

    const nameEl = document.querySelector("#cert-student-name");
    const topicEl = document.querySelector("#cert-course-topic");
    const hashEl = document.querySelector("#cert-verification-hash");
    const dateEl = document.querySelector("#cert-issue-date");

    if (nameEl) nameEl.innerText = studentName;
    if (topicEl && currentCourseData) topicEl.innerText = currentCourseData.topic;
    if (hashEl && currentCourseData) hashEl.innerText = currentCourseData.verification_hash;
    if (dateEl) dateEl.innerText = new Date().toLocaleDateString("sr-RS");

    modal.style.display = "flex";
}

/**
 * 5. Data Loading and UI Binding
 */
function loadCourseFromStorage() {
    const raw = localStorage.getItem("lms_active_course");
    if (!raw) {
        document.querySelector("#course-header-topic").innerText = "Nema pronađenog aktivnog kursa. Molimo generišite kurs sa početne stranice.";
        return;
    }

    try {
        currentCourseData = JSON.parse(raw);
        renderCourse(currentCourseData);
    } catch (e) {
        console.error("Greška pri parsiranju kursa:", e);
        document.querySelector("#course-header-topic").innerText = "Greška pri učitavanju podataka kursa.";
    }
}

function renderCourse(course) {
    document.title = `${course.topic} — Zvanični Masterclass`;
    document.querySelector("#course-header-topic").innerText = course.topic;

    const hashBadge = document.querySelector("#verification-badge");
    if (hashBadge && course.verification_hash) {
        hashBadge.innerText = course.verification_hash;
        hashBadge.title = "Kriptografski verifikovan sadržaj";
    }

    // Video Iframe Setup
    const iframe = document.querySelector("#masterclass-iframe");
    if (iframe && course.youtube_metadata) {
        const vid = course.youtube_metadata.video_id;
        iframe.src = `https://www.youtube-nocookie.com/embed/${vid}?enablejsapi=1&origin=${window.location.origin}&rel=0`;
    }

    // Chapter Navigation Bar
    const chapterBar = document.querySelector("#chapter-bar-container");
    if (chapterBar && course.youtube_metadata && course.youtube_metadata.chapters) {
        chapterBar.innerHTML = course.youtube_metadata.chapters.map((ch, idx) => `
            <button class="chapter-chip ${idx === 0 ? 'active' : ''}" data-seconds="${ch.seconds}">
                ▶ ${ch.timestamp} ${ch.title}
            </button>
        `).join("");
    }

    // Render Course Sections (1 to 7)
    const contentContainer = document.querySelector("#course-content-container");
    if (contentContainer && course.sections) {
        contentContainer.innerHTML = course.sections.map(sec => `
            <section class="course-section-block" id="section-${sec.index}" style="margin-bottom: 36px;">
                <h2 style="font-size: 1.6rem; color: var(--text-primary); border-bottom: 1px solid var(--border-color); padding-bottom: 8px; margin-bottom: 16px;">
                    ${sec.title}
                </h2>
                <div class="section-markdown-body">
                    ${formatMarkdownToHTML(sec.content_markdown)}
                </div>
            </section>
        `).join("");
    }

    // 3D Flashcards
    const flashcardsContainer = document.querySelector("#flashcards-container");
    if (flashcardsContainer && course.flashcards) {
        flashcardsContainer.innerHTML = course.flashcards.map((fc, idx) => `
            <div class="flip-card" data-idx="${idx}">
                <div class="flip-card-inner">
                    <div class="flip-card-front">
                        <span class="flashcard-badge">Pojam ${idx + 1}</span>
                        <h3>${fc.front}</h3>
                        <p style="font-size: 0.8rem; color: var(--accent-blue); margin-top: 12px;">(Klikni za odgovor ↻)</p>
                    </div>
                    <div class="flip-card-back">
                        <span class="flashcard-badge" style="background: rgba(34, 197, 94, 0.2); color: #86efac;">Definicija</span>
                        <p>${fc.back}</p>
                    </div>
                </div>
            </div>
        `).join("");
    }

    // Quiz Questions
    const quizContainer = document.querySelector("#quiz-questions-list");
    if (quizContainer && course.quiz) {
        quizScore = 0;
        questionsAnswered = 0;
        quizContainer.innerHTML = course.quiz.map((q, qIdx) => `
            <div class="quiz-question-card" data-idx="${qIdx}">
                <h4 style="margin-bottom: 12px; font-size: 1.05rem;">Pitanje ${qIdx + 1}: ${q.question}</h4>
                <div class="quiz-options-list">
                    ${q.options.map((opt, optIdx) => `
                        <button class="quiz-option-btn" 
                                data-correct="${optIdx === q.correct_index}"
                                data-explanation="${q.explanation}">
                            ${String.fromCharCode(65 + optIdx)}) ${opt}
                        </button>
                    `).join("")}
                </div>
                <div class="quiz-feedback"></div>
            </div>
        `).join("");
        updateQuizScoreDisplay();
    }

    // Render Agent Traces and Execution Metrics (autonomous-agents skill)
    renderAgentTracesAndMetrics(course);
}

/**
 * 6. Robust In-Browser Markdown & Typography Parser
 */
function formatMarkdownToHTML(md) {
    if (!md) return "";
    let html = md;

    // Clean mathematical notation & LaTeX escapes
    html = html.replace(/\\rightarrow/g, '➔');
    html = html.replace(/\\times/g, '×');
    html = html.replace(/\\le/g, '≤');
    html = html.replace(/\\ge/g, '≥');
    html = html.replace(/\\text\{([^}]+)\}/g, '$1');
    html = html.replace(/\\?\$([^\$\n]+)\\?\$/g, '<strong><em>$1</em></strong>');

    // Replace [mm:ss] with interactive chapter pills
    html = html.replace(/\[(\d{1,2}:\d{2})\]/g, (match, ts) => {
        const parts = ts.split(":").map(Number);
        const secs = parts[0] * 60 + parts[1];
        return `<button class="inline-chapter-pill" data-seconds="${secs}" title="Premotaj na ${ts}">▶ ${ts}</button>`;
    });

    // Clean stray markers
    html = html.replace(/^\s*#{1,6}\s*$/gm, '');
    html = html.replace(/^\s*---\s*$/gm, '<hr style="border: none; border-top: 1px solid var(--border-color); margin: 24px 0;">');

    // Replace headers
    html = html.replace(/^### (.*$)/gim, '<h3 style="margin: 18px 0 10px 0; color: var(--accent-blue);">$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2 style="margin: 22px 0 12px 0;">$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1 style="margin: 26px 0 14px 0;">$1</h1>');

    // Replace bold & italic
    html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');

    // Blockquotes & Callouts
    html = html.replace(/^\>\s*\[!TIP\]\s*(.*$)/gim, '<blockquote style="border-left: 4px solid var(--accent-green); background: rgba(34, 197, 94, 0.08); padding: 12px 16px; margin: 16px 0; border-radius: var(--radius-sm);">$1</blockquote>');
    html = html.replace(/^\>\s*\[!WARNING\]\s*(.*$)/gim, '<blockquote style="border-left: 4px solid var(--accent-amber); background: rgba(245, 158, 11, 0.08); padding: 12px 16px; margin: 16px 0; border-radius: var(--radius-sm);">$1</blockquote>');
    html = html.replace(/^\>\s*(.*$)/gim, '<blockquote style="border-left: 3px solid var(--accent-blue); padding: 8px 14px; margin: 12px 0; color: var(--text-secondary);">$1</blockquote>');

    // Replace code blocks
    html = html.replace(/```([a-z]*)([\s\S]*?)```/gim, '<div class="code-sandbox" style="background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 14px; margin: 16px 0; overflow-x: auto;"><pre><code style="font-family: var(--font-mono); font-size: 0.9rem;">$2</code></pre></div>');

    // Lists
    html = html.replace(/^\s*-\s+(.*$)/gim, '<div style="margin: 4px 0; padding-left: 18px; position: relative;"><span style="position: absolute; left: 0; color: var(--accent-blue);">•</span> $1</div>');
    html = html.replace(/^\s*(\d+)\.\s+(.*$)/gim, '<div style="margin: 6px 0; padding-left: 20px; position: relative;"><span style="position: absolute; left: 0; font-weight: 700; color: var(--accent-blue); font-size: 0.85rem;">$1.</span> $2</div>');

    // Paragraph breaks
    html = html.replace(/\n\n/g, '<p style="margin-bottom: 12px;"></p>');

    return html;
}

/**
 * 7. Autonomous Agent Traces & Metrics Rendering
 */
function renderAgentTracesAndMetrics(course) {
    const metricsStrip = document.querySelector("#metrics-summary-strip");
    const traceList = document.querySelector("#trace-steps-list");

    if (metricsStrip && course.execution_metrics) {
        const m = course.execution_metrics;
        metricsStrip.innerHTML = `
            <div class="trace-metric-tile">
                <div class="trace-metric-value">${m.total_steps || 0}</div>
                <div class="trace-metric-label">Koraka (Steps)</div>
            </div>
            <div class="trace-metric-tile">
                <div class="trace-metric-value">${m.total_estimated_tokens ? m.total_estimated_tokens.toLocaleString() : 0}</div>
                <div class="trace-metric-label">Tokena (Procena)</div>
            </div>
            <div class="trace-metric-tile">
                <div class="trace-metric-value">$${m.estimated_cost_usd !== undefined ? m.estimated_cost_usd.toFixed(4) : "0.0000"}</div>
                <div class="trace-metric-label">Trošak (USD)</div>
            </div>
            <div class="trace-metric-tile">
                <div class="trace-metric-value">${m.execution_time_seconds || 0}s</div>
                <div class="trace-metric-label">Vreme Izvršenja</div>
            </div>
            <div class="trace-metric-tile">
                <div class="trace-metric-value" style="font-size: 0.85rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    ${m.checkpoint_id || "lms-active"}
                </div>
                <div class="trace-metric-label">Thread / Checkpoint</div>
            </div>
            <div class="trace-metric-tile">
                <div class="trace-metric-value" style="color: var(--accent-green);">${Math.round((m.grounding_confidence || 1.0) * 100)}%</div>
                <div class="trace-metric-label">Utemeljenost (Grounding)</div>
            </div>
        `;
    }

    if (traceList) {
        const traces = course.trace_history || [];
        if (traces.length === 0) {
            traceList.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">Nema snimljenih tragova za ovu sesiju.</p>`;
        } else {
            traceList.innerHTML = traces.map(t => `
                <div class="trace-step-card">
                    <div class="trace-step-header">
                        <span class="trace-agent-pill">🤖 ${t.agent_name} • Korak ${t.step_number}</span>
                        <span style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">${t.tokens_used} tokena</span>
                    </div>
                    <div class="trace-thought-box">
                        <strong>💭 Misao (Thought):</strong> ${t.thought}
                    </div>
                    <div class="trace-action-box">
                        <strong>⚡ Akcija (Action):</strong> ${t.action}
                    </div>
                    <div class="trace-obs-box">
                        <strong>👁️ Opservacija (Observation):</strong> ${t.observation}
                    </div>
                    ${t.reflection ? `
                        <div style="margin-top: 6px; font-size: 0.85rem; color: #e9d5ff; padding: 4px 8px; border-left: 3px solid var(--accent-purple);">
                            <strong>⚖️ Refleksija (Reflection):</strong> ${t.reflection}
                        </div>
                    ` : ""}
                </div>
            `).join("");
        }
    }
}

function toggleTraceDrawer() {
    const drawer = document.querySelector("#trace-drawer");
    const btn = document.querySelector("#toggle-trace-btn");
    if (!drawer) return;

    if (drawer.style.display === "none" || !drawer.style.display) {
        drawer.style.display = "block";
        if (btn) btn.textContent = "Sakrij Revizorski Dnevnik (▲)";
    } else {
        drawer.style.display = "none";
        if (btn) btn.textContent = "Prikaži Revizorski Dnevnik (▼)";
    }
}
