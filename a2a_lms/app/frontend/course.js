/**
 * Google ADK A2A LMS Client Logic (2026).
 * Handles video seek synchronization, 3D flashcards, quiz evaluation, and certificate generation.
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
    // Delegate click on chapter pills and chips
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

    // Send YouTube postMessage API commands
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
 * 3. Robust Universal Quiz Engine
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
            triggerCertificateEligible();
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

function triggerCertificateEligible() {
    const banner = document.querySelector("#cert-banner");
    if (banner) banner.style.display = "block";
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
 * 5. Data Hydration from Storage or Server
 */
function loadCourseFromStorage() {
    const raw = sessionStorage.getItem("active_lms_course");
    if (raw) {
        try {
            currentCourseData = JSON.parse(raw);
            renderCourse(currentCourseData);
        } catch (e) {
            console.error("Failed to parse course data from session storage:", e);
        }
    }
}

function renderCourse(course) {
    currentCourseData = course;
    console.log("[LMS Client] Rendering course:", course.topic);

    // Title & Topic
    const topicEl = document.querySelector("#course-header-topic");
    if (topicEl) topicEl.innerText = course.topic;

    // Video Player
    const iframe = document.querySelector("#masterclass-iframe");
    if (iframe && course.youtube_metadata) {
        // Enforce enablejsapi=1 for postMessage control
        const embedUrl = course.youtube_metadata.embed_url;
        const separator = embedUrl.includes("?") ? "&" : "?";
        iframe.src = `${embedUrl}${separator}enablejsapi=1&origin=${encodeURIComponent(window.location.origin)}`;
    }

    // Chapters Bar
    const chaptersContainer = document.querySelector("#chapter-bar-container");
    if (chaptersContainer && course.youtube_metadata && course.youtube_metadata.chapters) {
        chaptersContainer.innerHTML = course.youtube_metadata.chapters.map(c => `
            <button class="chapter-chip" data-seconds="${c.seconds}" title="${c.title}">
                ▶ <strong>${c.timestamp}</strong> ${c.title}
            </button>
        `).join("");
    }

    // Sections & Markdown
    const contentContainer = document.querySelector("#course-content-container");
    if (contentContainer && course.sections) {
        contentContainer.innerHTML = course.sections.map(s => `
            <div class="course-section-block" id="section-${s.index}">
                <div class="markdown-body">
                    ${formatMarkdownToHTML(s.content_markdown)}
                </div>
            </div>
        `).join("<hr style='margin: 32px 0; border: 0; border-top: 1px solid var(--border-color);'>");
    }

    // Flashcards
    const flashcardsContainer = document.querySelector("#flashcards-container");
    if (flashcardsContainer && course.flashcards) {
        flashcardsContainer.innerHTML = course.flashcards.map((fc, i) => `
            <div class="flip-card">
                <div class="flip-card-inner">
                    <div class="flip-card-front">
                        <span style="font-size: 0.8rem; color: var(--accent-blue); font-weight: 700;">KARTICA #${i + 1}</span>
                        <h4 style="margin: 12px 0; font-size: 1.1rem;">${fc.front}</h4>
                        <span class="flip-hint">👆 Klikni za objašnjenje</span>
                    </div>
                    <div class="flip-card-back">
                        <span style="font-size: 0.8rem; color: var(--accent-purple); font-weight: 700;">ODGOVOR / DEFINICIJA</span>
                        <p style="margin-top: 12px; font-size: 0.95rem; line-height: 1.5;">${fc.back}</p>
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
                <h4 style="margin-bottom: 8px;">Pitanje ${qIdx + 1}: ${q.question}</h4>
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
}

/**
 * Lightweight in-browser Markdown parser with timestamp replacement
 */
function formatMarkdownToHTML(md) {
    if (!md) return "";
    let html = md;

    // Replace [mm:ss] with interactive chapter pills
    html = html.replace(/\[(\d{1,2}:\d{2})\]/g, (match, ts) => {
        const parts = ts.split(":").map(Number);
        const secs = parts[0] * 60 + parts[1];
        return `<button class="inline-chapter-pill" data-seconds="${secs}" title="Premotaj na ${ts}">▶ ${ts}</button>`;
    });

    // Replace headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Replace bold & italic
    html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');

    // Replace blockquotes
    html = html.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');

    // Replace code blocks
    html = html.replace(/```([a-z]*)([\s\S]*?)```/gim, '<div class="code-sandbox"><pre><code>$2</code></pre></div>');

    // Linebreaks
    html = html.replace(/\n\n/g, '<p></p>');

    return html;
}
