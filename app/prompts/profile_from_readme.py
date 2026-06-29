"""Turn a fetched GitHub repo (metadata + README) into a project profile.

``build_profile_prompt`` asks ``RoutedModel("stage1")`` for grounded JSON; a
Python ``serialize_profile`` then renders the inventory markdown so the
punctuation always round-trips through ``parse_projects_md``. The LLM only
supplies content — never the LaTeX/markdown scaffolding — matching the rest of
the codebase's content-only architecture.
"""
from __future__ import annotations

import json


def build_profile_prompt(repo_meta: dict, readme_md: str) -> tuple[str, str]:
    """Return ``(system_prompt, user_prompt)`` for distilling a repo into a profile."""
    system_prompt = (
        "You are a technical resume analyst. Given a GitHub repository's metadata and README, "
        "distill a truthful, ATS-friendly project profile.\n"
        "HARD RULES:\n"
        "- Ground every claim in the README/metadata. NEVER invent metrics, tools, or features "
        "the source does not support.\n"
        "- Only add a number/metric (wrapped in **bold**) when the README states it explicitly. "
        "If no metric is evidenced, write a strong bullet without one — do not fabricate.\n"
        "- Use the project's real tech stack and terminology, not generic buzzwords.\n"
        "Return JSON only."
    )

    meta_view = {
        "full_name": repo_meta.get("full_name", ""),
        "description": repo_meta.get("description", ""),
        "primary_language": repo_meta.get("language", ""),
        "topics": repo_meta.get("topics", []),
        "html_url": repo_meta.get("html_url", ""),
        "suggested_date_range": repo_meta.get("date_range", ""),
    }
    readme_excerpt = (readme_md or "").strip()[:12000] or "(no README provided)"

    user_prompt = f"""
Repository metadata:
{json.dumps(meta_view, indent=2)}

README (raw markdown, truncated):
\"\"\"
{readme_excerpt}
\"\"\"

Task: produce a project profile as JSON with exactly these keys:
- "title": short project name (no colon inside it)
- "one_line": one concise sentence describing what the project is
- "tech_stack": list of concrete technologies/libraries actually used
- "keywords": list of ATS keywords a recruiter/scanner would match on
- "bullets": list of 3 resume bullets following Impact -> Method -> Scale. Wrap any
  README-evidenced metric or core tool in **bold** (e.g. "**320 pages**", "**RAG pipeline**").
  Start each with a strong past-tense verb. No fabricated numbers.
- "what_contains": one paragraph on what the repository actually contains
- "core_architecture": list of bullets naming the key files/modules and their roles
- "ats_keywords": list of ATS keywords (may overlap with "keywords")

Return valid JSON only:
{{
  "title": "...",
  "one_line": "...",
  "tech_stack": ["..."],
  "keywords": ["..."],
  "bullets": ["...", "...", "..."],
  "what_contains": "...",
  "core_architecture": ["..."],
  "ats_keywords": ["..."]
}}
""".strip()
    return system_prompt, user_prompt


def _csv(items: object) -> str:
    if not isinstance(items, list):
        return str(items or "").strip()
    return ", ".join(str(item).strip() for item in items if str(item).strip())


def serialize_profile(repo_meta: dict, payload: dict) -> str:
    """Render the LLM payload into the exact numbered-inventory markdown schema.

    The single project is numbered ``1.`` because each imported repo lives in its
    own file and ``parse_projects_md`` keys per-file.
    """
    title = str(payload.get("title") or repo_meta.get("repo") or "Project").strip()
    title = title.split(":", 1)[0].strip() or "Project"
    one_line = str(payload.get("one_line") or repo_meta.get("description") or "").strip()
    date_range = str(repo_meta.get("date_range") or "").strip()
    html_url = str(repo_meta.get("html_url") or "").strip()
    tech_stack = _csv(payload.get("tech_stack"))
    keywords = _csv(payload.get("keywords"))
    ats_keywords = _csv(payload.get("ats_keywords")) or keywords

    bullets = [str(b).strip() for b in (payload.get("bullets") or []) if str(b).strip()]
    architecture = [str(a).strip() for a in (payload.get("core_architecture") or []) if str(a).strip()]
    what_contains = str(payload.get("what_contains") or "").strip()

    lines: list[str] = []
    lines.append(f"1. {title}: {one_line}" if one_line else f"1. {title}")
    if date_range:
        lines.append(f"[Date Range: {date_range}]")
    if html_url:
        lines.append(f"[GitHub URL: {html_url}]")
    if tech_stack:
        lines.append(f"[Tech Stack: {tech_stack}]")
    if keywords:
        lines.append(f"[Keywords: {keywords}]")
    for bullet in bullets:
        lines.append(f"- {bullet}")

    if what_contains:
        lines.append("")
        lines.append("### What the repo actually contains")
        lines.append(what_contains)

    if architecture:
        lines.append("")
        lines.append("### Core architecture")
        for item in architecture:
            lines.append(f"- {item}")

    if ats_keywords:
        lines.append("")
        lines.append("### ATS keywords")
        lines.append(ats_keywords)

    return "\n".join(lines).strip() + "\n"
