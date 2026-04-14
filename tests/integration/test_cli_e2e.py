from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def toon(*args: str, input_text: str | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    merged_env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-m", "toonprompt", *args],
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=merged_env,
    )


def test_version_command() -> None:
    r = toon("version")
    assert r.returncode == 0
    assert "0." in r.stdout


def test_inspect_json_prompt() -> None:
    prompt = '{"nodes": [{"id": 1, "name": "Alpha"}, {"id": 2, "name": "Beta"}]}'
    r = toon("inspect", "--prompt", prompt)
    assert r.returncode == 0
    assert "Action" in r.stdout


def test_dry_run_json_prompt() -> None:
    prompt = '{"nodes": [{"id": 1, "name": "Alpha"}, {"id": 2, "name": "Beta"}]}'
    r = toon("codex", "--prompt", prompt, "--dry-run")
    assert r.returncode == 0
    assert "dry-run" in r.stdout.lower()
    assert "tokens" in r.stdout.lower()


def test_metrics_json_output(tmp_path) -> None:
    config_home = tmp_path / "config_home"
    state_home = tmp_path / "state_home"
    cfg = config_home / "toonprompt" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("local_metrics_enabled = true\n")
    env = {"XDG_CONFIG_HOME": str(config_home), "XDG_STATE_HOME": str(state_home)}
    toon("inspect", "--prompt", '{"id":1}', env=env)
    r = toon("metrics", "--json", env=env)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert "transforms_attempted" in data


def test_config_init(tmp_path) -> None:
    path = tmp_path / "config.toml"
    r = toon("config", "init", "--path", str(path))
    assert r.returncode == 0
    assert path.exists()
