from __future__ import annotations


def build_analyze_jd_prompt(jd_text: str, skills_md: str) -> tuple[str, str]:
    system_prompt = (
        "You are a JD analysis expert. Return JSON only — no prose, no code fences. "
        "If a field cannot be determined from the text, use an empty list for list fields "
        'and "Not Specified" for string fields. Never invent skills the JD does not mention.\n\n'
        f"{skills_md}"
    )
    user_prompt = f"""
Analyze the job description below and return JSON only matching this exact schema:
{{
  "reasoning": "string — a paragraph on the company's core mission and the technical profile they want",
  "required_skills": ["string", ...],          // hard requirements; [] if none stated
  "nice_to_have": ["string", ...],             // preferred/bonus; [] if none stated
  "keywords": ["string", ...],                 // top 15 ATS keywords, most important first
  "tone": "startup_casual | enterprise_formal | research_academic | consulting_professional",
  "role_level": "intern | junior | mid | senior | lead",
  "company_name": "string — infer from context, else \\"Not Specified\\"",
  "role_title": "string — infer from context, else \\"Not Specified\\""
}}

Example (abridged) for a JD reading "Join Sarvam as a Forward Deployed Engineer; must know Python, LLMs, AWS; Kubernetes a plus":
{{
  "reasoning": "Sarvam builds production AI systems and needs an engineer who ships LLM features close to customers...",
  "required_skills": ["Python", "LLMs", "AWS"],
  "nice_to_have": ["Kubernetes"],
  "keywords": ["Python", "LLMs", "AWS", "Forward Deployed", "production", "..."],
  "tone": "startup_casual",
  "role_level": "mid",
  "company_name": "Sarvam",
  "role_title": "Forward Deployed Software Engineer"
}}

Job description:
{jd_text}
""".strip()
    return system_prompt, user_prompt

