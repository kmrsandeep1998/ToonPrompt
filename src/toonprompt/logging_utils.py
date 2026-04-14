from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re

from .config import default_state_dir


def log_event(event_type: str, payload: dict) -> Path:
    state_dir = default_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "events.jsonl"
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        **payload,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return path


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_ENV_ASSIGNMENT_PATTERN = re.compile(
    r"(?P<prefix>\b(?:export\s+)?)"
    r"(?P<key>[A-Z][A-Z0-9_]{1,63})"
    r"\s*=\s*"
    r'(?P<value>"[^"]*"|\'[^\']*\'|[^\s]+)'
)


def sanitize_prompt_for_hash(text: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        return f"{match.group('prefix')}{match.group('key')}=***"

    return _ENV_ASSIGNMENT_PATTERN.sub(_replace, text)
