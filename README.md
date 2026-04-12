# ToonPrompt

ToonPrompt is a pip-installable wrapper for coding CLIs such as Codex, Claude, Cursor, and Gemini. It preserves natural-language instructions, detects bulky structured context like JSON, YAML, logs, stack traces, and repeated records, then compresses only those sections into a deterministic Toon-style format before forwarding the prompt to the native tool.

## Why this exists

Large coding prompts often waste context on repeated keys, punctuation, and machine-shaped payloads. ToonPrompt reduces that overhead while keeping human intent readable and leaving uncertain content unchanged.

Default behavior:

- structured-only rewriting
- fail-open pass-through on uncertainty
- local minimal logs with redacted prompt hashes
- preview on demand
- prompt-only transformation

## Installation

### From GitHub

```bash
pip install git+https://github.com/kmrsandeep1998/ToonPrompt.git
```

### For development

```bash
git clone https://github.com/kmrsandeep1998/ToonPrompt.git
cd toonCli
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Quick start

Inspect a prompt without calling a native CLI:

```bash
toon inspect --prompt-file prompt.txt --preview --explain
```

Proxy a supported CLI:

```bash
toon codex --prompt-file prompt.txt -- --model gpt-5.4
printf '%s\n' '{"id":1,"name":"node"}' | toon claude --stdin -- --print
toon-cursor --prompt "Explain this stack trace" -- --help
```

Initialize config:

```bash
toon config init
```

Run diagnostics:

```bash
toon doctor
```

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

## Current limitations

- best-effort parity across tools, not identical behavior
- response text is not post-processed
- interactive native TUI input is not intercepted
- Windows support is deferred

## Compatibility Matrix

| Tool | Invocation style | Prompt sources | Notes |
|---|---|---|---|
| Codex CLI | `toon codex -- ...` | `--prompt`, `--prompt-file`, `--stdin` | Best-effort wrapper around the native binary. |
| Claude CLI | `toon claude -- ...` | `--prompt`, `--prompt-file`, `--stdin` | Structured prompt compression only; no response rewriting. |
| Cursor CLI | `toon cursor -- ...` | `--prompt`, `--prompt-file`, `--stdin` | Wrapper mode only; interactive TUI keystrokes are not intercepted. |
| Gemini CLI | `toon gemini -- ...` | `--prompt`, `--prompt-file`, `--stdin` | Same baseline behavior as other adapters. |

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

## Development

Run tests:

```bash
pytest
```
