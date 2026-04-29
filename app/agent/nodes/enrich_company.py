from __future__ import annotations

import json
import re

from app.agent.state import ResumeState
from app.llm.gemini import GeminiFlash
from app.utils.config import get_config
from app.utils.logger import log_error, log_status


def _extract_json_blob(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else "{}"


def enrich_company(state: ResumeState) -> ResumeState:
    config = get_config()
    if not config.get("enrich_with_web_search", False):
        state["jd_analysis"]["enriched_keywords"] = []
        return state

    log_status(state, "Enriching company context with web search...")
    company_name = str(state["jd_analysis"].get("company_name", "")).strip()
    role_title = str(state["jd_analysis"].get("role_title", "")).strip()
    if not company_name:
        state["jd_analysis"]["enriched_keywords"] = []
        return state

    try:
        from duckduckgo_search import DDGS
    except Exception as exc:  # pragma: no cover - optional dependency/runtime
        log_status(state, f"Company enrichment skipped: optional dependency unavailable ({exc}).")
        state["jd_analysis"]["enriched_keywords"] = []
        return state

    try:
        query = f"{company_name} tech stack engineering blog {role_title}".strip()
        snippets: list[str] = []
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=3):
                body = str(result.get("body", "")).strip()
                title = str(result.get("title", "")).strip()
                if body or title:
                    snippets.append(f"{title}: {body}".strip(": "))
        if not snippets:
            state["jd_analysis"]["enriched_keywords"] = []
            return state

        system_prompt = "Extract relevant technical ATS keywords from company snippets. Return JSON only."
        user_prompt = (
            f"Company: {company_name}\nRole: {role_title}\n"
            "Return JSON with one key: enriched_keywords (list of strings). "
            "Only include technical or engineering-relevant keywords.\n\n"
            + "\n".join(f"- {snippet}" for snippet in snippets)
        )
        response = GeminiFlash(model_name=config.get("gemini_semantic_model", "gemini-2.5-flash")).call(
            system_prompt,
            user_prompt,
            temperature=0.1,
        )
        payload = json.loads(_extract_json_blob(response))
        enriched = [str(item).strip() for item in payload.get("enriched_keywords", []) if str(item).strip()]
        state["jd_analysis"]["enriched_keywords"] = enriched
    except Exception as exc:
        log_error(state, f"Company enrichment fallback used: {exc}")
        state["jd_analysis"]["enriched_keywords"] = []

    return state
