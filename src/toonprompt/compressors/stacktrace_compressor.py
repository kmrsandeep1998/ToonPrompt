from __future__ import annotations

from typing import Iterable


def _looks_like_frame(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith('File "')
        or stripped.startswith("at ")
        or stripped.startswith("frame #")
        or (".go:" in stripped and ":" in stripped)
    )


def compress_stacktrace(text: str, head: int = 3, tail: int = 3) -> tuple[str, bool]:
    lines = [line.rstrip("\n") for line in text.splitlines() if line.strip()]
    if len(lines) < 8:
        return text, False
    frame_indices = [idx for idx, line in enumerate(lines) if _looks_like_frame(line)]
    if len(frame_indices) < 6:
        return text, False
    first = frame_indices[:head]
    last = frame_indices[-tail:]
    keep = set(first + last)
    out: list[str] = []
    omitted = 0
    for idx, line in enumerate(lines):
        if idx in keep or not _looks_like_frame(line):
            if omitted:
                out.append(f"[... {omitted} frames omitted ...]")
                omitted = 0
            out.append(line)
        else:
            omitted += 1
    if omitted:
        out.append(f"[... {omitted} frames omitted ...]")
    result = "\n".join(out) + "\n"
    return result, result != text
