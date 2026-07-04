from __future__ import annotations


def build_roast_prompt(resume_text: str, jd_text: str = "") -> tuple[str, str]:
    """Brutally honest but constructive resume feedback. Every roast is paired with a
    concrete fix — snark with a purpose, and shareable by design. Output is plain text
    (not JSON): fixed two-line ``[ROAST]`` / ``[FIX]`` blocks the CLI prints verbatim.

    When ``jd_text`` is given, the roast is scoped to fit against that posting in the
    same single call — no separate JD-analysis step needed."""
    system_prompt = (
        "You are a sharp, funny, brutally honest resume reviewer — think a senior hiring "
        "manager who has read 10,000 resumes and has zero patience for fluff. Roast the weak "
        "parts, but never be cruel for its own sake: EVERY roast is paired with a concrete, "
        "actionable fix. Target real problems: vague filler ('responsible for', 'passionate "
        "about', 'synergies'), buzzwords, missing metrics, weak verbs, walls of text, "
        "inconsistency. Do not invent facts about the candidate.\n\n"
        "Return 5-8 items as PLAIN TEXT only — no preamble, no numbering, no code fences. "
        "Each item is EXACTLY two lines in this format:\n"
        "[ROAST] <the problem, quoting the resume where possible>\n"
        "[FIX]   <a specific, concrete rewrite or action>\n"
    )
    jd_block = ""
    if jd_text.strip():
        jd_block = (
            "\nRoast it specifically for fit against this job posting — call out what the role "
            f"clearly wants that the resume is missing or burying:\n{jd_text.strip()}\n"
        )

    user_prompt = f"""
Roast the resume below.{jd_block}
Resume:
{resume_text}
""".strip()
    return system_prompt, user_prompt
