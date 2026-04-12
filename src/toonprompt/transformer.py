from __future__ import annotations

from dataclasses import replace
import time

from .config import Config
from .format import supported_format
from .logging_utils import log_event, sha256_text
from .models import PromptDocument, PromptSegment, SafetyDecision, SegmentType, TransformResult
from .serializer import to_toon


def transform_document(document: PromptDocument, config: Config) -> TransformResult:
    original_text = document.original_text
    if not supported_format(config.toon_format):
        return TransformResult(
            original_text=original_text,
            final_text=original_text,
            transformed=False,
            segments=document.segments,
            safety=SafetyDecision("pass-through", f"unsupported toon_format {config.toon_format}"),
            estimated_input_tokens=_estimate_tokens(original_text),
            estimated_output_tokens=_estimate_tokens(original_text),
            explanations=[f"Skipped rewrite because toon_format {config.toon_format} is unsupported."],
        )
    if len(original_text.encode("utf-8")) > config.limits["max_input_bytes"]:
        return TransformResult(
            original_text=original_text,
            final_text=original_text,
            transformed=False,
            segments=document.segments,
            safety=SafetyDecision("pass-through", "input exceeds max_input_bytes"),
            estimated_input_tokens=_estimate_tokens(original_text),
            estimated_output_tokens=_estimate_tokens(original_text),
            explanations=["Skipped rewrite because input exceeded max_input_bytes."],
        )

    started = time.perf_counter()
    segments: list[PromptSegment] = []
    explanations: list[str] = []
    transformed_any = False

    for segment in document.segments:
        updated = _transform_segment(segment, config)
        segments.append(updated)
        if updated.transformed_text is not None:
            transformed_any = True
            explanations.append(f"{updated.segment_type.value}: {updated.reason}")
        elif updated.reason:
            explanations.append(f"{updated.segment_type.value}: {updated.reason}")
        if (time.perf_counter() - started) * 1000 > config.limits["max_transform_time_ms"]:
            return _pass_through(document, "transform exceeded max_transform_time_ms", explanations)

    final_text = "".join(segment.transformed_text if segment.transformed_text is not None else segment.text for segment in segments)
    estimated_input_tokens = _estimate_tokens(original_text)
    estimated_output_tokens = _estimate_tokens(final_text)
    if transformed_any and estimated_output_tokens >= estimated_input_tokens:
        return TransformResult(
            original_text=original_text,
            final_text=original_text,
            transformed=False,
            segments=segments,
            safety=SafetyDecision("pass-through", "rewrite did not reduce estimated tokens"),
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_input_tokens,
            explanations=explanations + ["pass-through: rewrite did not reduce estimated tokens"],
        )
    result = TransformResult(
        original_text=original_text,
        final_text=final_text,
        transformed=transformed_any and final_text != original_text,
        segments=segments,
        safety=SafetyDecision("transformed" if transformed_any else "pass-through", "ok"),
        estimated_input_tokens=estimated_input_tokens,
        estimated_output_tokens=estimated_output_tokens,
        explanations=explanations,
    )
    _log_result(result, config)
    return result


def _transform_segment(segment: PromptSegment, config: Config) -> PromptSegment:
    if segment.segment_type is SegmentType.PLAIN:
        return segment
    if segment.confidence < 0.65:
        return replace(segment, reason="confidence below threshold; kept original")
    if segment.segment_type in {SegmentType.JSON, SegmentType.YAML, SegmentType.LOG, SegmentType.TABLE}:
        return replace(
            segment,
            transformed_text=to_toon(segment.parsed, name="data", max_depth=config.limits["max_depth"]) + "\n",
            reason=f"compressed {segment.segment_type.value} into Toon format",
        )
    if segment.segment_type is SegmentType.STACKTRACE:
        return replace(
            segment,
            transformed_text=to_toon({"stack": segment.parsed["lines"]}, name="trace", max_depth=config.limits["max_depth"]) + "\n",
            reason="compressed stack trace into Toon format",
        )
    if segment.segment_type is SegmentType.TREE:
        return replace(segment, reason="tree-like input already compact; kept original")
    return replace(segment, reason="unsupported segment type; kept original")


def _pass_through(document: PromptDocument, reason: str, explanations: list[str]) -> TransformResult:
    return TransformResult(
        original_text=document.original_text,
        final_text=document.original_text,
        transformed=False,
        segments=document.segments,
        safety=SafetyDecision("pass-through", reason),
        estimated_input_tokens=_estimate_tokens(document.original_text),
        estimated_output_tokens=_estimate_tokens(document.original_text),
        explanations=explanations + [f"pass-through: {reason}"],
    )


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _log_result(result: TransformResult, config: Config) -> None:
    if config.logging != "local-minimal":
        return
    log_event(
        "transform",
        {
            "action": result.safety.action,
            "reason": result.safety.reason,
            "input_tokens": result.estimated_input_tokens,
            "output_tokens": result.estimated_output_tokens,
            "prompt_hash": sha256_text(result.original_text) if config.redaction else None,
            "segment_types": [segment.segment_type.value for segment in result.segments],
            "transformed": result.transformed,
        },
    )
