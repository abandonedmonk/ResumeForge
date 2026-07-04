"""Unit tests for the GitHub Gap-Finder.

Stages 1-2 are pure/local and asserted directly; stage 3 (LLM) and the network
calls (fetch_user_repos / fetch_repo) are monkeypatched.
"""
from __future__ import annotations

from app.features import gap_finder

REPOS = [
    {"owner": "someuser", "repo": "SyntheticProbe", "description": "Mechanistic interpretability with PyTorch",
     "language": "Python", "topics": ["pytorch", "interpretability"], "fork": False,
     "stargazers_count": 12, "pushed_at": "2026-03-01", "date_range": "Jan'25 - Mar'26"},
    {"owner": "someuser", "repo": "todo-app", "description": "A simple todo list", "language": "JavaScript",
     "topics": [], "fork": False, "stargazers_count": 0, "pushed_at": "2024-01-01", "date_range": ""},
    {"owner": "someuser", "repo": "forked-lib", "description": "distributed pytorch training", "language": "Python",
     "topics": ["pytorch"], "fork": True, "stargazers_count": 99, "pushed_at": "2026-01-01"},
]


def test_extract_jd_keywords_drops_stopwords():
    keywords = gap_finder.extract_jd_keywords("We want strong PyTorch and distributed systems experience")
    assert "pytorch" in keywords
    assert "distributed" in keywords
    assert "want" not in keywords and "experience" not in keywords


def test_prefilter_ranks_relevant_and_drops_forks():
    keywords = ["pytorch", "interpretability", "distributed"]
    selected = gap_finder.prefilter_repos(REPOS, keywords, top_n=5)
    names = [repo["repo"] for repo in selected]
    assert names[0] == "SyntheticProbe"      # highest keyword overlap
    assert "forked-lib" not in names          # forks excluded even if high-signal


def test_prefilter_respects_top_n():
    selected = gap_finder.prefilter_repos(REPOS, ["python"], top_n=1)
    assert len(selected) == 1


def test_first_sentences_strips_markdown():
    readme = "# Title\n\n```py\ncode\n```\nThis is the first sentence. And the second one. Third."
    blurb = gap_finder._first_sentences(readme, count=2)
    assert "code" not in blurb
    assert blurb.startswith("This is the first sentence.")
    assert "second one" in blurb


def test_analyze_gap_parses_and_shapes(monkeypatch):
    class _Fake:
        def __init__(self, *a, **k):
            pass

        def call(self, system_prompt, user_prompt, temperature=None):
            return '{"missing":["PyTorch depth"],"undersold":[],"overclaimed":[],"suggested_bullets":["Add X"]}'

    monkeypatch.setattr(gap_finder, "RoutedStage1Model", _Fake)
    result = gap_finder.analyze_gap("inventory", "resume")
    assert result["missing"] == ["PyTorch depth"]
    assert set(result) == {"missing", "undersold", "overclaimed", "suggested_bullets"}


def test_analyze_gap_handles_bad_json(monkeypatch):
    class _Bad:
        def __init__(self, *a, **k):
            pass

        def call(self, *a, **k):
            return "no json"

    monkeypatch.setattr(gap_finder, "RoutedStage1Model", _Bad)
    result = gap_finder.analyze_gap("inv", "resume")
    assert all(value == [] for value in result.values())


def test_run_gap_finder_orchestration(monkeypatch):
    monkeypatch.setattr(gap_finder, "fetch_user_repos", lambda user, token="": REPOS)
    monkeypatch.setattr(
        gap_finder,
        "fetch_repo",
        lambda owner, repo, token="": {"readme": "First. Second. Third.", "language": "Python", "date_range": "x"},
    )

    class _Fake:
        def __init__(self, *a, **k):
            pass

        def call(self, *a, **k):
            return '{"missing":["m"],"undersold":[],"overclaimed":[],"suggested_bullets":[]}'

    monkeypatch.setattr(gap_finder, "RoutedStage1Model", _Fake)
    result = gap_finder.run_gap_finder("someuser", "resume text", "pytorch role", top_n=2)
    assert result["analysis"]["missing"] == ["m"]
    assert len(result["repos"]) >= 1
    assert "Repo:" in result["inventory"]
