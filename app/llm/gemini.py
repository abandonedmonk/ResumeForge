from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI

from app.llm.base import BaseLLM


class GeminiFlash(BaseLLM):
    provider_name = "gemini"

    def __init__(self) -> None:
        super().__init__()
        self.api_key = self.require_env(
            "GOOGLE_API_KEY",
            "GOOGLE_API_KEY is missing. Add it to your .env file to use Gemini Flash.",
        )
        self.client = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=self.api_key,
            temperature=0.3,
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
            text = str(response.content).strip()
            self.log(system_prompt, user_prompt, text)
            return text
        except Exception as exc:  # pragma: no cover - provider specific
            raise self.classify_exception(exc) from exc

