from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from toonprompt.cli import main


def test_inspect_preview(capsys) -> None:
    prompt = '{"nodes":[{"id":1,"name":"Node 1"},{"id":2,"name":"Node 2"}]}'
    code = main(["inspect", "--prompt", prompt, "--preview"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Estimated tokens" in captured.out
    assert "Estimator:" in captured.out
    assert "data:" in captured.out


def test_tool_print_final_prompt(capsys) -> None:
    prompt = '{"nodes":[{"id":1,"name":"Node 1"},{"id":2,"name":"Node 2"}]}'
    code = main(["codex", "--prompt", prompt, "--print-final-prompt"])
    captured = capsys.readouterr()
    assert code == 0
    assert "data:" in captured.out


def test_doctor_exit_code_when_tools_missing(capsys) -> None:
    with patch("toonprompt.cli.tool_status", return_value=(False, "missing")):
        code = main(["doctor"])
    captured = capsys.readouterr()
    assert code == 1
    assert "missing" in captured.out
    assert "Config valid: yes" in captured.out


def test_run_tool_executes_adapter() -> None:
    prompt = '{"nodes":[{"id":1,"name":"Node 1"},{"id":2,"name":"Node 2"}]}'
    with patch("toonprompt.cli.run_adapter", return_value=0) as run_adapter:
        code = main(["codex", "--prompt", prompt, "--", "--model", "gpt-5.4"])
    assert code == 0
    _, native_args, prompt_text = run_adapter.call_args[0]
    assert native_args == ["--model", "gpt-5.4"]
    assert "data:" in prompt_text


def test_invalid_config_returns_clean_error(capsys, monkeypatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    target = config_dir / "toonprompt" / "config.toml"
    target.parent.mkdir(parents=True)
    target.write_text('toon_format = "999"\n')
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    code = main(["inspect", "--prompt", '{"id":1}'])
    captured = capsys.readouterr()
    assert code == 2
    assert "unsupported toon_format 999" in captured.err


def test_metrics_command_reports_disabled_by_default(capsys) -> None:
    code = main(["metrics"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Local metrics are disabled" in captured.out


def test_metrics_command_reports_values_when_enabled(capsys, monkeypatch, tmp_path: Path) -> None:
    config_home = tmp_path / "config_home"
    state_home = tmp_path / "state_home"
    cfg = config_home / "toonprompt" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("local_metrics_enabled = true\n")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))
    prompt = '{"nodes":[{"id":1,"name":"Node 1"},{"id":2,"name":"Node 2"}]}'
    inspect_code = main(["inspect", "--prompt", prompt])
    metrics_code = main(["metrics"])
    captured = capsys.readouterr()
    assert inspect_code == 0
    assert metrics_code == 0
    assert "Transforms attempted: 1" in captured.out


def test_dry_run_does_not_execute_adapter(capsys) -> None:
    prompt = '{"nodes":[{"id":1,"name":"Node 1"}]}'
    with patch("toonprompt.cli.run_adapter") as run_adapter:
        code = main(["codex", "--prompt", prompt, "--dry-run", "--", "--model", "gpt-5.4"])
    captured = capsys.readouterr()
    assert code == 0
    run_adapter.assert_not_called()
    assert "dry-run" in captured.out.lower()


def test_metrics_json_output(capsys, monkeypatch, tmp_path: Path) -> None:
    config_home = tmp_path / "config_home"
    state_home = tmp_path / "state_home"
    cfg = config_home / "toonprompt" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("local_metrics_enabled = true\n")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))
    main(["inspect", "--prompt", '{"id":1}'])
    code = main(["metrics", "--json"])
    captured = capsys.readouterr()
    assert code == 0
    assert '"transforms_attempted"' in captured.out


def test_check_subcommand_fails_on_large_prompt(capsys, tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text('{"nodes":[{"id":1,"name":"A very long name value for token budget test"}]}')
    code = main(["check", "--max-tokens", "1", str(prompt_path)])
    captured = capsys.readouterr()
    assert code == 1
    assert "exceeds budget" in captured.err
