"""Cold Read Simulator — adversarial zero-context evaluation.

Every other tool optimizes *before* submission. This simulates what a recruiter
concludes *after*, from the resume alone. The cold constraint is enforced in the
prompt: no application history, no system framing — just the resume and JD.

Cheapest call in the pipeline (~1.75k tokens). Reading comprehension, not
generation, so it routes to a small fast model (Groq 8B) via ``task="cold_read"``.
"""
from __future__ import annotations

import json

from app.llm.router import RoutedStage1Model
from app.prompts.cold_read import build_cold_read_prompt
from app.utils.json_utils import extract_json_blob

FIELDS = ("targeted_role", "strongest_qualification", "biggest_gap")


def run_cold_read(resume_text: str, jd_text: str) -> dict:
    """Return ``{targeted_role, strongest_qualification, biggest_gap}``.

    On a malformed model response, missing fields fall back to a clear marker so
    callers always get the full schema."""
    system_prompt, user_prompt = build_cold_read_prompt(resume_text, jd_text)
    raw = RoutedStage1Model(task="cold_read").call(system_prompt, user_prompt)
    try:
        payload = json.loads(extract_json_blob(raw))
    except json.JSONDecodeError:
        payload = {}
    return {field: str(payload.get(field, "") or "(not determined)") for field in FIELDS}


def render_cold_read(result: dict) -> str:
    """Human-readable summary for the CLI."""
    return "\n".join(
        [
            "Cold Read (zero-context recruiter view)",
            "---------------------------------------",
            f"Targeted role:  {result.get('targeted_role', '')}",
            f"Strongest fit:  {result.get('strongest_qualification', '')}",
            f"Biggest gap:    {result.get('biggest_gap', '')}",
        ]
    )
