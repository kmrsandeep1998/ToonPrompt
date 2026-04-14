from __future__ import annotations

from dataclasses import replace
import time
from typing import AsyncIterator, Iterator

from .audit import write_audit_record
from .config import Config
from .compressors import compress_logs, compress_stacktrace, compress_yaml
from .estimators import TokenEstimator, build_estimator
from .format import supported_format
from .logging_utils import log_event, sanitize_prompt_for_hash, sha256_text
from .metrics import LocalMetricsStore
from .plugins import Compressor, load_config_compressors, load_entry_point_compressors
from .models import PromptDocument, PromptSegment, SafetyDecision, SegmentType, TransformResult
from .scoring import score_segment
from .segment_transformers import (
    SegmentTransformer,
    SerializerTransformer,
    StackTraceTransformer,
    TreePassthroughTransformer,
    UnsupportedPassthroughTransformer,
)
from .telemetry import emit_transform_span


class TransformationPolicy:
    def __init__(
        self,
        estimator: TokenEstimator | None = None,
        transformers: list[SegmentTransformer] | None = None,
        metrics_store: LocalMetricsStore | None = None,
    ) -> None:
        self.estimator = estimator
        self.transformers = transformers or [
            SerializerTransformer((SegmentType.JSON, SegmentType.YAML, SegmentType.LOG, SegmentType.TABLE)),
            StackTraceTransformer(),
            TreePassthroughTransformer(),
            UnsupportedPassthroughTransformer(),
        ]
        self.metrics_store = metrics_store or LocalMetricsStore()
        self._transformer_map = {
            segment_type: transformer
            for transformer in self.transformers
            for segment_type in transformer.segment_types
        }

    def apply(self, document: PromptDocument, config: Config, tool: str = "") -> TransformResult:
        active_tool = (tool or config.active_adapter or "").strip()
        config.active_adapter = active_tool
        estimator = self.estimator or build_estimator(config)
        original_text = document.original_text
        plugin_compressors = self._load_compressors(config)
        if not supported_format(config.toon_format):
            return self._pass_through(
                document,
                f"unsupported toon_format {config.toon_format}",
                [f"Skipped rewrite because toon_format {config.toon_format} is unsupported."],
                estimator=estimator,
                config=config,
                tool=active_tool,
            )
        if len(original_text.encode("utf-8")) > config.limits["max_input_bytes"]:
            return self._pass_through(
                document,
                "input exceeds max_input_bytes",
                ["Skipped rewrite because input exceeded max_input_bytes."],
                estimator=estimator,
                config=config,
                tool=active_tool,
            )

        started = time.perf_counter()
        segments: list[PromptSegment] = []
        explanations: list[str] = []
        transformed_any = False

        for segment in document.segments:
            updated = self._transform_segment(segment, config, estimator, plugin_compressors)
            segments.append(updated)
            if updated.transformed_text is not None:
                transformed_any = True
            if updated.reason:
                explanations.append(f"{updated.segment_type.value}: {updated.reason}")
            if (time.perf_counter() - started) * 1000 > config.limits["max_transform_time_ms"]:
                return self._pass_through(
                    document,
                    "transform exceeded max_transform_time_ms",
                    explanations,
                    estimator=estimator,
                    config=config,
                    tool=active_tool,
                )

        final_text = "".join(segment.transformed_text if segment.transformed_text is not None else segment.text for segment in segments)
        estimated_input_tokens = estimator.estimate(original_text)
        estimated_output_tokens = estimator.estimate(final_text)

        if transformed_any and estimated_output_tokens >= estimated_input_tokens:
            return self._pass_through(
                PromptDocument(original_text=original_text, segments=segments),
                "rewrite did not reduce estimated tokens",
                explanations + ["pass-through: rewrite did not reduce estimated tokens"],
                estimator=estimator,
                config=config,
                tool=active_tool,
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        result = TransformResult(
            original_text=original_text,
            final_text=final_text,
            transformed=transformed_any and final_text != original_text,
            segments=segments,
            safety=SafetyDecision("transformed" if transformed_any else "pass-through", "ok"),
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            estimator_name=estimator.name,
            explanations=explanations,
        )
        self._log_result(result, config)
        self._record_metrics(result, config, tool=active_tool)
        self._emit_telemetry(result, config, tool=active_tool)
        self._write_audit(result, config, tool=active_tool, duration_ms=elapsed_ms)
        return result

    async def run_async(self, document: PromptDocument, config: Config, tool: str = "") -> TransformResult:
        import asyncio

        return await asyncio.to_thread(self.apply, document, config, tool)

    def apply_stream(
        self,
        text: str,
        config: Config,
        tool: str = "",
        *,
        chunk_size: int = 8192,
    ) -> Iterator[str]:
        from .detector import build_document

        size = max(1, chunk_size)
        for chunk in _chunk_text(text, size):
            chunk_document = build_document(chunk)
            chunk_result = self.apply(chunk_document, config, tool=tool)
            yield chunk_result.final_text

    async def apply_stream_async(
        self,
        text: str,
        config: Config,
        tool: str = "",
        *,
        chunk_size: int = 8192,
    ) -> AsyncIterator[str]:
        import asyncio
        from .detector import build_document

        for chunk in _chunk_text(text, max(1, chunk_size)):
            result = await asyncio.to_thread(self.apply, build_document(chunk), config, tool)
            yield result.final_text

    def _transform_segment(
        self,
        segment: PromptSegment,
        config: Config,
        estimator: TokenEstimator,
        plugin_compressors: list[Compressor],
    ) -> PromptSegment:
        if segment.segment_type is SegmentType.PLAIN:
            return segment
        if not self._is_enabled(segment.segment_type, config):
            return replace(segment, reason="compression disabled by config; kept original")
        if segment.confidence < 0.65:
            return replace(segment, reason="confidence below threshold; kept original")
        if score_segment(segment.text, segment.segment_type.value).score < config.compression_threshold:
            return replace(segment, reason="compression score below threshold; kept original")
        custom = self._apply_custom_compressors(segment, estimator, plugin_compressors)
        if custom is not None:
            return custom
        transformer = self._transformer_map.get(segment.segment_type)
        if transformer is None:
            return replace(segment, reason="unsupported segment type; kept original")
        return transformer.transform(segment, config)

    def _pass_through(
        self,
        document: PromptDocument,
        reason: str,
        explanations: list[str],
        estimator: TokenEstimator,
        config: Config,
        tool: str,
    ) -> TransformResult:
        estimated = estimator.estimate(document.original_text)
        result = TransformResult(
            original_text=document.original_text,
            final_text=document.original_text,
            transformed=False,
            segments=document.segments,
            safety=SafetyDecision("pass-through", reason),
            estimated_input_tokens=estimated,
            estimated_output_tokens=estimated,
            estimator_name=estimator.name,
            explanations=explanations,
        )
        self._log_result(result, config)
        self._record_metrics(result, config=config, tool=tool)
        self._emit_telemetry(result, config, tool=tool)
        self._write_audit(result, config, tool=tool, duration_ms=0)
        return result

    def _log_result(self, result: TransformResult, config: Config) -> None:
        if config.logging != "local-minimal":
            return
        safe_for_hash = sanitize_prompt_for_hash(result.original_text)
        try:
            log_event(
                "transform",
                {
                    "action": result.safety.action,
                    "reason": result.safety.reason,
                    "input_tokens": result.estimated_input_tokens,
                    "output_tokens": result.estimated_output_tokens,
                    "prompt_hash": sha256_text(safe_for_hash) if config.redaction else None,
                    "segment_types": [segment.segment_type.value for segment in result.segments],
                    "transformed": result.transformed,
                },
            )
        except OSError:
            return

    def _record_metrics(self, result: TransformResult, config: Config | None, tool: str) -> None:
        if config is not None and not config.local_metrics_enabled:
            return
        try:
            self.metrics_store.record(
                transformed=result.transformed,
                input_tokens=result.estimated_input_tokens,
                output_tokens=result.estimated_output_tokens,
                reason=result.safety.reason,
                tool=tool or "unknown",
            )
        except OSError:
            return

    def _load_compressors(self, config: Config) -> list[Compressor]:
        compressors: list[Compressor] = []
        compressors.extend(_builtin_compressors())
        compressors.extend(
            load_entry_point_compressors(
                trusted_prefixes=config.trusted_plugin_prefixes,
                allow_untrusted=config.unsafe_allow_untrusted_plugins,
            )
        )
        compressors.extend(
            load_config_compressors(
                config.compressor_plugins,
                trusted_prefixes=config.trusted_plugin_prefixes,
                allow_untrusted=config.unsafe_allow_untrusted_plugins,
            )
        )
        return compressors

    def _apply_custom_compressors(
        self,
        segment: PromptSegment,
        estimator: TokenEstimator,
        compressors: list[Compressor],
    ) -> PromptSegment | None:
        for compressor in compressors:
            try:
                if not compressor.can_handle(segment.text, segment.segment_type.value):
                    continue
                candidate, changed = compressor.compress(segment.text)
            except Exception:
                continue
            if not changed:
                continue
            if estimator.estimate(candidate) >= estimator.estimate(segment.text):
                continue
            return replace(segment, transformed_text=candidate, reason=f"compressed with plugin {compressor.name}")
        return None

    def _emit_telemetry(self, result: TransformResult, config: Config, tool: str) -> None:
        segment_type = result.segments[0].segment_type.value if result.segments else "plain"
        emit_transform_span(
            config=config,
            tool=tool,
            action=result.safety.action,
            estimator=result.estimator_name,
            input_tokens=result.estimated_input_tokens,
            output_tokens=result.estimated_output_tokens,
            segment_type=segment_type,
        )

    def _write_audit(self, result: TransformResult, config: Config, tool: str, duration_ms: int) -> None:
        try:
            write_audit_record(
                config=config,
                tool=tool,
                action=result.safety.action,
                reason=result.safety.reason,
                estimator=result.estimator_name,
                input_text=result.original_text,
                input_tokens=result.estimated_input_tokens,
                output_tokens=result.estimated_output_tokens,
                duration_ms=duration_ms,
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


class _YamlCompressor:
    name = "builtin.yaml"

    def can_handle(self, text: str, segment_type: str) -> bool:
        return segment_type.lower() == SegmentType.YAML.value

    def compress(self, text: str) -> tuple[str, bool]:
        return compress_yaml(text)


class _LogCompressor:
    name = "builtin.log"

    def can_handle(self, text: str, segment_type: str) -> bool:
        return segment_type.lower() == SegmentType.LOG.value

    def compress(self, text: str) -> tuple[str, bool]:
        return compress_logs(text)


class _StacktraceCompressor:
    name = "builtin.stacktrace"

    def can_handle(self, text: str, segment_type: str) -> bool:
        return segment_type.lower() == SegmentType.STACKTRACE.value

    def compress(self, text: str) -> tuple[str, bool]:
        return compress_stacktrace(text)


def _builtin_compressors() -> list[Compressor]:
    return [_YamlCompressor(), _LogCompressor(), _StacktraceCompressor()]


def _chunk_text(text: str, chunk_size: int) -> Iterator[str]:
    if not text:
        yield ""
        return
    idx = 0
    while idx < len(text):
        end = min(len(text), idx + chunk_size)
        if end < len(text):
            split = text.rfind("\n", idx, end)
            if split > idx:
                end = split + 1
        if end <= idx:
            end = min(len(text), idx + chunk_size)
        yield text[idx:end]
        idx = end
