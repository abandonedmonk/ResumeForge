"""ResumeForge command-line interface.

A thin ``argparse`` wrapper over the existing pipeline so ResumeForge runs
headless and installs as a ``resumeforge`` binary — in addition to the Gradio UI.
Every subcommand reuses the same engine the UI does; there is no parallel logic.

Commands:
    resumeforge ui         Launch the Gradio web app.
    resumeforge init       Check LaTeX + provider keys; scaffold .env.
    resumeforge tailor     Tailor a resume to a job description (headless).
    resumeforge cold-read  Adversarial zero-context read of a resume vs a JD.
    resumeforge roast      Brutally honest, shareable resume feedback.
    resumeforge gap        What your resume is missing vs your GitHub.
    resumeforge receipt    Show the compression receipt for a run.

Every result-producing command accepts ``--json`` to print a single machine-readable
JSON object to stdout (and nothing else) — this is what agent skills consume.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

if __package__ in {None, ""}:  # allow `python app/cli.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.config import ROOT_DIR, get_config, resolve_path


# ── shared helpers ──────────────────────────────────────────────────────────
def _emit(args: argparse.Namespace, payload: dict, human: str) -> None:
    """Print pure JSON when ``--json`` is set, otherwise the human-readable text."""
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(human)


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
    from app.features.tailor import render_tailor, run_tailor

    jd_text = load_jd(args.jd)
    if not jd_text:
        raise SystemExit("Provide a job description with --jd (file, URL, or text).")

    if args.branch:  # validate up front — don't run a full pipeline then crash on a bad name
        from app.features.branches import valid_name

        try:
            valid_name(args.branch)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

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

    if getattr(args, "template", None):
        from app.parsers.template_registry import list_templates
        from app.utils.config import update_session_overrides

        available = list_templates()
        if args.template not in available:
            raise SystemExit(
                f"Unknown template '{args.template}'. Available: {', '.join(available) or '(none)'}."
            )
        update_session_overrides({"resume_template": args.template})

    payload = run_tailor(jd_text, original_tex, branch=args.branch or "", cold_read=args.cold_read)
    _emit(args, payload, render_tailor(payload))
    return 1 if payload["errors"] else 0


def _cmd_cold_read(args: argparse.Namespace) -> int:
    from app.features.cold_read import render_cold_read, run_cold_read

    jd_text = load_jd(args.jd)
    if not jd_text:
        raise SystemExit("Provide a job description with --jd (file, URL, or text).")
    result = run_cold_read(resume_to_text(args.resume), jd_text)
    _emit(args, result, render_cold_read(result))
    return 0


def _cmd_roast(args: argparse.Namespace) -> int:
    from app.features.roast import parse_roast_pairs, run_roast

    jd_text = load_jd(args.jd) if args.jd else ""
    text = run_roast(resume_to_text(args.resume), jd_text)
    payload = {"roast_text": text, "items": parse_roast_pairs(text)}
    _emit(args, payload, text)
    return 0


def _cmd_gap(args: argparse.Namespace) -> int:
    import os

    from app.features.gap_finder import render_gap, run_gap_finder

    jd_text = load_jd(args.jd)
    if not jd_text:
        raise SystemExit("Provide a job description with --jd (file, URL, or text).")
    token = (args.token or os.getenv("GITHUB_API_TOKEN", "")).strip()
    result = run_gap_finder(args.github, resume_to_text(args.resume), jd_text, token=token)
    _emit(args, result, render_gap(result))
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
    data = read_json(receipt_path)
    payload = {"run": str(target), "receipt": data}
    _emit(args, payload, f"Run: {target}\n{render_receipt(data)}")
    return 0


def _seed_tex(args: argparse.Namespace) -> str:
    """Resolve the source LaTeX for `branch new` from --from / --from-run / --from-file,
    or the latest run when no source is given."""
    from app.features.branches import read_branch_tex
    from app.utils.run_store import latest_run_dir, run_dir

    if args.from_branch:
        tex = read_branch_tex(args.from_branch)
        if tex is None:
            raise SystemExit(f"Source branch not found: {args.from_branch}")
        return tex
    if args.from_run:
        target = run_dir(args.from_run)
        if target is None or not (target / "resume.tex").exists():
            raise SystemExit(f"Run not found or has no resume.tex: {args.from_run}")
        return (target / "resume.tex").read_text(encoding="utf-8")
    if args.from_file:
        path = Path(args.from_file)
        if not path.exists():
            raise SystemExit(f"File not found: {path}")
        return path.read_text(encoding="utf-8")
    latest = latest_run_dir()
    if latest is None or not (latest / "resume.tex").exists():
        raise SystemExit(
            "No source given and no prior run to seed from. Use --from <branch>, "
            "--from-run <id>, or --from-file <cv.tex>."
        )
    return (latest / "resume.tex").read_text(encoding="utf-8")


def _cmd_branch(args: argparse.Namespace) -> int:
    from app.features import branches

    action = getattr(args, "branch_action", None)
    if action == "new":
        tex = _seed_tex(args)
        source = args.from_branch or args.from_run or args.from_file or "latest-run"
        path = branches.save_branch(args.name, tex, {"source": source})
        print(f"Created branch '{branches.valid_name(args.name)}' at {path}")
        return 0
    if action == "list":
        items = branches.list_branches()
        _emit(args, {"branches": items}, branches.render_branch_list(items))
        return 0
    if action == "show":
        tex = branches.read_branch_tex(args.name)
        if tex is None:
            raise SystemExit(f"Branch not found: {args.name}")
        meta = branches.branch_meta(args.name)
        tex_path = str(branches.branch_dir(args.name) / "resume.tex")
        payload = {"meta": meta, "tex_path": tex_path}
        human = "\n".join(
            [
                f"Branch: {meta.get('name', args.name)}",
                f"  updated: {meta.get('updated_at', '?')}",
                f"  source:  {meta.get('source', '')}",
                f"  role:    {meta.get('jd_role', '') or 'n/a'}",
                f"  tex:     {tex_path}",
            ]
        )
        _emit(args, payload, human)
        return 0
    if action == "delete":
        if not branches.delete_branch(args.name):
            raise SystemExit(f"Branch not found: {args.name}")
        print(f"Deleted branch: {branches.valid_name(args.name)}")
        return 0
    raise SystemExit("Usage: resumeforge branch {new|list|show|delete} ...")


def _cmd_diff(args: argparse.Namespace) -> int:
    from app.features.branches import diff_branches, render_diff

    try:
        result = diff_branches(args.a, args.b)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    _emit(args, result, render_diff(result))
    return 0


# ── parser ──────────────────────────────────────────────────────────────────
def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable JSON object to stdout.")


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
    p_tailor.add_argument("--template", help="Named template under templates/ (e.g. classic, modern, cs, bio, academia).")
    p_tailor.add_argument("--jd", required=True, help="Job description: file path, posting URL, or raw text.")
    p_tailor.add_argument("--branch", help="Label this run (used in the run-id).")
    p_tailor.add_argument("--cold-read", action="store_true", help="Also write a zero-context cold-read.json.")
    _add_json_flag(p_tailor)
    p_tailor.set_defaults(func=_cmd_tailor)

    p_cold = sub.add_parser("cold-read", help="Adversarial zero-context read of a resume vs a JD.")
    p_cold.add_argument("--resume", required=True, help="Resume file (.pdf/.tex/.md/.txt).")
    p_cold.add_argument("--jd", required=True, help="Job description: file path, posting URL, or raw text.")
    _add_json_flag(p_cold)
    p_cold.set_defaults(func=_cmd_cold_read)

    p_roast = sub.add_parser("roast", help="Brutally honest, shareable resume feedback.")
    p_roast.add_argument("--resume", required=True, help="Resume file (.pdf/.tex/.md/.txt).")
    p_roast.add_argument("--jd", help="Optional JD (file/URL/text) for a fit-scoped roast.")
    _add_json_flag(p_roast)
    p_roast.set_defaults(func=_cmd_roast)

    p_gap = sub.add_parser("gap", help="What your resume is missing vs your GitHub.")
    p_gap.add_argument("--github", required=True, help="GitHub username.")
    p_gap.add_argument("--resume", required=True, help="Resume file (.pdf/.tex/.md/.txt).")
    p_gap.add_argument("--jd", required=True, help="Job description: file path, posting URL, or raw text.")
    p_gap.add_argument("--token", help="GitHub API token (or set GITHUB_API_TOKEN) to raise rate limits.")
    _add_json_flag(p_gap)
    p_gap.set_defaults(func=_cmd_gap)

    p_receipt = sub.add_parser("receipt", help="Show the compression receipt for a run.")
    p_receipt.add_argument("--run-id", help="Run id under ~/.resumeforge/runs (default: latest).")
    p_receipt.add_argument("--last", action="store_true", help="Use the most recent run (default).")
    _add_json_flag(p_receipt)
    p_receipt.set_defaults(func=_cmd_receipt)

    p_branch = sub.add_parser("branch", help="Manage resume branches (git-for-your-resume).")
    p_branch.set_defaults(func=_cmd_branch)
    b_sub = p_branch.add_subparsers(dest="branch_action")

    b_new = b_sub.add_parser("new", help="Create/overwrite a branch from a source.")
    b_new.add_argument("name", help="Branch name (e.g. ml-research).")
    b_src = b_new.add_mutually_exclusive_group()
    b_src.add_argument("--from", dest="from_branch", help="Seed from another branch.")
    b_src.add_argument("--from-run", help="Seed from a run id under ~/.resumeforge/runs.")
    b_src.add_argument("--from-file", help="Seed from a .tex file.")
    b_new.set_defaults(func=_cmd_branch)

    b_list = b_sub.add_parser("list", help="List branches.")
    _add_json_flag(b_list)
    b_list.set_defaults(func=_cmd_branch)

    b_show = b_sub.add_parser("show", help="Show a branch's metadata and tex path.")
    b_show.add_argument("name", help="Branch name.")
    _add_json_flag(b_show)
    b_show.set_defaults(func=_cmd_branch)

    b_del = b_sub.add_parser("delete", help="Delete a branch.")
    b_del.add_argument("name", help="Branch name.")
    b_del.set_defaults(func=_cmd_branch)

    p_diff = sub.add_parser("diff", help="Unified diff of two branches' resume.tex.")
    p_diff.add_argument("a", help="First branch name.")
    p_diff.add_argument("b", help="Second branch name.")
    _add_json_flag(p_diff)
    p_diff.set_defaults(func=_cmd_diff)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Emit UTF-8 regardless of the platform console (Windows defaults to cp1252,
    # which crashes on non-Latin-1 chars in resume text and breaks --json output).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
