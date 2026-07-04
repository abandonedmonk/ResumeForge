"""Resume Roaster — brutally honest, shareable feedback with a fix for every jab.

Same ingestion as the rest of the pipeline, different prompt. Routes to a fast
model via ``task="roast"`` (snarky-but-structured is well within a small model's
range). Viral by design: people screenshot roasts, and every roast is paired with
an actionable ``[FIX]`` so it stays useful rather than mean.
"""
from __future__ import annotations

import re

from app.llm.router import RoutedStage2Model
from app.prompts.roast import build_roast_prompt

_PAIR_RE = re.compile(r"\[ROAST\]\s*(.+?)\s*\[FIX\]\s*(.+?)(?=\n\[ROAST\]|\Z)", re.IGNORECASE | re.DOTALL)


def _clean(text: str) -> str:
    cleaned = (text or "").strip()
    if "```" in cleaned:
        cleaned = cleaned.replace("```text", "").replace("```", "").strip()
    return cleaned


def run_roast(resume_text: str, jd_text: str = "") -> str:
    """Return the roast as formatted ``[ROAST]`` / ``[FIX]`` text."""
    system_prompt, user_prompt = build_roast_prompt(resume_text, jd_text)
    raw = RoutedStage2Model(task="roast").call(system_prompt, user_prompt)
    return _clean(raw)


def parse_roast_pairs(text: str) -> list[dict[str, str]]:
    """Structure a roast into ``[{roast, fix}, ...]`` — handy for a UI or JSON export."""
    pairs: list[dict[str, str]] = []
    for roast, fix in _PAIR_RE.findall(text or ""):
        pairs.append({"roast": " ".join(roast.split()), "fix": " ".join(fix.split())})
    return pairs
