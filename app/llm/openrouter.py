from __future__ import annotations

from app.llm.openai_compatible import OpenAICompatibleLLM


class OpenRouterFree(OpenAICompatibleLLM):
    """OpenRouter free tier (OpenAI-compatible endpoint)."""

    provider_name = "openrouter"
    env_var = "OPENROUTER_API_KEY"
    base_url = "https://openrouter.ai/api/v1"
    default_model = "openai/gpt-oss-20b:free"
    config_model_key = "openrouter_model"
