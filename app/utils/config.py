from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config.yaml"
# Optional gitignored override for personal values (candidate_name, dest_folder, ...).
LOCAL_CONFIG_PATH = ROOT_DIR / "config.local.yaml"

_config: dict[str, Any] | None = None


def get_config() -> dict[str, Any]:
    """Return a deep copy of the merged config so callers can mutate it freely.

    Values from ``config.yaml`` are overlaid with ``config.local.yaml`` (if
    present), letting users keep personal settings out of version control. The
    files are read once into a private module-level cache; returning a
    ``deepcopy`` prevents per-session mutations in the Gradio UI (e.g.
    ``config["stage1_model"] = ...``) from bleeding across concurrent sessions.
    """
    global _config
    if _config is None:
        load_dotenv(ROOT_DIR / ".env")
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"Missing config file at {CONFIG_PATH}")
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            merged = yaml.safe_load(handle) or {}
        if LOCAL_CONFIG_PATH.exists():
            with LOCAL_CONFIG_PATH.open("r", encoding="utf-8") as handle:
                merged.update(yaml.safe_load(handle) or {})
        _config = merged
    return copy.deepcopy(_config)


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return ROOT_DIR / path

