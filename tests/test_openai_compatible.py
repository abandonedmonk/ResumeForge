"""Unit tests for the shared OpenAI-compatible provider base + its subclasses.

Covers base-URL resolution, key handling (including keyless Ollama), model
resolution precedence, and the config-only subclasses that speak the OpenAI
chat-completions protocol. No network: the ``openai.OpenAI`` client is mocked.
"""
from __future__ import annotations

import pytest

from app.llm import openai_compatible as oc
from app.llm.copilot import CopilotModels
from app.llm.deepseek import DeepSeekModel
from app.llm.keystore import clear_session_keys
from app.llm.mistral import MistralModel
from app.llm.ollama import OllamaLocal
from app.llm.openrouter import OpenRouterFree
from app.llm.together import TogetherModel
from app.llm.xai import XAIModel
from app.utils.exceptions import ConfigError


class _FakeOpenAI:
    """Stand-in for ``openai.OpenAI`` that records how it was constructed."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Mock the OpenAI client and pin config to empty so defaults are deterministic."""
    clear_session_keys()
    monkeypatch.setattr(oc, "OpenAI", _FakeOpenAI)
    # BaseLLM.__init__ reads config via get_config(); force an empty mapping so
    # tests exercise the default_model fallback, not whatever config.yaml holds.
    monkeypatch.setattr("app.llm.base.get_config", dict)
    yield
    clear_session_keys()


# Subclasses whose endpoint is a fixed URL and that require a key.
KEYED_PROVIDERS = [
    (OpenRouterFree, "openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", "openai/gpt-oss-20b:free", "openrouter_model"),
    (CopilotModels, "copilot", "GITHUB_TOKEN", "https://models.inference.ai.azure.com", "gpt-4o", "copilot_model"),
    (MistralModel, "mistral", "MISTRAL_API_KEY", "https://api.mistral.ai/v1", "mistral-large-latest", "mistral_model"),
    (DeepSeekModel, "deepseek", "DEEPSEEK_API_KEY", "https://api.deepseek.com/v1", "deepseek-chat", "deepseek_model"),
    (TogetherModel, "together", "TOGETHER_API_KEY", "https://api.together.xyz/v1", "meta-llama/Llama-3.3-70B-Instruct-Turbo", "together_model"),
    (XAIModel, "xai", "XAI_API_KEY", "https://api.x.ai/v1", "grok-2-latest", "xai_model"),
]


@pytest.mark.parametrize("cls,name,env_var,base_url,default_model,config_key", KEYED_PROVIDERS)
def test_provider_class_attrs(cls, name, env_var, base_url, default_model, config_key):
    assert cls.provider_name == name
    assert cls.env_var == env_var
    assert cls.base_url == base_url
    assert cls.default_model == default_model
    assert cls.config_model_key == config_key
    assert cls.requires_key is True


@pytest.mark.parametrize("cls,name,env_var,base_url,default_model,config_key", KEYED_PROVIDERS)
def test_keyed_provider_builds_client(monkeypatch, cls, name, env_var, base_url, default_model, config_key):
    monkeypatch.setenv(env_var, "secret-key")
    model = cls()
    assert model.provider_name == name
    assert model.model == default_model
    assert model.client.base_url == base_url
    assert model.client.api_key == "secret-key"


def test_missing_key_raises_config_error(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        MistralModel()


def test_model_precedence_arg_over_default(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "k")
    assert XAIModel(model_name="grok-custom").model == "grok-custom"


def test_model_precedence_config_over_default(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "k")
    monkeypatch.setattr("app.llm.base.get_config", lambda: {"xai_model": "grok-from-config"})
    assert XAIModel().model == "grok-from-config"


def test_ollama_is_keyless_and_uses_base_url_env(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    model = OllamaLocal()
    assert model.requires_key is False
    # No key required; the SDK still needs a non-empty token -> placeholder.
    assert model.client.api_key == "ollama"
    assert model.client.base_url == "http://localhost:11434/v1"
    assert model.model == "llama3.1"


def test_ollama_base_url_env_override_adds_v1_suffix(monkeypatch):
    # A user who sets the host without the /v1 suffix should still get a valid URL.
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://remote-box:11434")
    assert OllamaLocal().client.base_url == "http://remote-box:11434/v1"


def test_ollama_model_env_override(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "mistral-nemo")
    assert OllamaLocal().model == "mistral-nemo"
