from __future__ import annotations

from openai import OpenAI

from app.llm.base import BaseLLM
from app.utils.exceptions import LLMError


class OpenAIGPT(BaseLLM):
    """Premium OpenAI GPT models (bring-your-own key)."""

    provider_name = "openai"

    def __init__(self, model_name: str | None = None, api_key: str | None = None) -> None:
        super().__init__()
        self.api_key = self.require_env(
            "OPENAI_API_KEY",
            "OPENAI_API_KEY is missing. Add it to your .env file or paste it in the UI to use GPT.",
            override=api_key,
        )
        self.client = OpenAI(api_key=self.api_key)
        self.model = model_name or self.config.get("openai_model", "gpt-4o")

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
                raise LLMError("OpenAI returned an empty response.")
            text = response.choices[0].message.content.strip()
            self.log(system_prompt, user_prompt, text)
            return text
        except Exception as exc:  # pragma: no cover - provider specific
            raise self.classify_exception(exc) from exc
