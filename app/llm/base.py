from __future__ import annotations

import os
from typing import Any

from app.utils.config import get_config
from app.utils.exceptions import AuthenticationError, ConfigError, LLMError, RateLimitError
from app.utils.logger import log_llm_interaction


class BaseLLM:
    provider_name = "base"

    def __init__(self) -> None:
        self.config = get_config()

    def log(self, system_prompt: str, user_prompt: str, response_text: str) -> None:
        log_llm_interaction(self.provider_name, system_prompt, user_prompt, response_text)

    @staticmethod
    def require_env(name: str, help_text: str) -> str:
        value = os.getenv(name, "").strip()
        if not value:
            raise ConfigError(help_text)
        return value

    @staticmethod
    def classify_exception(exc: Exception) -> Exception:
        message = str(exc).lower()
        if any(token in message for token in ("rate limit", "429", "quota", "resource exhausted")):
            return RateLimitError(str(exc))
        if any(token in message for token in ("401", "unauthorized", "bad credentials", "invalid api key", "expired_api_key", "authentication")):
            return AuthenticationError(str(exc))
        return LLMError(str(exc))

    def call(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        raise NotImplementedError
