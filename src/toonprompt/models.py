from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SegmentType(str, Enum):
    PLAIN = "plain"
    JSON = "json"
    YAML = "yaml"
    LOG = "log"
    STACKTRACE = "stacktrace"
    TREE = "tree"
    TABLE = "table"
    UNKNOWN = "unknown"


@dataclass
class PromptSegment:
    segment_type: SegmentType
    text: str
    source: str
    confidence: float
    parsed: object | None = None
    transformed_text: str | None = None
    reason: str | None = None


@dataclass
class PromptDocument:
    original_text: str
    segments: list[PromptSegment]


@dataclass
class SafetyDecision:
    action: str
    reason: str


@dataclass
class TransformResult:
    original_text: str
    final_text: str
    transformed: bool
    segments: list[PromptSegment]
    safety: SafetyDecision
    estimated_input_tokens: int
    estimated_output_tokens: int
    explanations: list[str] = field(default_factory=list)
