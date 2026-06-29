"""Multi-key pool with round-robin rotation.

Free-tier providers rate-limit aggressively. Users can supply several keys for
the same provider via ``NAME``, ``NAME_1``, ``NAME_2`` … (plus a session key
from the UI). ``ordered_keys`` returns every available key with a rotating
start offset so load spreads across keys, while the router still tries them all
on failure before moving to the next provider.
"""
from __future__ import annotations

import os
import threading

from app.llm.keystore import get_session_key

# Provider name -> the primary environment variable that holds its key.
PROVIDER_ENV: dict[str, str] = {
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "cohere": "COHERE_API_KEY",
    "copilot": "GITHUB_TOKEN",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

_lock = threading.Lock()
_rotation: dict[str, int] = {}


def _collect(base_name: str) -> list[str]:
    keys: list[str] = []
    session = get_session_key(base_name).strip()
    if session:
        keys.append(session)
    primary = os.getenv(base_name, "").strip()
    if primary:
        keys.append(primary)
    index = 1
    while True:
        value = os.getenv(f"{base_name}_{index}", "").strip()
        if not value:
            break
        keys.append(value)
        index += 1

    seen: set[str] = set()
    unique: list[str] = []
    for key in keys:
        if key and key not in seen:
            seen.add(key)
            unique.append(key)
    return unique


def ordered_keys(base_name: str) -> list[str]:
    """All keys for ``base_name``, rotated so successive calls start at a different key."""
    keys = _collect(base_name)
    if len(keys) <= 1:
        return keys
    with _lock:
        start = _rotation.get(base_name, 0) % len(keys)
        _rotation[base_name] = (start + 1) % len(keys)
    return keys[start:] + keys[:start]
