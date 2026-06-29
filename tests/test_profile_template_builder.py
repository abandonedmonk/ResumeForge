"""Unit tests for the Phase 6 profile → personal-template builder."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.parsers import profile_template_builder as ptb
from app.parsers.latex_assembler import PROJECTS_START, SKILLS_START, SUMMARY_PATTERN
from app.parsers.latex_parser import parse_latex_resume
from app.profiles import profile_store
from app.profiles.schema import Profile

_HAS_PDFLATEX = shutil.which("pdflatex") is not None
_needs_tex = pytest.mark.skipif(not _HAS_PDFLATEX, reason="pdflatex not on PATH")


def _sample_profile() -> Profile:
    return Profile.from_dict(
        {
            "contact": {
                "name": "Jane R&D Doe",
                "email": "jane@example.com",
                "phone": "+1 555 0100",
                "linkedin": "https://linkedin.com/in/jane",
                "github": "https://github.com/jane",
            },
            "education": [
                {"institution": "MIT", "city": "Cambridge", "degree": "BS CS", "dates": "2022 -- 2026", "gpa": "GPA: 3.9", "coursework": "Algorithms, OS"}
            ],
            "experience": [
                {"company": "Acme & Co", "role": "SWE Intern", "location": "Remote", "dates": "Jun 2024 -- Sep 2024",
                 "bullets": ["Built a **RAG pipeline** over 500 docs", "Cut latency by 40%"]}
            ],
            "certifications": [
                {"name": "Deep Learning", "issuer": "NVIDIA", "url": "https://learn.nvidia.com/cert/123"},
                {"name": "No-link cert", "issuer": "Self"},
            ],
        }
    )


# ── schema round-trip ───────────────────────────────────────────────────────
def test_profile_roundtrip():
    profile = _sample_profile()
    restored = Profile.from_dict(profile.to_dict())
    assert restored.to_dict() == profile.to_dict()
    assert restored.contact.name == "Jane R&D Doe"
    assert restored.experience[0].bullets == ["Built a **RAG pipeline** over 500 docs", "Cut latency by 40%"]


def test_empty_profile_is_empty():
    assert Profile().is_empty()
    assert not _sample_profile().is_empty()


# ── rendering (pure, no compile) ──────────────────────────────────────────────
def test_render_header_escapes_and_omits_missing_links():
    profile = _sample_profile()
    header = ptb.render_header(profile.contact)
    assert r"\textbf{Jane R\&D Doe}" in header
    assert r"\href{https://linkedin.com/in/jane}{\ul{LinkedIn}}" in header
    assert "Portfolio" not in header  # no website provided → fragment omitted
    assert not header.rstrip().endswith(r"\\")  # scaffold supplies the trailing \\ \vspace{6pt}


def test_render_experience_bold_and_macro():
    body = ptb.render_experience(_sample_profile().experience)
    assert r"\resumeItem{Built a \textbf{RAG pipeline} over 500 docs}" in body
    assert r"\resumeItem{Cut latency by 40\%}" in body


def test_render_certifications_link_optional():
    body = ptb.render_certifications(_sample_profile().certifications)
    assert r"\href{https://learn.nvidia.com/cert/123}{\underline{Certificate Link}}" in body
    assert r"\item No-link cert --- Self" in body
    assert body.count(r"\href") == 1  # the link-less cert has no href


def test_empty_sections_are_dropped():
    scaffold = (ptb.resolve_path("templates/classic/scaffold.tex")).read_text(encoding="utf-8")
    profile = Profile.from_dict({"contact": {"name": "Stu"}, "education": [{"institution": "State U", "degree": "BS"}]})
    tex = ptb.render_profile_template(profile, scaffold)
    assert r"\section{Experience}" not in tex
    assert r"\section{Certifications}" not in tex
    assert r"\section{Skills}" in tex and r"\section{Projects}" in tex


# ── build + compile self-check ────────────────────────────────────────────────
@_needs_tex
def test_build_personal_template_compiles_and_keeps_hooks():
    tex, _log = ptb.build_personal_template(_sample_profile(), "classic")
    assert SUMMARY_PATTERN.search(tex)
    assert SKILLS_START in tex and PROJECTS_START in tex
    # Experience now parses as a tailorable section (the \resumeItem fix).
    sections = parse_latex_resume(tex)
    assert sections["Experience"]["bullets"], "experience bullets not captured"


def test_unrenderable_template_raises():
    from app.utils.exceptions import ResumeForgeError
    with pytest.raises(ResumeForgeError):
        ptb.build_personal_template(_sample_profile(), "does-not-exist")


# ── resolver: personal template wins when present ─────────────────────────────
def test_resolve_resume_tex_source(tmp_path, monkeypatch):
    personal = tmp_path / "template.tex"
    monkeypatch.setattr(profile_store, "personal_template_path", lambda: personal)
    assert profile_store.resolve_resume_tex_source("templates/classic/template.tex") == "templates/classic/template.tex"
    personal.write_text(r"\documentclass{article}\begin{document}x\end{document}", encoding="utf-8")
    assert profile_store.resolve_resume_tex_source("templates/classic/template.tex") == str(personal)
