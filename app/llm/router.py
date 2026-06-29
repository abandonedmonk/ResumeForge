from __future__ import annotations

import time

from app.llm.anthropic_claude import AnthropicClaude
from app.llm.base import BaseLLM
from app.llm.cohere import CohereCommandR
from app.llm.copilot import CopilotModels
from app.llm.gemini import GeminiFlash
from app.llm.groq import GroqModel
from app.llm.keypool import PROVIDER_ENV, ordered_keys
from app.llm.openai_gpt import OpenAIGPT
from app.llm.openrouter import OpenRouterFree
from app.utils.config import get_config
from app.utils.exceptions import ConfigError, LLMError, RateLimitError

_PROVIDERS: dict[str, type[BaseLLM]] = {
    "groq": GroqModel,
    "openrouter": OpenRouterFree,
    "cohere": CohereCommandR,
    "copilot": CopilotModels,
    "gemini": GeminiFlash,
    "openai": OpenAIGPT,
    "anthropic": AnthropicClaude,
}

# Free, rate-limit-resilient cascade (no paid key required).
DEFAULT_FREE_CHAIN = ["groq", "openrouter", "gemini", "cohere", "copilot"]
# Premium cascade for bring-your-own paid keys.
DEFAULT_PREMIUM_CHAIN = ["openai", "anthropic", "gemini", "groq"]
# Back-compat alias used by the "custom" tier.
DEFAULT_FALLBACK_CHAIN = DEFAULT_FREE_CHAIN


def _get_provider(name: str, model_name: str | None = None, api_key: str | None = None) -> BaseLLM:
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ConfigError(
            f"Unknown LLM provider: '{name}'. Valid options: {list(_PROVIDERS.keys())}"
        )
    return cls(model_name=model_name, api_key=api_key)


def _describe(name: str, exc: Exception, model_name: str | None = None) -> str:
    target = f"{name}:{model_name}" if model_name else name
    return f"{target} -> {exc}"


def _backoff(attempt: int) -> None:
    # Brief exponential backoff between key attempts; capped so the UI never hangs.
    time.sleep(min(0.5 * (2 ** attempt), 4.0))


class RoutedModel:
    """Single parameterized router with tiered chains and per-provider key rotation.

    ``stage`` is ``"stage1"`` (reasoning, temp 0.2) or ``"stage2"`` (writing,
    temp 0.4). ``tier`` selects the provider chain: ``"free"`` (default),
    ``"premium"`` (paid GPT/Claude/Gemini), or ``"custom"`` (the ``fallback_chain``
    config key). For each provider every available key (``NAME``, ``NAME_1`` …,
    plus any UI session key) is tried — rotating on rate limits — before failing
    over to the next provider.
    """

    def __init__(self, stage: str, tier: str | None = None) -> None:
        if stage not in ("stage1", "stage2"):
            raise ConfigError(f"Unknown router stage: '{stage}'. Use 'stage1' or 'stage2'.")
        config = get_config()
        self.stage = stage
        self.tier = (tier or config.get("model_tier", "free")).lower()
        self.preferred = config.get(f"{stage}_model", "groq")
        self.chain = self._build_chain(config)

        if stage == "stage1":
            self.groq_models = [
                config.get("groq_reasoning_model", "llama-3.3-70b-versatile"),
                config.get(
                    "groq_fallback_reasoning_model",
                    config.get("groq_fallback_fast_model", "meta-llama/llama-4-maverick-17b-128e-instruct"),
                ),
            ]
            self.default_temp = 0.2
        else:
            self.groq_models = [
                config.get("groq_fast_model", "llama-3.3-70b-versatile"),
                config.get("groq_fallback_fast_model", "meta-llama/llama-4-maverick-17b-128e-instruct"),
            ]
            self.default_temp = 0.4

    def _build_chain(self, config: dict) -> list[str]:
        if self.tier == "premium":
            chain = list(config.get("premium_chain", DEFAULT_PREMIUM_CHAIN))
        elif self.tier == "custom":
            chain = list(config.get("fallback_chain", DEFAULT_FALLBACK_CHAIN))
        else:
            chain = list(config.get("free_chain", config.get("fallback_chain", DEFAULT_FREE_CHAIN)))
        # Honor an explicit stage preference for free/custom tiers (premium keeps its curated order).
        if self.tier != "premium" and self.preferred in chain:
            chain.remove(self.preferred)
            chain.insert(0, self.preferred)
        elif self.tier != "premium" and self.preferred and self.preferred not in chain:
            chain.insert(0, self.preferred)
        return chain

    def call(self, system_prompt: str, user_prompt: str, temperature: float | None = None) -> str:
        temp = temperature if temperature is not None else self.default_temp
        errors: list[str] = []
        seen: set[str] = set()
        for name in self.chain:
            if name in seen:
                continue
            seen.add(name)

            models = self.groq_models if name == "groq" else [None]
            keys = ordered_keys(PROVIDER_ENV.get(name, "")) or [None]
            provider_misconfigured = False

            for model_name in models:
                if provider_misconfigured:
                    break
                for attempt, key in enumerate(keys):
                    try:
                        return _get_provider(name, model_name, key).call(system_prompt, user_prompt, temperature=temp)
                    except RateLimitError as exc:
                        errors.append(_describe(name, exc, model_name))
                        if attempt + 1 < len(keys):
                            _backoff(attempt)
                        continue  # try the next key for this provider
                    except ConfigError as exc:
                        errors.append(_describe(name, exc, model_name))
                        provider_misconfigured = True  # missing key — skip provider entirely
                        break
                    except LLMError as exc:
                        errors.append(_describe(name, exc, model_name))
                        break  # generic failure — other keys unlikely to help; next model/provider
        raise LLMError(f"All {self.stage} ({self.tier}) providers failed. " + " | ".join(errors))


class RoutedStage1Model(RoutedModel):
    """Backward-compatible alias for the reasoning/selection stage."""

    def __init__(self, tier: str | None = None) -> None:
        super().__init__("stage1", tier=tier)


class RoutedStage2Model(RoutedModel):
    """Backward-compatible alias for the writing/generation stage."""

    def __init__(self, tier: str | None = None) -> None:
        super().__init__("stage2", tier=tier)
