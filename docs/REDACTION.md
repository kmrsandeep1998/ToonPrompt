# What ToonPrompt Redacts

When `redaction = true` (default), ToonPrompt avoids persisting raw prompt content.

Redacted behavior:

- Prompt content is not written to local logs or metrics.
- Audit logs store `sha256` hashes of prompt content.

Not redacted:

- Transformation action and reason
- Estimated token counts and delta
- Timestamp, session ID, and tool identifier

To disable persistence entirely:

- Set `local_metrics_enabled = false`
- Set `audit_log_enabled = false`
