from __future__ import annotations

import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from app.agent.state import ResumeState
from app.utils.config import get_config
from app.utils.logger import log_error, log_status


def compile_tex_to_pdf(tex_content: str, destination: Path) -> str:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        tex_path = temp_path / "resume.tex"
        tex_path.write_text(tex_content, encoding="utf-8")
        combined_output = ""

        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", tex_path.name],
                cwd=temp_path,
                capture_output=True,
                text=True,
                check=False,
            )
            combined_output = (result.stdout or "") + "\n" + (result.stderr or "")

        pdf_path = temp_path / "resume.pdf"
        if not pdf_path.exists():
            raise RuntimeError(combined_output or "pdflatex did not generate a PDF file.")

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, destination)
        return combined_output


def compile_pdf(state: ResumeState) -> ResumeState:
    log_status(state, "Compiling PDF with pdflatex...")
    if not state["final_tex"].strip():
        log_error(state, "No LaTeX content available for PDF compilation.")
        return state

    try:
        config = get_config()
        output_dir = Path(state["output_folder"])
        preview_dir = output_dir / config.get("preview_folder_name", ".preview")
        preview_name = f"preview_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
        temp_pdf = preview_dir / preview_name
        latex_output = compile_tex_to_pdf(state["final_tex"], temp_pdf)
        state["final_pdf_path"] = str(temp_pdf)
        if any(token in latex_output.lower() for token in ("warning", "undefined", "error")):
            state["status_updates"].append(latex_output.strip())
    except FileNotFoundError:
        log_error(state, "pdflatex was not found on PATH. Make sure MiKTeX is available in your terminal.")
    except Exception as exc:
        log_error(state, f"PDF compilation failed: {exc}")

    return state
