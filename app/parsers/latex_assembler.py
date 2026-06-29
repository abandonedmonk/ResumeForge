from __future__ import annotations

import re

from app.utils.config import get_config
from app.utils.validator import escape_latex


SUMMARY_PATTERN = re.compile(
    r"(\\\\\s*\\vspace\{6pt\}\s*\n\s*)\{(?P<summary>[^{}]*)\}(\s*\n\\end\{center\})",
    re.MULTILINE,
)
SKILLS_START = "% PLACEHOLDER_SKILLS_START"
SKILLS_END = "% PLACEHOLDER_SKILLS_END"
PROJECTS_START = "% PLACEHOLDER_PROJECTS_START"
PROJECTS_END = "% PLACEHOLDER_PROJECTS_END"
DEFAULT_PROJECT_DATE_RANGE = "Month Year -- Month Year"


def _default_project_url() -> str:
    return str(get_config().get("candidate_github_url", "")).strip()


def inject_sections(original_tex: str, original_sections: dict[str, dict[str, object]], tailored_sections: dict[str, dict[str, object]]) -> str:
    final_tex = original_tex
    for section_name, tailored in tailored_sections.items():
        original = original_sections.get(section_name)
        if not original:
            continue
        raw_tex = str(original.get("raw_tex", ""))
        new_bullets = tailored.get("new_bullets", [])
        if not raw_tex or not new_bullets:
            continue

        replacement_lines: list[str] = []
        bullet_index = 0
        for line in raw_tex.splitlines():
            stripped = line.strip()
            if stripped.startswith(r"\item") and bullet_index < len(new_bullets):
                indent = re.match(r"^\s*", line).group(0)
                replacement_lines.append(f"{indent}\\item {new_bullets[bullet_index]}")
                bullet_index += 1
            else:
                replacement_lines.append(line)

        final_tex = final_tex.replace(raw_tex, "\n".join(replacement_lines), 1)

    return final_tex


def inject_resume_personalization(
    original_tex: str,
    generated_headline: str,
    generated_skills: list[dict[str, object]],
    generated_projects: list[dict[str, object]],
) -> str:
    final_tex = inject_headline(original_tex, generated_headline)
    final_tex = inject_skills_section(final_tex, generated_skills)
    if PROJECTS_START not in final_tex or PROJECTS_END not in final_tex:
        return final_tex

    project_block = format_project_entries(generated_projects)
    start_index = final_tex.index(PROJECTS_START) + len(PROJECTS_START)
    end_index = final_tex.index(PROJECTS_END)
    replacement = f"\n{project_block}\n  " if project_block else "\n  "
    return f"{final_tex[:start_index]}{replacement}{final_tex[end_index:]}"


def inject_headline(original_tex: str, generated_headline: str) -> str:
    cleaned_headline = generated_headline.strip()
    if not cleaned_headline:
        return original_tex
    return SUMMARY_PATTERN.sub(
        lambda match: f"{match.group(1)}{{{escape_latex(cleaned_headline)}}}{match.group(3)}",
        original_tex,
        count=1,
    )


def inject_skills_section(original_tex: str, generated_skills: list[dict[str, object]]) -> str:
    if SKILLS_START not in original_tex or SKILLS_END not in original_tex:
        return original_tex

    skills_lines = format_skill_entries(generated_skills)
    skills_block = "\n    ".join(skills_lines)
    start_index = original_tex.index(SKILLS_START) + len(SKILLS_START)
    end_index = original_tex.index(SKILLS_END)
    replacement = f"\n    {skills_block}\n    "
    return f"{original_tex[:start_index]}{replacement}{original_tex[end_index:]}"


def format_skill_entries(generated_skills: list[dict[str, object]]) -> list[str]:
    lines: list[str] = []
    for index, category in enumerate(generated_skills):
        name = str(category.get("category", "")).strip()
        items = [str(item).strip() for item in category.get("items", []) if str(item).strip()]
        if not name or not items:
            continue
        rendered_items = ", ".join(_format_emphasis(item) for item in items)
        suffix = r" \\" if index < len(generated_skills) - 1 else ""
        lines.append(rf"\textbf{{{escape_latex(name)}}}: {rendered_items}{suffix}")
    return lines


def format_project_entries(generated_projects: list[dict[str, object]]) -> str:
    max_bullets = int(get_config().get("max_bullets_per_project", 3))
    blocks: list[str] = []
    for project in generated_projects:
        title = escape_latex(str(project.get("title", "")).strip())
        if not title:
            continue
        raw_url = str(project.get("url", "")).strip() or _default_project_url()
        date_range = escape_latex(str(project.get("date_range", "")).strip() or DEFAULT_PROJECT_DATE_RANGE)
        bullets = [_sanitize_project_bullet(str(bullet).strip()) for bullet in project.get("bullets", []) if str(bullet).strip()]
        if not bullets:
            continue

        if raw_url:
            url = _latex_url(raw_url)
            heading_title = rf"\textbf{{{title}}} $|$ \href{{{url}}}{{\underline{{Project Link}}}}"
        else:
            heading_title = rf"\textbf{{{title}}}"
        lines = [
            r"  \resumeProjectHeading",
            rf"    {{{heading_title}}}{{{date_range}}}",
            r"    \resumeItemListStart",
        ]
        for bullet in bullets[:max_bullets]:
            lines.append(rf"      \resumeItem{{{bullet}}}")
        lines.append(r"    \resumeItemListEnd")
        blocks.append("\n".join(lines))

    return "\n".join(blocks)


def _latex_url(url: str) -> str:
    return url.replace("\\", "/").replace(" ", "%20")


def _sanitize_project_bullet(text: str) -> str:
    cleaned = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
    cleaned = re.sub(r"\\underline\{([^}]*)\}", r"\1", cleaned)
    cleaned = cleaned.replace(r"\&", "&")
    cleaned = cleaned.replace(r"\%", "%")
    return _format_emphasis(cleaned)


def _format_emphasis(text: str) -> str:
    parts = re.split(r"(\*\*.*?\*\*)", text)
    rendered: list[str] = []
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            rendered.append(rf"\textbf{{{escape_latex(part[2:-2])}}}")
        else:
            rendered.append(escape_latex(part))
    return "".join(rendered)
