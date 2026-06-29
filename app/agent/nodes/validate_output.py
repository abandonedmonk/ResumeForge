from __future__ import annotations

from app.agent.state import ResumeState
from app.utils.logger import log_error, log_status
from app.utils.validator import count_is_valid, escape_latex, preserves_numbers


def _revert_changes_log(state: ResumeState, section_name: str, original_bullets: list[str], reason: str) -> None:
    for entry in state["changes_log"]:
        if entry.get("section") == section_name:
            entry["new_bullets"] = list(original_bullets)
            entry["reasoning"] = reason


def validate_output(state: ResumeState) -> ResumeState:
    log_status(state, "Validating tailored output...")

    for section_name, tailored in state["tailored_sections"].items():
        original_bullets = list(state["resume_sections"][section_name].get("bullets", []))
        new_bullets = list(tailored.get("new_bullets", []))
        reverted = False
        if not count_is_valid(original_bullets, new_bullets):
            log_error(state, f"Section '{section_name}' changed bullet count. Reverting to original bullets.")
            new_bullets = original_bullets
            reverted = True
        if not preserves_numbers(original_bullets, new_bullets):
            log_error(state, f"Section '{section_name}' lost numeric metrics. Reverting to original bullets.")
            new_bullets = original_bullets
            reverted = True

        if reverted:
            _revert_changes_log(
                state, section_name, original_bullets,
                "Reverted to original bullets during validation (count or metric mismatch).",
            )

        tailored["new_bullets"] = [escape_latex(bullet) for bullet in new_bullets]

    return state
