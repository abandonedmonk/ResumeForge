from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agent.nodes.analyze_jd import analyze_jd
from app.agent.nodes.assemble_latex import assemble_latex
from app.agent.nodes.compile_pdf import compile_pdf
from app.agent.nodes.enforce_one_page import enforce_one_page
from app.agent.nodes.enrich_company import enrich_company
from app.agent.nodes.generate_cover_letter import generate_cover_letter
from app.agent.nodes.generate_docx import generate_docx
from app.agent.nodes.generate_projects import generate_projects
from app.agent.nodes.generate_report import generate_report
from app.agent.nodes.load_inputs import load_inputs
from app.agent.nodes.parse_resume import parse_resume
from app.agent.nodes.save_and_display import save_and_display
from app.agent.nodes.score_original import score_original
from app.agent.nodes.score_resume import score_resume
from app.agent.nodes.tailor_section import tailor_sections
from app.agent.nodes.validate_output import validate_output
from app.agent.state import ResumeState, default_state
from app.utils.config import get_config


def _should_stop_after_compile(state: ResumeState) -> str:
    if any("pdflatex" in error.lower() or "pdf compilation" in error.lower() for error in state["errors"]):
        return "error"
    return "continue"


def _should_optimize(state: ResumeState) -> str:
    """Decide whether to re-tailor for a higher ATS score. Stops on target met,
    iteration cap, or a plateau (no gain over the previous pass) so the loop
    always terminates."""
    config = get_config()
    if not config.get("auto_optimize", True):
        return "done"
    scores = state.get("optimization_scores", [])
    if not scores:
        return "done"
    overall = int(scores[-1])
    threshold = int(config.get("auto_optimize_threshold", 80))
    max_iterations = int(config.get("max_optimize_iterations", 3))
    iteration = int(state.get("optimization_iteration", 0))

    if overall >= threshold:
        return "done"
    if iteration >= max_iterations:
        return "done"
    if len(scores) >= 2 and scores[-1] <= scores[-2]:
        return "done"  # plateau — another pass is unlikely to help
    return "retry"


def build_graph():
    graph = StateGraph(ResumeState)
    graph.add_node("load_inputs", load_inputs)
    graph.add_node("parse_resume", parse_resume)
    graph.add_node("analyze_jd", analyze_jd)
    graph.add_node("score_original", score_original)
    graph.add_node("enrich_company", enrich_company)
    graph.add_node("generate_projects", generate_projects)
    graph.add_node("tailor_sections", tailor_sections)
    graph.add_node("validate_output", validate_output)
    graph.add_node("assemble_latex", assemble_latex)
    graph.add_node("compile_pdf", compile_pdf)
    graph.add_node("enforce_one_page", enforce_one_page)
    graph.add_node("score_resume", score_resume)
    graph.add_node("generate_report", generate_report)
    graph.add_node("generate_cover_letter", generate_cover_letter)
    graph.add_node("generate_docx", generate_docx)
    graph.add_node("save_and_display", save_and_display)

    graph.set_entry_point("load_inputs")
    graph.add_edge("load_inputs", "parse_resume")
    graph.add_edge("parse_resume", "analyze_jd")
    graph.add_edge("analyze_jd", "score_original")
    graph.add_edge("score_original", "enrich_company")
    graph.add_edge("enrich_company", "generate_projects")
    graph.add_edge("generate_projects", "tailor_sections")
    graph.add_edge("tailor_sections", "validate_output")
    graph.add_edge("validate_output", "assemble_latex")
    graph.add_edge("assemble_latex", "compile_pdf")
    graph.add_conditional_edges(
        "compile_pdf",
        _should_stop_after_compile,
        {
            "continue": "enforce_one_page",
            "error": END,
        },
    )
    graph.add_edge("enforce_one_page", "score_resume")
    graph.add_conditional_edges(
        "score_resume",
        _should_optimize,
        {
            # Retry loops back to generate_projects — that node holds each project's
            # full body, the grounding source for surfacing real missing keywords.
            "retry": "generate_projects",
            "done": "generate_report",
        },
    )
    graph.add_edge("generate_report", "generate_cover_letter")
    graph.add_edge("generate_cover_letter", "generate_docx")
    graph.add_edge("generate_docx", "save_and_display")
    graph.add_edge("save_and_display", END)
    return graph.compile()


def run_agent(initial_state: dict | None = None) -> ResumeState:
    state = default_state()
    if initial_state:
        state.update(initial_state)
    graph = build_graph()
    # recursion_limit raised: the optimization loop can revisit nodes several times.
    return graph.invoke(state, config={"recursion_limit": 50})
