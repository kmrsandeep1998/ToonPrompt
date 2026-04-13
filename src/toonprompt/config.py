from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import sys

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
token_estimator = "auto"
tokenizer_model = "gpt-5.3-codex"
local_metrics_enabled = false
otel_enabled = false
audit_log_enabled = false
audit_log_path = ""
audit_log_max_bytes = 10485760
compression_threshold = 0.3

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

[compressors]
enabled = []
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
    token_estimator: str = "auto"
    tokenizer_model: str = "gpt-5.3-codex"
    local_metrics_enabled: bool = False
    otel_enabled: bool = False
    audit_log_enabled: bool = False
    audit_log_path: str = ""
    audit_log_max_bytes: int = 10485760
    compression_threshold: float = 0.3
    profile: str = "default"
    active_adapter: str = ""
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
    compressor_plugins: list[str] = field(default_factory=list)
    profiles: dict[str, dict] = field(default_factory=dict)


ALLOWED_ROOT_KEYS = {
    "mode",
    "fail_strategy",
    "preview",
    "logging",
    "learning_explanations",
    "redaction",
    "toon_format",
    "token_estimator",
    "tokenizer_model",
    "local_metrics_enabled",
    "otel_enabled",
    "audit_log_enabled",
    "audit_log_path",
    "audit_log_max_bytes",
    "compression_threshold",
    "tool_paths",
    "compression_rules",
    "limits",
    "compressors",
    "profile",
}

ALLOWED_SECTION_KEYS = {
    "tool_paths": {"codex", "claude", "cursor", "gemini"},
    "compression_rules": {"json", "yaml", "logs", "stacktraces", "trees", "tables"},
    "limits": {"max_input_bytes", "max_transform_time_ms", "max_depth"},
}

_BOOL_TRUE = {"1", "true", "yes", "on"}
_BOOL_FALSE = {"0", "false", "no", "off"}


def default_config_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return Path(base) / "toonprompt" / "config.toml"


def default_state_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
    return Path(base) / "toonprompt"


def load_config(cwd: Path | None = None, profile: str | None = None) -> Config:
    config = Config()
    config_path = default_config_path()
    if config_path.exists():
        config = _merge_config(config, _loads_toml(config_path.read_text(), source=str(config_path)))
    if cwd is None:
        cwd = Path.cwd()
    project_path = cwd / ".toonprompt.toml"
    if project_path.exists():
        config = _merge_config(config, _loads_toml(project_path.read_text(), source=str(project_path)))
    requested_profile = profile or os.environ.get("TOON_PROFILE", "default")
    config = _apply_profile(config, requested_profile)
    config = apply_env_overrides(config)
    return validate_config(config)


def write_default_config(target: Path | None = None) -> Path:
    if target is None:
        target = default_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(DEFAULT_CONFIG)
    return target


def apply_env_overrides(config: Config) -> Config:
    mapping = {
        "TOON_MODE": ("mode", str),
        "TOON_FAIL_STRATEGY": ("fail_strategy", str),
        "TOON_PREVIEW": ("preview", _parse_preview),
        "TOON_LOGGING": ("logging", _parse_logging),
        "TOON_REDACTION": ("redaction", _parse_bool),
        "TOON_FORMAT": ("toon_format", str),
        "TOON_TOKEN_ESTIMATOR": ("token_estimator", str),
        "TOON_TOKENIZER_MODEL": ("tokenizer_model", str),
        "TOON_LOCAL_METRICS": ("local_metrics_enabled", _parse_bool),
        "TOON_OTEL_ENABLED": ("otel_enabled", _parse_bool),
    }
    for env_key, (field_name, coerce) in mapping.items():
        raw = os.environ.get(env_key)
        if raw is None:
            continue
        try:
            setattr(config, field_name, coerce(raw))
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"{env_key}={raw!r}: {exc}") from exc
    max_input = os.environ.get("TOON_MAX_INPUT_BYTES")
    if max_input is not None:
        try:
            config.limits["max_input_bytes"] = int(max_input)
        except ValueError as exc:
            raise ConfigError(f"TOON_MAX_INPUT_BYTES={max_input!r}: must be an integer") from exc
    return config


