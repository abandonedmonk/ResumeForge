"""Shared base for providers that speak the OpenAI chat-completions API.

Groq/Gemini/Cohere use LangChain wrappers, but a growing set of providers
(OpenRouter, GitHub Models, Mistral, DeepSeek, Together, xAI, and local
Ollama) are all reachable through the plain ``openai`` SDK by pointing it at a
different ``base_url``. This base captures that one pattern so each provider is a
few lines of configuration instead of a copied ``call`` body.

Subclasses set class attributes:
  * ``provider_name``      — router/registry key (e.g. ``"mistral"``)
  * ``env_var``            — env var holding the API key (ignored if not required)
  * ``base_url``           — the API endpoint (default when ``base_url_env`` unset)
  * ``base_url_env``       — optional env var that overrides ``base_url`` (local)
  * ``default_model``      — model used when neither arg nor config supplies one
  * ``config_model_key``   — ``config.yaml`` key for the model (e.g. ``"mistral_model"``)
  * ``model_env``          — optional env var that overrides the model (e.g. ``OLLAMA_MODEL``)
  * ``requires_key``       — False for keyless local servers (Ollama)
"""
from __future__ import annotations

import os

from openai import OpenAI

from app.llm.base import BaseLLM
from app.utils.exceptions import LLMError


class OpenAICompatibleLLM(BaseLLM):
    provider_name = "openai_compatible"
    env_var = ""
    base_url = ""
    base_url_env: str | None = None
    default_model = ""
    config_model_key = ""
    model_env: str | None = None
    requires_key = True

    def __init__(self, model_name: str | None = None, api_key: str | None = None) -> None:
        super().__init__()
        base_url = self._resolve_base_url()
        if self.requires_key:
            key = self.require_env(
                self.env_var,
                f"{self.env_var} is missing. Add it to your .env file to use {self.provider_name}.",
                override=api_key,
            )
        else:
            # Local servers (e.g. Ollama) ignore auth; the OpenAI SDK still wants a
            # non-empty token, so pass a harmless placeholder.
            key = "ollama"
        self.client = OpenAI(base_url=base_url, api_key=key)
        env_model = os.getenv(self.model_env, "").strip() if self.model_env else ""
        self.model = model_name or env_model or self.config.get(self.config_model_key, self.default_model)

    def _resolve_base_url(self) -> str:
        """Fixed endpoint, unless ``base_url_env`` overrides it (local installs).

        When the URL comes from the environment we tolerate the common mistake of
        omitting the ``/v1`` suffix the OpenAI SDK expects.
        """
        if self.base_url_env:
            url = os.getenv(self.base_url_env, "").strip() or self.base_url
            url = url.rstrip("/")
            if not url.endswith("/v1"):
                url = f"{url}/v1"
            return url
        return self.base_url

    def call(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.4, max_tokens: int | None = None
    ) -> str:
        try:
            kwargs = {"model": self.model, "temperature": temperature}
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **kwargs,
            )
            if not response.choices or response.choices[0].message.content is None:
                raise LLMError(f"{self.provider_name} returned an empty response.")
            text = response.choices[0].message.content.strip()
            self.log(system_prompt, user_prompt, text)
            return text
        except Exception as exc:  # pragma: no cover - provider specific
            raise self.classify_exception(exc) from exc
