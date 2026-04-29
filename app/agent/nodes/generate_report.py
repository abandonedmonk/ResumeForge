from __future__ import annotations

from app.agent.state import ResumeState
from app.llm.router import RoutedStage2Model
from app.prompts.generate_report import build_report_prompt
from app.utils.logger import log_error, log_status


def _fallback_report(changes_log: list[dict], ats_score: dict | None = None) -> str:
    sections: list[str] = ["# ResumeForge Changes Report", ""]
    if ats_score:
        sections.append("## ATS Score")
        sections.append(f"- Overall: {ats_score.get('overall', 'N/A')}%")
        sections.append(f"- Keyword Match: {ats_score.get('keyword_match', {}).get('score', 'N/A')}%")
        sections.append(f"- Semantic Context: {ats_score.get('semantic_context', {}).get('score', 'N/A')}%")
        sections.append(f"- Section Quality: {ats_score.get('section_quality', {}).get('score', 'N/A')}%")
        sections.append(f"- Keyword Placement: {ats_score.get('keyword_placement', {}).get('score', 'N/A')}%")
        sections.append(f"- Impact Metrics: {ats_score.get('impact_metrics', {}).get('score', 'N/A')}%")
        sections.append("")
        recommendations = ats_score.get("recommendations", [])
        if recommendations:
            sections.append("### Recommendations")
            sections.extend(f"- {recommendation}" for recommendation in recommendations)
            sections.append("")
    for change in changes_log:
        sections.append(f"## {change['section']}")
        sections.append("### Before")
        sections.extend(f"- {bullet}" for bullet in change["old_bullets"])
        sections.append("")
        sections.append("### After")
        sections.extend(f"- {bullet}" for bullet in change["new_bullets"])
        sections.append("")
        sections.append(f"Reasoning: {change['reasoning']}")
        sections.append("")
    return "\n".join(sections)


def generate_report(state: ResumeState) -> ResumeState:
    log_status(state, "Generating changes report...")
    try:
        system_prompt, user_prompt = build_report_prompt(state["changes_log"], state.get("ats_score"))
        state["changes_report_md"] = RoutedStage2Model().call(system_prompt, user_prompt)
    except Exception as exc:
        log_error(state, f"Falling back to local report generation: {exc}")
        state["changes_report_md"] = _fallback_report(state["changes_log"], state.get("ats_score"))
    return state
