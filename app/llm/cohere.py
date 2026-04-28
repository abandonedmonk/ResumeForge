from __future__ import annotations

from langchain_cohere import ChatCohere

from app.llm.base import BaseLLM


class CohereCommandR(BaseLLM):
    provider_name = "cohere"

    def __init__(self) -> None:
        super().__init__()
        self.api_key = self.require_env(
            "COHERE_API_KEY",
            "COHERE_API_KEY is missing. Add it to your .env file to use Cohere fallback.",
        )
        self.client = ChatCohere(cohere_api_key=self.api_key, model="command-r", temperature=0.4)

    def call(self, system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
        try:
            response = self.client.invoke(
                [
                    ("system", system_prompt),
                    ("human", user_prompt),
                ],
                temperature=temperature,
            )
            text = str(response.content).strip()
            self.log(system_prompt, user_prompt, text)
            return text
        except Exception as exc:  # pragma: no cover - provider specific
            raise self.classify_exception(exc) from exc

