"""Prompt for the optional cover-letter generator.

Draws only on the tailored resume content already in state (headline, selected
skills, selected projects) and the JD analysis — same grounding ethos as the
rest of the pipeline (no invented experience).
"""
from __future__ import annotations

import json


def build_cover_letter_prompt(
    skills_md: str,
    jd_analysis: dict,
    resume_highlights: dict,
) -> tuple[str, str]:
    system_prompt = (
        f"{skills_md}\n\n"
        "You are an expert cover-letter writer. Write a concise, specific, one-page cover letter "
        "(3-4 short paragraphs) for the candidate, grounded ONLY in the resume highlights and job "
        "analysis provided. Do NOT invent employers, dates, or achievements not present below. "
        "Tone: direct and technical, no buzzwords or flattery. Return the letter as Markdown "
        "(no preamble, no '```'). Open with 'Dear Hiring Manager,' unless a contact is given."
    )

    user_prompt = f"""
Job analysis:
{json.dumps(jd_analysis, indent=2)}

Resume highlights to draw on:
- Headline: {resume_highlights.get('headline', '')}
- Skill categories: {json.dumps(resume_highlights.get('skills', []), indent=2)}
- Projects: {json.dumps(resume_highlights.get('projects', []), indent=2)}

Write the cover letter now. Reference the company/role from the job analysis, connect 2-3 concrete
projects/skills to the role's needs, and close with a brief, confident call to action.
""".strip()
    return system_prompt, user_prompt
