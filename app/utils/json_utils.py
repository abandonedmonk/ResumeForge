from __future__ import annotations

import json
import re

_FALLBACK_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_blob(text: str) -> str:
    """Extract the first valid JSON object from LLM response text.

    Uses ``json.JSONDecoder().raw_decode()`` to robustly find a balanced
    object even when the model wraps it in prose or markdown fences. Falls
    back to a greedy brace regex, and finally to ``"{}"`` when nothing parses.
    """
    if not text:
        return "{}"

    decoder = json.JSONDecoder()
    for start in range(len(text)):
        if text[start] != "{":
            continue
        try:
            _, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            continue
        return text[start:end]

    match = _FALLBACK_PATTERN.search(text)
    return match.group(0) if match else "{}"


def parse_json_object(text: str) -> dict:
    """Extract and parse the first JSON object from LLM response text.

    Combines :func:`extract_json_blob` with ``json.loads`` and returns an empty
    dict on malformed input — the "parse-or-empty" pattern used across the
    pipeline nodes and features.
    """
    try:
        return json.loads(extract_json_blob(text))
    except (json.JSONDecodeError, TypeError):
        return {}
