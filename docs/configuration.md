# Configuration

Global config path:

- Linux/macOS: `~/.config/toonprompt/config.toml`
- Windows: `%APPDATA%\toonprompt\config.toml`

Project override:

- `.toonprompt.toml` in the working directory

Named profiles:

```toml
[profile.default]
token_estimator = "auto"

[profile.aggressive]
token_estimator = "tiktoken"
compression_threshold = 0.2
```

Use with:

```bash
toon --profile aggressive inspect --prompt-file prompt.txt
```
