from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.llm.cohere import CohereCommandR
from app.llm.copilot import CopilotModels
from app.llm.gemini import GeminiFlash
from app.llm.groq import GroqModel
from app.llm.openrouter import OpenRouterFree
from app.utils.config import get_config
from app.utils.exceptions import AuthenticationError, ConfigError, LLMError, RateLimitError


def _provider_map():
    return {
        "groq": GroqModel,
        "openrouter": OpenRouterFree,
        "cohere": CohereCommandR,
        "copilot": CopilotModels,
        "gemini": GeminiFlash,
    }


def get_model(name: str, model_name: str | None = None):
    providers = _provider_map()
    provider_cls = providers.get(name, OpenRouterFree)
    if provider_cls == GroqModel:
        return GroqModel(model_name=model_name)
    return provider_cls()


def _describe_provider_error(name: str, exc: Exception, model_name: str | None = None) -> str:
    target = f"{name}:{model_name}" if model_name else name
    return f"{target} -> {exc}"


def _raise_combined_error(stage_name: str, errors: list[str], last_error: Exception | None) -> None:
    if errors:
        raise LLMError(f"{stage_name} providers failed. " + " | ".join(errors))
    if last_error:
        raise last_error
    raise LLMError(f"No {stage_name} models are configured.")


class RoutedStage2Model:
    """Generation/Writing model (Stage 2)."""
    def __init__(self) -> None:
        config = get_config()
        self.preferred = config.get("stage2_model", "groq")
        self.groq_model = config.get("groq_fast_model", "qwen-3-32b")
        self.groq_fallback_model = config.get(
            "groq_fallback_fast_model",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
        )
        self.order = ["groq", "openrouter", "cohere", "copilot"]
        
        if self.preferred in self.order:
            self.order.remove(self.preferred)
            self.order.insert(0, self.preferred)

    def call(self, system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
        last_error: Exception | None = None
        errors: list[str] = []
        for name in self.order:
            try:
                if name == "groq":
                    for groq_model_name in (self.groq_model, self.groq_fallback_model):
                        try:
                            provider = get_model("groq", model_name=groq_model_name)
                            return provider.call(system_prompt, user_prompt, temperature=temperature)
                        except (ConfigError, RateLimitError, LLMError) as exc:
                            errors.append(_describe_provider_error("groq", exc, groq_model_name))
                            last_error = exc
                    continue

                provider = get_model(name, model_name=None)
                return provider.call(system_prompt, user_prompt, temperature=temperature)
            except (ConfigError, RateLimitError, LLMError) as exc:
                errors.append(_describe_provider_error(name, exc))
                last_error = exc
                continue
        _raise_combined_error("Stage 2", errors, last_error)


class RoutedStage1Model:
    """Reasoning/Selection model (Stage 1)."""
    def __init__(self) -> None:
        config = get_config()
        self.preferred = config.get("stage1_model", "groq")
        self.groq_model = config.get("groq_reasoning_model", "llama-3.3-70b-versatile")
        self.groq_fallback_model = config.get(
            "groq_fallback_reasoning_model",
            config.get("groq_fallback_fast_model", "meta-llama/llama-4-maverick-17b-128e-instruct"),
        )
        self.order = ["groq", "openrouter", "cohere", "copilot"]
        
        if self.preferred in self.order:
            self.order.remove(self.preferred)
            self.order.insert(0, self.preferred)

    def call(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        last_error: Exception | None = None
        errors: list[str] = []
        for name in self.order:
            try:
                if name == "groq":
                    for groq_model_name in (self.groq_model, self.groq_fallback_model):
                        try:
                            provider = get_model("groq", model_name=groq_model_name)
                            return provider.call(system_prompt, user_prompt, temperature=temperature)
                        except (ConfigError, RateLimitError, LLMError) as exc:
                            errors.append(_describe_provider_error("groq", exc, groq_model_name))
                            last_error = exc
                    continue

                provider = get_model(name, model_name=None)
                return provider.call(system_prompt, user_prompt, temperature=temperature)
            except (ConfigError, RateLimitError, LLMError) as exc:
                errors.append(_describe_provider_error(name, exc))
                last_error = exc
                continue
        _raise_combined_error("Stage 1", errors, last_error)
