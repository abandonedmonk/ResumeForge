from __future__ import annotations

import re


JOB_TITLE_WORDS = (
    "engineer",
    "developer",
    "analyst",
    "scientist",
    "manager",
    "architect",
    "consultant",
    "intern",
    "specialist",
)


def _clean_piece(text: str, fallback: str) -> str:
    cleaned = re.sub(r"[^\w\s\-&,/]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_,")
    return cleaned or fallback


def extract_company_role(jd_text: str) -> tuple[str, str]:
    lines = [line.strip() for line in jd_text.splitlines() if line.strip()]
    company_name = "Company"
    role_title = "Role"

    patterns = [
        re.compile(r"\bat\s+([A-Z][A-Za-z0-9&,\- ]{2,})"),
        re.compile(r"\bjoin\s+([A-Z][A-Za-z0-9&,\- ]{2,})"),
        re.compile(r"^([A-Z][A-Za-z0-9&,\- ]+)\s+is\s+looking", re.IGNORECASE),
    ]

    for line in lines[:20]:
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                company_name = _clean_piece(match.group(1), company_name)
                break
        if company_name != "Company":
            break

    label_patterns = [
        re.compile(r"^(?:position|role|title)\s*:\s*(.+)$", re.IGNORECASE),
    ]
    for line in lines[:20]:
        for pattern in label_patterns:
            match = pattern.match(line)
            if match:
                candidate = match.group(1)
                if any(word in candidate.lower() for word in JOB_TITLE_WORDS):
                    role_title = _clean_piece(candidate, role_title)
                    break
        if role_title != "Role":
            break

    if role_title == "Role":
        for line in lines[:20]:
            if any(word in line.lower() for word in JOB_TITLE_WORDS) and len(line.split()) <= 10:
                role_title = _clean_piece(line, role_title)
                break

    return company_name, role_title

