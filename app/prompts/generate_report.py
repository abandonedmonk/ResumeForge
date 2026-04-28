from __future__ import annotations

import json


def build_report_prompt(changes_log: list[dict]) -> tuple[str, str]:
    system_prompt = "You are a clear technical writer."
    user_prompt = (
        "Convert this JSON changes log into a readable markdown report. "
        "Use one section per resume section, include before/after bullets, and summarize why changes were made.\n\n"
        f"{json.dumps(changes_log, indent=2)}"
    )
    return system_prompt, user_prompt

