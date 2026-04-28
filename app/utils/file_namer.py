from __future__ import annotations

import re
from datetime import datetime

from app.utils.config import get_config


WINDOWS_RESERVED = re.compile(r'[<>:"/\\|?*]+')


def sanitize_filename_part(value: str, fallback: str) -> str:
    cleaned = WINDOWS_RESERVED.sub(" ", value or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    return cleaned or fallback


def build_output_basename(company_name: str, role_title: str) -> str:
    company = sanitize_filename_part(company_name, "Company")
    role = sanitize_filename_part(role_title, "Role")
    return f"Anshuman Jena {company} {role}"


def build_output_filename(company_name: str, role_title: str) -> str:
    config = get_config()
    if not config.get("auto_name_pdf", True):
        fallback = sanitize_filename_part(config.get("fallback_name", "Anshuman Jena Tailored Resume"), "Resume")
        return f"{fallback}.pdf"
    return f"{build_output_basename(company_name, role_title)}.pdf"


def build_history_folder_name(company_name: str, role_title: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"{timestamp}_{build_output_basename(company_name, role_title)}"


def build_log_stem(company_name: str, role_title: str, suffix: str = "run") -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    basename = sanitize_filename_part(f"{company_name} {role_title}", "ResumeForge").replace(" ", "-")
    return f"{timestamp}_{basename}_{suffix}"
