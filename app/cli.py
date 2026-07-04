"""ResumeForge command-line interface.

A thin ``argparse`` wrapper over the existing pipeline so ResumeForge runs
headless and installs as a ``resumeforge`` binary — in addition to the Gradio UI.
Every subcommand reuses the same engine the UI does; there is no parallel logic.

Commands (grown phase by phase):
    resumeforge ui         Launch the Gradio web app.
    resumeforge init       Check LaTeX + provider keys; scaffold .env.
    resumeforge tailor     Tailor a resume to a job description (headless).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

if __package__ in {None, ""}:  # allow `python app/cli.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.config import ROOT_DIR, get_config, resolve_path


# ── shared input helpers (reused by later feature subcommands) ──────────────
def load_jd(value: str) -> str:
    """Resolve a ``--jd`` argument to text. A URL is passed through unchanged
    (the pipeline fetches it); an existing file is read; anything else is treated
    as raw JD text."""
    value = (value or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value  # load_inputs fetches URLs itself
    path = Path(value)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return value


def resume_to_text(path_str: str) -> str:
    """Best-effort plain text from a resume file (.pdf/.tex/.md/.txt), for the
    text-only features (roast / cold-read / gap)."""
    path = Path(path_str)
    if not path.exists():
        raise SystemExit(f"Resume file not found: {path}")
    if path.suffix.lower() == ".pdf":
        from app.integrations.resume_pdf import extract_pdf_text_and_links

        text, links = extract_pdf_text_and_links(path)
        if links:
            text = f"{text}\nLinks: " + " ".join(links)
        return text.strip()
    return path.read_text(encoding="utf-8").strip()


# ── commands ────────────────────────────────────────────────────────────────
def _cmd_ui(args: argparse.Namespace) -> int:
    import gradio as gr

    from app.main import build_ui

    config = get_config()
    demo = build_ui()
    demo.launch(
        theme=gr.themes.Soft(),
        inbrowser=bool(config.get("open_browser_on_launch", True)),
        server_name="0.0.0.0",
        server_port=int(config.get("gradio_port", 7860)),
        allowed_paths=[config["dest_folder"]] if config.get("dest_folder") else [],
    )
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    from app.llm.keypool import PROVIDER_ENV, available_providers
    from app.utils import tex_bootstrap

    # 1. .env scaffold
    env_path = ROOT_DIR / ".env"
    example_path = ROOT_DIR / ".env.example"
    if not env_path.exists() and example_path.exists():
        shutil.copyfile(example_path, env_path)
        print(f"Created {env_path} from .env.example — add your keys there.")
    elif env_path.exists():
        print(f".env present at {env_path}")

    # 2. LaTeX
    print("Checking LaTeX (pdflatex)...")
    pdflatex = tex_bootstrap.ensure_tex(auto_install=not args.no_install)
    print(f"  pdflatex: {pdflatex or 'NOT FOUND — install TeX or re-run without --no-install'}")

    # 3. Provider keys
    live = available_providers()
    if live:
        print("Provider keys detected: " + ", ".join(f"{p}({n})" for p, n in live.items()))
    else:
        print("No provider keys detected. Add at least one to .env:")
        for provider, env_name in PROVIDER_ENV.items():
            print(f"  {env_name}=   # {provider}")
    return 0


def _cmd_tailor(args: argparse.Namespace) -> int:
    from app.agent.graph import run_agent
    from app.utils.run_store import new_run_dir

    config = get_config()
    jd_text = load_jd(args.jd)
    if not jd_text:
        raise SystemExit("Provide a job description with --jd (file, URL, or text).")

    original_tex = ""
    if args.resume:
        resume_path = Path(args.resume)
        if resume_path.suffix.lower() != ".tex":
            raise SystemExit(
                "`tailor --resume` expects a .tex template. For a PDF/markdown resume, build your "
                "template first via `resumeforge ui` (Build My Profile), then re-run — or omit "
                "--resume to use your configured template."
            )
        original_tex = str(resolve_path(str(resume_path)))

    run = new_run_dir(args.branch or "")
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
    if pdf_src and Path(pdf_src).exists():
        shutil.copy2(pdf_src, run / "resume.pdf")

    from app.features.receipt import build_receipt_from_state, render_receipt
    from app.utils.run_store import write_json

    receipt = build_receipt_from_state(final)
    write_json(run / "receipt.json", receipt)

    print(f"Run:  {run}")
    print(f"ATS:  {final.get('ats_score_summary', 'n/a')}")
    print()
    print(render_receipt(receipt))

    if args.cold_read:
        from app.features.cold_read import render_cold_read, run_cold_read
        from app.utils.keyword_matcher import strip_latex_commands

        cold = run_cold_read(strip_latex_commands(final.get("final_tex", "")), jd_text)
        write_json(run / "cold-read.json", cold)
        print()
        print(render_cold_read(cold))

    for error in final.get("errors", []):
        print(f"  ! {error}")
    return 1 if final.get("errors") else 0


def _cmd_cold_read(args: argparse.Namespace) -> int:
    from app.features.cold_read import render_cold_read, run_cold_read

    jd_text = load_jd(args.jd)
    if not jd_text:
        raise SystemExit("Provide a job description with --jd (file, URL, or text).")
    result = run_cold_read(resume_to_text(args.resume), jd_text)
    print(render_cold_read(result))
    return 0


def _cmd_roast(args: argparse.Namespace) -> int:
    from app.features.roast import run_roast

    jd_text = load_jd(args.jd) if args.jd else ""
    print(run_roast(resume_to_text(args.resume), jd_text))
    return 0


def _cmd_gap(args: argparse.Namespace) -> int:
    import os

    from app.features.gap_finder import render_gap, run_gap_finder

    jd_text = load_jd(args.jd)
    if not jd_text:
        raise SystemExit("Provide a job description with --jd (file, URL, or text).")
    token = (args.token or os.getenv("GITHUB_API_TOKEN", "")).strip()
    result = run_gap_finder(args.github, resume_to_text(args.resume), jd_text, token=token)
    print(render_gap(result))
    return 0


def _cmd_receipt(args: argparse.Namespace) -> int:
    from app.features.receipt import render_receipt
    from app.utils.run_store import latest_run_dir, read_json, run_dir

    target = run_dir(args.run_id) if args.run_id else latest_run_dir()
    if target is None:
        raise SystemExit("No matching run found under ~/.resumeforge/runs.")
    receipt_path = target / "receipt.json"
    if not receipt_path.exists():
        raise SystemExit(f"No receipt.json in {target}.")
    print(f"Run: {target}")
    print(render_receipt(read_json(receipt_path)))
    return 0


# ── parser ──────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resumeforge",
        description="Free-tier AI resume engine - tailor, roast, cold-read, and gap-analyse resumes.",
    )
    sub = parser.add_subparsers(dest="command")

    p_ui = sub.add_parser("ui", help="Launch the Gradio web app.")
    p_ui.set_defaults(func=_cmd_ui)

    p_init = sub.add_parser("init", help="Check LaTeX + provider keys; scaffold .env.")
    p_init.add_argument("--no-install", action="store_true", help="Do not auto-install TinyTeX.")
    p_init.set_defaults(func=_cmd_init)

    p_tailor = sub.add_parser("tailor", help="Tailor a resume to a job description.")
    p_tailor.add_argument("--resume", help="Path to a .tex template (optional; defaults to configured template).")
    p_tailor.add_argument("--jd", required=True, help="Job description: file path, posting URL, or raw text.")
    p_tailor.add_argument("--branch", help="Label this run (used in the run-id).")
    p_tailor.add_argument("--cold-read", action="store_true", help="Also write a zero-context cold-read.json.")
    p_tailor.set_defaults(func=_cmd_tailor)

    p_cold = sub.add_parser("cold-read", help="Adversarial zero-context read of a resume vs a JD.")
    p_cold.add_argument("--resume", required=True, help="Resume file (.pdf/.tex/.md/.txt).")
    p_cold.add_argument("--jd", required=True, help="Job description: file path, posting URL, or raw text.")
    p_cold.set_defaults(func=_cmd_cold_read)

    p_roast = sub.add_parser("roast", help="Brutally honest, shareable resume feedback.")
    p_roast.add_argument("--resume", required=True, help="Resume file (.pdf/.tex/.md/.txt).")
    p_roast.add_argument("--jd", help="Optional JD (file/URL/text) for a fit-scoped roast.")
    p_roast.set_defaults(func=_cmd_roast)

    p_gap = sub.add_parser("gap", help="What your resume is missing vs your GitHub.")
    p_gap.add_argument("--github", required=True, help="GitHub username.")
    p_gap.add_argument("--resume", required=True, help="Resume file (.pdf/.tex/.md/.txt).")
    p_gap.add_argument("--jd", required=True, help="Job description: file path, posting URL, or raw text.")
    p_gap.add_argument("--token", help="GitHub API token (or set GITHUB_API_TOKEN) to raise rate limits.")
    p_gap.set_defaults(func=_cmd_gap)

    p_receipt = sub.add_parser("receipt", help="Show the compression receipt for a run.")
    p_receipt.add_argument("--run-id", help="Run id under ~/.resumeforge/runs (default: latest).")
    p_receipt.add_argument("--last", action="store_true", help="Use the most recent run (default).")
    p_receipt.set_defaults(func=_cmd_receipt)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
