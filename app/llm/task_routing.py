"""Task-aware provider routing.

The router historically only knew two *stages* (reasoning vs. writing) and pointed
both at the same preferred provider. That meant the intuitive split — let Gemini do
the semantic ATS scoring (huge context) while Groq writes the prose (fast) — never
actually happened, because Gemini sat behind Groq in the cascade.

This module maps each pipeline *task* to a preferred provider order, filtered to the
providers that actually have keys (auto-detect). Users override any task via a
``task_routing:`` block in ``config.yaml``. The chain still ends with the full tier
cascade as a fallback, so nothing ever dead-ends.
"""
from __future__ import annotations

from app.llm.keypool import available_providers

# Free, rate-limit-resilient cascade (no paid key required).
DEFAULT_FREE_CHAIN = ["groq", "openrouter", "gemini", "cohere", "copilot"]
# Premium cascade for bring-your-own paid keys.
DEFAULT_PREMIUM_CHAIN = ["openai", "anthropic", "gemini", "groq"]
# Back-compat alias used by the "custom" tier.
DEFAULT_FALLBACK_CHAIN = DEFAULT_FREE_CHAIN

# Providers with a large context window — preferred as the overflow target for
# ``large_context`` tasks and when a prompt is too big for the small free models.
LARGE_CONTEXT_PROVIDERS = ("gemini", "openai", "anthropic", "copilot")

# task name -> preferred provider order + whether it routinely sends big prompts.
TASK_ROUTES: dict[str, dict] = {
    "analyze_jd": {"preferred": ["groq"], "large_context": False},
    "ats_scoring": {"preferred": ["gemini"], "large_context": False},
    "project_selection": {"preferred": ["groq"], "large_context": False},
    "project_generation": {"preferred": ["groq"], "large_context": True},
    "tailor": {"preferred": ["groq"], "large_context": False},
    "cover_letter": {"preferred": ["groq"], "large_context": False},
    "report": {"preferred": ["groq"], "large_context": False},
}


def tier_chain(config: dict) -> list[str]:
    """The base provider cascade for the configured ``model_tier``."""
    tier = str(config.get("model_tier", "free")).lower()
    if tier == "premium":
        return list(config.get("premium_chain", DEFAULT_PREMIUM_CHAIN))
    if tier == "custom":
        return list(config.get("fallback_chain", DEFAULT_FALLBACK_CHAIN))
    return list(config.get("free_chain", config.get("fallback_chain", DEFAULT_FREE_CHAIN)))


def task_is_large_context(task: str) -> bool:
    return bool(TASK_ROUTES.get(task, {}).get("large_context", False))


def resolve_task_chain(
    task: str,
    base_chain: list[str],
    config: dict,
    live: dict[str, int] | None = None,
) -> list[str]:
    """Order the provider chain for ``task``: preferred providers first, then the rest
    of the tier cascade. When auto-detecting, drop providers with no key; if that would
    empty the chain, fall back to the unfiltered order so the router surfaces a clear
    ConfigError instead of silently doing nothing."""
    live = available_providers() if live is None else live

    overrides = config.get("task_routing") or {}
    override = overrides.get(task)
    if override:
        preferred = [override] if isinstance(override, str) else list(override)
    else:
        preferred = list(TASK_ROUTES.get(task, {}).get("preferred", []))

    ordered: list[str] = []
    for provider in preferred + list(base_chain):
        if provider and provider not in ordered:
            ordered.append(provider)

    live_ordered = [p for p in ordered if p in live]
    return live_ordered or ordered


def routing_summary(config: dict) -> dict:
    """``{ "live": {provider: key_count}, "tasks": {task: chosen_provider} }`` — for the
    runtime log line and the UI 'Providers & Routing' readout."""
    live = available_providers()
    base = tier_chain(config)
    tasks: dict[str, str] = {}
    for task in TASK_ROUTES:
        chain = resolve_task_chain(task, base, config, live)
        tasks[task] = chain[0] if chain else "(no key)"
    return {"live": live, "tasks": tasks}
