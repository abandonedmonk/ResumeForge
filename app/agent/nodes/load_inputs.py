from __future__ import annotations

from pathlib import Path

from app.agent.state import ResumeState
from app.parsers.projects_parser import resolve_projects_source
from app.parsers.template_registry import load_template
from app.profiles.profile_store import resolve_resume_tex_source
from app.utils.config import get_config, resolve_path, update_session_overrides
from app.utils.exceptions import ResumeForgeError
from app.utils.logger import log_error, log_status


def _load_value(value: str) -> str:
    if "\n" in value or "\r" in value:
        return value
    candidate = Path(value)
    if candidate.suffix.lower() in {".md", ".tex", ".txt"}:
        resolved = resolve_path(value)
        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {resolved}")
        return resolved.read_text(encoding="utf-8")
    return value


def load_inputs(state: ResumeState) -> ResumeState:
    config = get_config()
    log_status(state, "Loading inputs...")
    output_folder = state["output_folder"] or config.get("default_output_folder", "outputs")
    state["output_folder"] = str(resolve_path(output_folder))

    # Resolve the resume layout. An explicit template path (owner's personal file
    # via config.local, or a provided state value) wins; then a profile-builder
    # generated personal template (Phase 6); otherwise the named registry template.
    explicit_tex = state.get("original_resume_tex") or resolve_resume_tex_source(
        config.get("default_resume_tex", "")
    )
    if not explicit_tex:
        template = load_template(config.get("resume_template", "classic"))
        if template is not None:
            state["original_resume_tex"] = template.tex
            state["resume_template"] = template.name
            update_session_overrides(
                {
                    "max_projects": template.max_projects,
                    "max_skills": template.max_skills,
                    "max_bullets_per_project": template.max_bullets_per_project,
                }
            )
            config = get_config()
        else:
            log_error(state, "No resume template found; set default_resume_tex or add templates/<name>/template.tex.")
    else:
        state["resume_template"] = "custom"

    # Decide the page budget: one page unless 10+ years experience or an explicit opt-in.
    years = int(state.get("candidate_years_experience") or config.get("candidate_years_experience", 0) or 0)
    allow_two = bool(state.get("allow_two_pages") or config.get("allow_two_pages", False))
    state["candidate_years_experience"] = years
    state["allow_two_pages"] = allow_two
    state["max_pages"] = 2 if (allow_two or years >= 10) else 1

    if not state["jd_text"]:
        default_jd = str(config.get("default_jd_txt", ""))
        if default_jd:
            try:
                state["jd_text"] = _load_value(default_jd)
            except FileNotFoundError as exc:
                log_error(state, f"jd_text: {exc}")

    for field_name, default_key in (
        ("skills_md", "default_skills_md"),
        ("projects_context", "default_projects_md"),
        ("original_resume_tex", "default_resume_tex"),
    ):
        value = state.get(field_name)  # type: ignore[arg-type]
        if not value:
            value = str(config.get(default_key, ""))
        try:
            state[field_name] = _load_value(str(value))  # type: ignore[index]
        except FileNotFoundError as exc:
            log_error(state, f"{field_name}: {exc}")
            state[field_name] = "" if field_name != "projects_context" else {}  # type: ignore[index]

    # If the user imported GitHub-derived profiles, that directory transparently
    # replaces the bundled/default projects source (locked: "imported replace bundled").
    if isinstance(state.get("projects_context"), str):
        resolved = resolve_projects_source(state["projects_context"])
        if resolved != state["projects_context"]:
            log_status(state, f"Using imported GitHub profiles: {resolved}")
        state["projects_context"] = resolved

    # A JD given as a URL is fetched and replaced with the posting's text (non-fatal).
    jd_value = state["jd_text"].strip()
    if jd_value.startswith(("http://", "https://")) and "\n" not in jd_value:
        from app.parsers.jd_parser import fetch_jd_from_url

        log_status(state, f"Fetching job description from URL: {jd_value}")
        try:
            state["jd_text"] = fetch_jd_from_url(jd_value)
        except ResumeForgeError as exc:
            log_error(state, str(exc))

    if not state["jd_text"].strip():
        raise ResumeForgeError("Job description is empty — cannot proceed.")

    return state
