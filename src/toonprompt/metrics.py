from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json

from .config import default_state_dir
from .errors import ConfigError


METRICS_FILENAME = "metrics.json"


@dataclass
class MetricsSummary:
    transforms_attempted: int
    transforms_applied: int
    pass_through: int
    estimated_token_delta_total: int
    pass_through_reasons: dict[str, int]
    by_tool: dict[str, dict[str, int]]
    daily: dict[str, dict[str, int]]


class LocalMetricsStore:
    def __init__(self, state_dir: Path | None = None) -> None:
        self.state_dir = state_dir or default_state_dir()
        self.path = _safe_metrics_path(self.state_dir / METRICS_FILENAME)

    def record(
        self,
        transformed: bool,
        input_tokens: int,
        output_tokens: int,
        reason: str,
        tool: str = "unknown",
        ts: datetime | None = None,
    ) -> None:
        payload = self._load()
        safe_tool = tool.strip() if isinstance(tool, str) and tool.strip() else "unknown"
        date_key = (ts or datetime.now(timezone.utc)).date().isoformat()
        delta = input_tokens - output_tokens

        payload["transforms_attempted"] += 1
        _ensure_counter_block(payload["by_tool"], safe_tool)
        _ensure_counter_block(payload["daily"], date_key)
        payload["by_tool"][safe_tool]["attempted"] += 1
        payload["daily"][date_key]["attempted"] += 1

        if transformed:
            payload["transforms_applied"] += 1
            payload["estimated_token_delta_total"] += delta
            payload["by_tool"][safe_tool]["applied"] += 1
            payload["by_tool"][safe_tool]["delta"] += delta
            payload["daily"][date_key]["applied"] += 1
            payload["daily"][date_key]["delta"] += delta
        else:
            payload["pass_through"] += 1
            payload["by_tool"][safe_tool]["pass_through"] += 1
            payload["daily"][date_key]["pass_through"] += 1
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
            by_tool=payload["by_tool"],
            daily=payload["daily"],
        )

    def _load(self) -> dict:
        if not self.path.exists():
            return self._empty_payload()
        try:
            payload = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return self._empty_payload()
        return self._normalize_payload(payload)

    def _write(self, payload: dict) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def _empty_payload(self) -> dict:
        return {
            "schema_version": 2,
            "transforms_attempted": 0,
            "transforms_applied": 0,
            "pass_through": 0,
            "estimated_token_delta_total": 0,
            "pass_through_reasons": {},
            "by_tool": {},
            "daily": {},
        }

    def _normalize_payload(self, payload: object) -> dict:
        if not isinstance(payload, dict):
            return self._empty_payload()
        normalized = self._empty_payload()
        for key in ("transforms_attempted", "transforms_applied", "pass_through", "estimated_token_delta_total"):
            value = payload.get(key)
            if isinstance(value, int) and value >= 0:
                normalized[key] = value
        reasons = payload.get("pass_through_reasons")
        if isinstance(reasons, dict):
            safe_reasons: dict[str, int] = {}
            for reason, count in reasons.items():
                if isinstance(reason, str) and isinstance(count, int) and count >= 0:
                    safe_reasons[reason] = count
            normalized["pass_through_reasons"] = safe_reasons
        by_tool = payload.get("by_tool")
        if isinstance(by_tool, dict):
            normalized["by_tool"] = _normalize_counter_map(by_tool)
        daily = payload.get("daily")
        if isinstance(daily, dict):
            normalized["daily"] = _normalize_counter_map(daily)
        return normalized


def _normalize_counter_map(raw: dict[object, object]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        attempted = value.get("attempted")
        applied = value.get("applied")
        pass_through = value.get("pass_through")
        delta = value.get("delta")
        if not all(isinstance(item, int) for item in (attempted, applied, pass_through, delta)):
            continue
        if attempted < 0 or applied < 0 or pass_through < 0:
            continue
        out[key] = {
            "attempted": attempted,
            "applied": applied,
            "pass_through": pass_through,
            "delta": delta,
        }
    return out


def _ensure_counter_block(container: dict[str, dict[str, int]], key: str) -> None:
    current = container.get(key)
    if isinstance(current, dict):
        needed = {"attempted", "applied", "pass_through", "delta"}
        if needed.issubset(current) and all(isinstance(current[field], int) for field in needed):
            return
    container[key] = {"attempted": 0, "applied": 0, "pass_through": 0, "delta": 0}


def _safe_metrics_path(path: Path) -> Path:
    try:
        resolved = path.expanduser().resolve()
    except OSError as exc:
        raise ConfigError(f"invalid metrics path {path!s}: {exc}") from exc
    home = Path.home().resolve()
    allow_prefixes = [home, Path("/tmp"), Path("/private/var")]
    if not any(_is_within(resolved, base) for base in allow_prefixes):
        raise ConfigError(f"metrics path {path!s} must be within user-writable safe directories")
    return resolved


def _is_within(target: Path, base: Path) -> bool:
    try:
        target.relative_to(base.resolve())
        return True
    except ValueError:
        return False