def _merge_config(config: Config, raw: dict) -> Config:
    unknown_root = set(raw) - ALLOWED_ROOT_KEYS
    if unknown_root:
        messages = []
        for key in sorted(unknown_root):
            suggestion = _suggest_key(key, ALLOWED_ROOT_KEYS)
            hint = f" — did you mean '{suggestion}'?" if suggestion else ""
            messages.append(f"unknown config key: '{key}'{hint}")
        raise ConfigError("; ".join(messages))

    for key in (
        "mode",
        "fail_strategy",
        "preview",
        "logging",
        "learning_explanations",
        "redaction",
        "toon_format",
        "token_estimator",
        "tokenizer_model",
        "local_metrics_enabled",
        "otel_enabled",
        "audit_log_enabled",
        "audit_log_path",
        "audit_log_max_bytes",
        "compression_threshold",
    ):
        if key in raw:
            setattr(config, key, raw[key])

    if "profile" in raw:
        profile_raw = raw["profile"]
        if not isinstance(profile_raw, dict):
            raise ConfigError("[profile] must be a table of named profiles")
        for name, payload in profile_raw.items():
            if not isinstance(payload, dict):
                raise ConfigError(f"profile '{name}' must be a table")
            config.profiles[str(name)] = payload

    if "tool_paths" in raw:
        _check_section_keys("tool_paths", raw["tool_paths"])
        config.tool_paths.update(raw["tool_paths"])

    if "compression_rules" in raw:
        _check_section_keys("compression_rules", raw["compression_rules"])
        config.compression_rules.update(raw["compression_rules"])

    if "limits" in raw:
        _check_section_keys("limits", raw["limits"])
        config.limits.update(raw["limits"])

    if "compressors" in raw:
        compressors = raw["compressors"]
        if not isinstance(compressors, dict):
            raise ConfigError("[compressors] must be a table")
        enabled = compressors.get("enabled", [])
        if not isinstance(enabled, list) or not all(isinstance(item, str) for item in enabled):
            raise ConfigError("compressors.enabled must be a list of 'module:ClassName' strings")
        config.compressor_plugins = enabled

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
    if not isinstance(config.local_metrics_enabled, bool):
        raise ConfigError("local_metrics_enabled must be a boolean")
    if not isinstance(config.otel_enabled, bool):
        raise ConfigError("otel_enabled must be a boolean")
    if not isinstance(config.audit_log_enabled, bool):
        raise ConfigError("audit_log_enabled must be a boolean")
    if not isinstance(config.audit_log_path, str):
        raise ConfigError("audit_log_path must be a string")
    if not isinstance(config.audit_log_max_bytes, int) or config.audit_log_max_bytes <= 0:
        raise ConfigError("audit_log_max_bytes must be a positive integer")
    if not supported_format(config.toon_format):
        raise ConfigError(f"unsupported toon_format {config.toon_format}")
    if not isinstance(config.token_estimator, str):
        raise ConfigError("token_estimator must be a string")
    if config.token_estimator not in {"auto", "heuristic", "tiktoken", "anthropic", "google"}:
        raise ConfigError("token_estimator must be one of: auto, heuristic, tiktoken, anthropic, google")
    if not isinstance(config.tokenizer_model, str) or not config.tokenizer_model.strip():
        raise ConfigError("tokenizer_model must be a non-empty string")
    if not isinstance(config.compression_threshold, (int, float)) or not (0 <= float(config.compression_threshold) <= 1):
        raise ConfigError("compression_threshold must be between 0 and 1")
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
            parts = line[1:-1].split(".")
            current = root
            for part in parts:
                current = current.setdefault(part, {})
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        target = current if current else root
        target[key] = _parse_scalar(value)
    return root


def _parse_scalar(value: str) -> object:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith("[") and value.endswith("]"):
        raw_items = value[1:-1].strip()
        if not raw_items:
            return []
        return [item.strip().strip('"') for item in raw_items.split(",")]
    if value.isdigit():
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value


def _check_section_keys(section: str, raw: dict) -> None:
    unknown = set(raw) - ALLOWED_SECTION_KEYS[section]
    if unknown:
        raise ConfigError(f"unknown keys in [{section}]: {', '.join(sorted(unknown))}")


def _parse_bool(val: str) -> bool:
    lowered = val.lower()
    if lowered in _BOOL_TRUE:
        return True
    if lowered in _BOOL_FALSE:
        return False
    raise ValueError(f"expected boolean string, got {val!r}")


def _parse_preview(val: str) -> str:
    lowered = val.lower()
    if lowered in _BOOL_TRUE:
        return "always"
    if lowered in _BOOL_FALSE:
        return "never"
    if lowered in {"on-demand", "always", "never"}:
        return lowered
    raise ValueError(f"expected one of on-demand/always/never or a boolean value, got {val!r}")


def _parse_logging(val: str) -> str:
    lowered = val.lower()
    if lowered in _BOOL_TRUE:
        return "local-minimal"
    if lowered in _BOOL_FALSE:
        return "none"
    if lowered in {"local-minimal", "none"}:
        return lowered
    raise ValueError(f"expected one of local-minimal/none or a boolean value, got {val!r}")


def _apply_profile(config: Config, profile: str) -> Config:
    config.profile = profile
    if profile == "default":
        return config
    raw = config.profiles.get(profile)
    if raw is None:
        raise ConfigError(f"unknown profile '{profile}'")
    return _merge_config(config, raw)


def _suggest_key(bad_key: str, valid_keys: set[str]) -> str | None:
    def _edit_dist(a: str, b: str) -> int:
        m, n = len(a), len(b)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[:]
            dp[0] = i
            for j in range(1, n + 1):
                if a[i - 1] == b[j - 1]:
                    dp[j] = prev[j - 1]
                else:
                    dp[j] = 1 + min(prev[j], dp[j - 1], prev[j - 1])
        return dp[n]

    candidates = [(key, _edit_dist(bad_key, key)) for key in valid_keys]
    best_key, best_dist = min(candidates, key=lambda item: item[1])
    return best_key if best_dist <= 2 else None
