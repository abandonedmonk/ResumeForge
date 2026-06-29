from __future__ import annotations

import json

from app.agent.state import ResumeState
from app.llm.router import RoutedModel
from app.parsers.jd_parser import extract_company_role
from app.prompts.analyze_jd import build_analyze_jd_prompt
from app.utils.json_utils import extract_json_blob
from app.utils.logger import log_error, log_status


def analyze_jd(state: ResumeState) -> ResumeState:
    log_status(state, "Analyzing job description...")
    fallback_company, fallback_role = extract_company_role(state["jd_text"])
    analysis = {
        "required_skills": [],
        "nice_to_have": [],
        "keywords": [],
        "tone": "enterprise_formal",
        "role_level": "mid",
        "company_name": fallback_company,
        "role_title": fallback_role,
    }

    try:
        system_prompt, user_prompt = build_analyze_jd_prompt(state["jd_text"], state["skills_md"])
        response = RoutedModel("stage1").call(system_prompt, user_prompt)
        payload = json.loads(extract_json_blob(response))
        analysis.update(payload)
    except Exception as exc:
        log_error(state, f"JD analysis fallback used: {exc}")

    analysis["company_name"] = analysis.get("company_name") or fallback_company
    analysis["role_title"] = analysis.get("role_title") or fallback_role
    state["jd_analysis"] = analysis
    return state
