"""Unit tests for the per-model token budget registry + estimation/trimming."""
from __future__ import annotations

from app.llm import model_limits as ml


def test_estimate_tokens_monotonic():
    assert ml.estimate_tokens("") == 1  # floor of max(1, ...)
    assert ml.estimate_tokens("a" * 40) == 10
    assert ml.estimate_tokens("a" * 400) > ml.estimate_tokens("a" * 40)


def test_limits_for_known_and_unknown():
    known = ml.limits_for("llama-3.3-70b-versatile", config={})
    assert known["max_input_tokens"] == 10000 and known["max_output_tokens"] == 2048
    unknown = ml.limits_for("some-custom-model-xyz", config={})
    assert unknown == ml.DEFAULT_LIMITS


def test_limits_for_config_override_merges():
    cfg = {"model_limits": {"llama-3.3-70b-versatile": {"max_input_tokens": 5000}}}
    merged = ml.limits_for("llama-3.3-70b-versatile", config=cfg)
    assert merged["max_input_tokens"] == 5000          # overridden
    assert merged["max_output_tokens"] == 2048          # registry default kept


def test_provider_model_resolves_default_and_explicit():
    assert ml.provider_model("gemini", {}, None) == "gemini-2.5-flash"
    assert ml.provider_model("gemini", {"gemini_model": "gemini-2.0-flash"}, None) == "gemini-2.0-flash"
    assert ml.provider_model("groq", {}, "explicit-model") == "explicit-model"


def test_fits_boundary():
    # llama budget = 10000 input tokens => 40000 chars total across system+user.
    small = "x" * 100
    assert ml.fits("llama-3.3-70b-versatile", small, small, config={})
    big = "x" * 50000
    assert not ml.fits("llama-3.3-70b-versatile", "", big, config={})
    # Gemini's huge budget holds the same big prompt.
    assert ml.fits("gemini-2.5-flash", "", big, config={})


def test_trim_to_budget_marks_and_shrinks():
    text = "line\n" * 5000  # ~25k chars
    out = ml.trim_to_budget(text, max_input_tokens=1000)
    assert "…[trimmed to fit model context]" in out
    assert ml.estimate_tokens(out) <= 1000 + 20  # within budget + the short marker
    # Short text is returned untouched.
    assert ml.trim_to_budget("short", max_input_tokens=1000) == "short"
