from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from .config import Config
from .models import PromptSegment, SegmentType
from .serializer import to_toon


class SegmentTransformer(Protocol):
    segment_types: tuple[SegmentType, ...]

    def transform(self, segment: PromptSegment, config: Config) -> PromptSegment:
        ...


class SerializerTransformer:
    def __init__(self, segment_types: tuple[SegmentType, ...], root_name: str = "data") -> None:
        self.segment_types = segment_types
        self.root_name = root_name

    def transform(self, segment: PromptSegment, config: Config) -> PromptSegment:
        return replace(
            segment,
            transformed_text=to_toon(segment.parsed, name=self.root_name, max_depth=config.limits["max_depth"]) + "\n",
            reason=f"compressed {segment.segment_type.value} into Toon format",
        )


class StackTraceTransformer:
    segment_types = (SegmentType.STACKTRACE,)

    def transform(self, segment: PromptSegment, config: Config) -> PromptSegment:
        return replace(
            segment,
            transformed_text=to_toon({"stack": segment.parsed["lines"]}, name="trace", max_depth=config.limits["max_depth"]) + "\n",
            reason="compressed stack trace into Toon format",
        )


class TreePassthroughTransformer:
    segment_types = (SegmentType.TREE,)

    def transform(self, segment: PromptSegment, config: Config) -> PromptSegment:
        return replace(segment, reason="tree-like input already compact; kept original")


class UnsupportedPassthroughTransformer:
    segment_types = (SegmentType.UNKNOWN,)

    def transform(self, segment: PromptSegment, config: Config) -> PromptSegment:
        return replace(segment, reason="unsupported segment type; kept original")
