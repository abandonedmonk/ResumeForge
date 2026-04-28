from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.llm.cohere import CohereCommandR
from app.llm.copilot import CopilotModels
from app.llm.gemini import GeminiFlash
from app.llm.groq import GroqModel
from app.llm.openrouter import OpenRouterFree
from app.utils.config import get_config
from app.utils.exceptions import LLMError, RateLimitError


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


class RoutedStage2Model:
    """Generation/Writing model (Stage 2)."""
    def __init__(self) -> None:
        config = get_config()
        self.preferred = config.get("stage2_model", "groq")
        self.groq_model = config.get("groq_fast_model", "mixtral-8x7b-32768")
        self.order = ["groq", "cohere", "openrouter", "copilot"]
        
        if self.preferred in self.order:
            self.order.remove(self.preferred)
            self.order.insert(0, self.preferred)

    def call(self, system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
        last_error: Exception | None = None
        for name in self.order:
            try:
                model_name = self.groq_model if name == "groq" else None
                provider = get_model(name, model_name=model_name)
                return provider.call(system_prompt, user_prompt, temperature=temperature)
            except (RateLimitError, LLMError) as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise LLMError("No Stage 2 models are configured.")


class RoutedStage1Model:
    """Reasoning/Selection model (Stage 1)."""
    def __init__(self) -> None:
        config = get_config()
        self.preferred = config.get("stage1_model", "groq")
        self.groq_model = config.get("groq_reasoning_model", "llama-3.3-70b-versatile")
        self.order = ["groq", "openrouter", "cohere", "copilot"]
        
        if self.preferred in self.order:
            self.order.remove(self.preferred)
            self.order.insert(0, self.preferred)

    def call(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        last_error: Exception | None = None
        for name in self.order:
            try:
                model_name = self.groq_model if name == "groq" else None
                provider = get_model(name, model_name=model_name)
                return provider.call(system_prompt, user_prompt, temperature=temperature)
            except (RateLimitError, LLMError) as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise LLMError("No Stage 1 models are configured.")
