"""Local stdio MCP server exposing ResumeForge as typed tools.

Optional (`pip install -e ".[mcp]"`). Every tool is a thin wrapper over the same
functions the CLI uses — no separate engine. Run it as ``resumeforge-mcp`` (or
``python -m app.mcp_server``) and point an MCP client at it:

    {"mcpServers": {"resumeforge": {"command": "resumeforge-mcp"}}}

``jd`` / ``resume`` arguments accept raw text, a file path, or (for ``jd``) a URL —
they go through the same resolvers the CLI uses.
"""
from __future__ import annotations

from pathlib import Path


def _import_fastmcp():
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised only without the extra
        raise SystemExit(
            "The MCP server needs the optional 'mcp' dependency. Install it with:\n"
            "  pip install \"resumeforge[mcp]\"   (or: pip install mcp)"
        ) from exc
    return FastMCP


def build_server():
    """Construct the FastMCP server with all ResumeForge tools registered."""
    from app.cli import load_jd, resume_to_text

    FastMCP = _import_fastmcp()
    mcp = FastMCP("resumeforge")

    @mcp.tool()
    def compile_latex(tex: str, out_path: str = "") -> dict:
        """Compile LaTeX source to a PDF. Returns the output path and page count."""
        from app.agent.nodes.compile_pdf import compile_tex_to_pdf, parse_page_count
        from app.utils.run_store import new_run_dir

        destination = Path(out_path) if out_path else (new_run_dir("compile") / "resume.pdf")
        try:
            log = compile_tex_to_pdf(tex, destination)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "pdf_path": str(destination),
            "pages": parse_page_count(log),
            "log_tail": "\n".join(log.splitlines()[-15:]),
        }

    @mcp.tool()
    def tailor_resume(jd: str, resume_tex: str = "", branch: str = "", cold_read: bool = False) -> dict:
        """Tailor a resume to a job description. Writes artifacts under ~/.resumeforge/runs/."""
        from app.features.tailor import run_tailor

        return run_tailor(load_jd(jd), resume_tex, branch=branch, cold_read=cold_read)

    @mcp.tool()
    def roast_resume(resume: str, jd: str = "") -> dict:
        """Brutally honest, shareable resume feedback ([ROAST] -> [FIX])."""
        from app.features.roast import parse_roast_pairs, run_roast

        text = run_roast(resume_to_text(resume) if _is_path(resume) else resume, load_jd(jd) if jd else "")
        return {"roast_text": text, "items": parse_roast_pairs(text)}

    @mcp.tool()
    def cold_read(resume: str, jd: str) -> dict:
        """Adversarial zero-context read: targeted role / strongest fit / biggest gap."""
        from app.features.cold_read import run_cold_read

        return run_cold_read(resume_to_text(resume) if _is_path(resume) else resume, load_jd(jd))

    @mcp.tool()
    def find_github_gap(github_user: str, resume: str, jd: str, token: str = "") -> dict:
        """What the resume is missing vs the user's actual GitHub work."""
        import os

        from app.features.gap_finder import run_gap_finder

        resolved = resume_to_text(resume) if _is_path(resume) else resume
        gh_token = (token or os.getenv("GITHUB_API_TOKEN", "")).strip()
        return run_gap_finder(github_user, resolved, load_jd(jd), token=gh_token)

    @mcp.tool()
    def compression_receipt(original_tex: str, tailored_tex: str, jd_keywords: list[str] | None = None) -> dict:
        """Auditable diff between an original and tailored resume (local, no LLM)."""
        from app.features.receipt import build_receipt

        return build_receipt(original_tex, tailored_tex, {"keywords": jd_keywords or []})

    return mcp


def _is_path(value: str) -> bool:
    """Treat a short, newline-free string that points at an existing file as a path."""
    if not value or "\n" in value or len(value) > 400:
        return False
    return Path(value).is_file()


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
