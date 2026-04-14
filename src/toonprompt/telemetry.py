from __future__ import annotations

import importlib
import threading

from .config import Config

_LOCK = threading.Lock()
_CONFIGURED_KEY: tuple[str, str] | None = None
_TRACER = None


def _get_tracer(config: Config):
    if not getattr(config, "otel_enabled", False):
        return None
    service_name = (getattr(config, "otel_service_name", "") or "toonprompt").strip() or "toonprompt"
    endpoint = (getattr(config, "otel_endpoint", "") or "").strip()
    key = (endpoint, service_name)
    global _CONFIGURED_KEY, _TRACER
    with _LOCK:
        if _TRACER is not None and _CONFIGURED_KEY == key:
            return _TRACER
        tracer = _configure_tracing(service_name=service_name, endpoint=endpoint)
        _TRACER = tracer
        _CONFIGURED_KEY = key if tracer is not None else None
        return tracer


def _configure_tracing(*, service_name: str, endpoint: str):
    try:
        trace = importlib.import_module("opentelemetry.trace")
        sdk_trace = importlib.import_module("opentelemetry.sdk.trace")
        sdk_resources = importlib.import_module("opentelemetry.sdk.resources")
    except Exception:
        return None

    provider = None
    try:
        resource = sdk_resources.Resource.create({"service.name": service_name})
        provider = sdk_trace.TracerProvider(resource=resource)
        if endpoint:
            otlp = importlib.import_module("opentelemetry.exporter.otlp.proto.http.trace_exporter")
            sdk_export = importlib.import_module("opentelemetry.sdk.trace.export")
            exporter = otlp.OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(sdk_export.BatchSpanProcessor(exporter))
        try:
            trace.set_tracer_provider(provider)
        except Exception:
            # If a global provider is already configured, keep using it.
            pass
    except Exception:
        provider = None
    try:
        return trace.get_tracer(service_name)
    except Exception:
        return None


def emit_transform_span(
    *,
    config: Config,
    tool: str,
    action: str,
    estimator: str,
    input_tokens: int,
    output_tokens: int,
    segment_type: str,
) -> None:
    tracer = _get_tracer(config)
    if tracer is None:
        return
    try:
        with tracer.start_as_current_span("toonprompt.transform") as span:
            span.set_attribute("toon.tool", tool or "unknown")
            span.set_attribute("toon.action", action)
            span.set_attribute("toon.estimator", estimator)
            span.set_attribute("toon.input_tokens", input_tokens)
            span.set_attribute("toon.output_tokens", output_tokens)
            span.set_attribute("toon.delta_tokens", output_tokens - input_tokens)
            span.set_attribute("toon.segment_type", segment_type)
            endpoint = getattr(config, "otel_endpoint", "")
            if endpoint:
                span.set_attribute("toon.otel_endpoint", endpoint)
    except Exception:
        return
