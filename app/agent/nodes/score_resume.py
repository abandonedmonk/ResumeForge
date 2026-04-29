from __future__ import annotations

import json
import re

from app.agent.state import ResumeState
from app.llm.gemini import GeminiFlash
from app.prompts.score_resume import build_semantic_score_prompt
from app.utils.config import get_config
from app.utils.keyword_matcher import (
    build_synonym_map,
    extract_metrics_from_bullet,
    extract_resume_bullets,
    find_keyword_in_text,
    identify_high_value_zones,
    keyword_frequency,
    matched_keywords,
    normalize_keyword,
    section_quality_snapshot,
    split_sections,
    strip_latex_commands,
)
from app.utils.logger import log_error, log_status


def _extract_json_blob(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else "{}"


def _dedupe_keywords(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        normalized = normalize_keyword(cleaned)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(cleaned)
    return deduped


def _semantic_context_score(keywords: list[str], bullets: list[str]) -> dict[str, object]:
    config = get_config()
    if not config.get("ats_semantic_scoring", True):
        return {
            "score": 70,
            "contextual": [],
            "name_dropped": [],
            "absent": keywords,
            "fallback": True,
        }

    try:
        system_prompt, user_prompt = build_semantic_score_prompt(keywords, bullets)
        response = GeminiFlash(model_name=config.get("gemini_semantic_model", "gemini-2.5-flash")).call(
            system_prompt,
            user_prompt,
            temperature=0.1,
        )
        payload = json.loads(_extract_json_blob(response))
        contextual = [keyword for keyword, verdict in payload.get("keyword_results", {}).items() if verdict == "contextual"]
        name_dropped = [keyword for keyword, verdict in payload.get("keyword_results", {}).items() if verdict == "name_dropped"]
        absent = [keyword for keyword, verdict in payload.get("keyword_results", {}).items() if verdict == "absent"]
        score = int(round((len(contextual) / max(1, len(keywords))) * 100))
        return {
            "score": score,
            "contextual": contextual,
            "name_dropped": name_dropped,
            "absent": absent,
            "fallback": False,
        }
    except Exception as exc:
        return {
            "score": 70,
            "contextual": [],
            "name_dropped": [],
            "absent": [],
            "fallback": True,
            "error": str(exc),
        }


def _recommendations(scorecard: dict[str, object]) -> list[str]:
    recommendations: list[str] = []
    keyword_score = int(scorecard["keyword_match"]["score"])
    semantic_score = int(scorecard["semantic_context"]["score"])
    section_score = int(scorecard["section_quality"]["score"])
    placement_score = int(scorecard["keyword_placement"]["score"])
    impact_score = int(scorecard["impact_metrics"]["score"])

    if keyword_score < 70:
        recommendations.append("Add more required JD keywords naturally into your experience and project bullets.")
    if semantic_score < 70:
        recommendations.append("Show stronger evidence for the target skills through concrete achievements, systems, or outcomes.")
    if section_score < 80:
        recommendations.append("Strengthen core sections like Experience, Skills, or Projects so the resume looks complete to ATS parsers.")
    if placement_score < 70:
        recommendations.append("Move the most important JD keywords into your summary, skills block, and first bullet under recent experience.")
    if impact_score < 70:
        recommendations.append("Add more quantified impact with percentages, counts, speedups, or scale metrics.")
    if not recommendations:
        recommendations.append("The resume is already well-aligned; focus on small wording improvements for role-specific emphasis.")
    return recommendations


def score_resume(state: ResumeState) -> ResumeState:
    log_status(state, "Scoring final resume for ATS match...")
    resume_text = strip_latex_commands(state["final_tex"])
    bullets = extract_resume_bullets(state["final_tex"])
    synonym_map = build_synonym_map()

    base_keywords = _dedupe_keywords(
        list(state["jd_analysis"].get("keywords", []))
        + list(state["jd_analysis"].get("required_skills", []))
    )
    enriched_keywords = _dedupe_keywords(list(state["jd_analysis"].get("enriched_keywords", [])))

    matched = matched_keywords(base_keywords, resume_text, synonym_map)
    matched_enriched = matched_keywords(enriched_keywords, resume_text, synonym_map)
    keyword_score = int(
        round(
            (
                len(matched)
                + 0.5 * len(matched_enriched)
            )
            / max(1, len(base_keywords) + 0.5 * len(enriched_keywords))
            * 100
        )
    )

    semantic = _semantic_context_score(base_keywords, bullets)
    if semantic.get("fallback") and semantic.get("error"):
        log_error(state, f"ATS semantic scoring fallback used: {semantic['error']}")

    section_quality = section_quality_snapshot(state["final_tex"])
    zones = identify_high_value_zones(state["final_tex"])
    zone_weights = {"headline": 3.0, "skills": 2.0, "first_bullets": 1.5}
    weighted_hits = 0.0
    max_weight = float(len(base_keywords)) * sum(zone_weights.values())
    for keyword in base_keywords:
        for zone_name, zone_text in zones.items():
            if find_keyword_in_text(keyword, zone_text, synonym_map):
                weighted_hits += zone_weights[zone_name]
    placement_score = int(round((weighted_hits / max(1.0, max_weight)) * 100))

    metrics_bullets = sum(1 for bullet in bullets if extract_metrics_from_bullet(bullet))
    target_metrics = max(1, int(round(len(bullets) * 0.6)))
    impact_score = int(round(min(metrics_bullets / target_metrics, 1.0) * 100))

    sections = split_sections(state["final_tex"])
    skills_text = strip_latex_commands(sections.get("Skills", ""))
    _ = keyword_frequency(skills_text, base_keywords, synonym_map)

    missing_required = [
        skill for skill in state["jd_analysis"].get("required_skills", [])
        if not find_keyword_in_text(skill, resume_text, synonym_map)
    ]
    missing_nice = [
        skill for skill in state["jd_analysis"].get("nice_to_have", [])
        if not find_keyword_in_text(skill, resume_text, synonym_map)
    ]
    missing_enriched = [
        skill for skill in enriched_keywords
        if not find_keyword_in_text(skill, resume_text, synonym_map)
    ]

    overall = int(
        round(
            keyword_score * 0.35
            + int(semantic["score"]) * 0.20
            + int(section_quality["score"]) * 0.15
            + placement_score * 0.15
            + impact_score * 0.15
        )
    )

    state["skills_gap"] = {
        "missing_required": missing_required,
        "missing_nice_to_have": missing_nice,
        "missing_enriched": missing_enriched,
    }
    state["ats_score"] = {
        "overall": overall,
        "keyword_match": {
            "score": keyword_score,
            "matched": matched,
            "enriched_matched": matched_enriched,
            "total": len(base_keywords),
            "total_enriched": len(enriched_keywords),
        },
        "semantic_context": semantic,
        "section_quality": section_quality,
        "keyword_placement": {
            "score": placement_score,
            "high_value_hits": round(weighted_hits, 2),
            "zones": zones,
        },
        "impact_metrics": {
            "score": impact_score,
            "metrics_bullets": metrics_bullets,
            "total_bullets": len(bullets),
        },
        "skills_gap": state["skills_gap"],
        "recommendations": _recommendations(
            {
                "keyword_match": {"score": keyword_score},
                "semantic_context": {"score": int(semantic["score"])},
                "section_quality": {"score": int(section_quality["score"])},
                "keyword_placement": {"score": placement_score},
                "impact_metrics": {"score": impact_score},
            }
        ),
    }

    label = "Strong Match" if overall >= 75 else "Moderate Match" if overall >= 50 else "Needs Work"
    state["ats_score_summary"] = f"{overall}% Match - {label}"
    return state

