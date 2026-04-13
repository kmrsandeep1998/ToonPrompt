from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .config import Config


class TokenEstimator(Protocol):
    def estimate(self, text: str) -> int:
        """Estimate tokens for prompt-comparison decisions."""

    @property
    def name(self) -> str:
        ...


class HeuristicTokenEstimator:
    name = "heuristic-char4"

    def estimate(self, text: str) -> int:
        if not text:
            return 0
        return max(1, (len(text) + 3) // 4)


@dataclass
class TikTokenEstimator:
    model: str
    _encoder: object
    name: str = ""

    def __post_init__(self) -> None:
        self.name = f"tiktoken:{self.model}"

    def estimate(self, text: str) -> int:
        if not text:
            return 0
        return len(self._encoder.encode(text))


def build_estimator(config: Config) -> TokenEstimator:
    preferred_tool = (config.active_adapter or "").lower()
    if config.token_estimator == "heuristic":
        return HeuristicTokenEstimator()
    if config.token_estimator == "anthropic":
        return _try_anthropic_estimator() or HeuristicTokenEstimator()
    if config.token_estimator == "google":
        return _try_google_estimator() or HeuristicTokenEstimator()
    if config.token_estimator == "tiktoken":
        estimator = _try_tiktoken_estimator(config.tokenizer_model)
        if estimator is None:
            return HeuristicTokenEstimator()
        return estimator
    if preferred_tool == "claude":
        return _try_anthropic_estimator() or _try_tiktoken_estimator(config.tokenizer_model) or HeuristicTokenEstimator()
    if preferred_tool == "gemini":
        return _try_google_estimator() or _try_tiktoken_estimator(config.tokenizer_model) or HeuristicTokenEstimator()
    if preferred_tool in {"codex", "cursor"}:
        return _try_tiktoken_estimator(config.tokenizer_model) or HeuristicTokenEstimator()
    estimator = _try_tiktoken_estimator(config.tokenizer_model)
    if estimator is not None:
        return estimator
    return HeuristicTokenEstimator()


def estimator_status(config: Config) -> str:
    estimator = build_estimator(config)
    return estimator.name


def _try_tiktoken_estimator(model: str) -> TokenEstimator | None:
    try:
        import tiktoken  # type: ignore
    except Exception:
        return None
    try:
        encoder = tiktoken.encoding_for_model(model)
    except Exception:
        try:
            encoder = tiktoken.get_encoding("cl100k_base")
            model = f"{model}/cl100k_base"
        except Exception:
            return None
    return TikTokenEstimator(model=model, _encoder=encoder)


class AnthropicTokenEstimator:
    name = "anthropic-tokenizer"

    def estimate(self, text: str) -> int:
        if not text:
            return 0
        try:
            import anthropic  # type: ignore
            if hasattr(anthropic, "count_tokens"):
                return int(anthropic.count_tokens(text))
        except Exception:
            pass
        return HeuristicTokenEstimator().estimate(text)


class GoogleTokenEstimator:
    name = "google-tokenizer"

    def estimate(self, text: str) -> int:
        if not text:
            return 0
        try:
            import google.generativeai as genai  # type: ignore
            if hasattr(genai, "count_tokens"):
                result = genai.count_tokens(text)
                total = getattr(result, "total_tokens", None)
                if isinstance(total, int):
                    return total
        except Exception:
            pass
        return HeuristicTokenEstimator().estimate(text)


def _try_anthropic_estimator() -> TokenEstimator | None:
    try:
        import anthropic  # noqa: F401  # type: ignore
    except Exception:
        return None
    return AnthropicTokenEstimator()


def _try_google_estimator() -> TokenEstimator | None:
    try:
        import google.generativeai  # noqa: F401  # type: ignore
    except Exception:
        return None
    return GoogleTokenEstimator()
