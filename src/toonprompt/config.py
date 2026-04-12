from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as tomllib
    except ModuleNotFoundError:  # pragma: no cover
        tomllib = None


DEFAULT_CONFIG = """mode = "structured-only"
fail_strategy = "pass-through"
preview = "on-demand"
logging = "local-minimal"
learning_explanations = true
redaction = true
toon_format = "1"

[limits]
max_input_bytes = 262144
max_transform_time_ms = 250
max_depth = 12

[tool_paths]
codex = "codex"
claude = "claude"
cursor = "cursor-agent"
gemini = "gemini"

[compression_rules]
json = true
yaml = true
logs = true
stacktraces = true
trees = true
tables = true
"""


@dataclass
class Config:
    mode: str = "structured-only"
    fail_strategy: str = "pass-through"
    preview: str = "on-demand"
    logging: str = "local-minimal"
    learning_explanations: bool = True
    redaction: bool = True
    toon_format: str = "1"
    tool_paths: dict[str, str] = field(
        default_factory=lambda: {
            "codex": "codex",
            "claude": "claude",
            "cursor": "cursor-agent",
            "gemini": "gemini",
        }
    )
    compression_rules: dict[str, bool] = field(
        default_factory=lambda: {
            "json": True,
            "yaml": True,
            "logs": True,
            "stacktraces": True,
            "trees": True,
            "tables": True,
        }
    )
    limits: dict[str, int] = field(
        default_factory=lambda: {
            "max_input_bytes": 262144,
            "max_transform_time_ms": 250,
            "max_depth": 12,
        }
    )


def default_config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "toonprompt" / "config.toml"


def default_state_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "toonprompt"


def load_config(cwd: Path | None = None) -> Config:
    config = Config()
    config_path = default_config_path()
    if config_path.exists():
        config = _merge_config(config, _loads_toml(config_path.read_text()))
    if cwd is None:
        cwd = Path.cwd()
    project_path = cwd / ".toonprompt.toml"
    if project_path.exists():
        config = _merge_config(config, _loads_toml(project_path.read_text()))
    return config


def write_default_config(target: Path | None = None) -> Path:
    if target is None:
        target = default_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(DEFAULT_CONFIG)
    return target


def _merge_config(config: Config, raw: dict) -> Config:
    for key in ("mode", "fail_strategy", "preview", "logging", "learning_explanations", "redaction", "toon_format"):
        if key in raw:
            setattr(config, key, raw[key])
    if "tool_paths" in raw:
        config.tool_paths.update(raw["tool_paths"])
    if "compression_rules" in raw:
        config.compression_rules.update(raw["compression_rules"])
    if "limits" in raw:
        config.limits.update(raw["limits"])
    return config


def _loads_toml(text: str) -> dict:
    if tomllib is not None:
        return tomllib.loads(text)
    current: dict = {}
    root: dict = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            current = root.setdefault(section, {})
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        current if current else root
        target = current if current else root
        target[key] = _parse_scalar(value)
    return root


def _parse_scalar(value: str) -> object:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value in {"true", "false"}:
        return value == "true"
    if value.isdigit():
        return int(value)
    return value
