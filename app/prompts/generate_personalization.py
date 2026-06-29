from __future__ import annotations

import json


def _gap_keywords(skills_gap: dict[str, list[str]] | None) -> list[str]:
    """Flatten the populated skills-gap buckets into one ordered, de-duplicated list."""
    if not skills_gap:
        return []
    ordered: list[str] = []
    seen: set[str] = set()
    for bucket in ("missing_required", "missing_nice_to_have", "missing_enriched"):
        for item in skills_gap.get(bucket, []) or []:
            cleaned = str(item).strip()
            key = cleaned.lower()
            if cleaned and key not in seen:
                seen.add(key)
                ordered.append(cleaned)
    return ordered


def build_selection_prompt(
    skills_md: str,
    jd_analysis: dict,
    projects_context: dict[str, dict[str, object]],
    max_skills: int = 4,
    max_projects: int = 3,
    skills_gap: dict[str, list[str]] | None = None,
) -> tuple[str, str]:
    """Stage 1: Reasoning about which projects and skill categories to pick."""
    system_prompt = (
        f"{skills_md}\n\n"
        "You are an expert talent strategist. Your goal is to select the most relevant projects and skill categories for a specific job.\n"
        "Analyze the JD and the candidate's inventory. Pick the ones that offer the highest matching correlation.\n"
        "Return JSON only."
    )
    compact_inventory = []
    for key, project in projects_context.items():
        compact_inventory.append(
            {
                "key": key,
                "title": project.get("heading", key),
                "tech_stack": project.get("tech_stack", []),
                "keywords": project.get("keywords", []),
                "summary": project.get("summary", ""),
            }
        )

    gap_keywords = _gap_keywords(skills_gap)
    gap_block = ""
    if gap_keywords:
        gap_block = (
            "\nGAP TO CLOSE (a previous pass scored below target — these JD keywords are "
            "still missing). Prefer projects whose tech stack, keywords, or summary genuinely "
            f"evidence them; do NOT pick a project that has no real connection:\n{json.dumps(gap_keywords, indent=2)}\n"
        )

    user_prompt = f"""
Job analysis:
{json.dumps(jd_analysis, indent=2)}

Project inventory:
{json.dumps(compact_inventory, indent=2)}
{gap_block}
Task:
1. Select exactly {max_skills} skill categories from the provided skill file that best match this JD. Order them by relevance.
2. Select exactly {max_projects} projects from the inventory that best demonstrate the required experience.

Return valid JSON:
{{
  "selected_skill_categories": [{", ".join(f'"Category {i + 1}"' for i in range(max_skills))}],
  "selected_project_keys": [{", ".join(f'"project_key_{i + 1}"' for i in range(max_projects))}],
  "selection_reasoning": {{
    "skills": "why these categories...",
    "projects": "why these projects..."
  }}
}}
""".strip()
    return system_prompt, user_prompt


def build_generation_prompt(
    skills_md: str,
    jd_analysis: dict,
    selected_projects: list[dict],
    selected_skill_categories: list[str],
    max_bullets_per_project: int = 3,
    skills_gap: dict[str, list[str]] | None = None,
    recommendations: list[str] | None = None,
) -> tuple[str, str]:
    """Stage 2: Writing the actual tailored content for the selected items."""
    system_prompt = (
        f"{skills_md}\n\n"
        "You are a professional resume writer specializing in ATS optimization. "
        "Write compelling headline, bullet points, and skill lists based on the selected items, the detailed repo context, and the JD.\n"
        "Return JSON only. Use **bold emphasis** for key technical terms or achievements."
    )

    gap_keywords = _gap_keywords(skills_gap)
    gap_block = ""
    if gap_keywords or recommendations:
        lines = ["\nGAP TO CLOSE (integrate ONLY where truthful — never fabricate):"]
        if gap_keywords:
            lines.append(f"- Missing JD keywords: {json.dumps(gap_keywords)}")
        if recommendations:
            lines.append("- Scorer recommendations:")
            lines.extend(f"  - {rec}" for rec in recommendations)
        gap_block = "\n".join(lines) + "\n"

    user_prompt = f"""
Job analysis:
{json.dumps(jd_analysis, indent=2)}

Selected projects for detail:
{json.dumps(selected_projects, indent=2)}

Selected skill categories to fill:
{json.dumps(selected_skill_categories, indent=2)}
{gap_block}
Task:
1. Before writing, create "drafting_notes" summarizing which keywords from the JD you will prioritize for these specific selected items.
2. Write a tailored one-sentence headline.
3. For each selected skill category, pick 3-5 items from the candidate's actual skill inventory (from the system prompt) that best map to the JD requirements. Use the candidate's exact tool names (e.g., 'Ragas' not 'evals', 'LangGraph' or 'CrewAI' not 'agentic workflows', 'AWS (Bedrock, S3, etc)' not just 'AWS'). Do NOT invent new skills or paraphrase tool names. Sort the items within each skill category such that the exact matching technical keywords appear first in the list. CRITICAL: each individual skill item must appear in AT MOST ONE category — never repeat the same tool across multiple categories.
4. For each project, use the detailed repo context to rewrite exactly {max_bullets_per_project} bullet points that emphasize architecture, implementation depth, and role relevance. Preserve metrics and follow the style guide.
5. Do not ignore the detailed context just because the old bullets are short. Pull concrete implementation details from the provided project body when they are truthful and role-relevant.
6. GROUNDED KEYWORDS: If a required-but-missing keyword (see GAP TO CLOSE above, if present) is genuinely evidenced anywhere in a project's body/description/tech_stack — even if absent from its current bullets — surface it naturally in a bullet (e.g. a project that clearly built retrieval over documents can legitimately name **RAG**). If NO selected project genuinely supports a missing keyword, do NOT fabricate it; leave it out. Truthfulness outranks coverage.

Return valid JSON:
{{
  "drafting_notes": "A quick paragraph on your strategy for these specific items...",
  "headline": "sentence here",
  "skills": [
    {{"category": "Category Name", "items": ["Item 1", "Item 2"]}}
  ],
  "projects": [
    {{
      "title": "Project Title",
      "date_range": "Month Year -- Month Year",
      "bullets": [{", ".join(f'"bullet {i + 1}"' for i in range(max_bullets_per_project))}]
    }}
  ]
}}
""".strip()
    return system_prompt, user_prompt
