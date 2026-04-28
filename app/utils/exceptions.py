class ResumeForgeError(Exception):
    """Base application exception."""


class ConfigError(ResumeForgeError):
    """Raised for missing or invalid configuration."""


class LLMError(ResumeForgeError):
    """Raised when an LLM provider call fails."""


class RateLimitError(LLMError):
    """Raised when a provider rate limits requests."""

