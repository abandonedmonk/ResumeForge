from __future__ import annotations

from app.llm.openai_compatible import OpenAICompatibleLLM


class XAIModel(OpenAICompatibleLLM):
    """xAI Grok (OpenAI-compatible endpoint, bring-your-own key)."""

    provider_name = "xai"
    env_var = "XAI_API_KEY"
    base_url = "https://api.x.ai/v1"
    default_model = "grok-2-latest"
    config_model_key = "xai_model"
