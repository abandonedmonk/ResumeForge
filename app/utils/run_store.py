"""Per-run artifact store under ``~/.resumeforge/``.

The Gradio app writes into the repo's ``outputs/``. The installed CLI instead
writes each run to a stable user-home location so it works from any directory:

    ~/.resumeforge/runs/<run-id>/
    ├── resume.tex     # tailored LaTeX source (branchable)
    ├── resume.pdf     # compiled PDF
    ├── receipt.json   # compression receipt (Phase 2)
    └── cold-read.json # cold-read output, if requested (Phase 3)

Kept deliberately tiny: create/lookup run dirs and read/write JSON. Branch
management (``~/.resumeforge/branches/``) is a later phase and builds on this.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

HOME = Path.home() / ".resumeforge"
RUNS_DIR = HOME / "runs"


def runs_root() -> Path:
    """The ``~/.resumeforge/runs`` directory, created on first use."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return RUNS_DIR


def _slugify(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", (text or "").strip()).strip("-").lower()


def new_run_id(label: str = "") -> str:
    """Timestamped, filesystem-safe run id, e.g. ``20260704-113015`` or
    ``20260704-113015-ml-research`` when a label/branch is given."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = _slugify(label)
    return f"{stamp}-{slug}" if slug else stamp


def new_run_dir(label: str = "") -> Path:
    """Create and return a fresh run directory."""
    run_dir = runs_root() / new_run_id(label)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def run_dir(run_id: str) -> Path | None:
    """Return the directory for ``run_id`` if it exists, else ``None``."""
    candidate = runs_root() / run_id
    return candidate if candidate.is_dir() else None


def latest_run_dir() -> Path | None:
    """The most recently modified run directory, or ``None`` when there are none."""
    runs = [path for path in runs_root().iterdir() if path.is_dir()]
    return max(runs, key=lambda path: path.stat().st_mtime) if runs else None


def write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
