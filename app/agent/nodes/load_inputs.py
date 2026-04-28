from __future__ import annotations

from pathlib import Path

from app.agent.state import ResumeState
from app.utils.config import get_config, resolve_path
from app.utils.logger import log_error, log_status


def _load_value(value: str) -> str:
    if "\n" in value or "\r" in value:
        return value
    candidate = Path(value)
    if candidate.suffix.lower() in {".md", ".tex", ".txt"}:
        resolved = resolve_path(value)
        return resolved.read_text(encoding="utf-8")
    return value


def load_inputs(state: ResumeState) -> ResumeState:
    config = get_config()
    log_status(state, "Loading inputs...")
    output_folder = state["output_folder"] or config.get("default_output_folder", "outputs")
    state["output_folder"] = str(resolve_path(output_folder))

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

    if not state["jd_text"]:
        log_error(state, "Job description text is required.")

    return state
