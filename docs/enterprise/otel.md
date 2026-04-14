# OpenTelemetry

ToonPrompt can emit a transformation span when OTel is enabled.

```toml
otel_enabled = true
otel_endpoint = "http://localhost:4317"
otel_service_name = "toonprompt"
```

Span name:

- `toonprompt.transform`

Attributes:

- `toon.tool`
- `toon.action`
- `toon.estimator`
- `toon.input_tokens`
- `toon.output_tokens`
- `toon.delta_tokens`
- `toon.segment_type`
