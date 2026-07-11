from __future__ import annotations

from app.llm.openai_compatible import OpenAICompatibleLLM


class DeepSeekModel(OpenAICompatibleLLM):
    """DeepSeek (OpenAI-compatible endpoint, bring-your-own key)."""

    provider_name = "deepseek"
    env_var = "DEEPSEEK_API_KEY"
    base_url = "https://api.deepseek.com/v1"
    default_model = "deepseek-chat"
    config_model_key = "deepseek_model"
