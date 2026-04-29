from __future__ import annotations

from app.agent.state import ResumeState
from app.parsers.latex_parser import parse_latex_resume
from app.parsers.projects_parser import parse_projects_source
from app.utils.logger import log_status


def parse_resume(state: ResumeState) -> ResumeState:
    log_status(state, "Parsing resume and project context...")
    state["resume_sections"] = parse_latex_resume(state["original_resume_tex"])
    if isinstance(state["projects_context"], str):
        state["projects_context"] = parse_projects_source(state["projects_context"])
    state["generated_headline"] = ""
    state["generated_skills"] = []
    state["generated_projects"] = []
    state["personalization_notes"] = {}
    return state
