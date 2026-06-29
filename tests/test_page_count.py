"""Unit tests for parsing the pdflatex page-count line."""
from __future__ import annotations

from app.agent.nodes.compile_pdf import parse_page_count


def test_single_page():
    assert parse_page_count("Output written on resume.pdf (1 page, 54321 bytes).") == 1


def test_multiple_pages():
    assert parse_page_count("Output written on resume.pdf (2 pages, 99999 bytes).") == 2


def test_no_match_returns_none():
    assert parse_page_count("This run produced no PDF.") is None
    assert parse_page_count("") is None
