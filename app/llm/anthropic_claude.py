from __future__ import annotations

from anthropic import Anthropic

from app.llm.base import BaseLLM
from app.utils.exceptions import LLMError


class AnthropicClaude(BaseLLM):
    """Premium Anthropic Claude models (bring-your-own key)."""

    provider_name = "anthropic"

    def __init__(self, model_name: str | None = None, api_key: str | None = None) -> None:
        super().__init__()
        self.api_key = self.require_env(
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_API_KEY is missing. Add it to your .env file or paste it in the UI to use Claude.",
            override=api_key,
        )
        self.client = Anthropic(api_key=self.api_key)
        self.model = model_name or self.config.get("anthropic_model", "claude-sonnet-4-6")
        self.max_tokens = int(self.config.get("anthropic_max_tokens", 4096))

    def call(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.4, max_tokens: int | None = None
    ) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
            text = "".join(parts).strip()
            if not text:
                raise LLMError("Anthropic returned an empty response.")
            self.log(system_prompt, user_prompt, text)
            return text
        except Exception as exc:  # pragma: no cover - provider specific
            raise self.classify_exception(exc) from exc
