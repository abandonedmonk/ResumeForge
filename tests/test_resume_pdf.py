"""Unit tests for resume-PDF text + link extraction and link assignment."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.integrations.resume_import import _assign_links
from app.integrations.resume_pdf import extract_pdf_text_and_links
from app.profiles.schema import Certification, Profile

_HAS_PDFLATEX = shutil.which("pdflatex") is not None


def test_extract_handles_missing_file():
    text, links = extract_pdf_text_and_links("does/not/exist.pdf")
    assert text == "" and links == []


@pytest.mark.skipif(not _HAS_PDFLATEX, reason="pdflatex not on PATH")
def test_extract_text_and_links_from_real_pdf(tmp_path):
    from app.agent.nodes.compile_pdf import compile_tex_to_pdf

    tex = r"""
\documentclass{article}
\usepackage[hidelinks]{hyperref}
\begin{document}
Jane Doe — Software Engineer.
\href{https://github.com/janedoe}{GitHub} and
\href{https://www.linkedin.com/in/janedoe}{LinkedIn}.
\end{document}
"""
    pdf = tmp_path / "resume.pdf"
    compile_tex_to_pdf(tex, pdf)
    text, links = extract_pdf_text_and_links(pdf)
    assert "Jane Doe" in text
    assert "https://github.com/janedoe" in links
    assert "https://www.linkedin.com/in/janedoe" in links


def test_assign_links_routes_by_substring():
    profile = Profile(certifications=[Certification(name="Cert A"), Certification(name="Cert B")])
    _assign_links(
        profile,
        [
            "https://github.com/jane",
            "https://www.linkedin.com/in/jane",
            "mailto:jane@example.com",
            "https://coursera.org/verify/abc",
        ],
    )
    assert profile.contact.github == "https://github.com/jane"
    assert profile.contact.linkedin == "https://www.linkedin.com/in/jane"
    assert profile.contact.email == "jane@example.com"
    # leftover link assigned to the first cert lacking a URL
    assert profile.certifications[0].url == "https://coursera.org/verify/abc"
    assert profile.certifications[1].url == ""
