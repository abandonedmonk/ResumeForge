from __future__ import annotations

from app.agent.nodes.score_resume import compute_ats_score
from app.agent.state import ResumeState
from app.utils.logger import log_status


def score_original(state: ResumeState) -> ResumeState:
    """Score the untailored starting resume so the report can show a before->after
    delta. For a freshly-cloned generic template the baseline is naturally low —
    that is the honest 'before'."""
    if not state.get("original_resume_tex", "").strip():
        return state
    log_status(state, "Scoring the original resume to establish a baseline...")
    state["original_ats_score"] = compute_ats_score(
        state["original_resume_tex"], state["jd_analysis"], state
    )
    return state
