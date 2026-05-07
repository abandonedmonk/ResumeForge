from __future__ import annotations

import json


def build_semantic_score_prompt(keywords: list[str], resume_bullets: list[str], skills_text: str) -> tuple[str, str]:
    system_prompt = (
        "You are an ATS semantic analyzer. Evaluate whether each job keyword is demonstrated "
        "through meaningful resume evidence, merely name-dropped (e.g., just listed in a skills section), or absent. Return JSON only."
    )
    user_prompt = (
        "For each keyword, classify it as one of: contextual, name_dropped, absent.\n"
        "Use contextual only when the bullet shows real work, outcomes, ownership, or technical usage.\n"
        "Use name_dropped when the keyword appears but without meaningful evidence (e.g., if it only appears in the skills list).\n"
        "Return JSON with keys: keyword_results, contextual, name_dropped, absent.\n\n"
        f"Keywords:\n{json.dumps(keywords, indent=2)}\n\n"
        f"Skills List:\n{skills_text}\n\n"
        f"Resume bullets:\n{json.dumps(resume_bullets, indent=2)}"
    )
    return system_prompt, user_prompt

