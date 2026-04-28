from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agent.nodes.analyze_jd import analyze_jd
from app.agent.nodes.assemble_latex import assemble_latex
from app.agent.nodes.compile_pdf import compile_pdf
from app.agent.nodes.generate_projects import generate_projects
from app.agent.nodes.generate_report import generate_report
from app.agent.nodes.load_inputs import load_inputs
from app.agent.nodes.parse_resume import parse_resume
from app.agent.nodes.save_and_display import save_and_display
from app.agent.nodes.tailor_section import tailor_sections
from app.agent.nodes.validate_output import validate_output
from app.agent.state import ResumeState, default_state


def _should_stop_after_compile(state: ResumeState) -> str:
    if any("pdflatex" in error.lower() or "pdf compilation" in error.lower() for error in state["errors"]):
        return "error"
    return "continue"


def build_graph():
    graph = StateGraph(ResumeState)
    graph.add_node("load_inputs", load_inputs)
    graph.add_node("parse_resume", parse_resume)
    graph.add_node("analyze_jd", analyze_jd)
    graph.add_node("generate_projects", generate_projects)
    graph.add_node("tailor_sections", tailor_sections)
    graph.add_node("validate_output", validate_output)
    graph.add_node("assemble_latex", assemble_latex)
    graph.add_node("compile_pdf", compile_pdf)
    graph.add_node("generate_report", generate_report)
    graph.add_node("save_and_display", save_and_display)

    graph.set_entry_point("load_inputs")
    graph.add_edge("load_inputs", "parse_resume")
    graph.add_edge("parse_resume", "analyze_jd")
    graph.add_edge("analyze_jd", "generate_projects")
    graph.add_edge("generate_projects", "tailor_sections")
    graph.add_edge("tailor_sections", "validate_output")
    graph.add_edge("validate_output", "assemble_latex")
    graph.add_edge("assemble_latex", "compile_pdf")
    graph.add_conditional_edges(
        "compile_pdf",
        _should_stop_after_compile,
        {
            "continue": "generate_report",
            "error": END,
        },
    )
    graph.add_edge("generate_report", "save_and_display")
    graph.add_edge("save_and_display", END)
    return graph.compile()


def run_agent(initial_state: dict | None = None) -> ResumeState:
    state = default_state()
    if initial_state:
        state.update(initial_state)
    graph = build_graph()
    return graph.invoke(state)
