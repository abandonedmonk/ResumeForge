from __future__ import annotations

from app.agent.state import ResumeState
from app.utils.logger import log_error, log_status
from app.utils.validator import count_is_valid, escape_latex, preserves_numbers


def validate_output(state: ResumeState) -> ResumeState:
    log_status(state, "Validating tailored output...")
    known_projects = set(state["projects_context"].keys())
    _ = known_projects

    for section_name, tailored in state["tailored_sections"].items():
        original_bullets = list(state["resume_sections"][section_name].get("bullets", []))
        new_bullets = list(tailored.get("new_bullets", []))
        if not count_is_valid(original_bullets, new_bullets):
            log_error(state, f"Section '{section_name}' changed bullet count. Reverting to original bullets.")
            new_bullets = original_bullets
        if not preserves_numbers(original_bullets, new_bullets):
            log_error(state, f"Section '{section_name}' lost numeric metrics. Reverting to original bullets.")
            new_bullets = original_bullets

        tailored["new_bullets"] = [escape_latex(bullet) for bullet in new_bullets]

    return state
