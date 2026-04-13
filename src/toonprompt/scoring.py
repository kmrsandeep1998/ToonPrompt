from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass
class CompressionScore:
    score: float
    segment_type: str
    confidence: float


def score_segment(text: str, segment_type: str) -> CompressionScore:
    lowered = segment_type.lower()
    if lowered == "json":
        repeats = max(0, text.count('{"') - 1)
        return CompressionScore(score=min(0.95, 0.5 + repeats * 0.03), segment_type="json", confidence=0.85)
    if lowered == "yaml":
        return CompressionScore(score=0.6, segment_type="yaml", confidence=0.75)
    if lowered == "log":
        repeated_lines = _count_repeated_lines(text)
        return CompressionScore(score=min(0.9, 0.3 + repeated_lines * 0.05), segment_type="log", confidence=0.8)
    if lowered == "stacktrace":
        frames = len([line for line in text.splitlines() if line.strip().startswith("File ") or line.strip().startswith("at ")])
        return CompressionScore(score=0.4 if frames < 6 else 0.75, segment_type="stacktrace", confidence=0.8)
    if lowered == "plain":
        return CompressionScore(score=0.05, segment_type="prose", confidence=0.9)
    return CompressionScore(score=0.2, segment_type=lowered or "mixed", confidence=0.6)


def _count_repeated_lines(text: str) -> int:
    seen: dict[str, int] = {}
    for line in text.splitlines():
        normalized = re.sub(r"\d", "0", line.strip())
        if not normalized:
            continue
        seen[normalized] = seen.get(normalized, 0) + 1
    return sum(1 for count in seen.values() if count >= 3)
