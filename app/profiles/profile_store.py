"""Load/save the structured profile + the rendered personal template.

Everything lives under the already-gitignored ``examples/my_profile/``. The
``resolve_resume_tex_source`` resolver mirrors ``resolve_projects_source`` so a
generated personal template transparently replaces the bundled one.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from app.profiles.schema import Profile
from app.utils.config import get_config, resolve_path

DEFAULT_PROFILE_YAML = "examples/my_profile/profile.yaml"
DEFAULT_PERSONAL_TEX = "examples/my_profile/template.tex"
DEFAULT_ASSETS_DIR = "examples/my_profile/assets"


def profile_yaml_path() -> Path:
    return resolve_path(str(get_config().get("profile_yaml", DEFAULT_PROFILE_YAML) or DEFAULT_PROFILE_YAML))


def personal_template_path() -> Path:
    return resolve_path(str(get_config().get("personal_resume_tex", DEFAULT_PERSONAL_TEX) or DEFAULT_PERSONAL_TEX))


def assets_dir() -> Path:
    return resolve_path(str(get_config().get("candidate_assets_dir", DEFAULT_ASSETS_DIR) or DEFAULT_ASSETS_DIR))


def load_profile() -> Profile | None:
    path = profile_yaml_path()
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Profile.from_dict(data)


def save_profile(profile: Profile) -> Path:
    path = profile_yaml_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(profile.to_dict(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def save_personal_template(tex: str) -> Path:
    path = personal_template_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tex if tex.endswith("\n") else tex + "\n", encoding="utf-8")
    return path


def has_personal_template() -> bool:
    path = personal_template_path()
    return path.is_file() and bool(path.read_text(encoding="utf-8").strip())


def resolve_resume_tex_source(default_source: str) -> str:
    """Prefer the generated personal template when present, else the default.

    Analogue of ``resolve_projects_source`` (projects_parser.py): once the user
    has built a profile, the rendered ``examples/my_profile/template.tex`` becomes
    the resume layout; otherwise the bundled/registry template is used.
    """
    if has_personal_template():
        return str(personal_template_path())
    return default_source
