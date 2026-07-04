"""Unit tests for the Resume Roaster (LLM mocked)."""
from __future__ import annotations

from app.features import roast
from app.prompts.roast import build_roast_prompt

SAMPLE = (
    "[ROAST] \"Responsible for managing team deliverables\" — this says nothing.\n"
    "[FIX]   \"Led a 4-person team to ship X, cutting Y by 30%\"\n"
    "[ROAST] Three different fonts detected. Were you testing something?\n"
    "[FIX]   Use one consistent font; LaTeX enforces this for free.\n"
)


class _FakeModel:
    response = SAMPLE

    def __init__(self, *args, **kwargs):
        pass

    def call(self, system_prompt, user_prompt, temperature=None):
        return self.response


def test_run_roast_passes_through(monkeypatch):
    monkeypatch.setattr(roast, "RoutedStage2Model", _FakeModel)
    out = roast.run_roast("resume text")
    assert "[ROAST]" in out and "[FIX]" in out


def test_run_roast_strips_code_fences(monkeypatch):
    class _Fenced(_FakeModel):
        response = "```text\n" + SAMPLE + "```"

    monkeypatch.setattr(roast, "RoutedStage2Model", _Fenced)
    out = roast.run_roast("resume text")
    assert "```" not in out


def test_parse_roast_pairs():
    pairs = roast.parse_roast_pairs(SAMPLE)
    assert len(pairs) == 2
    assert pairs[0]["roast"].startswith('"Responsible for managing')
    assert pairs[0]["fix"].startswith('"Led a 4-person team')


def test_jd_scopes_prompt():
    _system, user = build_roast_prompt("resume", jd_text="Senior ML Engineer, PyTorch, MLOps")
    assert "PyTorch" in user
    # Without a JD, no posting block is added.
    _system2, user2 = build_roast_prompt("resume")
    assert "job posting" not in user2
