from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import gradio as gr
import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
from app.utils.config import clear_session_overrides, get_config, resolve_path, set_session_overrides
from app.utils.file_namer import build_log_stem
from app.utils.logger import get_logs_dir, log_error, log_status, write_run_log


def _read_uploaded_text(file_obj: Any) -> str:
    if not file_obj:
        return ""
    if isinstance(file_obj, str):
        path = Path(file_obj)
    else:
        path = Path(file_obj.name)
    return path.read_text(encoding="utf-8")


def _safe_file_output(path_str: str | None):
    if not path_str:
        return None
    path = Path(path_str)
    if path.exists() and path.is_file():
        return str(path)
    return None


def _score_badge_html(summary: str, score_data: dict) -> str:
    overall = int(score_data.get("overall", 0) or 0)
    label = summary or "ATS score unavailable"
    if overall >= 75:
        bg = "#d1fae5"
        fg = "#065f46"
    elif overall >= 50:
        bg = "#fef3c7"
        fg = "#92400e"
    else:
        bg = "#fee2e2"
        fg = "#991b1b"
    return (
        f"<div style='padding:14px 18px;border-radius:12px;background:{bg};color:{fg};"
        f"font-weight:700;font-size:22px;text-align:center'>{label}</div>"
    )


def _before_after_html(original_score: dict, final_score: dict) -> str:
    """Render the before→after ATS delta banner; empty string when no baseline."""
    if not original_score:
        return ""
    before = int(original_score.get("overall", 0) or 0)
    after = int((final_score or {}).get("overall", 0) or 0)
    if after > before:
        arrow, color = "▲", "#065f46"
    elif after < before:
        arrow, color = "▼", "#991b1b"
    else:
        arrow, color = "→", "#92400e"
    return (
        f"<div style='padding:8px 14px;border-radius:10px;background:#f1f5f9;color:{color};"
        f"font-weight:600;text-align:center'>ATS {before}% {arrow} {after}% "
        f"<span style='opacity:.7;font-weight:400'>(before → after optimization)</span></div>"
    )


def _ats_analysis_markdown(score_data: dict, skills_gap: dict) -> str:
    if not score_data:
        return "ATS analysis unavailable."
    recommendations = score_data.get("recommendations", [])
    return "\n".join(
        [
            f"## Overall ATS Match: {score_data.get('overall', 'N/A')}%",
            "",
            "### Sub-scores",
            f"- Keyword Match: {score_data.get('keyword_match', {}).get('score', 'N/A')}%",
            f"- Semantic Context: {score_data.get('semantic_context', {}).get('score', 'N/A')}%",
            f"- Section Quality: {score_data.get('section_quality', {}).get('score', 'N/A')}%",
            f"- Keyword Placement: {score_data.get('keyword_placement', {}).get('score', 'N/A')}%",
            f"- Impact Metrics: {score_data.get('impact_metrics', {}).get('score', 'N/A')}%",
            "",
            "### Skills Gap",
            f"- Missing Required: {', '.join(skills_gap.get('missing_required', [])) or 'None'}",
            f"- Missing Nice-to-Have: {', '.join(skills_gap.get('missing_nice_to_have', [])) or 'None'}",
            f"- Missing Enriched: {', '.join(skills_gap.get('missing_enriched', [])) or 'None'}",
            "",
            "### Recommendations",
            *([f"- {item}" for item in recommendations] or ["- None"]),
        ]
    )


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


