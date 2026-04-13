from __future__ import annotations

from toonprompt.config import Config
from toonprompt.estimators import HeuristicTokenEstimator, build_estimator


def test_heuristic_estimator_selected_explicitly() -> None:
    config = Config()
    config.token_estimator = "heuristic"
    estimator = build_estimator(config)
    assert isinstance(estimator, HeuristicTokenEstimator)
    assert estimator.name == "heuristic-char4"


def test_auto_estimator_falls_back_when_tiktoken_unavailable() -> None:
    config = Config()
    config.token_estimator = "auto"
    config.tokenizer_model = "gpt-5.3-codex"
    estimator = build_estimator(config)
    # Local test environments without tiktoken should still produce a valid estimator.
    assert estimator.estimate("hello world") > 0


def test_auto_estimator_prefers_tool_specific_backend_with_fallback() -> None:
    config = Config()
    config.token_estimator = "auto"
    config.active_adapter = "claude"
    estimator = build_estimator(config)
    assert estimator.estimate("hello world") > 0
