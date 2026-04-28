from __future__ import annotations

from app.agent.state import ResumeState
from app.parsers.latex_assembler import inject_resume_personalization, inject_sections
from app.utils.logger import log_status


def assemble_latex(state: ResumeState) -> ResumeState:
    log_status(state, "Assembling final LaTeX...")
    final_tex = inject_sections(
        state["original_resume_tex"],
        state["resume_sections"],
        state["tailored_sections"],
    )
    state["final_tex"] = inject_resume_personalization(
        final_tex,
        state["generated_headline"],
        state["generated_skills"],
        state["generated_projects"],
    )
    return state