def _build_run_log_content(final_state: dict, new_logs: list[Path]) -> str:
    config = get_config()
    notes = final_state.get("personalization_notes", {}) or {}
    generated_skills = final_state.get("generated_skills", []) or []
    generated_projects = final_state.get("generated_projects", []) or []
    lines = [
        "ResumeForge Run Log",
        f"Generated: {datetime.now().isoformat()}",
        f"Company: {final_state.get('jd_analysis', {}).get('company_name', 'Company')}",
        f"Role: {final_state.get('jd_analysis', {}).get('role_title', 'Role')}",
        f"ATS Summary: {final_state.get('ats_score_summary', 'N/A')}",
        "",
        "Pipeline Configuration:",
        f"- Stage 1 (Selection): {config.get('stage1_model', 'unknown')} | Groq: {config.get('groq_reasoning_model', 'N/A')}",
        f"- Stage 2 (Writing): {config.get('stage2_model', 'unknown')} | Groq: {config.get('groq_fast_model', 'N/A')}",
        f"- Company Enrichment: {config.get('enrich_with_web_search', False)}",
        "",
        "Status Updates:",
        *([f"- {line}" for line in final_state.get("status_updates", [])] or ["- None"]),
        "",
        "Errors:",
        *([f"- {line}" for line in final_state.get("errors", [])] or ["- None"]),
        "",
        "AI Decision Notes:",
        f"- Drafting strategy: {notes.get('drafting_notes', '') or 'None'}",
        f"- Headline: {final_state.get('generated_headline', '') or 'None'}",
        f"- Headline rationale: {notes.get('headline_reason', '') or 'None'}",
        f"- Skills selection rationale: {notes.get('skills_reason', '') or 'None'}",
        *(
            [f"- Skill category: {category.get('category', '')} -> {', '.join(category.get('items', []))}" for category in generated_skills]
            or ["- Skill category: None"]
        ),
        f"- Project selection rationale: {notes.get('project_selection_reason', '') or 'None'}",
        *(
            [
                f"- Project: {project.get('title', '')} | Selection reasoning: {project.get('selection_reason', '') or 'No per-project rationale provided.'}"
                for project in generated_projects
            ]
            or ["- Project: None"]
        ),
        "",
        "Run Artifacts:",
        f"- Preview PDF: {final_state.get('final_pdf_path', '') or 'Not generated'}",
        "",
        "ATS Breakdown:",
        f"- Overall: {final_state.get('ats_score', {}).get('overall', 'N/A')}",
        f"- Keyword Match: {final_state.get('ats_score', {}).get('keyword_match', {}).get('score', 'N/A')}",
        f"- Semantic Context: {final_state.get('ats_score', {}).get('semantic_context', {}).get('score', 'N/A')}",
        f"- Section Quality: {final_state.get('ats_score', {}).get('section_quality', {}).get('score', 'N/A')}",
        f"- Keyword Placement: {final_state.get('ats_score', {}).get('keyword_placement', {}).get('score', 'N/A')}",
        f"- Impact Metrics: {final_state.get('ats_score', {}).get('impact_metrics', {}).get('score', 'N/A')}",
        "",
        "LLM Log Files:",
        *([f"- {path}" for path in new_logs] or ["- None"]),
    ]
    return "\n".join(lines)


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
_PROFILE_MARKER_RE = re.compile(r"^<!-- resumeforge:profile (.+?) -->\s*$", re.MULTILINE)


def _render_profiles_preview(results: list) -> str:
    """Concatenate successful profiles with an editable, parseable file marker."""
    blocks = [
        f"<!-- resumeforge:profile {result.filename} -->\n{result.content.rstrip()}"
        for result in results
        if result.ok
    ]
    return "\n\n".join(blocks)


def _parse_profiles_preview(text: str) -> list[tuple[str, str]]:
    """Recover ``(filename, content)`` pairs from the (possibly edited) preview."""
    matches = list(_PROFILE_MARKER_RE.finditer(text or ""))
    pairs: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if name and content:
            pairs.append((name, content))
    return pairs


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


def _dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


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


