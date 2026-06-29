"""Build a structured Profile from an uploaded resume PDF (auto-fill).

extract → LLM → Profile. Links are assigned by substring so the user gets
pre-filled LinkedIn/GitHub/cert URLs. Best-effort: never raises on partial data
(auto-fill is not auto-render — the user reviews/corrects before generating).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.integrations.resume_pdf import extract_pdf_text_and_links
from app.llm.router import RoutedModel
from app.profiles.schema import Profile
from app.prompts.profile_from_resume import build_resume_extraction_prompt
from app.utils.json_utils import extract_json_blob


@dataclass
class ResumeImportResult:
    ok: bool
    message: str
    profile: Profile
    links: list[str]


def _assign_links(profile: Profile, links: list[str]) -> None:
    """Fill obvious contact/cert URLs from embedded links the LLM may have missed."""
    leftovers: list[str] = []
    for link in links:
        low = link.lower()
        if "linkedin.com" in low and not profile.contact.linkedin:
            profile.contact.linkedin = link
        elif "github.com" in low and not profile.contact.github:
            profile.contact.github = link
        elif low.startswith("mailto:") and not profile.contact.email:
            profile.contact.email = link[len("mailto:") :]
        else:
            leftovers.append(link)

    # Attach remaining links to certs that lack one, in order.
    for cert in profile.certifications:
        if cert.url or not leftovers:
            continue
        cert.url = leftovers.pop(0)


def import_profile_from_pdf(pdf_path: str | Path, token: str = "") -> ResumeImportResult:
    text, links = extract_pdf_text_and_links(pdf_path)
    if not text and not links:
        return ResumeImportResult(
            ok=False,
            message="Could not read any text or links from the PDF (it may be scanned/image-only).",
            profile=Profile(),
            links=[],
        )

    system_prompt, user_prompt = build_resume_extraction_prompt(text, links)
    try:
        raw = RoutedModel("stage1").call(system_prompt, user_prompt)
        payload = json.loads(extract_json_blob(raw))
        profile = Profile.from_dict(payload if isinstance(payload, dict) else {})
    except Exception as exc:
        # LLM/parse failure is non-fatal — still hand back any extracted links.
        profile = Profile()
        _assign_links(profile, links)
        return ResumeImportResult(
            ok=False,
            message=f"Extracted {len(links)} link(s); LLM parsing failed ({exc}). Fill the fields manually.",
            profile=profile,
            links=links,
        )

    _assign_links(profile, links)
    return ResumeImportResult(
        ok=True,
        message=f"Auto-filled from PDF ({len(links)} link(s) found). Review and correct before generating.",
        profile=profile,
        links=links,
    )
