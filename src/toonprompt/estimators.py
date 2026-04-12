from __future__ import annotations

from typing import Protocol


class TokenEstimator(Protocol):
    def estimate(self, text: str) -> int:
        """Estimate tokens for prompt-comparison decisions."""


class HeuristicTokenEstimator:
    def estimate(self, text: str) -> int:
        if not text:
            return 0
        return max(1, (len(text) + 3) // 4)
