"""Unit tests for fetching a job description from a URL (mocked network)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests

from app.parsers import jd_parser
from app.utils.exceptions import ResumeForgeError


class _FakeResponse:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


_HTML = """
<html><head><style>.x{color:red}</style><script>var a=1;</script></head>
<body><nav>menu</nav>
<h1>Senior Backend Engineer</h1>
<p>We are looking for a backend engineer with Python, FastAPI, and AWS experience.
Responsibilities include building scalable APIs and mentoring juniors.</p>
<footer>© 2026</footer></body></html>
"""


def test_fetch_extracts_visible_text(monkeypatch):
    monkeypatch.setattr(jd_parser.requests, "get", lambda *a, **k: _FakeResponse(_HTML))
    text = jd_parser.fetch_jd_from_url("https://example.com/job/123")
    assert "Senior Backend Engineer" in text
    assert "FastAPI" in text
    assert "var a=1" not in text  # script stripped
    assert "color:red" not in text  # style stripped


def test_fetch_network_error_raises(monkeypatch):
    def _boom(*a, **k):
        raise requests.ConnectionError("no route")

    monkeypatch.setattr(jd_parser.requests, "get", _boom)
    with pytest.raises(ResumeForgeError):
        jd_parser.fetch_jd_from_url("https://example.com/job/123")


def test_fetch_too_short_raises(monkeypatch):
    monkeypatch.setattr(jd_parser.requests, "get", lambda *a, **k: _FakeResponse("<html><body>hi</body></html>"))
    with pytest.raises(ResumeForgeError):
        jd_parser.fetch_jd_from_url("https://example.com/empty")
