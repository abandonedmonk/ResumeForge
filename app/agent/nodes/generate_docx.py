"""Build a clean ATS-friendly .docx alongside the PDF (no LLM cost, always runs)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.agent.state import ResumeState
from app.parsers.docx_builder import build_docx
from app.utils.config import get_config
from app.utils.logger import log_error, log_status


def generate_docx(state: ResumeState) -> ResumeState:
    if not state.get("final_tex", "").strip():
        return state
    log_status(state, "Building DOCX export...")
    try:
        config = get_config()
        preview_dir = Path(state["output_folder"]) / config.get("preview_folder_name", ".preview")
        docx_path = preview_dir / f"resume_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.docx"
        build_docx(state, docx_path)
        state["final_docx_path"] = str(docx_path)
        log_status(state, "DOCX export ready.")
    except Exception as exc:
        log_error(state, f"DOCX export failed: {exc}")
        state["final_docx_path"] = ""
    return state
