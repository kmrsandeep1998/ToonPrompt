from __future__ import annotations

from pathlib import Path

import pytest

from toonprompt.config import Config, load_config, validate_config
from toonprompt.errors import ConfigError


def _set_config_env(monkeypatch: pytest.MonkeyPatch, config_home: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("APPDATA", str(config_home))


def test_validate_config_rejects_invalid_limit() -> None:
    config = Config()
    config.limits["max_depth"] = 0
    with pytest.raises(ConfigError, match="limits.max_depth"):
        validate_config(config)


def test_project_config_overrides_global_and_is_valid(monkeypatch, tmp_path: Path) -> None:
    global_dir = tmp_path / "global"
    project_dir = tmp_path / "project"
    global_file = global_dir / "toonprompt" / "config.toml"
    project_file = project_dir / ".toonprompt.toml"
    global_file.parent.mkdir(parents=True)
    project_dir.mkdir()
    global_file.write_text('[tool_paths]\ncodex = "/global/codex"\n')
    project_file.write_text('[tool_paths]\ncodex = "/project/codex"\n')
    _set_config_env(monkeypatch, global_dir)
    config = load_config(cwd=project_dir)
    assert config.tool_paths["codex"] == "/project/codex"


def test_unknown_key_raises_config_error(monkeypatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    target = config_dir / "toonprompt" / "config.toml"
    target.parent.mkdir(parents=True)
    target.write_text('mystery = "value"\n')
    _set_config_env(monkeypatch, config_dir)
    with pytest.raises(ConfigError, match="unknown config key"):
        load_config(cwd=tmp_path)


def test_invalid_token_estimator_raises_config_error(monkeypatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    target = config_dir / "toonprompt" / "config.toml"
    target.parent.mkdir(parents=True)
    target.write_text('token_estimator = "bad-mode"\n')
    _set_config_env(monkeypatch, config_dir)
    with pytest.raises(ConfigError, match="token_estimator"):
        load_config(cwd=tmp_path)


def test_non_string_token_estimator_raises_config_error(monkeypatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    target = config_dir / "toonprompt" / "config.toml"
    target.parent.mkdir(parents=True)
    target.write_text("token_estimator = [\"auto\"]\n")
    _set_config_env(monkeypatch, config_dir)
    with pytest.raises(ConfigError, match="token_estimator must be a string"):
        load_config(cwd=tmp_path)


def test_env_override_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TOON_MODE", "structured-only")
    config = load_config(cwd=tmp_path)
    assert config.mode == "structured-only"


def test_env_override_preview_bool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TOON_PREVIEW", "yes")
    config = load_config(cwd=tmp_path)
    assert config.preview == "always"


def test_env_override_invalid_preview(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TOON_PREVIEW", "maybe")
    with pytest.raises(ConfigError, match="TOON_PREVIEW"):
        load_config(cwd=tmp_path)


def test_env_override_max_input_bytes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TOON_MAX_INPUT_BYTES", "1024")
    config = load_config(cwd=tmp_path)
    assert config.limits["max_input_bytes"] == 1024


def test_profile_section_applies_named_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    target = config_dir / "toonprompt" / "config.toml"
    target.parent.mkdir(parents=True)
    target.write_text(
        "\n".join(
            [
                "[profile.fast]",
                'token_estimator = "heuristic"',
            ]
        )
    )
    _set_config_env(monkeypatch, config_dir)
    config = load_config(cwd=tmp_path, profile="fast")
    assert config.profile == "fast"
    assert config.token_estimator == "heuristic"


def test_compressor_trust_config_is_loaded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    target = config_dir / "toonprompt" / "config.toml"
    target.parent.mkdir(parents=True)
    target.write_text(
        "\n".join(
            [
                "[compressors]",
                'enabled = ["example.plugins:Compressor"]',
                'trusted_prefixes = ["example.plugins"]',
                "allow_untrusted = true",
            ]
        )
    )
    _set_config_env(monkeypatch, config_dir)
    config = load_config(cwd=tmp_path)
    assert config.compressor_plugins == ["example.plugins:Compressor"]
    assert config.trusted_plugin_prefixes == ["example.plugins"]
    assert config.unsafe_allow_untrusted_plugins is True


def test_validate_config_rejects_empty_trusted_plugin_prefixes() -> None:
    config = Config()
    config.trusted_plugin_prefixes = []
    with pytest.raises(ConfigError, match="trusted_plugin_prefixes"):
        validate_config(config)
