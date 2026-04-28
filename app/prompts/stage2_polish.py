from __future__ import annotations


def build_stage2_prompt(
    skills_md: str,
    jd_analysis: dict,
    stage1_bullets: list[str],
    section_name: str,
) -> tuple[str, str]:
    system_prompt = (
        f"{skills_md}\n\n"
        "You are a technical resume writer. Make bullets sound sharp, human, and impressive "
        "without dropping ATS keywords or metrics."
    )
    joined_bullets = "\n".join(f"- {bullet}" for bullet in stage1_bullets)
    user_prompt = f"""
Section: {section_name}
Company tone: {jd_analysis.get("tone", "enterprise_formal")}

Polish these ATS-optimized bullets.
Rules:
- Keep all keywords from the input bullets
- Keep all numbers and metrics unchanged
- Start bullets with strong, varied action verbs
- Keep each bullet concise enough for a resume
- Return only the final bullets, one per line, with no numbering

Bullets:
{joined_bullets}
""".strip()
    return system_prompt, user_prompt

