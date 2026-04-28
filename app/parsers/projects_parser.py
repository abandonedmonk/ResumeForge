from __future__ import annotations

import re


def parse_projects_md(md_content: str) -> dict[str, dict[str, object]]:
    projects = _parse_inventory_format(md_content)
    if projects:
        return projects
    return _parse_heading_format(md_content)


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
    bullets: list[str] = []

    for line in lines:
        stripped = line.strip()
        tech_match = re.match(r"^\[Tech Stack:\s*(.+?)\]\s*$", stripped)
        if tech_match:
            tech_stack = [item.strip() for item in tech_match.group(1).split(",") if item.strip()]
        elif stripped.startswith("- "):
            bullets.append(stripped[2:].strip())

    projects[title] = {
        "title": title,
        "heading": heading,
        "tech_stack": tech_stack,
        "bullets": bullets,
        "body": body,
    }


def match_project(section_text: str, projects_dict: dict[str, dict[str, object]]) -> str | None:
    lowered_text = section_text.lower()
    for project_name, description in projects_dict.items():
        if project_name.lower() in lowered_text:
            bullets = description.get("bullets", [])
            return "\n".join(str(bullet) for bullet in bullets)
    return None
