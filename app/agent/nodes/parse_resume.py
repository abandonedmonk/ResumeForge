from __future__ import annotations

from app.agent.state import ResumeState
from app.parsers.latex_parser import parse_latex_resume
from app.parsers.projects_parser import parse_projects_source
from app.utils.logger import log_error, log_status


def parse_resume(state: ResumeState) -> ResumeState:
    log_status(state, "Parsing resume template and project context...")
    try:
        state["resume_sections"] = parse_latex_resume(state["original_resume_tex"])
        if isinstance(state["projects_context"], str):
            state["projects_context"] = parse_projects_source(state["projects_context"])
    except Exception as exc:
        log_error(state, f"Failed to parse resume template: {exc}")
        state["resume_sections"] = {}
        if isinstance(state["projects_context"], str):
            state["projects_context"] = {}
    return state
