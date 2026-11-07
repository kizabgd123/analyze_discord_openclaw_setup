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


def _safe_escape(val: Any, default: str = "") -> str:
    if val is None:
        return html.escape(default)
    return html.escape(str(val))


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
        q_agent = _safe_escape(q.get("agent"), "Agent")
        q_reason = _safe_escape(q.get("reason"), "general")
        q_latency = f"{q.get('latency_seconds', 0.0):.1f}s"
        q_text = _safe_escape(q.get("question"), "")
        ans_text = _safe_escape(q.get("answer") or "(No answer returned)")
        q_time = _safe_escape(q.get("timestamp"), "")
        q_status = _safe_escape(q.get("status") or "PASSED")
        citations = q.get("citations", {})
        err = q.get("error")

        citations_html = ""
        if citations:
            cit_items = "".join([f"<li><strong>[{_safe_escape(k)}]</strong> Source ID: {_safe_escape(v)}</li>" for k, v in citations.items()])
            citations_html = f'<div class="citations-box"><h4>Citations:</h4><ul>{cit_items}</ul></div>'

        error_block = f'<pre class="raw-error">{_safe_escape(err)}</pre>' if err else ''
        status_badge = f'<span class="badge badge-{"success" if q_status == "PASSED" else "danger"}">{q_status}</span>'

        nlm_cards += f"""
        <div class="nlm-card">
            <div class="nlm-header">
                <span class="nlm-title">🔎 [{q_agent} | {q_reason}] ({q_latency}): {q_text}</span>
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
        verdict = html.escape(exp.get("skeptic_verdict", "PENDING"))
        deciding_reason = html.escape(exp.get("deciding_reason", "—"))
        cv = exp.get("cv_score")
        cv_str = f"{cv:.5f}" if cv is not None else '<span class="text-danger">NONE</span>'
        status = html.escape(exp.get("status", "PENDING"))
        
        exit_code = exp.get("exit_code")
        signal = exp.get("signal")
        if signal:
            exit_str = f"SIG {signal}"
        elif exit_code is not None:
            exit_str = f"Code {exit_code}"
        else:
            exit_str = "—"

        debug_cnt = exp.get("debug_attempts", 0)
        debug_str = f"{debug_cnt}/2" if debug_cnt else "0/2"

        pt = exp.get("phase_timings", {})
        if pt:
            timing_str = f"Tot: {exp.get('elapsed_seconds', 0):.0f}s (NLM: {pt.get('nlm_seconds', 0):.0f}s, Run: {pt.get('runner_seconds', 0):.0f}s)"
        else:
            timing_str = f"{exp.get('elapsed_seconds', 0):.1f}s"

        if status == "PASSED":
            status_badge = '<span class="badge badge-success">PASSED</span>'
        elif status == "BLOCKED":
            status_badge = '<span class="badge badge-blocked">BLOCKED</span>'
        else:
            status_badge = f'<span class="badge badge-danger">{status}</span>'

        if verdict == "PROCEED":
            verdict_badge = '<span class="badge badge-success">PROCEED</span>'
        elif "CONDITIONS" in verdict:
            verdict_badge = '<span class="badge badge-warning">CONDITIONS</span>'
        elif verdict == "BLOCK":
            verdict_badge = '<span class="badge badge-danger">BLOCK</span>'
        else:
            verdict_badge = f'<span class="badge badge-info">{verdict}</span>'

        verdict_vs_base = exp.get("verdict_vs_base", "N/A")
        paired_diffs = exp.get("paired_diffs", [])
        diff_str = ""
        if paired_diffs and any(d != 0.0 for d in paired_diffs):
            mean_diff = sum(paired_diffs) / len(paired_diffs)
            diff_sign = "+" if mean_diff > 0 else ""
            diff_color = "#3fb950" if mean_diff > 0 else "#f85149"
            diff_str = f"<br><small style='color: {diff_color}; font-weight: bold;'>Δ {diff_sign}{mean_diff:.5f}</small>"

        if verdict_vs_base == "BETTER_CV":
            verdict_base_badge = f'<span class="badge badge-better">BETTER_CV</span>{diff_str}'
        elif verdict_vs_base == "WORSE_CV":
            verdict_base_badge = f'<span class="badge badge-worse">WORSE_CV</span>{diff_str}'
        elif verdict_vs_base == "INCONCLUSIVE_CV":
            verdict_base_badge = f'<span class="badge badge-inconclusive">INCONCLUSIVE</span>{diff_str}'
        elif verdict_vs_base == "BASELINE":
            verdict_base_badge = '<span class="badge badge-baseline">BASELINE (Exp 0)</span>'
        else:
            verdict_base_badge = f'<span class="badge badge-info">{html.escape(str(verdict_vs_base))}</span>'

        code = exp.get("code")
        if code:
            code_block = f"<br><details style='margin-top:6px;'><summary style='cursor:pointer; color:#58a6ff; font-size:11px;'>View Generated Code</summary><pre style='max-height:180px; overflow:auto; font-size:11px; background:#0d1117; padding:8px; border-radius:4px; text-align:left;'><code>{html.escape(code)}</code></pre></details>"
        else:
            code_block = ""

        lineage = exp.get("debate_lineage")
        lineage_html = ""
        if lineage:
            hyp_id = html.escape(str(lineage.get("hypothesis_id") or exp.get("hypothesis_id") or ""))
            model_id = html.escape(str(lineage.get("model") or "gemini-3.8-flash-high"))
            account_id = html.escape(str(lineage.get("account") or "kiza101288@gmail.com"))
            prompt_hashes = lineage.get("prompt_sha256", {})
            p_items = "".join([f"<li><strong>{html.escape(k)}:</strong> <code>{html.escape(v[:12])}...</code></li>" for k, v in prompt_hashes.items() if v])

            gate = lineage.get("policy_gate", {})
            gate_auth = gate.get("authorized", True)
            gate_badge = '<span class="badge badge-success">GATE: APPROVED</span>' if gate_auth else '<span class="badge badge-blocked">GATE: BLOCKED</span>'
            gate_reason_text = html.escape(str(gate.get("reason") or ""))

            objs = lineage.get("objections", [])
            obj_rows = ""
            for o in objs:
                oid = html.escape(str(o.get("objection_id", "OBJ")))
                sev = html.escape(str(o.get("severity", "CRITICAL")))
                sev_badge = f'<span class="badge badge-{"danger" if sev=="CRITICAL" else "warning"}">{sev}</span>'
                claim = html.escape(str(o.get("original_claim", "")))
                obj_rows += f"<li><strong>{oid}</strong> {sev_badge}: {claim}</li>"

            resolutions = lineage.get("resolutions", [])
            res_rows = ""
            for r in resolutions:
                roid = html.escape(str(r.get("objection_id", "OBJ")))
                rst = html.escape(str(r.get("status", "")))
                rst_badge = f'<span class="badge badge-{"success" if rst=="RESOLVED" else "danger"}">{rst}</span>'
                res_rows += f"<li><strong>{roid}</strong> {rst_badge}</li>"

            lineage_html = f"""
            <details style='margin-top:6px;'>
                <summary style='cursor:pointer; color:#79c0ff; font-size:11px;'>🛡️ Debate Lineage & Policy Gate</summary>
                <div style='background:#161b22; padding:8px; border-radius:4px; font-size:11px; margin-top:4px;'>
                    <div><strong>ID:</strong> <code>{hyp_id}</code> | <strong>Model:</strong> {model_id} ({account_id})</div>
                    <div style='margin-top:4px;'>{gate_badge} <small>{gate_reason_text}</small></div>
                    {f"<div style='margin-top:4px;'><strong>Prompt SHA-256:</strong><ul style='margin:2px 0 0 16px; padding:0;'>{p_items}</ul></div>" if p_items else ""}
                    {f"<div style='margin-top:4px;'><strong>Objections ({len(objs)}):</strong><ul style='margin:2px 0 0 16px; padding:0;'>{obj_rows}</ul></div>" if obj_rows else ""}
                    {f"<div style='margin-top:4px;'><strong>Resolutions:</strong><ul style='margin:2px 0 0 16px; padding:0;'>{res_rows}</ul></div>" if res_rows else ""}
                </div>
            </details>
            """

        hyp_display = f"{hyp}{code_block}{lineage_html}"

        exp_rows += f"""
        <tr>
            <td><strong>#{exp_no}</strong></td>
            <td>{hyp_display}</td>
            <td>{verdict_badge}</td>
            <td><small>{deciding_reason}</small></td>
            <td><code>{cv_str}</code></td>
            <td>{verdict_base_badge}</td>
            <td>{status_badge}</td>
            <td><small>{exit_str}</small></td>
            <td><small>{debug_str}</small></td>
            <td><small>{timing_str}</small></td>
        </tr>
        """

    # Debug attempts list
    debug_attempts = state.get("debug_attempts", [])
    debug_html = ""
    if debug_attempts:
        d_items = ""
        for da in debug_attempts:
            d_items += f"""
            <div class="debug-card">
                <div class="debug-header">
                    <strong>Exp #{da.get('exp_no')} — Attempt #{da.get('attempt')}/2</strong>
                    <span class="chat-time">{html.escape(da.get('timestamp', ''))}</span>
                </div>
                <div class="debug-err"><strong>Error Encountered:</strong><pre>{html.escape(da.get('error', ''))}</pre></div>
                <div class="debug-fix"><strong>Engineer Fix:</strong> {html.escape(da.get('fix_summary', ''))}</div>
            </div>
            """
        debug_html = f"""
        <div class="debug-attempts-container">
            <h3 style="font-size: 1.05rem; margin-top: 1rem; margin-bottom: 0.5rem; color: #e3b341;">🛠️ Debug Loop History ({len(debug_attempts)})</h3>
            {d_items}
        </div>
        """

    exp_table = f"""
    <div class="folds-notice">🔒 <strong>CV Split Protocol:</strong> {html.escape(folds_info)} (Fixed for all experiments)</div>
    <div class="table-wrapper">
        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 5%;">Exp #</th>
                    <th style="width: 23%;">Hypothesis</th>
                    <th style="width: 9%;">Skeptic</th>
                    <th style="width: 17%;">Deciding Reason</th>
                    <th style="width: 10%;">Real CV (AUC)</th>
                    <th style="width: 12%;">Verdict vs Base</th>
                    <th style="width: 7%;">Status</th>
                    <th style="width: 5%;">Exit</th>
                    <th style="width: 5%;">Debug</th>
                    <th style="width: 7%;">Timing</th>
                </tr>
            </thead>
            <tbody>{exp_rows or '<tr><td colspan="10">No experiments executed yet</td></tr>'}</tbody>
        </table>
    </div>
    {debug_html}
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
        .badge-warning {{ background: #563d04; color: #e3b341; }}
        .badge-blocked {{ background: #4a1d1d; color: #ff7b72; border: 1px solid #da3633; }}
        .badge-info {{ background: #173863; color: #79c0ff; }}
        .badge-kaggle-page {{ background: #003666; color: #58a6ff; }}
        .badge-public-notebook {{ background: #2f224f; color: #d2a8ff; }}
        .badge-discussion {{ background: #453000; color: #d29922; }}
        .badge-academic {{ background: #0f4035; color: #56d364; }}
        .badge-repo {{ background: #343941; color: #c9d1d9; }}
        .badge-lesson {{ background: #3b2300; color: #ffa657; margin-left: 0.5rem; }}
        .badge-engine {{ background: #1a365d; color: #63b3ed; border: 1px solid #2b6cb0; font-family: monospace; font-size: 0.78rem; }}
        .badge-better {{ background: #1b4725; color: #48bb78; border: 1px solid #2f855a; }}
        .badge-worse {{ background: #5c1d1d; color: #f56565; border: 1px solid #c53030; }}
        .badge-inconclusive {{ background: #4a3e12; color: #ecc94b; border: 1px solid #b7791f; }}
        .badge-baseline {{ background: #233044; color: #90cdf4; border: 1px solid #3182ce; }}
        .debug-attempts-container {{ margin-top: 1rem; }}
        .debug-card {{
            background: #1c1507;
            border: 1px solid #d29922;
            border-radius: 6px;
            padding: 0.8rem;
            margin-bottom: 0.6rem;
            font-size: 0.88rem;
        }}
        .debug-header {{ display: flex; justify-content: space-between; color: #e3b341; margin-bottom: 0.3rem; }}
        .debug-err pre {{
            background: #2b0b0d;
            color: #ff9b9b;
            padding: 0.4rem 0.6rem;
            border-radius: 4px;
            font-size: 0.8rem;
            white-space: pre-wrap;
            margin: 0.3rem 0;
            max-height: 120px;
            overflow-y: auto;
        }}
        .debug-fix {{ color: #7ee787; margin-top: 0.3rem; }}
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
                <span><strong>AI Engine:</strong> <span class="badge badge-engine">⚡ Antigravity agy (gemini-3.8-flash-high | kiza101288@gmail.com)</span></span>
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
