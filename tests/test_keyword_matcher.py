"""Unit tests for the ATS keyword-matching utilities."""
from __future__ import annotations

from app.utils import keyword_matcher as km


def test_normalize_keyword():
    assert km.normalize_keyword("Node.JS & React!") == "node.js and react"
    assert km.normalize_keyword("  C++  ") == "c++"


def test_synonym_expansion_and_match():
    synonyms = km.build_synonym_map()
    assert "rag" in km.expand_keyword_variants("RAG", synonyms)
    assert "retrieval augmented generation" in km.expand_keyword_variants("rag", synonyms)
    assert km.find_keyword_in_text("k8s", "we run Kubernetes in prod", synonyms)
    assert not km.find_keyword_in_text("rust", "we run Kubernetes in prod", synonyms)


def test_matched_keywords_filters():
    synonyms = km.build_synonym_map()
    assert km.matched_keywords(["AWS", "Rust"], "deployed on aws lambda", synonyms) == ["AWS"]


def test_strip_latex_commands():
    out = km.strip_latex_commands(r"\textbf{Built} a \href{http://x}{link} \item now")
    assert "Built" in out and "link" in out
    assert "\\" not in out and "textbf" not in out


def test_extract_resume_bullets_both_macros():
    tex = r"\resumeItem{First bullet} \resumeItem{Second \textbf{bold}}"
    bullets = km.extract_resume_bullets(tex)
    assert bullets[0] == "First bullet"
    assert "bold" in bullets[1] and "\\textbf" not in bullets[1]


def test_split_sections():
    sections = km.split_sections(r"\section{Experience} did things \section{Education} learned")
    assert set(sections) == {"Experience", "Education"}
    assert "did things" in sections["Experience"]


def test_extract_metrics_from_bullet():
    assert km.extract_metrics_from_bullet("improved latency by 25%")
    assert km.extract_metrics_from_bullet("handled $5 budget")
    assert not km.extract_metrics_from_bullet("built a backend service")
