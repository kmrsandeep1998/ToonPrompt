# Profiles

Profiles let you switch ToonPrompt behavior by context.

Example:

```toml
[profile.default]
token_estimator = "auto"

[profile.work]
token_estimator = "tiktoken"
local_metrics_enabled = true

[profile.readonly]
preview = "always"
```

Use:

```bash
toon --profile work codex --prompt-file prompt.txt -- --model gpt-5.4
```

You can also set:

```bash
export TOON_PROFILE=work
```
