from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import uuid

from .config import Config, default_state_dir

_SESSION_ID = str(uuid.uuid4())

try:
    from importlib.metadata import version as _pkg_version

    _VERSION = _pkg_version("toonprompt")
except Exception:  # pragma: no cover
    _VERSION = "0.0.0"


def write_audit_record(
    *,
    config: Config,
    tool: str,
    action: str,
    reason: str,
    estimator: str,
    input_text: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: int,
) -> None:
    if not config.audit_log_enabled:
        return
    path = _audit_path(config)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "version": _VERSION,
        "tool": tool or "unknown",
        "action": action,
        "reason": reason,
        "estimator": estimator,
        "input_hash": f"sha256:{hashlib.sha256(input_text.encode('utf-8')).hexdigest()}",
        "input_tokens_est": input_tokens,
        "output_tokens_est": output_tokens,
        "delta_tokens": output_tokens - input_tokens,
        "duration_ms": duration_ms,
        "session_id": _SESSION_ID,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    _rotate_if_needed(path, config.audit_log_max_bytes)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def read_audit(
    config: Config,
    *,
    tail: int | None = None,
    since_prefix: str | None = None,
    tool: str | None = None,
) -> list[dict]:
    path = _audit_path(config)
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if since_prefix:
        rows = [row for row in rows if str(row.get("ts", "")).startswith(since_prefix)]
    if tool:
        rows = [row for row in rows if row.get("tool") == tool]
    if tail is not None and tail > 0:
        rows = rows[-tail:]
    return rows


def _audit_path(config: Config) -> Path:
    if config.audit_log_path:
        return Path(config.audit_log_path)
    return default_state_dir() / "audit.jsonl"


def _rotate_if_needed(path: Path, max_bytes: int) -> None:
    if path.exists() and path.stat().st_size >= max_bytes:
        rotated = path.with_suffix(".jsonl.1")
        if rotated.exists():
            rotated.unlink()
        path.rename(rotated)
