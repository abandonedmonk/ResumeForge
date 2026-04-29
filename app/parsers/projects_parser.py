from __future__ import annotations

import re

from app.utils.config import resolve_path


def parse_projects_md(md_content: str) -> dict[str, dict[str, object]]:
    projects = _parse_inventory_format(md_content)
    if projects:
        return projects
    return _parse_heading_format(md_content)


def parse_projects_source(projects_source: str) -> dict[str, dict[str, object]]:
    candidate = resolve_path(projects_source)
    if candidate.is_dir():
        merged_projects: dict[str, dict[str, object]] = {}
        for path in sorted(candidate.glob("*.md")):
            merged_projects.update(parse_projects_md(path.read_text(encoding="utf-8")))
        return merged_projects
    if candidate.is_file():
        return parse_projects_md(candidate.read_text(encoding="utf-8"))
    return parse_projects_md(projects_source)


def _parse_heading_format(md_content: str) -> dict[str, dict[str, object]]:
    projects: dict[str, dict[str, object]] = {}
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in md_content.splitlines():
        heading_match = re.match(r"^##\s+(.+?)\s*$", line)
        if heading_match:
            if current_heading:
                body = "\n".join(current_lines).strip()
                projects[current_heading] = {
                    "title": current_heading,
                    "heading": current_heading,
                    "tech_stack": [],
                    "bullets": [entry.lstrip("- ").strip() for entry in body.splitlines() if entry.strip().startswith("-")],
                    "body": body,
                }
            current_heading = heading_match.group(1).strip()
            current_lines = []
            continue
        if current_heading:
            current_lines.append(line)

    if current_heading:
        body = "\n".join(current_lines).strip()
        projects[current_heading] = {
            "title": current_heading,
            "heading": current_heading,
            "tech_stack": [],
            "bullets": [entry.lstrip("- ").strip() for entry in body.splitlines() if entry.strip().startswith("-")],
            "body": body,
        }

    return projects


def _parse_inventory_format(md_content: str) -> dict[str, dict[str, object]]:
    projects: dict[str, dict[str, object]] = {}
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in md_content.splitlines():
        heading_match = re.match(r"^\d+\.\s+(.+?)\s*$", line)
        if heading_match:
            if current_heading:
                _store_inventory_project(projects, current_heading, current_lines)
            current_heading = heading_match.group(1).strip()
            current_lines = []
            continue
        if current_heading:
            current_lines.append(line)

    if current_heading:
        _store_inventory_project(projects, current_heading, current_lines)

    return projects


def _store_inventory_project(
    projects: dict[str, dict[str, object]],
    heading: str,
    lines: list[str],
) -> None:
    body = "\n".join(lines).strip()
    title = heading.split(":", 1)[0].strip()
    tech_stack: list[str] = []
    keywords: list[str] = []
    bullets: list[str] = []
    url = ""
    date_range = ""
    context_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        tech_match = re.match(r"^\[Tech Stack:\s*(.+?)\]\s*$", stripped)
        url_match = re.match(r"^\[GitHub URL:\s*(.+?)\]\s*$", stripped)
        date_match = re.match(r"^\[Date Range:\s*(.+?)\]\s*$", stripped)
        keywords_match = re.match(r"^\[Keywords:\s*(.+?)\]\s*$", stripped)
        if tech_match:
            tech_stack = [item.strip() for item in tech_match.group(1).split(",") if item.strip()]
        elif url_match:
            url = url_match.group(1).strip()
        elif date_match:
            date_range = date_match.group(1).strip()
        elif keywords_match:
            keywords = [item.strip() for item in keywords_match.group(1).split(",") if item.strip()]
        elif stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
        elif stripped:
            context_lines.append(stripped)

    projects[title] = {
        "title": title,
        "heading": heading,
        "tech_stack": tech_stack,
        "keywords": keywords,
        "bullets": bullets,
        "body": body,
        "summary": _summarize_context(context_lines),
        "url": url,
        "date_range": date_range,
    }


def match_project(section_text: str, projects_dict: dict[str, dict[str, object]]) -> str | None:
    lowered_text = section_text.lower()
    for project_name, description in projects_dict.items():
        if project_name.lower() in lowered_text:
            return str(description.get("body", "")).strip() or "\n".join(
                str(bullet) for bullet in description.get("bullets", [])
            )
    return None


def _summarize_context(lines: list[str], limit: int = 900) -> str:
    if not lines:
        return ""
    cleaned_lines = [
        line
        for line in lines
        if not line.startswith("[")
        and not line.startswith("- ")
        and not line.startswith("### ATS Keywords")
        and not line.startswith("### Resume-safe metrics")
    ]
    summary = " ".join(cleaned_lines)
    return summary[:limit].strip()
