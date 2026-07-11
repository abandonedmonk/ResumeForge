"""Per-model token budgets + estimation/trimming helpers.

The numbers here are **effective per-request budgets for the free tier**, not the
models' raw architectural context windows. Groq's free tier, for example, rejects
requests over roughly 12k *total* tokens (input + output) even though
``llama-3.3-70b-versatile`` can technically hold far more — so the budget below is
set conservatively (~80% of the real cap) to absorb the ``len // 4`` token estimate's
error and never trip a 413.

The router uses these to (1) route an oversized prompt to a bigger-context provider
before trimming, (2) cap output tokens so the *total* stays under the per-request
limit, and (3) trim the input only as a last resort. Users can override any entry via
a ``model_limits:`` block in ``config.yaml`` without touching code.
"""
from __future__ import annotations

from app.utils.config import get_config

# Effective free-tier per-request budgets. Keyed by the model string each provider
# reports. ``max_input_tokens`` leaves room for ``max_output_tokens`` under the cap.
MODEL_LIMITS: dict[str, dict[str, int]] = {
    # --- Groq (free tier ~12k total per request) ---
    "llama-3.3-70b-versatile": {"max_input_tokens": 10000, "max_output_tokens": 2048},
    "meta-llama/llama-4-maverick-17b-128e-instruct": {"max_input_tokens": 10000, "max_output_tokens": 2048},
    # --- OpenRouter free models (typically small windows) ---
    "openai/gpt-oss-20b:free": {"max_input_tokens": 6000, "max_output_tokens": 1024},
    # --- Cohere trial ---
    "command-r": {"max_input_tokens": 6000, "max_output_tokens": 1024},
    # --- Gemini (huge context; the big-context overflow target) ---
    "gemini-2.5-flash": {"max_input_tokens": 120000, "max_output_tokens": 4096},
    "gemini-2.0-flash": {"max_input_tokens": 120000, "max_output_tokens": 4096},
    # --- GitHub Models / Copilot (GPT-4o, 128k) ---
    "gpt-4o": {"max_input_tokens": 120000, "max_output_tokens": 4096},
    # --- Premium (generous) ---
    "claude-sonnet-4-6": {"max_input_tokens": 180000, "max_output_tokens": 4096},
    # --- Additional OpenAI-compatible providers (bring-your-own key; generous) ---
    "mistral-large-latest": {"max_input_tokens": 120000, "max_output_tokens": 4096},
    "deepseek-chat": {"max_input_tokens": 60000, "max_output_tokens": 4096},
    "meta-llama/Llama-3.3-70B-Instruct-Turbo": {"max_input_tokens": 120000, "max_output_tokens": 4096},
    "grok-2-latest": {"max_input_tokens": 120000, "max_output_tokens": 4096},
    # --- Local Ollama (conservative; small models on consumer hardware) ---
    "llama3.1": {"max_input_tokens": 8000, "max_output_tokens": 2048},
}

# Used when a model string isn't in the registry (e.g. a custom model the user set).
# Generous so we don't trim unnecessarily; add a ``model_limits`` entry to tighten it.
DEFAULT_LIMITS: dict[str, int] = {"max_input_tokens": 120000, "max_output_tokens": 4096}

# Provider -> (config key, hard-coded default) for resolving the effective model string
# when the router passes ``model_name=None`` (provider picks its own model).
_PROVIDER_MODEL_KEYS: dict[str, tuple[str, str]] = {
    "groq": ("groq_fast_model", "llama-3.3-70b-versatile"),
    "openrouter": ("openrouter_model", "openai/gpt-oss-20b:free"),
    "cohere": ("cohere_model", "command-r"),
    "gemini": ("gemini_model", "gemini-2.5-flash"),
    "copilot": ("copilot_model", "gpt-4o"),
    "openai": ("openai_model", "gpt-4o"),
    "anthropic": ("anthropic_model", "claude-sonnet-4-6"),
    "mistral": ("mistral_model", "mistral-large-latest"),
    "deepseek": ("deepseek_model", "deepseek-chat"),
    "together": ("together_model", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    "xai": ("xai_model", "grok-2-latest"),
    "ollama": ("ollama_model", "llama3.1"),
}


def estimate_tokens(text: str) -> int:
    """Cheap ``len // 4`` token estimate — no tokenizer dependency."""
    return max(1, len(text or "") // 4)


def limits_for(model_name: str, config: dict | None = None) -> dict[str, int]:
    """Effective budget for ``model_name``: registry default merged under config overrides."""
    cfg = config if config is not None else get_config()
    base = dict(MODEL_LIMITS.get(model_name, DEFAULT_LIMITS))
    overrides = (cfg.get("model_limits") or {}).get(model_name)
    if isinstance(overrides, dict):
        for key in ("max_input_tokens", "max_output_tokens"):
            if key in overrides:
                base[key] = int(overrides[key])
    return base


def provider_model(provider: str, config: dict, model_name: str | None = None) -> str:
    """Resolve the effective model string for a provider (so we can look up its budget)."""
    if model_name:
        return model_name
    key, default = _PROVIDER_MODEL_KEYS.get(provider, ("", ""))
    return str(config.get(key, default)) if key else default


def fits(model_name: str, system_prompt: str, user_prompt: str, config: dict | None = None) -> bool:
    """True when the prompt fits the model's input budget."""
    budget = limits_for(model_name, config)["max_input_tokens"]
    return estimate_tokens(system_prompt) + estimate_tokens(user_prompt) <= budget


def trim_to_budget(text: str, max_input_tokens: int, reserve_tokens: int = 0) -> str:
    """Trim ``text`` to fit ``max_input_tokens - reserve_tokens``, cutting on a line
    boundary when possible and appending a visible marker. Never silent."""
    budget = max(1, max_input_tokens - reserve_tokens)
    if estimate_tokens(text) <= budget:
        return text
    char_budget = budget * 4
    head = text[:char_budget]
    nl = head.rfind("\n")
    if nl > char_budget // 2:  # prefer a clean line boundary near the end
        head = head[:nl]
    return head.rstrip() + "\n\n…[trimmed to fit model context]"
