from __future__ import annotations

from langchain_groq import ChatGroq

from app.llm.base import BaseLLM
from app.utils.exceptions import LLMError


class GroqModel(BaseLLM):
    provider_name = "groq"

    def __init__(self, model_name: str | None = None) -> None:
        super().__init__()
        self.api_key = self.require_env(
            "GROQ_API_KEY",
            "GROQ_API_KEY is missing. Add it to your .env file to use Groq.",
        )
        # Use provided model_name or fallback to config, then default
        self.model = model_name or self.config.get("groq_model", "llama-3.3-70b-versatile")
        self.client = ChatGroq(
            model=self.model,
            groq_api_key=self.api_key,
        )

    def call(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        try:
            response = self.client.invoke(
                [
                    ("system", system_prompt),
                    ("human", user_prompt),
                ],
                temperature=temperature,
            )
            if response.content is None:
                raise LLMError("Groq returned an empty response.")
            text = str(response.content).strip()
            self.log(system_prompt, user_prompt, text)
            return text
        except Exception as exc:  # pragma: no cover - provider specific
            raise self.classify_exception(exc) from exc
