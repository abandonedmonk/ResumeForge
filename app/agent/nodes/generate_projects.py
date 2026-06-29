from __future__ import annotations

import json

from app.agent.state import ResumeState
from app.llm.router import RoutedModel
from app.prompts.generate_personalization import build_selection_prompt, build_generation_prompt
from app.utils.config import get_config
from app.utils.json_utils import extract_json_blob
from app.utils.logger import log_error, log_status

# changes_log sections that this node (re)writes each pass — pruned on retry so the
# log reflects the latest generation rather than stacking duplicates per iteration.
_OWNED_SECTIONS = {"Headline", "Skills", "Projects"}


def _fallback_skills() -> list[dict[str, object]]:
    return [
        {"category": "Languages", "items": ["Python", "Rust", "C++", "C", "SQL"]},
        {"category": "AI & ML Frameworks", "items": ["PyTorch", "Accelerate", "LangChain", "OpenCV"]},
        {
            "category": "Gen AI & LLM Engineering",
            "items": [
                "Agentic Workflows",
                "LLM Quantization",
                "Retrieval-Augmented Generation (RAG)",
                "Fine-Tuning",
                "Prompt Engineering",
            ],
        },
        {
            "category": "Cloud, APIs & MLOps",
            "items": ["AWS (S3, Lambda, API Gateway, EventBridge)", "GCP", "FastAPI"],
        },
    ]


def _fallback_projects(projects_context: dict[str, dict[str, object]], limit: int = 3) -> list[dict[str, object]]:
    projects: list[dict[str, object]] = []
    for project in list(projects_context.values())[:limit]:
        bullets = list(project.get("bullets", []))[:3]
        if not bullets:
            continue
        projects.append(
            {
                "title": project.get("heading", project.get("title", "Project")),
                "bullets": bullets,
                "date_range": str(project.get("date_range", "")).strip() or "Month Year -- Month Year",
                "url": str(project.get("url", "")).strip(),
                "selection_reason": "Fallback selection used because personalization generation failed.",
            }
        )
    return projects


