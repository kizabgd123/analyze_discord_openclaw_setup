"""
html_generator.py — Standalone Deterministic HTML Dashboard Generator.
======================================================================
Renders an executive, mobile-friendly single-page dashboard strictly from
the state logs. Never invokes an LLM to generate or format the content.
"""

import os
import html
import json
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger("Kaggle2.HTMLGenerator")


def render_html_dashboard(state: Dict[str, Any], output_path: Path) -> Path:
    """
    Renders the complete self-contained HTML report.
    Sections:
      1. Top banner: Failures and Warnings (raw error tracebacks).
      2. Sources Directory with Origin Classification.
      3. Live Multi-Agent Transcript (with Pre-Planning Lesson queries).
      4. NotebookLM Research Q&A Log (verbatim answers & citations).
      5. Experiments Matrix (Fixed Folds note, Real CV ROC-AUC, Status).
      6. Cumulative Lessons Learned.
      7. Submissions Table (strictly s6e11-<run_id>-<exp_no>).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    run_id = state.get("run_id", "unknown-run")
    competition = state.get("competition", "playground-series-s6e11")
    timestamp = state.get("updated_at", "")
    failures = state.get("failures", [])
    sources = state.get("sources", [])
    transcript = state.get("transcript", [])
    nlm_queries = state.get("nlm_queries", [])
    experiments = state.get("experiments", [])
    lessons = state.get("lessons", [])
    submissions = state.get("submissions", [])
    folds_info = state.get("folds_info", "StratifiedKFold (n_splits=5, shuffle=True, random_state=42) — FROZEN")

    # 1. Failures section
    failures_html = ""
    if failures:
        fail_items = ""
        for f in failures:
            fail_items += f"""
            <div class="fail-card">
                <div class="fail-title">⚠️ [{html.escape(f.get('type', 'ERROR'))}] {html.escape(f.get('title', 'Failure'))}</div>
                <div class="fail-time">{html.escape(f.get('timestamp', ''))}</div>
                <pre class="raw-error">{html.escape(f.get('raw_error', 'No raw trace provided'))}</pre>
            </div>
            """
        failures_html = f"""
        <section class="section alert-section">
            <h2 class="alert-header">🚨 FAILURES & WARNINGS ({len(failures)})</h2>
            <div class="failures-container">{fail_items}</div>
        </section>
        """

    # 2. Sources section
    sources_rows = ""
    for s in sources:
        origin = html.escape(s.get("origin", "external reference"))
        title = html.escape(s.get("title", "Untitled"))
        url = s.get("url")
        link_html = f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{html.escape(url)}</a>' if url else '<span class="text-muted">Local file / Lesson</span>'
        badge_class = f"badge-{origin.replace(' ', '-').lower()}"
        sources_rows += f"""
        <tr>
            <td><span class="badge {badge_class}">{origin}</span></td>
            <td><strong>{title}</strong></td>
            <td>{link_html}</td>
        </tr>
        """
    sources_table = f"""
    <div class="table-wrapper">
        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 15%;">Origin</th>
                    <th style="width: 45%;">Source Title</th>
                    <th style="width: 40%;">URL / Location</th>
                </tr>
            </thead>
            <tbody>{sources_rows or '<tr><td colspan="3">No sources recorded</td></tr>'}</tbody>
        </table>
    </div>
    """

    # 3. Transcript section
    transcript_cards = ""
    for msg in transcript:
        role = html.escape(msg.get("role", "Agent"))
        agent_name = html.escape(msg.get("agent", role))
        text = html.escape(msg.get("message", ""))
        time_str = html.escape(msg.get("timestamp", ""))
        role_class = f"role-{role.lower()}"
        is_lesson_query = msg.get("is_lesson_query", False)
        lesson_badge = '<span class="badge badge-lesson">PRE-PLANNING LESSON QUERY</span>' if is_lesson_query else ''
        transcript_cards += f"""
        <div class="chat-card {role_class}">
            <div class="chat-header">
                <span class="agent-name">{agent_name} ({role})</span>
                {lesson_badge}
                <span class="chat-time">{time_str}</span>
            </div>
            <div class="chat-body">{text}</div>
        </div>
        """

    # 4. NotebookLM Q&A section
    nlm_cards = ""
    for q in nlm_queries:
        q_text = html.escape(q.get("question", ""))
        ans_text = html.escape(q.get("answer") or "(No answer returned)")
        q_time = html.escape(q.get("timestamp", ""))
        q_status = html.escape(q.get("status", "PASSED"))
        citations = q.get("citations", {})
        err = q.get("error")

        citations_html = ""
        if citations:
            cit_items = "".join([f"<li><strong>[{html.escape(str(k))}]</strong> Source ID: {html.escape(str(v))}</li>" for k, v in citations.items()])
            citations_html = f'<div class="citations-box"><h4>Citations:</h4><ul>{cit_items}</ul></div>'

        error_block = f'<pre class="raw-error">{html.escape(err)}</pre>' if err else ''
        status_badge = f'<span class="badge badge-{"success" if q_status == "PASSED" else "danger"}">{q_status}</span>'

        nlm_cards += f"""
        <div class="nlm-card">
            <div class="nlm-header">
                <span class="nlm-title">🔎 Query: {q_text}</span>
                {status_badge}
                <span class="chat-time">{q_time}</span>
            </div>
            {error_block}
            <div class="nlm-answer">{ans_text}</div>
            {citations_html}
        </div>
        """

    # 5. Experiments section
    exp_rows = ""
    for exp in experiments:
        exp_no = exp.get("exp_no", 0)
        hyp = html.escape(exp.get("hypothesis", ""))
        cv = exp.get("cv_score")
        cv_str = f"{cv:.5f}" if cv is not None else '<span class="text-danger">NOT RUN / FAILED</span>'
        status = html.escape(exp.get("status", "PENDING"))
        elapsed = f"{exp.get('elapsed_seconds', 0):.1f}s"
        status_badge = f'<span class="badge badge-{"success" if status == "PASSED" else "danger"}">{status}</span>'

        exp_rows += f"""
        <tr>
            <td><strong>#{exp_no}</strong></td>
            <td>{hyp}</td>
            <td><code>{cv_str}</code></td>
            <td>{status_badge}</td>
            <td>{elapsed}</td>
        </tr>
        """
    exp_table = f"""
    <div class="folds-notice">🔒 <strong>CV Split Protocol:</strong> {html.escape(folds_info)} (Fixed for all experiments)</div>
    <div class="table-wrapper">
        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 8%;">Exp #</th>
                    <th style="width: 45%;">Hypothesis</th>
                    <th style="width: 17%;">Real CV (ROC-AUC)</th>
                    <th style="width: 15%;">Status</th>
                    <th style="width: 15%;">Duration</th>
                </tr>
            </thead>
            <tbody>{exp_rows or '<tr><td colspan="5">No experiments executed yet</td></tr>'}</tbody>
        </table>
    </div>
    """

    # 6. Lessons section
    lessons_html = ""
    for l in lessons:
        l_no = l.get("exp_no", 0)
        l_status = html.escape(l.get("status", "PASSED"))
        l_cv = l.get("cv_score")
        cv_disp = f"CV ROC-AUC: {l_cv:.5f}" if l_cv is not None else "CV: FAILED / NONE"
        lessons_html += f"""
        <div class="lesson-card">
            <div class="lesson-header">
                <h3>Experiment #{l_no} Postmortem — {l_status}</h3>
                <span class="badge badge-info">{cv_disp}</span>
            </div>
            <div class="lesson-grid">
                <div class="lesson-col">
                    <strong>✅ What Worked:</strong>
                    <p>{html.escape(l.get('what_worked', 'None'))}</p>
                </div>
                <div class="lesson-col">
                    <strong>❌ What Failed:</strong>
                    <p>{html.escape(l.get('what_failed', 'None'))}</p>
                </div>
            </div>
            <div class="lesson-row">
                <strong>💡 Root Cause Reasoning:</strong>
                <p>{html.escape(l.get('why', ''))}</p>
            </div>
            <div class="lesson-row">
                <strong>➡️ Next Round Recommendations:</strong>
                <p>{html.escape(l.get('next_steps', ''))}</p>
            </div>
        </div>
        """

    # 7. Submissions section
    subs_rows = ""
    for sub in submissions:
        tag = html.escape(sub.get("tag", ""))
        sha256 = html.escape(sub.get("sha256", "")[:12] + "...")
        cv = sub.get("cv_score")
        cv_str = f"{cv:.5f}" if cv is not None else "N/A"
        pub = sub.get("public_score")
        pub_str = f"{pub:.5f}" if pub is not None else '<span class="text-muted">Evaluating...</span>'
        gap_str = f"{(pub - cv):+.5f}" if (pub is not None and cv is not None) else "—"

        subs_rows += f"""
        <tr>
            <td><code>{tag}</code></td>
            <td><code>{sha256}</code></td>
            <td>{cv_str}</td>
            <td><strong>{pub_str}</strong></td>
            <td>{gap_str}</td>
        </tr>
        """
    subs_table = f"""
    <div class="table-wrapper">
        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 28%;">Tag (Strict Filter)</th>
                    <th style="width: 18%;">SHA-256</th>
                    <th style="width: 18%;">Real CV</th>
                    <th style="width: 18%;">Public LB</th>
                    <th style="width: 18%;">CV vs LB Gap</th>
                </tr>
            </thead>
            <tbody>{subs_rows or '<tr><td colspan="5">No submissions executed for this run yet (Budget: 5 max)</td></tr>'}</tbody>
        </table>
    </div>
    """

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>S6E11 Multi-Agent Dashboard | Run {run_id}</title>
    <style>
        :root {{
            --bg-main: #0d1117;
            --bg-card: #161b22;
            --bg-darker: #090d13;
            --border: #30363d;
            --text-main: #c9d1d9;
            --text-muted: #8b949e;
            --text-heading: #58a6ff;
            --accent-green: #238636;
            --accent-red: #da3633;
            --accent-yellow: #d29922;
            --accent-blue: #1f6feb;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-main);
            color: var(--text-main);
            font-family: var(--font-family);
            line-height: 1.5;
            padding: 1rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.2rem;
            margin-bottom: 1.5rem;
        }}
        header h1 {{ font-size: 1.6rem; color: var(--text-heading); margin-bottom: 0.3rem; }}
        .meta-bar {{ color: var(--text-muted); font-size: 0.9rem; display: flex; flex-wrap: wrap; gap: 1rem; }}
        .section {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.2rem;
            margin-bottom: 1.5rem;
        }}
        .section h2 {{
            font-size: 1.3rem;
            color: var(--text-heading);
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
        }}
        .alert-section {{ border-color: var(--accent-red); background: #220b0b; }}
        .alert-header {{ color: #ff7b72 !important; border-bottom-color: #551a1a !important; }}
        .fail-card {{
            background: #2d1214;
            border: 1px solid var(--accent-red);
            border-radius: 6px;
            padding: 0.8rem;
            margin-bottom: 0.8rem;
        }}
        .fail-title {{ font-weight: bold; color: #ff7b72; font-size: 1.05rem; }}
        .fail-time {{ font-size: 0.8rem; color: #f85149; margin-bottom: 0.5rem; }}
        .raw-error {{
            background: #140506;
            color: #ff9b9b;
            padding: 0.8rem;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.85rem;
            overflow-x: auto;
            white-space: pre-wrap;
        }}
        .table-wrapper {{ overflow-x: auto; }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
            text-align: left;
        }}
        .data-table th, .data-table td {{
            padding: 0.6rem 0.8rem;
            border-bottom: 1px solid var(--border);
        }}
        .data-table th {{ background: var(--bg-darker); color: var(--text-muted); }}
        .badge {{
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-success {{ background: #1f502c; color: #3fb950; }}
        .badge-danger {{ background: #5a1e1e; color: #f85149; }}
        .badge-info {{ background: #173863; color: #79c0ff; }}
        .badge-kaggle-page {{ background: #003666; color: #58a6ff; }}
        .badge-public-notebook {{ background: #2f224f; color: #d2a8ff; }}
        .badge-discussion {{ background: #453000; color: #d29922; }}
        .badge-academic {{ background: #0f4035; color: #56d364; }}
        .badge-repo {{ background: #343941; color: #c9d1d9; }}
        .badge-lesson {{ background: #3b2300; color: #ffa657; margin-left: 0.5rem; }}
        .folds-notice {{
            background: var(--bg-darker);
            border-left: 4px solid var(--accent-blue);
            padding: 0.6rem 1rem;
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }}
        .chat-card {{
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.8rem;
            margin-bottom: 0.8rem;
            background: var(--bg-darker);
        }}
        .role-strategist {{ border-left: 4px solid #79c0ff; }}
        .role-engineer {{ border-left: 4px solid #7ee787; }}
        .role-skeptic {{ border-left: 4px solid #ffa657; }}
        .chat-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            margin-bottom: 0.4rem;
        }}
        .agent-name {{ font-weight: bold; color: var(--text-heading); }}
        .chat-time {{ color: var(--text-muted); font-size: 0.8rem; }}
        .chat-body {{ font-size: 0.92rem; white-space: pre-wrap; }}
        .nlm-card {{
            background: var(--bg-darker);
            border: 1px solid #1f3b58;
            border-radius: 6px;
            padding: 0.8rem;
            margin-bottom: 0.8rem;
        }}
        .nlm-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }}
        .nlm-title {{ font-weight: bold; color: #79c0ff; font-size: 0.95rem; }}
        .nlm-answer {{ font-size: 0.9rem; margin-bottom: 0.5rem; line-height: 1.45; }}
        .citations-box {{
            background: #111e2e;
            padding: 0.5rem 0.8rem;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-top: 0.5rem;
        }}
        .citations-box h4 {{ color: #58a6ff; margin-bottom: 0.2rem; font-size: 0.82rem; }}
        .citations-box ul {{ list-style-type: none; }}
        .lesson-card {{
            background: var(--bg-darker);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .lesson-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.8rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.4rem;
        }}
        .lesson-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 0.8rem;
        }}
        @media (max-width: 768px) {{
            .lesson-grid {{ grid-template-columns: 1fr; }}
            .meta-bar {{ flex-direction: column; gap: 0.3rem; }}
        }}
        .lesson-col, .lesson-row {{ font-size: 0.9rem; }}
        .lesson-col p, .lesson-row p {{ margin-top: 0.2rem; color: #adbac7; }}
        .lesson-row {{ margin-top: 0.6rem; }}
        a {{ color: var(--text-heading); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Playground S6E11 Multi-Agent Command Dashboard</h1>
            <div class="meta-bar">
                <span><strong>Competition:</strong> {html.escape(competition)}</span>
                <span><strong>Run ID:</strong> <code>{html.escape(run_id)}</code></span>
                <span><strong>Updated:</strong> {html.escape(timestamp)}</span>
            </div>
        </header>

        {failures_html}

        <section class="section">
            <h2>📚 Knowledge Grounding Sources Directory</h2>
            {sources_table}
        </section>

        <section class="section">
            <h2>🔬 Cross-Validation & Experiments Matrix</h2>
            {exp_table}
        </section>

        <section class="section">
            <h2>🚀 Kaggle Submissions Ledger</h2>
            {subs_table}
        </section>

        <section class="section">
            <h2>💡 Cumulative Lessons Learned</h2>
            <div class="lessons-container">{lessons_html or '<p class="text-muted">No lessons recorded yet</p>'}</div>
        </section>

        <section class="section">
            <h2>🤖 Multi-Agent Live Conversation Transcript</h2>
            <div class="transcript-container">{transcript_cards or '<p class="text-muted">No transcript entries</p>'}</div>
        </section>

        <section class="section">
            <h2>🧠 NotebookLM Research Assistant Q&A Log</h2>
            <div class="nlm-container">{nlm_cards or '<p class="text-muted">No NotebookLM queries recorded</p>'}</div>
        </section>
    </div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    logger.info(f"[HTMLGenerator] Dashboard rendered at {output_path}")
    return output_path
