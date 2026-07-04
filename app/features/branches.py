"""LaTeX semantic branching — "git for your resume".

Because ResumeForge outputs ``.tex`` *source*, a user can keep several tailored forks
(``main``, ``ml-research``, ``quant``, ``swe``) and diff them, instead of juggling static
PDFs. Lightweight by design: each branch is a named saved ``resume.tex`` plus metadata;
``~/.resumeforge/runs/`` stays the immutable per-run history. No fork/merge semantics.

Storage (built on the Phase 10 run-store):

    ~/.resumeforge/branches/<name>/
    ├── resume.tex
    └── meta.json   # {name, created_at, updated_at, source, jd_role, jd_company, ats}
"""
from __future__ import annotations

from datetime import datetime
from difflib import unified_diff
from pathlib import Path

from app.utils import run_store
from app.utils.run_store import read_json, write_json

# Module-level so tests can monkeypatch it to a tmp dir (mirrors run_store).
BRANCHES_DIR = run_store.HOME / "branches"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def valid_name(name: str) -> str:
    """Normalise a branch name to a filesystem-safe slug, or raise ``ValueError``."""
    slug = run_store._slugify(name)
    if not slug:
        raise ValueError(f"Invalid branch name: {name!r}. Use letters, numbers, or hyphens.")
    return slug


def branches_root() -> Path:
    BRANCHES_DIR.mkdir(parents=True, exist_ok=True)
    return BRANCHES_DIR


def branch_dir(name: str) -> Path | None:
    """Return the directory for ``name`` if the branch exists, else ``None``."""
    candidate = branches_root() / valid_name(name)
    return candidate if candidate.is_dir() else None


def save_branch(name: str, tex: str, meta: dict | None = None) -> Path:
    """Create or overwrite a branch. ``created_at`` is set once; ``updated_at`` each save."""
    slug = valid_name(name)
    target = branches_root() / slug
    target.mkdir(parents=True, exist_ok=True)
    (target / "resume.tex").write_text(tex or "", encoding="utf-8")

    meta_path = target / "meta.json"
    existing = read_json(meta_path) if meta_path.exists() else {}
    merged = {**existing, **(meta or {})}
    merged["name"] = slug
    merged.setdefault("created_at", existing.get("created_at") or _now())
    merged["updated_at"] = _now()
    write_json(meta_path, merged)
    return target


def read_branch_tex(name: str) -> str | None:
    target = branch_dir(name)
    if target is None:
        return None
    tex_path = target / "resume.tex"
    return tex_path.read_text(encoding="utf-8") if tex_path.exists() else None


def branch_meta(name: str) -> dict:
    target = branch_dir(name)
    if target is None:
        return {}
    meta_path = target / "meta.json"
    return read_json(meta_path) if meta_path.exists() else {"name": valid_name(name)}


def list_branches() -> list[dict]:
    """All branches with their metadata, most-recently-updated first."""
    root = branches_root()
    branches: list[dict] = []
    for path in root.iterdir():
        if not path.is_dir():
            continue
        meta_path = path / "meta.json"
        meta = read_json(meta_path) if meta_path.exists() else {"name": path.name}
        meta.setdefault("name", path.name)
        branches.append(meta)
    branches.sort(key=lambda meta: meta.get("updated_at", ""), reverse=True)
    return branches


def delete_branch(name: str) -> bool:
    """Delete a branch. Returns ``True`` if it existed."""
    import shutil

    target = branch_dir(name)
    if target is None:
        return False
    shutil.rmtree(target)
    return True


def diff_branches(a: str, b: str) -> dict:
    """Unified diff of two branches' ``resume.tex``. Raises ``ValueError`` if either is missing."""
    tex_a = read_branch_tex(a)
    tex_b = read_branch_tex(b)
    if tex_a is None:
        raise ValueError(f"Branch not found: {a}")
    if tex_b is None:
        raise ValueError(f"Branch not found: {b}")

    slug_a, slug_b = valid_name(a), valid_name(b)
    lines = list(
        unified_diff(
            tex_a.splitlines(),
            tex_b.splitlines(),
            fromfile=f"{slug_a}/resume.tex",
            tofile=f"{slug_b}/resume.tex",
            lineterm="",
        )
    )
    added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
    return {"a": slug_a, "b": slug_b, "added": added, "removed": removed, "unified": "\n".join(lines)}


def render_branch_list(branches: list[dict]) -> str:
    if not branches:
        return "No branches yet. Create one: resumeforge branch new <name> --from-file <cv.tex>"
    lines = ["Branches", "--------"]
    for meta in branches:
        role = meta.get("jd_role") or meta.get("source") or ""
        suffix = f"  ({role})" if role else ""
        lines.append(f"  {meta.get('name', '?')}  ·  updated {meta.get('updated_at', '?')}{suffix}")
    return "\n".join(lines)


def render_diff(result: dict) -> str:
    header = f"diff {result['a']} -> {result['b']}  (+{result['added']} / -{result['removed']})"
    body = result.get("unified", "")
    return f"{header}\n{body}" if body else f"{header}\n(no differences)"
