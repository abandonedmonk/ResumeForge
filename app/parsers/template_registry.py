"""Registry of one-page resume templates.

Each template lives in ``templates/<name>/`` with a ``template.tex`` (the LaTeX
layout, using the shared ``% PLACEHOLDER_*`` markers and ``\\resumeProjectHeading``
commands) and an optional ``config.json`` describing its content budget. All
templates share the same injection convention, so the assembler is template-
agnostic — only the budget knobs differ.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.utils.config import ROOT_DIR

TEMPLATES_DIR = ROOT_DIR / "templates"

_DEFAULTS = {
    "compiler": "pdflatex",
    "max_projects": 3,
    "max_skills": 4,
    "max_bullets_per_project": 3,
    "description": "",
}


@dataclass(frozen=True)
class TemplateConfig:
    name: str
    tex_path: Path
    compiler: str = "pdflatex"
    max_projects: int = 3
    max_skills: int = 4
    max_bullets_per_project: int = 3
    description: str = ""

    @property
    def tex(self) -> str:
        return self.tex_path.read_text(encoding="utf-8")


def list_templates() -> list[str]:
    if not TEMPLATES_DIR.is_dir():
        return []
    return sorted(
        p.name for p in TEMPLATES_DIR.iterdir() if (p / "template.tex").is_file()
    )


def load_template(name: str | None) -> TemplateConfig | None:
    """Return the TemplateConfig for ``name``, or None if it cannot be resolved."""
    if not name:
        return None
    tex_path = TEMPLATES_DIR / name / "template.tex"
    if not tex_path.is_file():
        return None
    meta = dict(_DEFAULTS)
    config_path = TEMPLATES_DIR / name / "config.json"
    if config_path.is_file():
        try:
            meta.update(json.loads(config_path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    return TemplateConfig(
        name=name,
        tex_path=tex_path,
        compiler=str(meta.get("compiler", "pdflatex")),
        max_projects=int(meta.get("max_projects", 3)),
        max_skills=int(meta.get("max_skills", 4)),
        max_bullets_per_project=int(meta.get("max_bullets_per_project", 3)),
        description=str(meta.get("description", "")),
    )
