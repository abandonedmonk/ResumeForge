"""Gradio callback functions for ResumeForge — the logic bound to buttons in
``app.main.build_ui``. Presentation is delegated to ``app.ui.render``.
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import gradio as gr
import yaml

from app.agent.graph import run_agent
from app.agent.nodes.save_and_display import save_reviewed_output
from app.integrations.profile_builder import import_profiles
from app.integrations.profile_store import imported_dir, list_profiles, save_named
from app.integrations.resume_import import import_profile_from_pdf
from app.integrations.skills_refresh import append_missing, missing_against, suggestions_markdown
from app.llm.keystore import clear_session_keys, set_session_keys
from app.llm.router import RoutedStage2Model
from app.parsers.profile_template_builder import build_personal_template
from app.parsers.projects_parser import parse_projects_source
from app.profiles.profile_store import assets_dir, load_profile, save_personal_template, save_profile
from app.profiles.schema import Profile
from app.ui.render import (
    _ats_analysis_markdown,
    _before_after_html,
    _build_run_log_content,
    _dump_yaml,
    _parse_profiles_preview,
    _render_profiles_preview,
    _safe_file_output,
    _score_badge_html,
)
from app.utils.config import (
    clear_session_overrides,
    get_config,
    resolve_path,
    set_session_overrides,
)
from app.utils.file_namer import build_log_stem
from app.utils.logger import get_logs_dir, log_error, log_status, write_run_log


# ── Full Generator ─────────────────────────────────────────────────────────
def _run_resumeforge(
    output_folder: str,
    stage1_model: str,
    stage2_model: str,
    enrich_with_web_search: bool,
    jd_text_override: str = "",
    model_tier: str = "free",
    openai_key: str = "",
    anthropic_key: str = "",
    generate_cover_letter: bool = False,
):
    set_session_keys({"OPENAI_API_KEY": openai_key, "ANTHROPIC_API_KEY": anthropic_key})
    set_session_overrides(
        {
            "stage1_model": stage1_model,
            "stage2_model": stage2_model,
            "enrich_with_web_search": enrich_with_web_search,
            "model_tier": model_tier,
            "generate_cover_letter": generate_cover_letter,
        }
    )
    try:
        return _run_resumeforge_inner(output_folder, jd_text_override)
    finally:
        clear_session_overrides()
        clear_session_keys()


def _run_resumeforge_inner(output_folder: str, jd_text_override: str = ""):
    config = get_config()
    logs_before = {path.name for path in get_logs_dir().glob("*.log")}
    session_state: dict[str, Any] = {"status_updates": [], "errors": []}
    log_status(session_state, "Starting ResumeForge preview generation...")

    # Use pasted JD if provided, otherwise fall back to the file in config
    if jd_text_override and jd_text_override.strip():
        jd_text = jd_text_override.strip()
        log_status(session_state, "Using pasted Job Description text.")
    else:
        jd_text = resolve_path(config.get("default_jd_txt", "")).read_text(encoding="utf-8") if config.get("default_jd_txt", "") else ""
        log_status(session_state, f"Using JD file: {config.get('default_jd_txt', 'N/A')}")

    initial_state = {
        "jd_text": jd_text,
        "original_resume_tex": str(config["default_resume_tex"]),
        "skills_md": str(config["default_skills_md"]),
        "projects_context": str(config["default_projects_md"]),
        "output_folder": output_folder,
        "status_updates": session_state["status_updates"],
        "errors": session_state["errors"],
    }
    final_state = run_agent(initial_state)
    new_logs = sorted(path for path in get_logs_dir().glob("*.log") if path.name not in logs_before)
    run_log_content = _build_run_log_content(final_state, new_logs)
    company_name = str(final_state.get("jd_analysis", {}).get("company_name", "Company"))
    role_title = str(final_state.get("jd_analysis", {}).get("role_title", "Role"))
    run_log_name = f"{build_log_stem(company_name, role_title, suffix='run')}.log"
    run_log_path = write_run_log(run_log_name, run_log_content)
    final_state["run_log_path"] = str(run_log_path)
    final_state["run_log_paths"] = [str(path) for path in new_logs] + [str(run_log_path)]
    status_text = "\n".join(final_state["status_updates"]) or "No status updates."
    errors_text = "\n".join(final_state["errors"]) or "No errors."
    return (
        _score_badge_html(final_state.get("ats_score_summary", ""), final_state.get("ats_score", {})),
        _before_after_html(final_state.get("original_ats_score", {}), final_state.get("ats_score", {})),
        _ats_analysis_markdown(final_state.get("ats_score", {}), final_state.get("skills_gap", {})),
        final_state["changes_report_md"],
        final_state["final_tex"],
        _safe_file_output(final_state.get("final_pdf_path")),
        status_text,
        errors_text,
        run_log_content,
        final_state,
        final_state.get("cover_letter_md", "") or "_Cover letter not enabled for this run._",
        _safe_file_output(final_state.get("final_docx_path")),
    )


def _apply_ai_edit_request(current_latex: str, edit_request: str, stage2_model: str, output_folder: str) -> tuple[str, str, Any]:
    if not current_latex.strip():
        return current_latex, "No LaTeX preview available yet.", None
    if not edit_request.strip():
        return current_latex, "Enter an edit request first.", None

    config = get_config()
    skills_md = resolve_path(config["default_skills_md"]).read_text(encoding="utf-8")
    session_state: dict[str, Any] = {"status_updates": [], "errors": []}
    log_status(session_state, "Applying AI edit request to LaTeX preview...")
    system_prompt = (
        f"{skills_md}\n\n"
        "You are editing a LaTeX resume file. Return the full updated LaTeX only. "
        "Preserve structure unless the request explicitly changes it."
    )
    user_prompt = f"""
