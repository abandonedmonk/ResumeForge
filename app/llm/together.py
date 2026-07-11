from __future__ import annotations

from app.llm.openai_compatible import OpenAICompatibleLLM


class TogetherModel(OpenAICompatibleLLM):
    """Together AI (OpenAI-compatible endpoint, bring-your-own key)."""

    provider_name = "together"
    env_var = "TOGETHER_API_KEY"
    base_url = "https://api.together.xyz/v1"
    default_model = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    config_model_key = "together_model"
