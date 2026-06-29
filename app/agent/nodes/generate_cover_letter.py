"""Optional cover-letter node. No-op unless ``generate_cover_letter`` is enabled.

Kept opt-in (default off) because it's an extra LLM call. Enabled via the
``generate_cover_letter`` config key or a per-run session override from the UI.
"""
from __future__ import annotations

from app.agent.state import ResumeState
from app.llm.router import RoutedStage2Model
from app.prompts.cover_letter import build_cover_letter_prompt
from app.utils.config import get_config
from app.utils.logger import log_error, log_status


def generate_cover_letter(state: ResumeState) -> ResumeState:
    if not get_config().get("generate_cover_letter", False):
        return state

    log_status(state, "Generating cover letter...")
    highlights = {
        "headline": state.get("generated_headline", ""),
        "skills": state.get("generated_skills", []),
        "projects": [
            {"title": project.get("title", ""), "bullets": project.get("bullets", [])}
            for project in state.get("generated_projects", [])
        ],
    }
    try:
        system_prompt, user_prompt = build_cover_letter_prompt(
            state["skills_md"], state.get("jd_analysis", {}), highlights
        )
        response = RoutedStage2Model(task="cover_letter").call(system_prompt, user_prompt)
        cleaned = response.strip().replace("```markdown", "").replace("```", "").strip()
        state["cover_letter_md"] = cleaned
        log_status(state, "Cover letter ready.")
    except Exception as exc:
        log_error(state, f"Cover letter generation failed: {exc}")
        state["cover_letter_md"] = ""
    return state
