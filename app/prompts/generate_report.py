from __future__ import annotations

import json


def build_report_prompt(changes_log: list[dict], ats_score: dict | None = None) -> tuple[str, str]:
    system_prompt = "You are a clear technical writer."
    user_prompt = (
        "Convert this JSON changes log into a readable markdown report. "
        "Use one section per resume section, include before/after bullets, summarize why changes were made, "
        "and include ATS scoring insights if provided.\n\n"
        f"ATS Score:\n{json.dumps(ats_score or {}, indent=2)}\n\n"
        f"Changes Log:\n{json.dumps(changes_log, indent=2)}"
    )
    return system_prompt, user_prompt
