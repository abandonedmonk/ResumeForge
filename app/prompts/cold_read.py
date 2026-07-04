from __future__ import annotations


def build_cold_read_prompt(resume_text: str, jd_text: str) -> tuple[str, str]:
    """Adversarial zero-context read. The evaluator is given ONLY the resume and JD —
    no application history, no framing — and must infer, in three fields, what a busy
    recruiter would conclude in the first pass."""
    system_prompt = (
        "You are a busy technical recruiter seeing this resume for the first time, with no "
        "prior context about the candidate. You have 20 seconds. Read only what is on the page "
        "and answer honestly, even if unflattering. Return JSON only — no prose, no code fences."
    )
    user_prompt = f"""
Given ONLY the resume and job description below, return JSON matching this exact schema:
{{
  "targeted_role": "string — the single role you think this person is aiming for, based purely on the resume",
  "strongest_qualification": "string — their single strongest qualification for THIS job description",
  "biggest_gap": "string — the biggest gap or mismatch you see between the resume and this JD"
}}

Do not invent details. If the resume points at a different role than the JD, say so plainly in "targeted_role".

Job description:
{jd_text}

Resume:
{resume_text}
""".strip()
    return system_prompt, user_prompt
