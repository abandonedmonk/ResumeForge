"""Per-session API key store.

Lets the UI inject keys for a single run (e.g. a pasted premium key) without
writing them to ``.env`` or the on-disk config. Keys live in thread-local
storage so concurrent Gradio sessions stay isolated, and they are never logged
or persisted.
"""
from __future__ import annotations

import threading

_local = threading.local()


def set_session_keys(keys: dict[str, str] | None) -> None:
    """Replace the current thread's session keys (e.g. {"OPENAI_API_KEY": "sk-..."})."""
    _local.keys = {name: value.strip() for name, value in (keys or {}).items() if value and value.strip()}


def get_session_key(name: str) -> str:
    """Return the session-scoped value for ``name`` (empty string if unset)."""
    return getattr(_local, "keys", {}).get(name, "")


def clear_session_keys() -> None:
    """Drop all session keys for the current thread."""
    _local.keys = {}
