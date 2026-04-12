from __future__ import annotations

from dataclasses import replace
import time

from .config import Config
from .estimators import HeuristicTokenEstimator, TokenEstimator
from .format import supported_format
from .logging_utils import log_event, sha256_text
from .models import PromptDocument, PromptSegment, SafetyDecision, SegmentType, TransformResult
from .segment_transformers import (
    SegmentTransformer,
    SerializerTransformer,
    StackTraceTransformer,
    TreePassthroughTransformer,
    UnsupportedPassthroughTransformer,
)


class TransformationPolicy:
    def __init__(
        self,
        estimator: TokenEstimator | None = None,
        transformers: list[SegmentTransformer] | None = None,
    ) -> None:
        self.estimator = estimator or HeuristicTokenEstimator()
        self.transformers = transformers or [
            SerializerTransformer((SegmentType.JSON, SegmentType.YAML, SegmentType.LOG, SegmentType.TABLE)),
            StackTraceTransformer(),
            TreePassthroughTransformer(),
            UnsupportedPassthroughTransformer(),
        ]
        self._transformer_map = {
            segment_type: transformer
            for transformer in self.transformers
            for segment_type in transformer.segment_types
        }

    def apply(self, document: PromptDocument, config: Config) -> TransformResult:
        original_text = document.original_text
        if not supported_format(config.toon_format):
            return self._pass_through(
                document,
                f"unsupported toon_format {config.toon_format}",
                [f"Skipped rewrite because toon_format {config.toon_format} is unsupported."],
            )
        if len(original_text.encode("utf-8")) > config.limits["max_input_bytes"]:
            return self._pass_through(
                document,
                "input exceeds max_input_bytes",
                ["Skipped rewrite because input exceeded max_input_bytes."],
            )

        started = time.perf_counter()
        segments: list[PromptSegment] = []
        explanations: list[str] = []
        transformed_any = False

        for segment in document.segments:
            updated = self._transform_segment(segment, config)
            segments.append(updated)
            if updated.transformed_text is not None:
                transformed_any = True
            if updated.reason:
                explanations.append(f"{updated.segment_type.value}: {updated.reason}")
            if (time.perf_counter() - started) * 1000 > config.limits["max_transform_time_ms"]:
                return self._pass_through(document, "transform exceeded max_transform_time_ms", explanations)

        final_text = "".join(segment.transformed_text if segment.transformed_text is not None else segment.text for segment in segments)
        estimated_input_tokens = self.estimator.estimate(original_text)
        estimated_output_tokens = self.estimator.estimate(final_text)

        if transformed_any and estimated_output_tokens >= estimated_input_tokens:
            return self._pass_through(
                PromptDocument(original_text=original_text, segments=segments),
                "rewrite did not reduce estimated tokens",
                explanations + ["pass-through: rewrite did not reduce estimated tokens"],
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
        self._log_result(result, config)
        return result

    def _transform_segment(self, segment: PromptSegment, config: Config) -> PromptSegment:
        if segment.segment_type is SegmentType.PLAIN:
            return segment
        if not self._is_enabled(segment.segment_type, config):
            return replace(segment, reason="compression disabled by config; kept original")
        if segment.confidence < 0.65:
            return replace(segment, reason="confidence below threshold; kept original")
        transformer = self._transformer_map.get(segment.segment_type)
        if transformer is None:
            return replace(segment, reason="unsupported segment type; kept original")
        return transformer.transform(segment, config)

    def _pass_through(self, document: PromptDocument, reason: str, explanations: list[str]) -> TransformResult:
        estimated = self.estimator.estimate(document.original_text)
        result = TransformResult(
            original_text=document.original_text,
            final_text=document.original_text,
            transformed=False,
            segments=document.segments,
            safety=SafetyDecision("pass-through", reason),
            estimated_input_tokens=estimated,
            estimated_output_tokens=estimated,
            explanations=explanations,
        )
        return result

    def _log_result(self, result: TransformResult, config: Config) -> None:
        if config.logging != "local-minimal":
            return
        try:
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
        except OSError:
            return

    def _is_enabled(self, segment_type: SegmentType, config: Config) -> bool:
        key_by_type = {
            SegmentType.JSON: "json",
            SegmentType.YAML: "yaml",
            SegmentType.LOG: "logs",
            SegmentType.STACKTRACE: "stacktraces",
            SegmentType.TREE: "trees",
            SegmentType.TABLE: "tables",
        }
        key = key_by_type.get(segment_type)
        if key is None:
            return True
        return config.compression_rules.get(key, True)
