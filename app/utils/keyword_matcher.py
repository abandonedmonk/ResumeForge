from __future__ import annotations

import re
from collections import Counter


def normalize_keyword(keyword: str) -> str:
    lowered = keyword.lower().strip()
    lowered = lowered.replace("&", " and ")
    lowered = re.sub(r"[^a-z0-9\+\#\.\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def build_synonym_map() -> dict[str, set[str]]:
    groups = {
        "react": {"react", "reactjs", "react.js"},
        "node.js": {"node", "nodejs", "node.js"},
        "machine learning": {"machine learning", "ml"},
        "artificial intelligence": {"artificial intelligence", "ai"},
        "retrieval augmented generation": {"retrieval augmented generation", "rag"},
        "large language models": {"large language models", "llms", "llm"},
        "c plus plus": {"c++", "cpp", "c plus plus"},
        "javascript": {"javascript", "js"},
        "typescript": {"typescript", "ts"},
        "postgresql": {"postgresql", "postgres", "psql"},
        "amazon web services": {"amazon web services", "aws"},
        "google cloud platform": {"google cloud platform", "gcp"},
        "kubernetes": {"kubernetes", "k8s"},
    }
    synonym_map: dict[str, set[str]] = {}
    for _canonical, variants in groups.items():
        normalized_variants = {normalize_keyword(variant) for variant in variants}
        for variant in normalized_variants:
            synonym_map[variant] = normalized_variants
    return synonym_map


def expand_keyword_variants(keyword: str, synonym_map: dict[str, set[str]]) -> set[str]:
    normalized = normalize_keyword(keyword)
    return synonym_map.get(normalized, {normalized})


def find_keyword_in_text(keyword: str, text: str, synonym_map: dict[str, set[str]]) -> bool:
    haystack = f" {normalize_keyword(text)} "
    for variant in expand_keyword_variants(keyword, synonym_map):
        pattern = f" {variant} "
        if pattern in haystack:
            return True
    return False


def matched_keywords(keywords: list[str], text: str, synonym_map: dict[str, set[str]]) -> list[str]:
    return [keyword for keyword in keywords if find_keyword_in_text(keyword, text, synonym_map)]


def extract_metrics_from_bullet(bullet: str) -> bool:
    return bool(re.search(r"(\d+[%xX]?|\$\d+|\d+\+)", bullet))


def strip_latex_commands(tex_content: str) -> str:
    text = tex_content
    text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\underline\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", text)
    text = re.sub(r"[%$&_#{}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_resume_bullets(tex_content: str) -> list[str]:
    bullets = re.findall(r"\\resumeItem\{(.*?)\}", tex_content, re.DOTALL)
    if bullets:
        return [strip_latex_commands(bullet) for bullet in bullets]
    line_items = re.findall(r"\\item\s+(.*)", tex_content)
    return [strip_latex_commands(item) for item in line_items]


def split_sections(tex_content: str) -> dict[str, str]:
    pattern = re.compile(r"\\section\{([^}]*)\}")
    matches = list(pattern.finditer(tex_content))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(tex_content)
        sections[match.group(1).strip()] = tex_content[start:end]
    return sections


def identify_high_value_zones(tex_content: str) -> dict[str, str]:
    sections = split_sections(tex_content)
    headline_match = re.search(r"\\begin\{center\}(.*?)\\end\{center\}", tex_content, re.DOTALL)
    headline = strip_latex_commands(headline_match.group(1)) if headline_match else ""
    skills_section = strip_latex_commands(sections.get("Skills", ""))

    first_bullets: list[str] = []
    for section_name, content in sections.items():
        if "experience" not in section_name.lower():
            continue
        bullets = extract_resume_bullets(content)
        if bullets:
            first_bullets.append(bullets[0])

    return {
        "headline": headline,
        "skills": skills_section,
        "first_bullets": " ".join(first_bullets),
    }


def section_quality_snapshot(tex_content: str) -> dict[str, object]:
    sections = split_sections(tex_content)
    normalized_map = {name.lower(): content for name, content in sections.items()}
    expected = ["experience", "education", "skills", "projects"]
    found = [name for name in expected if any(name in section_name for section_name in normalized_map)]
    issues: list[str] = []

    for expected_name in expected:
        matches = [content for section_name, content in normalized_map.items() if expected_name in section_name]
        if not matches:
            issues.append(f"Missing section: {expected_name.title()}")
            continue
        if not strip_latex_commands(matches[0]):
            issues.append(f"Empty section: {expected_name.title()}")

    bullet_counts = {
        name: len(extract_resume_bullets(content))
        for name, content in sections.items()
    }
    for name, count in bullet_counts.items():
        lowered = name.lower()
        if "experience" in lowered or "project" in lowered:
            if count < 2:
                issues.append(f"Thin section: {name}")
            if count > 12:
                issues.append(f"Crowded section: {name}")

    completeness = max(0, 100 - len(issues) * 10)
    if found:
        completeness = min(100, int((len(found) / len(expected)) * 70 + completeness * 0.3))

    return {
        "score": completeness,
        "sections_found": [name.title() for name in found],
        "issues": issues,
        "bullet_counts": bullet_counts,
    }


def keyword_frequency(text: str, keywords: list[str], synonym_map: dict[str, set[str]]) -> Counter[str]:
    normalized_text = f" {normalize_keyword(text)} "
    counts: Counter[str] = Counter()
    for keyword in keywords:
        for variant in expand_keyword_variants(keyword, synonym_map):
            counts[keyword] += normalized_text.count(f" {variant} ")
    return counts

