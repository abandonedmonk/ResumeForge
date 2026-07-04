"""Unit tests for the Cold Read Simulator (LLM mocked)."""
from __future__ import annotations

from app.features import cold_read


class _FakeModel:
    """Stand-in for RoutedStage1Model that returns a canned response."""

    response = (
        '{"targeted_role":"ML Engineer","strongest_qualification":"PyTorch depth",'
        '"biggest_gap":"No production MLOps"}'
    )

    def __init__(self, *args, **kwargs):
        pass

    def call(self, system_prompt, user_prompt, temperature=None):
        return self.response


def test_run_cold_read_parses(monkeypatch):
    monkeypatch.setattr(cold_read, "RoutedStage1Model", _FakeModel)
    result = cold_read.run_cold_read("resume text", "jd text")
    assert result["targeted_role"] == "ML Engineer"
    assert result["strongest_qualification"] == "PyTorch depth"
    assert set(result) == set(cold_read.FIELDS)


def test_run_cold_read_handles_bad_json(monkeypatch):
    class _Bad(_FakeModel):
        response = "sorry, I could not produce JSON"

    monkeypatch.setattr(cold_read, "RoutedStage1Model", _Bad)
    result = cold_read.run_cold_read("resume", "jd")
    assert set(result) == set(cold_read.FIELDS)
    assert all(value == "(not determined)" for value in result.values())


def test_render_contains_all_fields():
    text = cold_read.render_cold_read(
        {"targeted_role": "X", "strongest_qualification": "Y", "biggest_gap": "Z"}
    )
    assert "Targeted role:" in text and "X" in text
    assert "Biggest gap:" in text and "Z" in text
