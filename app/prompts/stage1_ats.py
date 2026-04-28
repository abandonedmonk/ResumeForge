from __future__ import annotations


def build_stage1_prompt(
    skills_md: str,
    jd_analysis: dict,
    section_name: str,
    bullets: list[str],
    project_context: str | None,
) -> tuple[str, str]:
    system_prompt = (
        f"{skills_md}\n\n"
        "You are an ATS optimization expert. Focus on keyword coverage and relevance only. "
        "Another model will improve prose quality later."
    )
    joined_bullets = "\n".join(f"- {bullet}" for bullet in bullets)
    user_prompt = f"""
Section: {section_name}
JD keywords: {jd_analysis.get("keywords", [])}
Required skills: {jd_analysis.get("required_skills", [])}
Role level: {jd_analysis.get("role_level", "mid")}
Project context:
{project_context or "None"}

Rewrite the bullets below.
Rules:
- Keep the exact same number of bullets
- Preserve all metrics and numbers
- Do not invent projects, tools, or responsibilities
- Return only the rewritten bullets, one per line, with no numbering

Bullets:
{joined_bullets}
""".strip()
    return system_prompt, user_prompt

