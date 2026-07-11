from __future__ import annotations

from app.llm.openai_compatible import OpenAICompatibleLLM


class OllamaLocal(OpenAICompatibleLLM):
    """Local Ollama models via its OpenAI-compatible endpoint (no API key).

    Enabled by setting ``OLLAMA_BASE_URL`` (default ``http://localhost:11434/v1``)
    in ``.env``; that env var also gates availability, so ResumeForge never dials a
    local server that isn't configured. Pick the model with ``ollama_model`` in
    ``config.yaml`` (must be pulled first via ``ollama pull <model>``).
    """

    provider_name = "ollama"
    env_var = "OLLAMA_BASE_URL"  # used only as the availability signal, not as auth
    base_url = "http://localhost:11434/v1"
    base_url_env = "OLLAMA_BASE_URL"
    default_model = "llama3.1"
    config_model_key = "ollama_model"
    model_env = "OLLAMA_MODEL"
    requires_key = False
