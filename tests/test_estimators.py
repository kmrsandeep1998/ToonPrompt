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