def build_ui() -> gr.Blocks:
    config = get_config()
    with gr.Blocks(title="ResumeForge - Resume Tailoring Agent") as demo:
        gr.Markdown("# ResumeForge - Resume Tailoring Agent")
        
        with gr.Tabs():
            with gr.Tab("Archetype Matcher (Quick)"):
                gr.Markdown("Skip the generation. Paste a JD and instantly find out which of your 5 pre-made resumes to submit.")
                with gr.Row():
                    with gr.Column(scale=1):
                        matcher_jd = gr.Textbox(label="Paste Job Description", lines=15, max_lines=30)
                        matcher_model = gr.Dropdown(
                            label="Reasoning Model",
                            choices=["groq", "openrouter", "cohere", "copilot"],
                            value=config.get("stage1_model", "groq"),
                        )
                        match_btn = gr.Button("Find Matching Resume", variant="primary")
                    with gr.Column(scale=1):
                        matcher_output = gr.Markdown("Waiting for JD...")
                        
            with gr.Tab("Full Generator (Custom PDF)"):
                gr.Markdown("Generate a fully custom LaTeX resume tailored line-by-line to a JD.")
                with gr.Row():
                    with gr.Column():
                        # ── Job Description input ──────────────────────────────────
                        with gr.Accordion("📋 Paste Job Description", open=False):
                            gr.Markdown(
                                "Paste the full JD text here. Leave blank to use the default JD file from config: "
                                f"`{resolve_path(config.get('default_jd_txt', 'N/A'))}`"
                            )
                            jd_text_input = gr.Textbox(
                                label="Job Description (paste text, or a posting URL)",
                                placeholder="Paste the job description here… or paste a https://… job posting URL",
                                lines=14,
                                max_lines=40,
                            )
                            clear_jd_button = gr.Button("🗑️ Clear JD", size="sm", variant="secondary")
                            clear_jd_button.click(fn=lambda: "", outputs=jd_text_input)

                        # ── Other inputs ───────────────────────────────────────────
                        gr.Markdown(f"Template: `{resolve_path(config['default_resume_tex'])}`")
                        gr.Markdown(f"Projects Inventory: `{resolve_path(config['default_projects_md'])}`")
                        output_folder = gr.Textbox(
                            label="Output Folder",
                            value=str(resolve_path(config.get("default_output_folder", "outputs"))),
                        )
                        stage1_model = gr.Dropdown(
                            label="Stage 1 Model (Selection)",
                            choices=["groq", "openrouter", "gemini", "cohere", "copilot", "openai", "anthropic"],
                            value=config.get("stage1_model", "groq"),
                        )
                        stage2_model = gr.Dropdown(
                            label="Stage 2 Model (Writing)",
                            choices=["groq", "cohere", "openrouter", "gemini", "copilot", "openai", "anthropic"],
                            value=config.get("stage2_model", "groq"),
                        )
                        enrich_toggle = gr.Checkbox(
                            label="Enrich with web search",
                            value=bool(config.get("enrich_with_web_search", False)),
                        )
                        cover_letter_toggle = gr.Checkbox(
                            label="Generate cover letter (extra LLM call)",
                            value=bool(config.get("generate_cover_letter", False)),
                        )
                        model_tier = gr.Dropdown(
                            label="Model Tier",
                            choices=["free", "premium", "custom"],
                            value=config.get("model_tier", "free"),
                            info="free = cascade across free providers · premium = your GPT/Claude/Gemini keys",
                        )
                        with gr.Accordion("🔑 Premium keys (optional, not stored)", open=False):
                            openai_key = gr.Textbox(
                                label="OpenAI API key", type="password", placeholder="sk-…"
                            )
                            anthropic_key = gr.Textbox(
                                label="Anthropic API key", type="password", placeholder="sk-ant-…"
                            )
                        gr.Markdown(f"Using root skill file: `{resolve_path(config['default_skills_md'])}`")
                        run_button = gr.Button("Generate Preview", variant="primary")

                    with gr.Column():
                        ats_badge = gr.HTML()
                        ats_delta = gr.HTML()
                        with gr.Tabs():
                            with gr.Tab("ATS Analysis"):
                                ats_analysis = gr.Markdown()
                            with gr.Tab("Changes Made"):
                                changes_md = gr.Markdown()
                            with gr.Tab("LaTeX Preview"):
                                latex_preview = gr.Code(language="latex", lines=24)
                                edit_request = gr.Textbox(
                                    label="Ask AI to edit this preview",
                                    placeholder="Example: Make the bullets more concise and emphasize backend APIs.",
                                    lines=3,
                                )
                                apply_edit_button = gr.Button("Apply AI Edit")
                                edit_status = gr.Textbox(label="Edit Status", lines=2)
                            with gr.Tab("Cover Letter"):
                                cover_letter_md = gr.Markdown("_Enable \"Generate cover letter\" before running._")
                            with gr.Tab("Preview PDF"):
                                pdf_file = gr.File(label="Preview PDF", type="filepath")
                                docx_file = gr.File(label="Resume (.docx)", type="filepath")
                            with gr.Tab("Logs"):
                                log_preview = gr.Textbox(label="Run Log", lines=18)
                        status_box = gr.Textbox(label="Status Log", lines=10)
                        error_box = gr.Textbox(label="Errors", lines=8)
                        save_button = gr.Button("Approve & Save PDF")
                        save_status = gr.Textbox(label="Save Status", lines=2)
                        saved_pdf_file = gr.File(label="Saved PDF", type="filepath")

            with gr.Tab("Build Profile from GitHub"):
                gr.Markdown(
                    "Paste GitHub repo URLs (one per line). ResumeForge reads each README + "
                    "metadata via the public GitHub API and distills a truthful, reusable project "
                    "profile. Once you save any profile, the imported set replaces the bundled "
                    "examples as your projects source.\n\n"
                    "_Anonymous GitHub API allows ~60 requests/hr; add a token below (or set "
                    "`GITHUB_API_TOKEN`) to raise it to 5000/hr._"
                )
                with gr.Row():
                    with gr.Column(scale=1):
                        repos_input = gr.Textbox(
                            label="GitHub repo URLs (one per line)",
                            placeholder="https://github.com/owner/repo\nowner/another-repo",
                            lines=8,
                        )
                        with gr.Accordion("🔑 GitHub token (optional, not stored)", open=False):
                            github_token_input = gr.Textbox(
                                label="GitHub API token",
                                type="password",
                                placeholder="github_pat_… or ghp_…",
                            )
                        import_btn = gr.Button("Import Repos", variant="primary")
                        import_status = gr.Markdown()
                        gr.Markdown("---")
                        refresh_skills_btn = gr.Button("Suggest Skills from Imports", size="sm")
                        append_skills_btn = gr.Button("Append New Skills to skills.md", size="sm", variant="secondary")
                        skills_suggestions = gr.Markdown()
                        append_skills_status = gr.Markdown()
                    with gr.Column(scale=1):
                        profiles_preview = gr.Code(
                            label="Generated profiles (editable — edits are saved)",
                            language="markdown",
                            lines=24,
                        )
                        save_profiles_btn = gr.Button("Save Profiles", variant="primary")
                        save_profiles_status = gr.Markdown()
                        imported_listing = gr.Markdown(_list_imported_markdown())

            with gr.Tab("Build My Profile"):
                gr.Markdown(
                    "Enter your identity, education, experience, and certifications — or upload an "
                    "existing resume PDF to auto-fill (embedded links extract reliably; text is "
                    "best-effort). ResumeForge renders a personal one-page LaTeX template from this and "
                    "uses it automatically as your resume layout. Certifications appear as text with an "
                    "optional link; uploaded cert files are stored locally as your own evidence."
                )
                _contact_init = _profile_initial_contact()
                with gr.Row():
                    with gr.Column(scale=1):
                        with gr.Accordion("📄 Auto-fill from an existing resume PDF", open=False):
                            resume_pdf_input = gr.File(label="Resume PDF", type="filepath", file_types=[".pdf"])
                            autofill_btn = gr.Button("Auto-fill from PDF")
                            autofill_status = gr.Markdown()
                        gr.Markdown("**Contact**")
                        pf_name = gr.Textbox(label="Full name", value=_contact_init[0])
                        pf_email = gr.Textbox(label="Email", value=_contact_init[1])
                        pf_phone = gr.Textbox(label="Phone", value=_contact_init[2])
                        pf_linkedin = gr.Textbox(label="LinkedIn URL", value=_contact_init[3])
                        pf_github = gr.Textbox(label="GitHub URL", value=_contact_init[4])
                        pf_website = gr.Textbox(label="Website / Portfolio URL", value=_contact_init[5])
                        pf_location = gr.Textbox(label="Location", value=_contact_init[6])
                        sync_contact_btn = gr.Button("Apply contact → profile")
                        with gr.Accordion("📎 Certificate files (stored locally as evidence)", open=False):
                            cert_files = gr.File(
                                label="Cert PDFs / images",
                                type="filepath",
                                file_count="multiple",
                                file_types=[".pdf", ".jpg", ".jpeg", ".png"],
                            )
                            store_assets_btn = gr.Button("Store cert files")
                            assets_status = gr.Markdown()
                    with gr.Column(scale=1):
                        profile_yaml = gr.Code(
                            label="Profile (editable) — edit education / experience / certifications here",
                            language="yaml",
                            lines=24,
                            value=_profile_initial_yaml(),
                        )
                        generate_template_btn = gr.Button("Generate My Template", variant="primary")
                        generate_status = gr.Markdown()
                        rendered_tex_preview = gr.Code(label="Rendered template (.tex)", language="latex", lines=14)

        state_store = gr.State({})

        autofill_btn.click(
            fn=_profile_autofill_from_pdf,
            inputs=[resume_pdf_input],
            outputs=[profile_yaml, pf_name, pf_email, pf_phone, pf_linkedin, pf_github, pf_website, pf_location, autofill_status],
        )
        sync_contact_btn.click(
            fn=_profile_sync_contact,
            inputs=[profile_yaml, pf_name, pf_email, pf_phone, pf_linkedin, pf_github, pf_website, pf_location],
            outputs=[profile_yaml, generate_status],
        )
        store_assets_btn.click(
            fn=_profile_store_assets,
            inputs=[cert_files],
            outputs=[assets_status],
        )
        generate_template_btn.click(
            fn=_profile_generate,
            inputs=[profile_yaml],
            outputs=[generate_status, rendered_tex_preview],
        )

        import_btn.click(
            fn=_import_github_profiles,
            inputs=[repos_input, github_token_input],
            outputs=[profiles_preview, import_status],
        )
        save_profiles_btn.click(
            fn=_save_github_profiles,
            inputs=[profiles_preview],
            outputs=[save_profiles_status, imported_listing],
        )
        refresh_skills_btn.click(
            fn=_refresh_skills_suggestions,
            inputs=[],
            outputs=[skills_suggestions],
        )
        append_skills_btn.click(
            fn=_append_skills_to_file,
            inputs=[],
            outputs=[append_skills_status],
        )

        match_btn.click(
            fn=_quick_match_jd,
            inputs=[matcher_jd, matcher_model],
            outputs=[matcher_output],
        )

        run_button.click(
            fn=_run_resumeforge,
            inputs=[output_folder, stage1_model, stage2_model, enrich_toggle, jd_text_input, model_tier, openai_key, anthropic_key, cover_letter_toggle],
            outputs=[ats_badge, ats_delta, ats_analysis, changes_md, latex_preview, pdf_file, status_box, error_box, log_preview, state_store, cover_letter_md, docx_file],
        )
        apply_edit_button.click(
            fn=_apply_ai_edit_request,
            inputs=[latex_preview, edit_request, stage2_model, output_folder],
            outputs=[latex_preview, edit_status, pdf_file],
        )
        save_button.click(
            fn=_save_preview,
            inputs=[state_store, latex_preview],
            outputs=[saved_pdf_file, save_status, state_store],
        )
    return demo


