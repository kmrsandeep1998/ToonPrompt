# ToonPrompt

ToonPrompt is a pip-installable wrapper for coding CLIs such as Codex, Claude, Cursor, and Gemini. It preserves natural-language instructions, detects bulky structured context like JSON, YAML, logs, stack traces, and repeated records, then compresses only those sections into a deterministic Toon-style format before forwarding the prompt to the native tool.

This repository is currently in public alpha. The packaging metadata, contribution docs, and release scaffolding are intentionally lightweight so the project can ship early without hiding the rough edges.

## At a glance

- **What it is:** a CLI + Python SDK for prompt optimization.
- **Why it exists:** to reduce structured-context token overhead without rewriting user intent.
- **How it works:** detect segment types, compress high-confidence structured parts, pass through everything else.
- **When to use it:** before sending large coding prompts containing JSON/YAML/logs/stacktraces to AI coding tools.
- **When not to use it:** if your workflow depends on full interactive terminal capture or strict byte-for-byte prompt preservation.

## Why this exists

Large coding prompts often waste context on repeated keys, punctuation, and machine-shaped payloads. ToonPrompt reduces that overhead while keeping human intent readable and leaving uncertain content unchanged.

Default behavior:

- structured-only rewriting
- fail-open pass-through on uncertainty
- local minimal logs with redacted prompt hashes
- preview on demand
- prompt-only transformation

## What ToonPrompt can do

- Run as a direct wrapper (`toon codex ...`, `toon claude ...`, etc.).
- Inspect transformations without invoking native tools (`toon inspect`).
- Enforce token budgets in CI (`toon check --max-tokens ...`).
- Track local metrics and audit records (opt-in).
- Expose a Python SDK (`ToonPrompt`) for app integration.
- Provide monorepo integration assets for Homebrew, VS Code, and GitHub Actions.

## Installation

### From GitHub

```bash
pip install git+https://github.com/kmrsandeep1998/ToonPrompt.git
```

### For development

