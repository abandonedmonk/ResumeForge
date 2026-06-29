"""Token-aware routing tests: skip-to-bigger-then-trim, and task=None back-compat."""
from __future__ import annotations

import app.llm.router as router
import app.llm.task_routing as task_routing


class _FakeProvider:
    def __init__(self, name, model_name, calls):
        self.name = name
        self.model_name = model_name
        self.calls = calls

    def call(self, system_prompt, user_prompt, temperature=0.3, max_tokens=None):
        self.calls.append(
            {"name": self.name, "model": self.model_name, "user": user_prompt, "max_tokens": max_tokens}
        )
        return "OK"


def _patch(monkeypatch, live):
    calls: list[dict] = []
    monkeypatch.setattr(router, "ordered_keys", lambda base: ["k"])
    monkeypatch.setattr(router, "_get_provider", lambda name, model_name=None, key=None: _FakeProvider(name, model_name, calls))
    monkeypatch.setattr(task_routing, "available_providers", lambda: dict(live))
    return calls


def test_oversized_prompt_skips_small_model_for_bigger(monkeypatch):
    calls = _patch(monkeypatch, {"groq": 1, "gemini": 1})
    big_user = "x" * 44000  # ~11k tokens: too big for Groq (10k), fits Gemini (120k)
    out = router.RoutedModel("stage2", task="project_generation").call("", big_user)
    assert out == "OK"
    assert len(calls) == 1
    assert calls[0]["name"] == "gemini"          # skipped Groq, routed to the big model
    assert calls[0]["user"] == big_user          # not trimmed — a model fit


def test_nothing_fits_trims_to_largest(monkeypatch):
    calls = _patch(monkeypatch, {"groq": 1})      # only small-budget Groq is live
    huge_user = "y" * 200000                       # ~50k tokens, exceeds Groq's 10k
    out = router.RoutedModel("stage2", task="project_generation").call("", huge_user)
    assert out == "OK"
    assert calls[0]["name"] == "groq"
    assert "…[trimmed to fit model context]" in calls[0]["user"]   # trimmed, not silent
    assert len(calls[0]["user"]) < len(huge_user)
    assert calls[0]["max_tokens"] == 2048          # output capped from the registry


def test_task_none_is_backward_compatible(monkeypatch):
    calls = _patch(monkeypatch, {"groq": 1, "gemini": 1})
    model = router.RoutedModel("stage1")           # no task -> legacy path
    assert model.chain[0] == "groq"                # unchanged free-chain ordering
    out = model.call("sys", "user")
    assert out == "OK"
    assert calls[0]["name"] == "groq"
    assert calls[0]["max_tokens"] is None          # legacy path passes no output cap
