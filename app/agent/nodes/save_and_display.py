from __future__ import annotations

from pathlib import Path

from app.agent.state import ResumeState
from app.agent.nodes.compile_pdf import compile_tex_to_pdf
from app.utils.config import get_config
from app.utils.file_namer import build_history_folder_name, build_output_basename, build_output_filename
from app.utils.logger import log_status


def save_and_display(state: ResumeState) -> ResumeState:
    log_status(state, "Preview ready. Waiting for approval before saving.")
    return state


def save_reviewed_output(state: ResumeState, reviewed_tex: str | None = None) -> ResumeState:
    log_status(state, "Saving approved output...")
    if not state["final_pdf_path"] and not reviewed_tex:
        return state

    output_dir = Path(state["output_folder"])
    output_dir.mkdir(parents=True, exist_ok=True)

    company_name = state["jd_analysis"].get("company_name", "Company")
    role_title = state["jd_analysis"].get("role_title", "Role")
    filename = build_output_filename(company_name, role_title)
    final_pdf_path = output_dir / filename
    tex_to_save = reviewed_tex if reviewed_tex is not None else state["final_tex"]

    if reviewed_tex is not None and reviewed_tex != state["final_tex"]:
        compile_tex_to_pdf(tex_to_save, final_pdf_path)
        state["final_tex"] = reviewed_tex
    else:
        preview_pdf = Path(state["final_pdf_path"])
        preview_pdf.replace(final_pdf_path)

    state["saved_pdf_path"] = str(final_pdf_path)

    config = get_config()
    if config.get("save_history", True):
        history_dir = output_dir / "history" / build_history_folder_name(company_name, role_title)
        history_dir.mkdir(parents=True, exist_ok=True)
        basename = build_output_basename(company_name, role_title)
        history_pdf = history_dir / f"{basename}.pdf"
        compile_tex_to_pdf(state["final_tex"], history_pdf)
        (history_dir / f"{basename}.tex").write_text(state["final_tex"], encoding="utf-8")
        (history_dir / "changes_report.md").write_text(state["changes_report_md"], encoding="utf-8")

    return state