```bash
git clone https://github.com/kmrsandeep1998/ToonPrompt.git
cd ToonPrompt
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Quick start

Inspect a prompt without calling a native CLI:

```bash
toon inspect --prompt-file prompt.txt --preview --explain
toon inspect --prompt-file prompt.txt --dry-run --diff --format markdown
```

Proxy a supported CLI:

```bash
toon codex --prompt-file prompt.txt -- --model gpt-5.4
toon codex --prompt-file prompt.txt --dry-run
printf '%s\n' '{"id":1,"name":"node"}' | toon claude --stdin -- --print
toon-cursor --prompt "Explain this stack trace" -- --help
toon aider --prompt-file prompt.txt -- --model sonnet
toon continue --prompt "Summarize this error context"
```

Initialize config:

```bash
toon config init
```

Run diagnostics:

```bash
toon doctor
```

Show local metrics (opt-in):

```bash
toon metrics
toon metrics --json
toon audit --tail 20
toon audit --tool codex --since 2026-04 --json
```

Validate prompt files against a token budget:

```bash
toon check --max-tokens 12000 prompts/*.txt
```

## When to use each command

- `toon inspect`: understand exactly what will change and why.
- `toon <tool>`: run transformed prompt through a supported CLI.
- `toon metrics` / `toon audit`: observe compression behavior over time.
- `toon check`: block oversized prompt files in pre-commit/CI pipelines.
- `toon doctor`: validate local setup and adapter availability.

## Supported prompt sources

- `--prompt` for inline text
- `--prompt-file` for file-backed prompts
- `--stdin` for piped input

Interactive keystroke capture inside terminal UIs is intentionally out of scope for v0.1.

## How transformation works

ToonPrompt builds a prompt document, classifies segments, and only rewrites supported structured sections. Plain-language instructions remain unchanged.

Example JSON input:

```json
{
  "nodes": [
    {"id": 1, "name": "Node 1"},
    {"id": 2, "name": "Node 2"}
  ]
}
```

Compressed Toon-style output:

```txt
data:
  nodes[2]{id,name}:
    1,Node 1
    2,Node 2
```

## Configuration

Global config path:

```txt
~/.config/toonprompt/config.toml
```

Project override:

```txt
.toonprompt.toml
```

Generate the default config with:

```bash
toon config init
```

Use a named profile:

```bash
toon --profile fast codex --prompt-file prompt.txt -- --model gpt-5.4
```

Token estimation modes:

- `token_estimator = "auto"`: use `tiktoken` if installed, else heuristic fallback
- `token_estimator = "heuristic"`: always use lightweight character-based estimate
- `token_estimator = "tiktoken"`: prefer tokenizer backend, fallback to heuristic if unavailable

Install tokenizer support:

```bash
pip install "toonprompt[tokenizers]"
```

## Environment overrides

ToonPrompt supports runtime overrides through `TOON_*` variables:

- `TOON_MODE`
- `TOON_FAIL_STRATEGY`
- `TOON_PREVIEW` (`always` / `on-demand` / `never`, or boolean aliases)
- `TOON_LOGGING` (`local-minimal` / `none`, or boolean aliases)
- `TOON_REDACTION`
- `TOON_FORMAT`
- `TOON_TOKEN_ESTIMATOR`
- `TOON_TOKENIZER_MODEL`
- `TOON_LOCAL_METRICS`
- `TOON_MAX_INPUT_BYTES`

Environment values override global and project config files.

## Current limitations

- best-effort parity across tools, not identical behavior
- response text is not post-processed
- interactive native TUI input is not intercepted
- Aider and Continue adapters are wrapper-mode baseline integrations

## Compatibility Matrix

| Tool | Invocation style | Prompt sources | Notes |
|---|---|---|---|
| Codex CLI | `toon codex -- ...` | `--prompt`, `--prompt-file`, `--stdin` | Best-effort wrapper around the native binary; release workflow coverage targets Python 3.9-3.12. |
| Claude CLI | `toon claude -- ...` | `--prompt`, `--prompt-file`, `--stdin` | Structured prompt compression only; no response rewriting; release workflow coverage targets Python 3.9-3.12. |
| Cursor CLI | `toon cursor -- ...` | `--prompt`, `--prompt-file`, `--stdin` | Wrapper mode only; interactive TUI keystrokes are not intercepted; release workflow coverage targets Python 3.9-3.12. |
| Gemini CLI | `toon gemini -- ...` | `--prompt`, `--prompt-file`, `--stdin` | Same baseline behavior as other adapters; release workflow coverage targets Python 3.9-3.12. |
| Aider CLI | `toon aider -- ...` | `--prompt`, `--prompt-file`, `--stdin` | Wrapper-mode integration for initial prompt compression before native execution. |
| Continue CLI | `toon continue -- ...` | `--prompt`, `--prompt-file`, `--stdin` | Wrapper-mode integration for CLI-based Continue workflows. |

## Toon Format Versioning

ToonPrompt serializes structured segments using `toon_format = "1"`. Version `1` guarantees:

- stable indentation with two-space nesting
- array headers in the form `name[count]:`
- scalar-record tables in the form `name[count]{field1,field2}:`
- escaped commas, newlines, and backslashes inside cells
- fail-open pass-through when input cannot be converted safely

Future format versions should be additive and explicitly gated by config so generated prompts remain predictable.

## Benchmarks

Sample fixtures for token-savings benchmarking live in [`benchmarks/fixtures`](./benchmarks/fixtures). They cover:

- nested JSON payloads
- repeated application logs
- mixed natural language plus structured context

Run the fixture benchmark script with:

```bash
PYTHONPATH=src python3 scripts/benchmark_fixtures.py
```

Token deltas in alpha are still **estimates** and should be interpreted as directional, not billing-accurate.

## Development

Run tests:

```bash
pytest
```

Useful repo docs:

- [Changelog](./CHANGELOG.md)
- [Contributing](./CONTRIBUTING.md)
- [Security](./SECURITY.md)
- [Releasing](./docs/RELEASING.md)
- [Operations](./docs/OPERATIONS.md)
- [Docs site config](./mkdocs.yml)

## Python SDK

```python
from toonprompt import ToonPrompt

client = ToonPrompt(profile="default")
result = client.transform('{"id":1,"name":"node"}')
print(result.output)
```

## Distribution

- PyPI package: `pip install toonprompt`
- pipx: `pipx install toonprompt`
- Dockerfile included for containerized CLI usage

## Ecosystem Starters

- Homebrew formula template: [`packaging/homebrew/Formula/toonprompt.rb`](./packaging/homebrew/Formula/toonprompt.rb)
- Homebrew tap auto-bump workflow: [`.github/workflows/homebrew-tap.yml`](./.github/workflows/homebrew-tap.yml)
- VS Code extension starter: [`integrations/vscode/toonprompt-vscode`](./integrations/vscode/toonprompt-vscode)
- GitHub Action composite check: [`.github/actions/toonprompt-check/action.yml`](./.github/actions/toonprompt-check/action.yml)
- Standalone action scaffold: [`integrations/github-action/toonprompt-check`](./integrations/github-action/toonprompt-check)
