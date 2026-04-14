# Audit Logging

Enable audit logging:

```toml
audit_log_enabled = true
audit_log_path = ""
audit_log_max_bytes = 10485760
```

Query records:

```bash
toon audit --tail 50
toon audit --tool codex --since 2026-04 --json
```
