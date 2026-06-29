"""Parse extracted resume text + links into the structured Profile schema.

Best-effort, grounded extraction (mirrors profile_from_readme.py): the LLM fills
only what the resume evidences and leaves everything else empty — no invention.
"""
from __future__ import annotations

import json


def build_resume_extraction_prompt(resume_text: str, links: list[str]) -> tuple[str, str]:
    system_prompt = (
        "You parse a resume's raw text into structured JSON. "
        "HARD RULES:\n"
        "- Extract ONLY what the text supports. Never invent companies, dates, degrees, metrics, or skills.\n"
        "- Leave any field you cannot determine as an empty string or empty list.\n"
        "- Preserve the candidate's wording for experience bullets; do not embellish.\n"
        "Return JSON only."
    )

    excerpt = (resume_text or "").strip()[:14000] or "(no extractable text)"
    links_view = json.dumps(links[:30], indent=2) if links else "[]"

    user_prompt = f"""
Hyperlinks found embedded in the PDF (use to fill contact/cert URLs where they clearly belong):
{links_view}

Resume text (raw, may be imperfectly ordered):
\"\"\"
{excerpt}
\"\"\"

Return valid JSON with exactly this shape (omit nothing; use "" / [] when unknown):
{{
  "contact": {{"name": "", "email": "", "phone": "", "linkedin": "", "github": "", "website": "", "location": ""}},
  "education": [
    {{"institution": "", "city": "", "degree": "", "dates": "", "gpa": "", "coursework": ""}}
  ],
  "experience": [
    {{"company": "", "role": "", "location": "", "dates": "", "bullets": ["", ""]}}
  ],
  "certifications": [
    {{"name": "", "issuer": "", "date": "", "url": ""}}
  ]
}}
""".strip()
    return system_prompt, user_prompt
