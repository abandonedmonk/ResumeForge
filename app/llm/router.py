from __future__ import annotations

import logging
import time

from app.llm.anthropic_claude import AnthropicClaude
from app.llm.base import BaseLLM
from app.llm.cohere import CohereCommandR
from app.llm.copilot import CopilotModels
from app.llm.deepseek import DeepSeekModel
from app.llm.gemini import GeminiFlash
from app.llm.groq import GroqModel
from app.llm.keypool import PROVIDER_ENV, ordered_keys
from app.llm.mistral import MistralModel
from app.llm.model_limits import estimate_tokens, limits_for, provider_model, trim_to_budget
from app.llm.ollama import OllamaLocal
from app.llm.openai_gpt import OpenAIGPT
from app.llm.openrouter import OpenRouterFree
from app.llm.task_routing import (
    DEFAULT_FALLBACK_CHAIN,
    DEFAULT_FREE_CHAIN,
    DEFAULT_PREMIUM_CHAIN,
    resolve_task_chain,
    task_is_large_context,
    tier_chain,
)
from app.llm.together import TogetherModel
from app.llm.xai import XAIModel
from app.utils.config import get_config
from app.utils.exceptions import ConfigError, LLMError, RateLimitError

logger = logging.getLogger(__name__)

# Re-exported for back-compat (these chains now live in task_routing).
__all__ = [
    "RoutedModel",
    "RoutedStage1Model",
    "RoutedStage2Model",
    "DEFAULT_FREE_CHAIN",
    "DEFAULT_PREMIUM_CHAIN",
    "DEFAULT_FALLBACK_CHAIN",
]

_PROVIDERS: dict[str, type[BaseLLM]] = {
    "groq": GroqModel,
    "openrouter": OpenRouterFree,
    "cohere": CohereCommandR,
    "copilot": CopilotModels,
    "gemini": GeminiFlash,
    "openai": OpenAIGPT,
    "anthropic": AnthropicClaude,
    "mistral": MistralModel,
    "deepseek": DeepSeekModel,
    "together": TogetherModel,
    "xai": XAIModel,
    "ollama": OllamaLocal,
}


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
    """Parameterized router with tiered chains, per-provider key rotation, optional
    task-aware provider selection, and token-budget awareness.

    ``stage`` is ``"stage1"`` (reasoning, temp 0.2) or ``"stage2"`` (writing, temp 0.4).
    ``tier`` selects the provider chain: ``"free"`` (default), ``"premium"``, or
    ``"custom"``. ``task`` (optional) routes the call to the best provider for that job
    (e.g. ``"ats_scoring"`` -> Gemini, ``"tailor"`` -> Groq) and enables the
    skip-to-bigger-then-trim token logic. With ``task=None`` the behavior is identical
    to the original two-stage router.
    """

    def __init__(self, stage: str, tier: str | None = None, task: str | None = None) -> None:
        if stage not in ("stage1", "stage2"):
            raise ConfigError(f"Unknown router stage: '{stage}'. Use 'stage1' or 'stage2'.")
        config = get_config()
        self.stage = stage
        self.tier = (tier or config.get("model_tier", "free")).lower()
        self.preferred = config.get(f"{stage}_model", "groq")
        self.task = task
        self.large_context = task_is_large_context(task) if task else False

        if task:
            self.chain = resolve_task_chain(task, tier_chain(config), config)
        else:
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
        if not self.task:
            return self._call_legacy(system_prompt, user_prompt, temp)
        return self._call_token_aware(system_prompt, user_prompt, temp)

    def _call_legacy(self, system_prompt: str, user_prompt: str, temp: float) -> str:
        """Original behavior — exact, for ``task=None`` back-compat (no token logic)."""
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

    def _call_token_aware(self, system_prompt: str, user_prompt: str, temp: float) -> str:
        """Task path: prefer a provider that *fits* the prompt (skip to a bigger-context
        model when needed); only trim the input if nothing in the chain can hold it."""
        config = get_config()
        prompt_tokens = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
        sys_tokens = estimate_tokens(system_prompt)

        # (provider, model_name) candidates in chain order; groq contributes its 2 models.
        candidates: list[tuple[str, str | None]] = []
        for name in self.chain:
            models = self.groq_models if name == "groq" else [None]
            for model_name in models:
                candidates.append((name, model_name))

        def input_budget(name: str, model_name: str | None) -> int:
            return limits_for(provider_model(name, config, model_name), config)["max_input_tokens"]

        any_fits = any(prompt_tokens <= input_budget(n, m) for n, m in candidates)
        if any_fits:
            order = candidates  # chain order; non-fitting models are skipped below
        else:
            # Nothing fits — route to the largest-budget model and trim as a last resort.
            order = sorted(candidates, key=lambda nm: input_budget(*nm), reverse=True)
            biggest = input_budget(*order[0]) if order else prompt_tokens
            logger.warning(
                "%s/%s prompt ~%d tokens exceeds every provider budget (max %d); trimming input.",
                self.stage, self.task, prompt_tokens, biggest,
            )

        errors: list[str] = []
        misconfigured: set[str] = set()
        for name, model_name in order:
            if name in misconfigured:
                continue
            limits = limits_for(provider_model(name, config, model_name), config)
            if any_fits and prompt_tokens > limits["max_input_tokens"]:
                continue  # a bigger model exists — skip this one
            user = (
                user_prompt
                if any_fits
                else trim_to_budget(user_prompt, limits["max_input_tokens"], reserve_tokens=sys_tokens)
            )
            keys = ordered_keys(PROVIDER_ENV.get(name, "")) or [None]
            out_cap = limits["max_output_tokens"]
            for attempt, key in enumerate(keys):
                try:
                    return _get_provider(name, model_name, key).call(
                        system_prompt, user, temperature=temp, max_tokens=out_cap
                    )
                except RateLimitError as exc:
                    errors.append(_describe(name, exc, model_name))
                    if attempt + 1 < len(keys):
                        _backoff(attempt)
                    continue
                except ConfigError as exc:
                    errors.append(_describe(name, exc, model_name))
                    misconfigured.add(name)  # missing key — skip both this provider's models
                    break
                except LLMError as exc:
                    errors.append(_describe(name, exc, model_name))
                    break
        raise LLMError(
            f"All {self.stage} ({self.tier}, task={self.task}) providers failed. " + " | ".join(errors)
        )


class RoutedStage1Model(RoutedModel):
    """Backward-compatible alias for the reasoning/selection stage."""

    def __init__(self, tier: str | None = None, task: str | None = None) -> None:
        super().__init__("stage1", tier=tier, task=task)


class RoutedStage2Model(RoutedModel):
    """Backward-compatible alias for the writing/generation stage."""

    def __init__(self, tier: str | None = None, task: str | None = None) -> None:
        super().__init__("stage2", tier=tier, task=task)
