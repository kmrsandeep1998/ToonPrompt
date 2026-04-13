from __future__ import annotations

import re

TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\s*"
    r"|^\[\d+\]\s*"
    r"|^\d{2}/\w+/\d{4}[: ]"
)
MIN_RUN = 3


def _normalize(line: str) -> str:
    return TIMESTAMP_RE.sub("", line).strip()


def compress_logs(text: str) -> tuple[str, bool]:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < MIN_RUN:
        return text, False
    out: list[str] = []
    i = 0
    compressed = False
    while i < len(lines):
        base = lines[i]
        base_norm = _normalize(base)
        j = i + 1
        while j < len(lines) and _normalize(lines[j]) == base_norm:
            j += 1
        run = j - i
        if run >= MIN_RUN:
            out.append(f"[×{run}] {base_norm}")
            compressed = True
        else:
            out.extend(lines[i:j])
        i = j
    if not compressed:
        return text, False
    return "\n".join(out) + "\n", True
