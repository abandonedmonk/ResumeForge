from __future__ import annotations

from app.llm.base import BaseLLM
from app.llm.cohere import CohereCommandR
from app.llm.copilot import CopilotModels
from app.llm.gemini import GeminiFlash
from app.llm.groq import GroqModel
from app.llm.openrouter import OpenRouterFree
from app.utils.config import get_config
from app.utils.exceptions import ConfigError, LLMError, RateLimitError

_PROVIDERS: dict[str, type[BaseLLM]] = {
    "groq": GroqModel,
    "openrouter": OpenRouterFree,
    "cohere": CohereCommandR,
    "copilot": CopilotModels,
    "gemini": GeminiFlash,
}

DEFAULT_FALLBACK_CHAIN = ["groq", "openrouter", "gemini", "cohere", "copilot"]


def _get_provider(name: str, model_name: str | None = None) -> BaseLLM:
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ConfigError(
            f"Unknown LLM provider: '{name}'. Valid options: {list(_PROVIDERS.keys())}"
        )
    if name in ("groq", "gemini") and model_name:
        return cls(model_name=model_name)  # type: ignore[call-arg]
    return cls()


def _describe(name: str, exc: Exception, model_name: str | None = None) -> str:
    target = f"{name}:{model_name}" if model_name else name
    return f"{target} -> {exc}"


class RoutedModel:
    """Single parameterized router with cascading provider fallback.

    ``stage`` is ``"stage1"`` (reasoning/selection, temp 0.2) or ``"stage2"``
    (writing/generation, temp 0.4). The provider order is read from the
    ``fallback_chain`` config key with the configured preferred provider moved
    to the front, so every provider in the chain — including Gemini — is
    reachable.
    """

    def __init__(self, stage: str) -> None:
        if stage not in ("stage1", "stage2"):
            raise ConfigError(f"Unknown router stage: '{stage}'. Use 'stage1' or 'stage2'.")
        config = get_config()
        self.stage = stage
        self.preferred = config.get(f"{stage}_model", "groq")

        chain = list(config.get("fallback_chain", DEFAULT_FALLBACK_CHAIN))
        if self.preferred in chain:
            chain.remove(self.preferred)
            chain.insert(0, self.preferred)
        elif self.preferred:
            chain.insert(0, self.preferred)
        self.chain = chain

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

    def call(self, system_prompt: str, user_prompt: str, temperature: float | None = None) -> str:
        temp = temperature if temperature is not None else self.default_temp
        errors: list[str] = []
        seen: set[str] = set()
        for name in self.chain:
            if name in seen:
                continue
            seen.add(name)
            if name == "groq":
                for model_name in self.groq_models:
                    try:
                        return _get_provider("groq", model_name).call(system_prompt, user_prompt, temperature=temp)
                    except (RateLimitError, LLMError, ConfigError) as exc:
                        errors.append(_describe("groq", exc, model_name))
                continue
            try:
                return _get_provider(name).call(system_prompt, user_prompt, temperature=temp)
            except (RateLimitError, LLMError, ConfigError) as exc:
                errors.append(_describe(name, exc))
        raise LLMError(f"All {self.stage} providers failed. " + " | ".join(errors))


class RoutedStage1Model(RoutedModel):
    """Backward-compatible alias for the reasoning/selection stage."""

    def __init__(self) -> None:
        super().__init__("stage1")


class RoutedStage2Model(RoutedModel):
    """Backward-compatible alias for the writing/generation stage."""

    def __init__(self) -> None:
        super().__init__("stage2")