def generate_projects(state: ResumeState) -> ResumeState:
    log_status(state, "Starting two-stage personalization (Selection -> Writing)...")
    projects_context = state["projects_context"]
    if not isinstance(projects_context, dict) or not projects_context:
        log_error(state, "Project inventory is empty. Projects section will remain blank.")
        return state

    budget = get_config()
    max_skills = int(budget.get("max_skills", 4))
    max_projects = int(budget.get("max_projects", 3))
    max_bullets = int(budget.get("max_bullets_per_project", 3))

    # On an optimization retry the scorer has populated skills_gap / recommendations.
    # Feed them in so the selection and writing target the real missing keywords.
    is_retry = int(state.get("optimization_iteration", 0)) > 0
    skills_gap = state.get("skills_gap") if is_retry else None
    recommendations = state.get("ats_score", {}).get("recommendations") if is_retry else None
    if is_retry:
        log_status(state, "Optimization retry: regenerating to close the ATS keyword gap...")
        state["changes_log"] = [
            change for change in state["changes_log"]
            if change.get("section") not in _OWNED_SECTIONS
        ]

    try:
        # --- Stage 1: Selection (Reasoning) ---
        log_status(state, "Stage 1: Selecting best-fit projects and skill categories...")
        sel_sys, sel_user = build_selection_prompt(
            state["skills_md"],
            state["jd_analysis"],
            projects_context,
            max_skills=max_skills,
            max_projects=max_projects,
            skills_gap=skills_gap,
        )
        sel_response = RoutedModel("stage1").call(sel_sys, sel_user)
        sel_payload = json.loads(extract_json_blob(sel_response))
        
        selected_keys = sel_payload.get("selected_project_keys", [])
        selected_skills = sel_payload.get("selected_skill_categories", [])
        selection_reasoning = sel_payload.get("selection_reasoning", {})

        # Prepare context for Stage 2
        selected_projects_data = []
        for key in selected_keys:
            p = projects_context.get(key)
            if p:
                selected_projects_data.append({
                    "key": key,
                    "title": p.get("heading", key),
                    "tech_stack": p.get("tech_stack", []),
                    "keywords": p.get("keywords", []),
                    "bullets": p.get("bullets", []),
                    "body": p.get("body", ""),
                    "summary": p.get("summary", ""),
                    "url": p.get("url", ""),
                    "date_range": p.get("date_range", "Month Year -- Month Year")
                })
        
        # --- Stage 2: Generation (Writing) ---
        log_status(state, "Stage 2: Writing tailored headline, bullets, and skill lists...")
        gen_sys, gen_user = build_generation_prompt(
            state["skills_md"],
            state["jd_analysis"],
            selected_projects_data,
            selected_skills,
            max_bullets_per_project=max_bullets,
            skills_gap=skills_gap,
            recommendations=recommendations,
        )
        gen_response = RoutedModel("stage2").call(gen_sys, gen_user)
        gen_payload = json.loads(extract_json_blob(gen_response))

        state["generated_headline"] = str(gen_payload.get("headline", "")).strip()

        # Format Skills — then deduplicate across categories
        raw_skills = [
            {
                "category": str(category.get("category", "")).strip(),
                "items": [str(item).strip() for item in category.get("items", []) if str(item).strip()],
            }
            for category in gen_payload.get("skills", [])
            if isinstance(category, dict)
        ]
        seen: set[str] = set()
        deduped_skills: list[dict[str, object]] = []
        for cat in raw_skills:
            unique_items: list[str] = []
            for item in cat["items"]:
                # Normalise: lowercase + strip anything after the first '(' for fuzzy matching
                key = item.lower().split("(")[0].strip()
                if key not in seen:
                    seen.add(key)
                    unique_items.append(item)
            if unique_items:
                deduped_skills.append({"category": cat["category"], "items": unique_items})
        state["generated_skills"] = deduped_skills

        # Format Projects
        formatted_projects: list[dict[str, object]] = []
        for index, project in enumerate(gen_payload.get("projects", [])):
            if not isinstance(project, dict):
                continue
            source_project = selected_projects_data[index] if index < len(selected_projects_data) else {}
            formatted_projects.append(
                {
                    "title": str(project.get("title", "")).strip() or str(source_project.get("title", "")).strip(),
                    "bullets": [str(bullet).strip() for bullet in project.get("bullets", []) if str(bullet).strip()],
                    "date_range": str(project.get("date_range", "")).strip()
                    or str(source_project.get("date_range", "")).strip()
                    or "Month Year -- Month Year",
                    "url": str(source_project.get("url", "")).strip(),
                    "selection_reason": selection_reasoning.get("projects", "Selected for JD relevance."),
                }
            )
        state["generated_projects"] = formatted_projects

        state["personalization_notes"] = {
            "drafting_notes": str(gen_payload.get("drafting_notes", "")).strip(),
            "headline_reason": "Generated for JD relevance.",
            "skills_reason": str(selection_reasoning.get("skills", "")).strip(),
            "project_selection_reason": str(selection_reasoning.get("projects", "")).strip(),
        }

    except Exception as exc:
        log_error(state, f"Two-stage generation failed, using fallback: {exc}")
        state["generated_headline"] = "AI engineer with experience building production RAG systems."
        state["generated_skills"] = _fallback_skills()
        state["generated_projects"] = _fallback_projects(projects_context)
        state["personalization_notes"] = {
            "headline_reason": "Fallback used.",
            "skills_reason": "Fallback used.",
            "project_selection_reason": "Fallback used.",
        }

    # Final cleanup and logging — honor the active template's content budget.
    state["generated_skills"] = state["generated_skills"][:max_skills]
    state["generated_projects"] = state["generated_projects"][:max_projects]

    if state["generated_headline"]:
        state["changes_log"].append({
            "section": "Headline",
            "old_bullets": [], "new_bullets": [state["generated_headline"]],
            "reasoning": state["personalization_notes"]["headline_reason"]
        })

    if state["generated_skills"]:
        state["changes_log"].append({
            "section": "Skills",
            "old_bullets": [],
            "new_bullets": [f"{c['category']}: {', '.join(c['items'])}" for c in state["generated_skills"]],
            "reasoning": state["personalization_notes"]["skills_reason"]
        })

    if state["generated_projects"]:
        state["changes_log"].append({
            "section": "Projects",
            "old_bullets": [],
            "new_bullets": [f"{p['title']}: {' | '.join(p['bullets'])}" for p in state["generated_projects"]],
            "reasoning": state["personalization_notes"]["project_selection_reason"]
        })

    return state
