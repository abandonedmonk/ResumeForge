"""Storage for user-imported GitHub project profiles.

Profiles are reusable "memory" files under the gitignored
``imported_profiles_dir`` (default ``examples/my_profile/project_profiles``).
One file per repo (``{owner}__{repo}.md``) makes re-import idempotent: importing
the same repo overwrites only its file; new repos add files; nothing else is
touched.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.utils.config import get_config, resolve_path

DEFAULT_DIR = "examples/my_profile/project_profiles"


def imported_dir() -> Path:
    return resolve_path(str(get_config().get("imported_profiles_dir", DEFAULT_DIR) or DEFAULT_DIR))


def _sanitize(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip())
    return cleaned.strip("-._") or "profile"


def profile_filename(owner: str, repo: str) -> str:
    return f"{_sanitize(owner)}__{_sanitize(repo)}.md"


def profile_path(owner: str, repo: str) -> Path:
    return imported_dir() / profile_filename(owner, repo)


def save_profile(owner: str, repo: str, content: str) -> Path:
    path = profile_path(owner, repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
    return path


def save_named(filename: str, content: str) -> Path:
    """Write ``content`` to ``filename`` inside the imported dir (sanitized)."""
    safe = _sanitize(filename[:-3]) + ".md" if filename.endswith(".md") else _sanitize(filename) + ".md"
    path = imported_dir() / safe
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
    return path


def list_profiles() -> list[Path]:
    directory = imported_dir()
    return sorted(directory.glob("*.md")) if directory.is_dir() else []


def load_profile_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
