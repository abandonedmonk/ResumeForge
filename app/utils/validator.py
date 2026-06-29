from __future__ import annotations

import re
import unicodedata
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

UNICODE_TEXT_REPLACEMENTS = {
    "\u00a0": " ",
    "\u2009": " ",
    "\u202f": " ",
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2026": "...",
}


def normalize_latex_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    for source, replacement in UNICODE_TEXT_REPLACEMENTS.items():
        normalized = normalized.replace(source, replacement)
    return normalized


def escape_latex(text: str) -> str:
    text = normalize_latex_text(text)
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
