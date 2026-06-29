from __future__ import annotations

import json
from typing import Any

from app.agent.state import ResumeState
from app.llm.router import RoutedModel
from app.prompts.score_resume import build_semantic_score_prompt
from app.utils.config import get_config
from app.utils.json_utils import extract_json_blob
from app.utils.keyword_matcher import (
    build_synonym_map,
    extract_metrics_from_bullet,
    extract_resume_bullets,
    find_keyword_in_text,
    identify_high_value_zones,
    matched_keywords,
    normalize_keyword,
    section_quality_snapshot,
    split_sections,
    strip_latex_commands,
)
from app.utils.logger import log_error, log_status

DEFAULT_ATS_WEIGHTS = {
    "keyword_match": 0.35,
    "semantic_context": 0.20,
    "section_quality": 0.15,
    "keyword_placement": 0.15,
    "impact_metrics": 0.15,
}


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


def _semantic_context_score(keywords: list[str], bullets: list[str], skills_text: str) -> dict[str, object]:
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
        system_prompt, user_prompt = build_semantic_score_prompt(keywords, bullets, skills_text)
        response = RoutedModel("stage1", task="ats_scoring").call(system_prompt, user_prompt, temperature=0.1)
        payload = json.loads(extract_json_blob(response))
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


def compute_ats_score(
    resume_tex: str,
    jd_analysis: dict[str, Any],
    state: ResumeState | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Score a LaTeX resume against a JD analysis. Pure-ish: depends only on the two
    inputs (plus config for weights/semantic toggle). ``state`` is used solely for
    optional error logging; pass ``None`` to score silently (e.g. the baseline)."""
    resume_text = strip_latex_commands(resume_tex)
    bullets = extract_resume_bullets(resume_tex)
    synonym_map = build_synonym_map()

    base_keywords = _dedupe_keywords(
        list(jd_analysis.get("keywords", []))
        + list(jd_analysis.get("required_skills", []))
    )
    enriched_keywords = _dedupe_keywords(list(jd_analysis.get("enriched_keywords", [])))

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

    sections = split_sections(resume_tex)
    skills_text = strip_latex_commands(sections.get("Skills", ""))

    semantic = _semantic_context_score(base_keywords, bullets, skills_text)
    if state is not None and semantic.get("fallback") and semantic.get("error"):
        log_error(state, f"ATS semantic scoring fallback used: {semantic['error']}")

    section_quality = section_quality_snapshot(resume_tex)
    zones = identify_high_value_zones(resume_tex)
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

    missing_required = [
        skill for skill in jd_analysis.get("required_skills", [])
        if not find_keyword_in_text(skill, resume_text, synonym_map)
    ]
    missing_nice = [
        skill for skill in jd_analysis.get("nice_to_have", [])
        if not find_keyword_in_text(skill, resume_text, synonym_map)
    ]
    missing_enriched = [
        skill for skill in enriched_keywords
        if not find_keyword_in_text(skill, resume_text, synonym_map)
    ]

    if weights is None:
        weights = {**DEFAULT_ATS_WEIGHTS, **get_config().get("ats_score_weights", {})}
    overall = int(
        round(
            keyword_score * weights["keyword_match"]
            + int(semantic["score"]) * weights["semantic_context"]
            + int(section_quality["score"]) * weights["section_quality"]
            + placement_score * weights["keyword_placement"]
            + impact_score * weights["impact_metrics"]
        )
    )

    skills_gap = {
        "missing_required": missing_required,
        "missing_nice_to_have": missing_nice,
        "missing_enriched": missing_enriched,
    }
    return {
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
            "zones": list(zones.keys()),
        },
        "impact_metrics": {
            "score": impact_score,
            "metrics_bullets": metrics_bullets,
            "total_bullets": len(bullets),
        },
        "skills_gap": skills_gap,
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


def score_resume(state: ResumeState) -> ResumeState:
    iteration = int(state.get("optimization_iteration", 0)) + 1
    log_status(state, f"Scoring final resume for ATS match (pass {iteration})...")

    ats_score = compute_ats_score(state["final_tex"], state["jd_analysis"], state)
    overall = int(ats_score["overall"])

    state["ats_score"] = ats_score
    state["skills_gap"] = ats_score["skills_gap"]
    state["optimization_iteration"] = iteration
    state["optimization_scores"] = list(state.get("optimization_scores", [])) + [overall]

    label = "Strong Match" if overall >= 75 else "Moderate Match" if overall >= 50 else "Needs Work"
    state["ats_score_summary"] = f"{overall}% Match - {label}"
    return state

