from __future__ import annotations

import copy
import threading
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config.yaml"
# Optional gitignored override for personal values (candidate_name, dest_folder, ...).
LOCAL_CONFIG_PATH = ROOT_DIR / "config.local.yaml"

_config: dict[str, Any] | None = None
_session = threading.local()


def set_session_overrides(overrides: dict[str, Any] | None) -> None:
    """Set per-run config overrides for the current thread (e.g. UI selections).

    Because ``get_config()`` returns a fresh deepcopy each call, mutating its
    result no longer propagates to pipeline nodes. Session overrides are the
    supported way to pass per-request settings (model tier, chosen models,
    toggles) into the graph without bleeding across concurrent sessions.
    """
    _session.overrides = dict(overrides or {})


def update_session_overrides(overrides: dict[str, Any] | None) -> None:
    """Merge additional keys into the current thread's session overrides."""
    current = dict(getattr(_session, "overrides", {}))
    current.update(overrides or {})
    _session.overrides = current


def clear_session_overrides() -> None:
    _session.overrides = {}


def _session_overrides() -> dict[str, Any]:
    return getattr(_session, "overrides", {})


def get_config() -> dict[str, Any]:
    """Return a deep copy of the merged config so callers can mutate it freely.

    Layering (last wins): ``config.yaml`` -> ``config.local.yaml`` (gitignored
    personal values) -> per-thread session overrides. Returning a ``deepcopy``
    keeps concurrent Gradio sessions isolated.
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
    result = copy.deepcopy(_config)
    result.update(_session_overrides())
    return result


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return ROOT_DIR / path

