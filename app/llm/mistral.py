from __future__ import annotations

from app.llm.openai_compatible import OpenAICompatibleLLM


class MistralModel(OpenAICompatibleLLM):
    """Mistral AI (OpenAI-compatible endpoint, bring-your-own key)."""

    provider_name = "mistral"
    env_var = "MISTRAL_API_KEY"
    base_url = "https://api.mistral.ai/v1"
    default_model = "mistral-large-latest"
    config_model_key = "mistral_model"
