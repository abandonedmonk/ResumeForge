"""Unit tests for the Phase 5 GitHub profile builder (no network, no real LLM)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.integrations import github, profile_builder
from app.parsers import projects_parser
from app.prompts.profile_from_readme import serialize_profile
from app.utils.exceptions import ResumeForgeError


# ── parse_repo_url ──────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/owner/repo",
        "https://github.com/owner/repo.git",
        "https://github.com/owner/repo/",
        "owner/repo",
        "github.com/owner/repo",
        "https://github.com/owner/repo/tree/main",
        "https://www.github.com/owner/repo?tab=readme-ov-file",
    ],
)
def test_parse_repo_url_variants(url):
    assert github.parse_repo_url(url) == ("owner", "repo")


def test_parse_repo_url_rejects_garbage():
    with pytest.raises(ResumeForgeError):
        github.parse_repo_url("not-a-repo")


def test_default_date_range():
    assert github._default_date_range("2026-02-15T00:00:00Z", "2026-03-20T00:00:00Z") == "Feb'26 – Mar'26"
    assert github._default_date_range("2026-02-15T00:00:00Z", "2026-02-28T00:00:00Z") == "Feb'26"
    assert github._default_date_range("", "") == ""


# ── serialize -> parse round-trip (proves the schema + date_range fix) ───────
def _sample_payload():
    return {
        "title": "AskAlpha",
        "one_line": "Voice-native financial research agent",
        "tech_stack": ["Python", "FastAPI", "FAISS"],
        "keywords": ["Voice AI", "RAG", "FAISS"],
        "bullets": [
            "Built a **RAG pipeline** over SEC filings.",
            "Engineered a bidirectional WebSocket stream.",
            "Optimized a Monte Carlo engine to run in **9.3ms**.",
        ],
        "what_contains": "A FastAPI backend with a React frontend.",
        "core_architecture": ["main.py boots the FastAPI app."],
        "ats_keywords": ["FastAPI", "RAG", "FAISS"],
    }


def test_serialize_round_trips_to_one_project():
    meta = {
        "repo": "AskAlpha",
        "html_url": "https://github.com/o/AskAlpha",
        "date_range": "Feb'26 – Mar'26",
        "description": "x",
    }
    md = serialize_profile(meta, _sample_payload())
    parsed = projects_parser.parse_projects_md(md)
    assert len(parsed) == 1
    project = next(iter(parsed.values()))
    assert project["title"] == "AskAlpha"
    assert project["bullets"]
    assert project["tech_stack"] == ["Python", "FastAPI", "FAISS"]
    assert project["keywords"] == ["Voice AI", "RAG", "FAISS"]
    assert project["date_range"] == "Feb'26 – Mar'26"  # proves the [Date Range:] emission + regex fix
    assert project["url"] == "https://github.com/o/AskAlpha"


# ── resolve_projects_source: imported dir wins when non-empty ────────────────
def test_resolve_projects_source_prefers_imported(tmp_path, monkeypatch):
    imported = tmp_path / "imported"
    imported.mkdir()
    (imported / "o__r.md").write_text("1. R: desc\n- bullet\n", encoding="utf-8")

    monkeypatch.setattr(projects_parser, "get_config", lambda: {"imported_profiles_dir": str(imported)})
    monkeypatch.setattr(projects_parser, "resolve_path", lambda p: Path(p))

    assert projects_parser.resolve_projects_source("inputs/project_profiles") == str(imported)


def test_resolve_projects_source_falls_back_when_empty(tmp_path, monkeypatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(projects_parser, "get_config", lambda: {"imported_profiles_dir": str(empty)})
    monkeypatch.setattr(projects_parser, "resolve_path", lambda p: Path(p))

    assert projects_parser.resolve_projects_source("inputs/project_profiles") == "inputs/project_profiles"


# ── import_profiles: mocked fetch + LLM, batch degrades per-repo ─────────────
def test_import_profiles_batch_with_mocks(monkeypatch):
    import json as _json

    def fake_fetch(owner, repo, token=""):
        if repo == "bad":
            from app.utils.exceptions import ResumeForgeError
            raise ResumeForgeError("Repo not found or private")
        return {
            "owner": owner,
            "repo": repo,
            "html_url": f"https://github.com/{owner}/{repo}",
            "date_range": "Jan'26 – Feb'26",
            "description": "desc",
            "readme": "# readme",
        }

    class FakeModel:
        def __init__(self, *a, **k):
            pass

        def call(self, system, user, temperature=None):
            return _json.dumps(_sample_payload())

    monkeypatch.setattr(profile_builder, "fetch_repo", fake_fetch)
    monkeypatch.setattr(profile_builder, "RoutedModel", FakeModel)

    results = profile_builder.import_profiles(["o/good", "o/bad", "  "])
    assert len(results) == 2  # blank line skipped
    ok = [r for r in results if r.ok]
    bad = [r for r in results if not r.ok]
    assert len(ok) == 1 and ok[0].filename == "o__good.md"
    assert ok[0].content.strip().startswith("1. AskAlpha:")
    assert len(bad) == 1 and "not found" in bad[0].message
