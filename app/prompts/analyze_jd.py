from __future__ import annotations


def build_analyze_jd_prompt(jd_text: str, skills_md: str) -> tuple[str, str]:
    system_prompt = f"You are a JD analysis expert.\n\n{skills_md}"
    user_prompt = f"""
Analyze the job description below and return JSON only with these keys:
- reasoning: a paragraph summarizing the company's core mission and the specific technical profile they are looking for.
- required_skills: list[str]
- nice_to_have: list[str]
- keywords: list[str] with the top 15 ATS keywords
- tone: one of [startup_casual, enterprise_formal, research_academic, consulting_professional]
- role_level: one of [intern, junior, mid, senior, lead]
- company_name: string (infer aggressively from context, e.g., "We're hiring at Sarvam" -> "Sarvam", else return "Not Specified")
- role_title: string (infer aggressively from context, e.g., "Forward Deployed Software Engineer", else return "Not Specified")

Job description:
{jd_text}
""".strip()
    return system_prompt, user_prompt

