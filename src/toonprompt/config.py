from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os

from .errors import ConfigError
from .format import supported_format
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


ALLOWED_ROOT_KEYS = {
    "mode",
    "fail_strategy",
    "preview",
    "logging",
    "learning_explanations",
    "redaction",
    "toon_format",
    "tool_paths",
    "compression_rules",
    "limits",
}
ALLOWED_SECTION_KEYS = {
    "tool_paths": {"codex", "claude", "cursor", "gemini"},
    "compression_rules": {"json", "yaml", "logs", "stacktraces", "trees", "tables"},
    "limits": {"max_input_bytes", "max_transform_time_ms", "max_depth"},
}


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
        config = _merge_config(config, _loads_toml(config_path.read_text(), source=str(config_path)))
    if cwd is None:
        cwd = Path.cwd()
    project_path = cwd / ".toonprompt.toml"
    if project_path.exists():
        config = _merge_config(config, _loads_toml(project_path.read_text(), source=str(project_path)))
    return validate_config(config)


def write_default_config(target: Path | None = None) -> Path:
    if target is None:
        target = default_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(DEFAULT_CONFIG)
    return target


def _merge_config(config: Config, raw: dict) -> Config:
    unknown_root = set(raw) - ALLOWED_ROOT_KEYS
    if unknown_root:
        raise ConfigError(f"unknown config keys: {', '.join(sorted(unknown_root))}")
    for key in ("mode", "fail_strategy", "preview", "logging", "learning_explanations", "redaction", "toon_format"):
        if key in raw:
            setattr(config, key, raw[key])
    if "tool_paths" in raw:
        _check_section_keys("tool_paths", raw["tool_paths"])
        config.tool_paths.update(raw["tool_paths"])
    if "compression_rules" in raw:
        _check_section_keys("compression_rules", raw["compression_rules"])
        config.compression_rules.update(raw["compression_rules"])
    if "limits" in raw:
        _check_section_keys("limits", raw["limits"])
        config.limits.update(raw["limits"])
    return config


def validate_config(config: Config) -> Config:
    if config.mode != "structured-only":
        raise ConfigError("mode must be 'structured-only'")
    if config.fail_strategy != "pass-through":
        raise ConfigError("fail_strategy must be 'pass-through'")
    if config.preview not in {"on-demand", "always", "never"}:
        raise ConfigError("preview must be one of: on-demand, always, never")
    if config.logging not in {"local-minimal", "none"}:
        raise ConfigError("logging must be one of: local-minimal, none")
    if not isinstance(config.learning_explanations, bool):
        raise ConfigError("learning_explanations must be a boolean")
    if not isinstance(config.redaction, bool):
        raise ConfigError("redaction must be a boolean")
    if not supported_format(config.toon_format):
        raise ConfigError(f"unsupported toon_format {config.toon_format}")
    for key, value in config.tool_paths.items():
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"tool_paths.{key} must be a non-empty string")
    for key, value in config.compression_rules.items():
        if not isinstance(value, bool):
            raise ConfigError(f"compression_rules.{key} must be a boolean")
    for key, value in config.limits.items():
        if not isinstance(value, int) or value <= 0:
            raise ConfigError(f"limits.{key} must be a positive integer")
    return config


def _loads_toml(text: str, source: str) -> dict:
    if tomllib is not None:
        try:
            return tomllib.loads(text)
        except Exception as exc:  # pragma: no cover
            raise ConfigError(f"invalid TOML in {source}: {exc}") from exc
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


def _check_section_keys(section: str, raw: dict) -> None:
    unknown = set(raw) - ALLOWED_SECTION_KEYS[section]
    if unknown:
        raise ConfigError(f"unknown keys in [{section}]: {', '.join(sorted(unknown))}")
