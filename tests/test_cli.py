from __future__ import annotations

from unittest.mock import patch

from toonprompt.cli import main


def test_inspect_preview(capsys) -> None:
    prompt = '{"nodes":[{"id":1,"name":"Node 1"},{"id":2,"name":"Node 2"}]}'
    code = main(["inspect", "--prompt", prompt, "--preview"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Estimated tokens" in captured.out
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


def test_run_tool_executes_adapter() -> None:
    prompt = '{"nodes":[{"id":1,"name":"Node 1"},{"id":2,"name":"Node 2"}]}'
    with patch("toonprompt.cli.run_adapter", return_value=0) as run_adapter:
        code = main(["codex", "--prompt", prompt, "--", "--model", "gpt-5.4"])
    assert code == 0
    _, native_args, prompt_text = run_adapter.call_args[0]
    assert native_args == ["--model", "gpt-5.4"]
    assert "data:" in prompt_text