Edit request:
{edit_request}

Current LaTeX resume:
{current_latex}
""".strip()
    set_session_overrides({"stage2_model": stage2_model})
    try:
        updated = RoutedStage2Model().call(system_prompt, user_prompt)
    except Exception as exc:
        log_error(session_state, f"AI edit request failed: {exc}")
        return current_latex, "\n".join(session_state["errors"]), None
    finally:
        clear_session_overrides()
    cleaned = updated.strip()
    if "```" in cleaned:
        cleaned = cleaned.replace("```latex", "").replace("```tex", "").replace("```", "").strip()
    # Strip any prose the LLM may have prepended before \documentclass
    doc_idx = cleaned.find(r"\documentclass")
    if doc_idx > 0:
        cleaned = cleaned[doc_idx:]

    # Recompile to update the PDF preview
    new_pdf_path: str | None = None
    try:
        from app.agent.nodes.compile_pdf import compile_tex_to_pdf
        preview_dir = Path(output_folder) / config.get("preview_folder_name", ".preview")
        preview_name = f"edit_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
        temp_pdf = preview_dir / preview_name
        compile_tex_to_pdf(cleaned, temp_pdf)
        new_pdf_path = str(temp_pdf)
        log_status(session_state, "Applied AI edit and recompiled PDF preview.")
    except Exception as exc:
        log_error(session_state, f"PDF recompile after edit failed: {exc}")
        log_status(session_state, "Applied AI edit request to the preview. Review the LaTeX before saving.")

    return cleaned, "\n".join(session_state["status_updates"] + session_state["errors"]), new_pdf_path


def _save_preview(final_state: dict, reviewed_latex: str):
    if not final_state:
        return None, "No preview is loaded yet.", final_state

    updated_state = save_reviewed_output(final_state, reviewed_latex)
    saved_path = updated_state.get("saved_pdf_path", "")
    if not saved_path:
        errors = "\n".join(updated_state.get("errors", [])) or "Save failed."
        return None, errors, updated_state
    safe_path = _safe_file_output(saved_path)
    if not safe_path:
        return None, f"Expected a saved PDF file but got: {saved_path}", updated_state
    return safe_path, f"Saved approved PDF to {safe_path}", updated_state


# ── Archetype Matcher ──────────────────────────────────────────────────────
def _quick_match_jd(jd_text: str, model: str) -> str:
    if not jd_text.strip():
        return "⚠️ Please paste a Job Description first."

    from app.llm.router import RoutedStage1Model

    system_prompt = """You are an expert tech recruiter routing applications.
