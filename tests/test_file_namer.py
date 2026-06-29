"""Unit tests for output/log file naming."""
from __future__ import annotations

import re

from app.utils import file_namer as fn


def test_sanitize_filename_part_strips_reserved():
    assert fn.sanitize_filename_part('Goo/gle: "X"?', "Company") == "Goo gle X"
    assert fn.sanitize_filename_part("   ", "Fallback") == "Fallback"
    assert fn.sanitize_filename_part("trailing...", "F") == "trailing"


def test_build_output_basename_with_candidate(monkeypatch):
    monkeypatch.setattr(fn, "get_config", lambda: {"candidate_name": "Jane Doe"})
    assert fn.build_output_basename("Acme", "Backend Engineer") == "Jane Doe Acme Backend Engineer"


def test_build_output_basename_without_candidate(monkeypatch):
    monkeypatch.setattr(fn, "get_config", lambda: {"candidate_name": ""})
    assert fn.build_output_basename("Acme", "SWE") == "Acme SWE"


def test_build_output_filename_auto_and_fallback(monkeypatch):
    monkeypatch.setattr(fn, "get_config", lambda: {"candidate_name": "", "auto_name_pdf": True})
    assert fn.build_output_filename("Acme", "SWE") == "Acme SWE.pdf"
    monkeypatch.setattr(fn, "get_config", lambda: {"auto_name_pdf": False, "fallback_name": "My Resume"})
    assert fn.build_output_filename("Acme", "SWE") == "My Resume.pdf"


def test_build_history_folder_name_shape(monkeypatch):
    monkeypatch.setattr(fn, "get_config", lambda: {"candidate_name": ""})
    name = fn.build_history_folder_name("Acme", "SWE")
    assert re.match(r"^\d{4}-\d{2}-\d{2}_\d{6}_Acme SWE$", name)


def test_build_log_stem_shape():
    stem = fn.build_log_stem("Acme Corp", "Data Scientist", suffix="run")
    assert re.match(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_Acme-Corp-Data-Scientist_run$", stem)
