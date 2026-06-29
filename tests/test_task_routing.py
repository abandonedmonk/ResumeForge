"""Unit tests for task-aware provider routing."""
from __future__ import annotations

from app.llm import task_routing as tr

FREE = tr.DEFAULT_FREE_CHAIN


def test_ats_prefers_gemini_when_live():
    live = {"groq": 1, "gemini": 1}
    chain = tr.resolve_task_chain("ats_scoring", FREE, {}, live=live)
    assert chain[0] == "gemini"


def test_tailor_prefers_groq_when_live():
    live = {"groq": 1, "gemini": 1}
    chain = tr.resolve_task_chain("tailor", FREE, {}, live=live)
    assert chain[0] == "groq"


def test_drops_dead_providers_but_keeps_order():
    # Only openrouter has a key: ats_scoring (prefers gemini) falls back to it.
    live = {"openrouter": 1}
    chain = tr.resolve_task_chain("ats_scoring", FREE, {}, live=live)
    assert chain == ["openrouter"]


def test_config_override_wins():
    live = {"groq": 1, "gemini": 1}
    cfg = {"task_routing": {"tailor": "gemini"}}
    chain = tr.resolve_task_chain("tailor", FREE, cfg, live=live)
    assert chain[0] == "gemini"


def test_empty_live_returns_unfiltered_fallback():
    # No detected keys -> don't silently empty the chain; surface the full order.
    chain = tr.resolve_task_chain("tailor", FREE, {}, live={})
    assert chain == FREE


def test_tier_chain_selects_by_tier():
    assert tr.tier_chain({"model_tier": "premium"}) == tr.DEFAULT_PREMIUM_CHAIN
    assert tr.tier_chain({"model_tier": "free"}) == tr.DEFAULT_FREE_CHAIN


def test_routing_summary_uses_live(monkeypatch):
    monkeypatch.setattr(tr, "available_providers", lambda: {"groq": 2, "gemini": 1})
    summary = tr.routing_summary({"model_tier": "free"})
    assert summary["live"] == {"groq": 2, "gemini": 1}
    assert summary["tasks"]["ats_scoring"] == "gemini"
    assert summary["tasks"]["tailor"] == "groq"
