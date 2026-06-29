from __future__ import annotations

import json


def build_semantic_score_prompt(keywords: list[str], resume_bullets: list[str], skills_text: str) -> tuple[str, str]:
    system_prompt = (
        "You are an ATS semantic analyzer. Evaluate whether each job keyword is demonstrated "
        "through meaningful resume evidence, merely name-dropped (e.g., just listed in a skills "
        "section), or absent. Return JSON only — no prose, no code fences."
    )
    user_prompt = (
        "For each keyword, classify it as exactly one of: contextual, name_dropped, absent.\n"
        "- contextual: a bullet shows real work, outcomes, ownership, or technical usage of it.\n"
        "- name_dropped: it appears (e.g. only in the skills list) but with no real evidence.\n"
        "- absent: it does not appear at all.\n"
        "Every input keyword must appear exactly once as a key in keyword_results. If you are "
        "unsure, prefer the weaker verdict (name_dropped over contextual, absent over name_dropped).\n\n"
        "Return JSON matching this schema:\n"
        "{\n"
        '  "keyword_results": {"<keyword>": "contextual|name_dropped|absent", ...},\n'
        '  "contextual": ["<keyword>", ...],\n'
        '  "name_dropped": ["<keyword>", ...],\n'
        '  "absent": ["<keyword>", ...]\n'
        "}\n\n"
        'Example — keywords ["RAG", "Docker", "Kafka"], a bullet "Built a RAG pipeline over 10k docs", '
        'skills list "Docker, Python":\n'
        "{\n"
        '  "keyword_results": {"RAG": "contextual", "Docker": "name_dropped", "Kafka": "absent"},\n'
        '  "contextual": ["RAG"],\n'
        '  "name_dropped": ["Docker"],\n'
        '  "absent": ["Kafka"]\n'
        "}\n\n"
        f"Keywords:\n{json.dumps(keywords, indent=2)}\n\n"
        f"Skills List:\n{skills_text}\n\n"
        f"Resume bullets:\n{json.dumps(resume_bullets, indent=2)}"
    )
    return system_prompt, user_prompt

