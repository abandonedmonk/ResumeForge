from __future__ import annotations

from app.agent.state import ResumeState
from app.parsers.latex_assembler import inject_resume_personalization, inject_sections
from app.utils.logger import log_error, log_status


def assemble_latex(state: ResumeState) -> ResumeState:
    log_status(state, "Assembling final LaTeX document...")
    try:
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
    except Exception as exc:
        log_error(state, f"LaTeX assembly failed: {exc}. Falling back to original template.")
        state["final_tex"] = state["original_resume_tex"]
    return state
