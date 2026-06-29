"""Best-effort extraction of text + hyperlinks from an existing resume PDF.

Links (URI annotations) extract reliably; text is best-effort ("limited info but
works"). Never raises on a malformed PDF — returns whatever it could read.
"""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def _extract_links(page) -> list[str]:
    links: list[str] = []
    annots = page.get("/Annots")
    if not annots:
        return links
    try:
        annots = annots.get_object()
    except Exception:
        return links
    for annot in annots:
        try:
            obj = annot.get_object()
            action = obj.get("/A")
            if action is None:
                continue
            uri = action.get_object().get("/URI")
            if uri:
                links.append(str(uri))
        except Exception:
            continue
    return links


def extract_pdf_text_and_links(pdf_path: str | Path) -> tuple[str, list[str]]:
    """Return ``(full_text, ordered_unique_links)`` from a PDF, best-effort."""
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return "", []

    text_parts: list[str] = []
    links: list[str] = []
    seen: set[str] = set()
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            pass
        for link in _extract_links(page):
            if link not in seen:
                seen.add(link)
                links.append(link)

    return "\n".join(text_parts).strip(), links
