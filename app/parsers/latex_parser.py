from __future__ import annotations

import re

SECTION_PATTERN = re.compile(r"(\\(?:section|subsection)\{.*?\})", re.DOTALL)


def parse_latex_resume(tex_content: str) -> dict[str, dict[str, object]]:
    if not tex_content.strip():
        return {}

    parts = SECTION_PATTERN.split(tex_content)
    if len(parts) == 1:
        bullets = _extract_bullets(tex_content)
        return {
            "Document": {
                "header": "Document",
                "raw_tex": tex_content,
                "bullets": bullets,
            }
        }

    sections: dict[str, dict[str, object]] = {}
    for index in range(1, len(parts), 2):
        header_tex = parts[index]
        body_tex = parts[index + 1] if index + 1 < len(parts) else ""
        section_tex = f"{header_tex}{body_tex}"
        header = re.sub(r"\\(?:section|subsection)\{(.*?)\}", r"\1", header_tex).strip()
        sections[header] = {
            "header": header,
            "raw_tex": section_tex,
            "bullets": _extract_bullets(section_tex),
        }
    return sections


def _extract_bullets(section_tex: str) -> list[str]:
    bullets: list[str] = []
    for line in section_tex.splitlines():
        stripped = line.strip()
        # Experience/Projects use the \resumeItem{...} macro; Education/Skills use a
        # bare \item. Capture both so non-fixed sections (e.g. Experience) are tailorable.
        if stripped.startswith(r"\resumeItem{"):
            body = stripped[len(r"\resumeItem{") :]
            if body.endswith("}"):
                body = body[:-1]
            bullets.append(body.strip())
        elif stripped.startswith(r"\item"):
            bullets.append(stripped[len(r"\item") :].strip())
    return bullets

