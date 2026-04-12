from __future__ import annotations

from pathlib import Path

import pytest

from toonprompt.config import Config, load_config, validate_config
from toonprompt.errors import ConfigError


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
    monkeypatch.setenv("XDG_CONFIG_HOME", str(global_dir))
    config = load_config(cwd=project_dir)
    assert config.tool_paths["codex"] == "/project/codex"


def test_unknown_key_raises_config_error(monkeypatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    target = config_dir / "toonprompt" / "config.toml"
    target.parent.mkdir(parents=True)
    target.write_text('mystery = "value"\n')
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    with pytest.raises(ConfigError, match="unknown config keys"):
        load_config(cwd=tmp_path)
