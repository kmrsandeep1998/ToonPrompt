from __future__ import annotations


class ToonPromptError(Exception):
    """Base user-facing error for ToonPrompt."""


class ConfigError(ToonPromptError):
    """Raised when ToonPrompt configuration is invalid."""


class PromptInputError(ToonPromptError):
    """Raised when prompt sources are invalid or unreadable."""


class AdapterExecutionError(ToonPromptError):
    """Raised when a native tool cannot be executed."""