The candidate has 5 pre-made 'Archetype' resumes ready to go. Each contains exactly 3 specific projects:

1. **GenAI / Agent Engineer**
   - Projects: AskAlpha, Ironclad Agent, CLIGenix
   - Best for: LLM apps, agentic workflows, RAG, prompt engineering.
2. **Computer Vision Engineer**
   - Projects: FCOSCraterNet, Food Package Freshness, Autonomous Navigation
   - Best for: Image processing, object detection, Deep Learning, visual AI.
3. **MLOps / AI Infrastructure Engineer**
   - Projects: MLOps Heart Disease, Ironclad Agent, AskAlpha
   - Best for: CI/CD, pipelines, deployment, Docker, systems, backend AI.
4. **AI / Applied Researcher**
   - Projects: Hybrid Quantum-Classical, FCOSCraterNet, CLIGenix
   - Best for: Heavy math, custom architecture, fine-tuning, algorithm research.
5. **Edge AI / Robotics Engineer**
   - Projects: Autonomous Navigation, Food Package Freshness, Ironclad Agent
   - Best for: Hardware, C++, real-time inference, Rust, robotics, embedded.

Analyze the Job Description. Pick the SINGLE best Archetype for this role.
Return your answer formatted EXACTLY like this (use Markdown):

### Recommended Resume: [Archetype Name]
**Why:** [2-3 sentences explaining exactly why this archetype fits the JD's core requirements, explicitly mentioning how the 3 included projects align with the role.]
"""
    try:
        from app.utils.config import get_config
        config = get_config()
        # Temporarily override stage1_model for this call
        config["stage1_model"] = model
        response = RoutedStage1Model().call(system_prompt, f"Job Description:\n{jd_text}")
        return response.strip()
    except Exception as exc:
        return f"**Error matching JD:** {exc}"


# ── GitHub Profile Builder ─────────────────────────────────────────────────
def _list_imported_markdown() -> str:
    paths = list_profiles()
    if not paths:
        return "_No imported profiles yet. Once you import any, they replace the bundled examples._"
    listing = "\n".join(f"- `{path.name}`" for path in paths)
    return (
        f"**Imported profiles** (in `{imported_dir()}`) — used instead of the bundled "
        f"examples once present:\n\n{listing}"
    )


def _import_github_profiles(repos_text: str, github_token: str) -> tuple[str, str]:
    urls = [line.strip() for line in (repos_text or "").splitlines() if line.strip()]
    if not urls:
        return "", "⚠️ Paste at least one GitHub repo URL (one per line)."
    token = (github_token or os.getenv("GITHUB_API_TOKEN", "")).strip()
    results = import_profiles(urls, token=token)
    preview = _render_profiles_preview(results)
    status = "\n".join(f"{'✅' if r.ok else '❌'} {r.url} — {r.message}" for r in results)
    if not preview:
        status += "\n\nNo valid profiles generated — nothing to save."
    return preview, status


def _save_github_profiles(preview_text: str) -> tuple[str, str]:
    pairs = _parse_profiles_preview(preview_text)
    if not pairs:
        return "Nothing to save — import some repos first.", _list_imported_markdown()
    saved = [str(save_named(name, content)) for name, content in pairs]
    return f"Saved {len(saved)} profile(s):\n" + "\n".join(saved), _list_imported_markdown()


def _compute_missing_skills() -> tuple[dict[str, list[str]], Path]:
    config = get_config()
    skills_path = resolve_path(str(config.get("default_skills_md", "skills.md")))
    directory = imported_dir()
    if not directory.is_dir() or not any(directory.glob("*.md")):
        return {}, skills_path
    projects = parse_projects_source(str(directory))
    skills_text = skills_path.read_text(encoding="utf-8") if skills_path.exists() else ""
    return missing_against(list(projects.values()), skills_text), skills_path


def _refresh_skills_suggestions() -> str:
    directory = imported_dir()
    if not directory.is_dir() or not any(directory.glob("*.md")):
        return "Import and save some profiles first, then refresh."
    missing, _ = _compute_missing_skills()
    return suggestions_markdown(missing)


def _append_skills_to_file() -> str:
    missing, skills_path = _compute_missing_skills()
    added = append_missing(skills_path, missing)
    if not added:
        return "Nothing new to append — `skills.md` already covers the imported tech."
    return f"Appended {added} suggested skill(s) under a new heading in `{skills_path}`."


# ── Profile Builder (identity / education / experience / certs) ─────────────
_PROFILE_SKELETON = {
    "contact": {"name": "", "email": "", "phone": "", "linkedin": "", "github": "", "website": "", "location": ""},
    "education": [{"institution": "", "city": "", "degree": "", "dates": "", "gpa": "", "coursework": ""}],
    "experience": [{"company": "", "role": "", "location": "", "dates": "", "bullets": ["", ""]}],
    "certifications": [{"name": "", "issuer": "", "date": "", "url": ""}],
}
_CONTACT_FIELDS = ("name", "email", "phone", "linkedin", "github", "website", "location")


def _profile_initial_yaml() -> str:
    profile = load_profile()
    return _dump_yaml(profile.to_dict() if profile else _PROFILE_SKELETON)


def _profile_initial_contact() -> tuple[str, ...]:
    profile = load_profile()
    if not profile:
        return ("",) * len(_CONTACT_FIELDS)
    return tuple(getattr(profile.contact, field) for field in _CONTACT_FIELDS)


def _profile_autofill_from_pdf(pdf_path: str | None) -> tuple:
    if not pdf_path:
        return (gr.update(), *(gr.update() for _ in _CONTACT_FIELDS), "Upload a resume PDF first.")
    result = import_profile_from_pdf(pdf_path)
    profile = result.profile
    contact = tuple(getattr(profile.contact, field) for field in _CONTACT_FIELDS)
    return (_dump_yaml(profile.to_dict()), *contact, result.message)


def _profile_sync_contact(yaml_text: str, *contact_values: str) -> tuple[str, str]:
    try:
        data = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        return yaml_text, f"⚠️ YAML parse error — fix it before syncing: {exc}"
    if not isinstance(data, dict):
        data = {}
    data["contact"] = dict(zip(_CONTACT_FIELDS, contact_values, strict=False))
    return _dump_yaml(data), "Contact fields merged into the profile below. Edit the lists directly, then Generate."


def _profile_store_assets(files: list | None) -> str:
    if not files:
        return "No files selected."
    destination = assets_dir()
    destination.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for file_obj in files:
        source = Path(file_obj if isinstance(file_obj, str) else file_obj.name)
        target = destination / source.name
        shutil.copy2(source, target)
        saved.append(target.name)
    return f"Stored {len(saved)} file(s) in `{destination}`: {', '.join(saved)}"


def _profile_generate(yaml_text: str) -> tuple[str, str]:
    try:
        data = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        return f"⚠️ YAML parse error: {exc}", ""
    profile = Profile.from_dict(data if isinstance(data, dict) else {})
    if profile.is_empty():
        return "⚠️ Profile is empty — add at least your name and one education entry.", ""
    try:
        tex, _log = build_personal_template(profile, get_config().get("resume_template", "classic"))
    except Exception as exc:
        return f"❌ Could not build the template: {exc}", ""
    save_profile(profile)
    path = save_personal_template(tex)
    return (
        f"✅ Saved your profile and personal template to `{path}`. "
        "It is now used automatically as your resume layout when you generate a resume.",
        tex,
    )
