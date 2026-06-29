from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from app.agent.state import ResumeState
from app.utils.config import get_config
from app.utils.logger import log_error, log_status

_PAGE_COUNT_RE = re.compile(r"Output written on .*?\((\d+) pages?", re.IGNORECASE)


def parse_page_count(latex_output: str) -> int | None:
    """Return the page count pdflatex reported, or None if not found."""
    match = _PAGE_COUNT_RE.search(latex_output or "")
    return int(match.group(1)) if match else None


def compile_tex_to_pdf(tex_content: str, destination: Path) -> str:
    temp_dir = tempfile.mkdtemp(prefix="resumeforge_")
    try:
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
                timeout=60,
            )
            combined_output = (result.stdout or "") + "\n" + (result.stderr or "")

        pdf_path = temp_path / "resume.pdf"
        if not pdf_path.exists():
            raise RuntimeError(combined_output or "pdflatex did not generate a PDF file.")

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, destination)
        return combined_output
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def compile_final(state: ResumeState) -> str:
    """Compile ``state['final_tex']`` to a fresh preview PDF; update path + page count.

    Shared by the ``compile_pdf`` node and the one-page enforcer so re-compiles
    after trimming go through the same code path. Raises on compile failure.
    """
    config = get_config()
    output_dir = Path(state["output_folder"])
    preview_dir = output_dir / config.get("preview_folder_name", ".preview")
    preview_name = f"preview_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
    temp_pdf = preview_dir / preview_name
    latex_output = compile_tex_to_pdf(state["final_tex"], temp_pdf)
    state["final_pdf_path"] = str(temp_pdf)
    state["page_count"] = parse_page_count(latex_output) or state.get("page_count", 1) or 1
    return latex_output


def compile_pdf(state: ResumeState) -> ResumeState:
    log_status(state, "Compiling PDF with pdflatex...")
    if not state["final_tex"].strip():
        log_error(state, "No LaTeX content available for PDF compilation.")
        return state

    try:
        latex_output = compile_final(state)
        # pdflatex flags real errors with lines beginning "!" or "LaTeX Error:".
        if any(
            line.lstrip().startswith("!") or "LaTeX Error:" in line
            for line in latex_output.splitlines()
        ):
            state["status_updates"].append(latex_output.strip())
    except FileNotFoundError:
        log_error(state, "pdflatex was not found on PATH. Make sure MiKTeX is available in your terminal.")
    except subprocess.TimeoutExpired:
        log_error(state, "PDF compilation timed out after 60s. The LaTeX template may have an infinite loop.")
    except Exception as exc:
        log_error(state, f"PDF compilation failed: {exc}")

    return state
