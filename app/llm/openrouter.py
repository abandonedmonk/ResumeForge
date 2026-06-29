from __future__ import annotations

from openai import OpenAI

from app.llm.base import BaseLLM
from app.utils.exceptions import LLMError


class OpenRouterFree(BaseLLM):
    provider_name = "openrouter"

    def __init__(self) -> None:
        super().__init__()
        self.api_key = self.require_env(
            "OPENROUTER_API_KEY",
            "OPENROUTER_API_KEY is missing. Add it to your .env file to use OpenRouter.",
        )
        self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=self.api_key)
        self.model = self.config.get("openrouter_model", "openai/gpt-oss-20b:free")

    def call(self, system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            if not response.choices or response.choices[0].message.content is None:
                raise LLMError("OpenRouter returned an empty response.")
            text = response.choices[0].message.content.strip()
            self.log(system_prompt, user_prompt, text)
            return text
        except Exception as exc:  # pragma: no cover - provider specific
            raise self.classify_exception(exc) from exc
