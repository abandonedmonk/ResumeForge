from __future__ import annotations

import re
from collections.abc import Iterable


LATEX_SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_latex(text: str) -> str:
    escaped: list[str] = []
    for char in text:
        escaped.append(LATEX_SPECIAL_CHARS.get(char, char))
    return "".join(escaped)


def extract_numbers(lines: Iterable[str]) -> set[str]:
    found: set[str] = set()
    for line in lines:
        found.update(re.findall(r"\d+(?:\.\d+)?", line))
    return found


def preserves_numbers(original: list[str], rewritten: list[str]) -> bool:
    original_numbers = extract_numbers(original)
    if not original_numbers:
        return True
    new_numbers = extract_numbers(rewritten)
    return original_numbers.issubset(new_numbers)


def count_is_valid(original: list[str], rewritten: list[str]) -> bool:
    return len(original) == len(rewritten)


def contains_unknown_project_name(text: str, known_projects: set[str]) -> bool:
    normalized_projects = {name.lower() for name in known_projects if name.strip()}
    if not normalized_projects:
        return False
    words = set(re.findall(r"[A-Za-z][A-Za-z0-9\-\+\.]+", text.lower()))
    return any(project.lower() in words for project in normalized_projects if project.lower() not in text.lower())

