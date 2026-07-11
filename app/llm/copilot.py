from __future__ import annotations

from app.llm.openai_compatible import OpenAICompatibleLLM


class CopilotModels(OpenAICompatibleLLM):
    """GitHub Models / Copilot (OpenAI-compatible endpoint).

    Auth is a GitHub personal access token with *models* access, stored in
    ``GITHUB_TOKEN``.
    """

    provider_name = "copilot"
    env_var = "GITHUB_TOKEN"
    base_url = "https://models.inference.ai.azure.com"
    default_model = "gpt-4o"
    config_model_key = "copilot_model"
