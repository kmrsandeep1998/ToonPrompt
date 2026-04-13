from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from .config import default_state_dir


METRICS_FILENAME = "metrics.json"


@dataclass
class MetricsSummary:
    transforms_attempted: int
    transforms_applied: int
    pass_through: int
    estimated_token_delta_total: int
    pass_through_reasons: dict[str, int]


class LocalMetricsStore:
    def __init__(self, state_dir: Path | None = None) -> None:
        self.state_dir = state_dir or default_state_dir()
        self.path = self.state_dir / METRICS_FILENAME

    def record(
        self,
        transformed: bool,
        input_tokens: int,
        output_tokens: int,
        reason: str,
    ) -> None:
        payload = self._load()
        payload["transforms_attempted"] += 1
        if transformed:
            payload["transforms_applied"] += 1
            payload["estimated_token_delta_total"] += input_tokens - output_tokens
        else:
            payload["pass_through"] += 1
            payload["pass_through_reasons"][reason] = payload["pass_through_reasons"].get(reason, 0) + 1
        self._write(payload)

    def summary(self) -> MetricsSummary:
        payload = self._load()
        return MetricsSummary(
            transforms_attempted=payload["transforms_attempted"],
            transforms_applied=payload["transforms_applied"],
            pass_through=payload["pass_through"],
            estimated_token_delta_total=payload["estimated_token_delta_total"],
            pass_through_reasons=payload["pass_through_reasons"],
        )

    def _load(self) -> dict:
        if not self.path.exists():
            return {
                "transforms_attempted": 0,
                "transforms_applied": 0,
                "pass_through": 0,
                "estimated_token_delta_total": 0,
                "pass_through_reasons": {},
            }
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return {
                "transforms_attempted": 0,
                "transforms_applied": 0,
                "pass_through": 0,
                "estimated_token_delta_total": 0,
                "pass_through_reasons": {},
            }

    def _write(self, payload: dict) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True))
