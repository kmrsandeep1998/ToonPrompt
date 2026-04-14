from __future__ import annotations

from .config import Config


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
    if not getattr(config, "otel_enabled", False):
        return
    try:
        from opentelemetry import trace  # type: ignore

        tracer = trace.get_tracer(getattr(config, "otel_service_name", "toonprompt"))
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
