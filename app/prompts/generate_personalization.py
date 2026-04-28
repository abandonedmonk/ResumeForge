from __future__ import annotations

import json


def build_selection_prompt(
    skills_md: str,
    jd_analysis: dict,
    projects_context: dict[str, dict[str, object]],
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
            }
        )
    user_prompt = f"""
Job analysis:
{json.dumps(jd_analysis, indent=2)}

Project inventory:
{json.dumps(compact_inventory, indent=2)}

Task:
1. Select exactly 4 skill categories from the provided skill file that best match this JD. Order them by relevance.
2. Select exactly 3 projects from the inventory that best demonstrate the required experience.

Return valid JSON:
{{
  "selected_skill_categories": ["Category 1", "Category 2", "Category 3", "Category 4"],
  "selected_project_keys": ["project_key_1", "project_key_2", "project_key_3"],
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
) -> tuple[str, str]:
    """Stage 2: Writing the actual tailored content for the selected items."""
    system_prompt = (
        f"{skills_md}\n\n"
        "You are a professional resume writer specializing in ATS optimization. "
        "Write compelling headline, bullet points, and skill lists based on the selected items and JD.\n"
        "Return JSON only. Use **bold emphasis** for key technical terms or achievements."
    )
    user_prompt = f"""
Job analysis:
{json.dumps(jd_analysis, indent=2)}

Selected projects for detail:
{json.dumps(selected_projects, indent=2)}

Selected skill categories to fill:
{json.dumps(selected_skill_categories, indent=2)}

Task:
1. Before writing, create "drafting_notes" summarizing which keywords from the JD you will prioritize for these specific selected items.
2. Write a tailored one-sentence headline.
3. For each selected skill category, list 3-5 specific technical skills or tools mentioned in the JD that fit that category.
4. For each project, rewrite exactly 3 bullet points to emphasize relative experience and impact. Preserve metrics and follow the style guide.

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
      "bullets": ["bullet 1", "bullet 2", "bullet 3"]
    }}
  ]
}}
""".strip()
    return system_prompt, user_prompt
