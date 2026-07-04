from __future__ import annotations


def build_gap_prompt(inventory: str, resume_text: str) -> tuple[str, str]:
    """Stage 3 of the gap-finder: given a compact inventory of what the candidate has
    actually built (from GitHub) and what their resume currently claims, surface the
    delta. Grounded — the model may only reason from the inventory, never invent repos."""
    system_prompt = (
        "You compare what a developer has actually built (GitHub inventory) against what "
        "their resume claims, and surface the delta. Ground every statement in the provided "
        "inventory — never invent projects, tools, or metrics not present in it. "
        "Return JSON only — no prose, no code fences."
    )
    user_prompt = f"""
Compare the GitHub inventory against the resume and return JSON matching this exact schema:
{{
  "missing": ["string", ...],       // real, resume-worthy work in the GitHub inventory that the resume does not mention
  "undersold": ["string", ...],     // things the resume mentions but understates vs the evidence
  "overclaimed": ["string", ...],   // resume claims NOT supported by the inventory (flag honestly; [] if none)
  "suggested_bullets": ["string", ...] // up to 3 concrete resume bullets the candidate could add, grounded in the inventory
}}

GitHub inventory (what they actually built):
{inventory}

Resume (what they currently claim):
{resume_text}
""".strip()
    return system_prompt, user_prompt
