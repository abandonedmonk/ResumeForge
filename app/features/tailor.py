"""Shared tailoring orchestration — the headless pipeline behind both the CLI
(`resumeforge tailor`) and the MCP `tailor_resume` tool.

`run_tailor` runs the LangGraph agent, writes the run artifacts, and returns the
same payload dict the CLI has always built. Keeping it here means the CLI and MCP
share one code path instead of duplicating ~40 lines.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from app.agent.graph import run_agent
from app.features.receipt import build_receipt_from_state, render_receipt
from app.utils.config import get_config
from app.utils.run_store import new_run_dir, write_json


def run_tailor(jd_text: str, original_tex: str = "", branch: str = "", cold_read: bool = False) -> dict:
    """Tailor a resume headless and return a structured payload.

    ``original_tex`` is a path or LaTeX content (empty = use the configured template).
    ``branch`` (if given) persists the result to the branch store; ``cold_read`` also
    runs the zero-context read. The caller is responsible for validating inputs
    (e.g. branch-name validity) before calling.
    """
    config = get_config()
    run = new_run_dir(branch or "")
    initial_state = {
        "jd_text": jd_text,
        "original_resume_tex": original_tex,
        "skills_md": str(config["default_skills_md"]),
        "projects_context": str(config["default_projects_md"]),
        "output_folder": str(run),
    }
    final = run_agent(initial_state)

    (run / "resume.tex").write_text(final.get("final_tex", ""), encoding="utf-8")
    pdf_src = final.get("final_pdf_path", "")
    pdf_out = ""
    if pdf_src and Path(pdf_src).exists():
        shutil.copy2(pdf_src, run / "resume.pdf")
        pdf_out = str(run / "resume.pdf")

    receipt = build_receipt_from_state(final)
    write_json(run / "receipt.json", receipt)

    cold = None
    if cold_read:
        from app.features.cold_read import run_cold_read
        from app.utils.keyword_matcher import strip_latex_commands

        cold = run_cold_read(strip_latex_commands(final.get("final_tex", "")), jd_text)
        write_json(run / "cold-read.json", cold)

    branch_saved = None
    if branch:
        from app.features.branches import save_branch

        jd = final.get("jd_analysis", {})
        branch_saved = save_branch(
            branch,
            final.get("final_tex", ""),
            {
                "source": run.name,
                "jd_role": jd.get("role_title", ""),
                "jd_company": jd.get("company_name", ""),
                "ats": final.get("ats_score_summary", ""),
            },
        ).name

    return {
        "run_dir": str(run),
        "branch": branch_saved,
        "ats_summary": final.get("ats_score_summary", ""),
        "ats_score": final.get("ats_score", {}),
        "receipt": receipt,
        "cold_read": cold,
        "errors": final.get("errors", []),
        "artifacts": {
            "tex": str(run / "resume.tex"),
            "pdf": pdf_out,
            "receipt": str(run / "receipt.json"),
            "cold_read": str(run / "cold-read.json") if cold is not None else "",
        },
    }


def render_tailor(payload: dict) -> str:
    """Human-readable summary of a ``run_tailor`` payload (for the CLI)."""
    lines = [
        f"Run:  {payload.get('run_dir', '')}",
        f"ATS:  {payload.get('ats_summary') or 'n/a'}",
        "",
        render_receipt(payload.get("receipt", {})),
    ]
    cold = payload.get("cold_read")
    if cold is not None:
        from app.features.cold_read import render_cold_read

        lines += ["", render_cold_read(cold)]
    if payload.get("branch"):
        lines += ["", f"Saved to branch: {payload['branch']}"]
    lines += [f"  ! {error}" for error in payload.get("errors", [])]
    return "\n".join(lines)