def run_test_mode() -> int:
    config = get_config()
    initial_state = {
        "jd_text": resolve_path(config.get("default_jd_txt", "test_files/jd.txt")).read_text(encoding="utf-8"),
        "original_resume_tex": str(config["default_resume_tex"]),
        "skills_md": str(config["default_skills_md"]),
        "projects_context": str(config["default_projects_md"]),
        "output_folder": str(resolve_path(config.get("default_output_folder", "outputs"))),
    }
    final_state = run_agent(initial_state)
    print("Status updates:")
    print("\n".join(final_state["status_updates"]))
    print("\nErrors:")
    print("\n".join(final_state["errors"]) or "None")
    print(f"\nPDF: {final_state['final_pdf_path'] or 'Not generated'}")
    print(f"Report length: {len(final_state['changes_report_md'])}")
    return 1 if final_state["errors"] else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ResumeForge")
    parser.add_argument("--test", action="store_true", help="Run the agent on bundled sample files.")
    args = parser.parse_args()

    if args.test:
        return run_test_mode()

    demo = build_ui()
    config = get_config()
    demo.launch(
        theme=gr.themes.Soft(),
        inbrowser=bool(config.get("open_browser_on_launch", True)),
        server_name="0.0.0.0",
        server_port=int(config.get("gradio_port", 7860)),
        allowed_paths=[config["dest_folder"]] if config.get("dest_folder") else [],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
