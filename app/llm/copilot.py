from __future__ import annotations

from openai import OpenAI

from app.llm.base import BaseLLM


class CopilotModels(BaseLLM):
    provider_name = "copilot"

    def __init__(self) -> None:
        super().__init__()
        self.api_key = self.require_env(
            "GITHUB_TOKEN",
            "GITHUB_TOKEN is missing. Create a GitHub personal access token with models access and add it to .env.",
        )
        self.client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=self.api_key)
        self.model = self.config.get("copilot_model", "gpt-4o")

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
            text = response.choices[0].message.content.strip()
            self.log(system_prompt, user_prompt, text)
            return text
        except Exception as exc:  # pragma: no cover - provider specific
            raise self.classify_exception(exc) from exc

