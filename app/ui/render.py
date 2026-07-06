"""Pure presentation helpers for the Gradio UI — HTML/markdown builders and
formatters with no pipeline side effects. Imported by ``app.ui.actions`` and
``app.main``.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import yaml

from app.llm.task_routing import routing_summary
from app.utils.config import get_config


def _safe_file_output(path_str: str | None):
    if not path_str:
        return None
    path = Path(path_str)
    if path.exists() and path.is_file():
        return str(path)
    return None


def _score_badge_html(summary: str, score_data: dict) -> str:
    overall = int(score_data.get("overall", 0) or 0)
    label = summary or "ATS score unavailable"
    if overall >= 75:
        bg = "#d1fae5"
        fg = "#065f46"
    elif overall >= 50:
        bg = "#fef3c7"
        fg = "#92400e"
    else:
        bg = "#fee2e2"
        fg = "#991b1b"
    return (
        f"<div style='padding:14px 18px;border-radius:12px;background:{bg};color:{fg};"
        f"font-weight:700;font-size:22px;text-align:center'>{label}</div>"
    )


def _before_after_html(original_score: dict, final_score: dict) -> str:
    """Render the before→after ATS delta banner; empty string when no baseline."""
    if not original_score:
        return ""
    before = int(original_score.get("overall", 0) or 0)
    after = int((final_score or {}).get("overall", 0) or 0)
    if after > before:
        arrow, color = "▲", "#065f46"
    elif after < before:
        arrow, color = "▼", "#991b1b"
    else:
        arrow, color = "→", "#92400e"
    return (
        f"<div style='padding:8px 14px;border-radius:10px;background:#f1f5f9;color:{color};"
        f"font-weight:600;text-align:center'>ATS {before}% {arrow} {after}% "
        f"<span style='opacity:.7;font-weight:400'>(before → after optimization)</span></div>"
    )


def _ats_analysis_markdown(score_data: dict, skills_gap: dict) -> str:
    if not score_data:
        return "ATS analysis unavailable."
    recommendations = score_data.get("recommendations", [])
    return "\n".join(
        [
            f"## Overall ATS Match: {score_data.get('overall', 'N/A')}%",
            "",
            "### Sub-scores",
            f"- Keyword Match: {score_data.get('keyword_match', {}).get('score', 'N/A')}%",
            f"- Semantic Context: {score_data.get('semantic_context', {}).get('score', 'N/A')}%",
            f"- Section Quality: {score_data.get('section_quality', {}).get('score', 'N/A')}%",
            f"- Keyword Placement: {score_data.get('keyword_placement', {}).get('score', 'N/A')}%",
            f"- Impact Metrics: {score_data.get('impact_metrics', {}).get('score', 'N/A')}%",
            "",
            "### Skills Gap",
            f"- Missing Required: {', '.join(skills_gap.get('missing_required', [])) or 'None'}",
            f"- Missing Nice-to-Have: {', '.join(skills_gap.get('missing_nice_to_have', [])) or 'None'}",
            f"- Missing Enriched: {', '.join(skills_gap.get('missing_enriched', [])) or 'None'}",
            "",
            "### Recommendations",
            *([f"- {item}" for item in recommendations] or ["- None"]),
        ]
    )


def _routing_markdown() -> str:
    """Human-readable 'which provider does what' readout from the current keys/config."""
    summary = routing_summary(get_config())
    live = summary["live"]
    if not live:
        return (
            "**No provider keys detected.** Add at least one key (e.g. `GROQ_API_KEY`) to "
            "`.env` — see [docs/PROVIDERS.md](docs/PROVIDERS.md)."
        )
    live_line = " · ".join(f"`{p}` ({n} key{'s' if n > 1 else ''})" for p, n in live.items())
    labels = {
        "analyze_jd": "JD analysis",
        "ats_scoring": "ATS scoring",
        "project_selection": "Project pick",
        "project_generation": "Writing",
        "tailor": "Tailoring",
        "cover_letter": "Cover letter",
        "report": "Report",
    }
    rows = "\n".join(f"| {labels.get(t, t)} | `{p}` |" for t, p in summary["tasks"].items())
    return (
        f"**Live providers:** {live_line}\n\n"
        "| Task | Provider |\n|---|---|\n" + rows + "\n\n"
        "_Auto-detected from your keys. Override per task via `task_routing` in `config.yaml`. "
        "Oversized prompts skip to a bigger-context model, then trim as a last resort._"
    )


def _build_run_log_content(final_state: dict, new_logs: list[Path]) -> str:
    config = get_config()
    notes = final_state.get("personalization_notes", {}) or {}
    generated_skills = final_state.get("generated_skills", []) or []
    generated_projects = final_state.get("generated_projects", []) or []
    lines = [
        "ResumeForge Run Log",
        f"Generated: {datetime.now().isoformat()}",
        f"Company: {final_state.get('jd_analysis', {}).get('company_name', 'Company')}",
        f"Role: {final_state.get('jd_analysis', {}).get('role_title', 'Role')}",
        f"ATS Summary: {final_state.get('ats_score_summary', 'N/A')}",
        "",
        "Pipeline Configuration:",
        f"- Stage 1 (Selection): {config.get('stage1_model', 'unknown')} | Groq: {config.get('groq_reasoning_model', 'N/A')}",
        f"- Stage 2 (Writing): {config.get('stage2_model', 'unknown')} | Groq: {config.get('groq_fast_model', 'N/A')}",
        f"- Company Enrichment: {config.get('enrich_with_web_search', False)}",
        "",
        "Status Updates:",
        *([f"- {line}" for line in final_state.get("status_updates", [])] or ["- None"]),
        "",
        "Errors:",
        *([f"- {line}" for line in final_state.get("errors", [])] or ["- None"]),
        "",
        "AI Decision Notes:",
        f"- Drafting strategy: {notes.get('drafting_notes', '') or 'None'}",
        f"- Headline: {final_state.get('generated_headline', '') or 'None'}",
        f"- Headline rationale: {notes.get('headline_reason', '') or 'None'}",
        f"- Skills selection rationale: {notes.get('skills_reason', '') or 'None'}",
        *(
            [f"- Skill category: {category.get('category', '')} -> {', '.join(category.get('items', []))}" for category in generated_skills]
            or ["- Skill category: None"]
        ),
        f"- Project selection rationale: {notes.get('project_selection_reason', '') or 'None'}",
        *(
            [
                f"- Project: {project.get('title', '')} | Selection reasoning: {project.get('selection_reason', '') or 'No per-project rationale provided.'}"
                for project in generated_projects
            ]
            or ["- Project: None"]
        ),
        "",
        "Run Artifacts:",
        f"- Preview PDF: {final_state.get('final_pdf_path', '') or 'Not generated'}",
        "",
        "ATS Breakdown:",
        f"- Overall: {final_state.get('ats_score', {}).get('overall', 'N/A')}",
        f"- Keyword Match: {final_state.get('ats_score', {}).get('keyword_match', {}).get('score', 'N/A')}",
        f"- Semantic Context: {final_state.get('ats_score', {}).get('semantic_context', {}).get('score', 'N/A')}",
        f"- Section Quality: {final_state.get('ats_score', {}).get('section_quality', {}).get('score', 'N/A')}",
        f"- Keyword Placement: {final_state.get('ats_score', {}).get('keyword_placement', {}).get('score', 'N/A')}",
        f"- Impact Metrics: {final_state.get('ats_score', {}).get('impact_metrics', {}).get('score', 'N/A')}",
        "",
        "LLM Log Files:",
        *([f"- {path}" for path in new_logs] or ["- None"]),
    ]
    return "\n".join(lines)


# ── GitHub profile preview (editable, parseable markers) ────────────────────
_PROFILE_MARKER_RE = re.compile(r"^<!-- resumeforge:profile (.+?) -->\s*$", re.MULTILINE)


def _render_profiles_preview(results: list) -> str:
    """Concatenate successful profiles with an editable, parseable file marker."""
    blocks = [
        f"<!-- resumeforge:profile {result.filename} -->\n{result.content.rstrip()}"
        for result in results
        if result.ok
    ]
    return "\n\n".join(blocks)


def _parse_profiles_preview(text: str) -> list[tuple[str, str]]:
    """Recover ``(filename, content)`` pairs from the (possibly edited) preview."""
    matches = list(_PROFILE_MARKER_RE.finditer(text or ""))
    pairs: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if name and content:
            pairs.append((name, content))
    return pairs


def _dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
