from __future__ import annotations

from unittest.mock import patch

import pytest

from toonprompt.adapters import (
    AiderToolAdapter,
    BinaryToolAdapter,
    ContinueToolAdapter,
    resolve_adapter,
    run_adapter,
    tool_status,
)
from toonprompt.config import Config
from toonprompt.errors import AdapterExecutionError


def test_resolve_adapter_uses_configured_binary() -> None:
    config = Config()
    config.tool_paths["codex"] = "/usr/local/bin/codex"
    adapter = resolve_adapter("codex", config)
    assert adapter == BinaryToolAdapter(tool="codex", binary="/usr/local/bin/codex")


def test_tool_status_returns_missing_binary() -> None:
    with patch("toonprompt.adapters.shutil.which", return_value=None):
        present, detail = tool_status("gemini", Config())
    assert present is False
    assert detail == "gemini"


def test_run_adapter_streams_prompt_to_subprocess() -> None:
    adapter = BinaryToolAdapter(tool="claude", binary="claude")
    with patch("toonprompt.adapters.shutil.which", return_value="/usr/local/bin/claude"), patch("toonprompt.adapters.subprocess.run") as run:
        run.return_value.returncode = 0
        rc = run_adapter(adapter, ["--print"], "hello")
    assert rc == 0
    assert run.call_args.kwargs["input"] == "hello"
    assert run.call_args.kwargs["text"] is True


def test_run_adapter_raises_clear_error_when_binary_is_missing() -> None:
    adapter = BinaryToolAdapter(tool="gemini", binary="gemini")
    with patch("toonprompt.adapters.shutil.which", return_value=None):
        with pytest.raises(AdapterExecutionError, match="gemini CLI not found"):
            run_adapter(adapter, [], "hello")


def test_resolve_adapter_returns_aider_specialization() -> None:
    adapter = resolve_adapter("aider", Config())
    assert isinstance(adapter, AiderToolAdapter)


def test_resolve_adapter_returns_continue_specialization() -> None:
    adapter = resolve_adapter("continue", Config())
    assert isinstance(adapter, ContinueToolAdapter)


def test_run_adapter_aider_uses_message_flag_and_disables_stdin() -> None:
    adapter = AiderToolAdapter(tool="aider", binary="aider")
    with patch("toonprompt.adapters.shutil.which", return_value="/usr/local/bin/aider"), patch(
        "toonprompt.adapters.subprocess.run"
    ) as run:
        run.return_value.returncode = 0
        rc = run_adapter(adapter, ["--yes"], "fix failing tests")
    assert rc == 0
    assert run.call_args.args[0][:3] == ["aider", "--message", "fix failing tests"]
    assert run.call_args.kwargs["input"] is None


def test_run_adapter_continue_uses_prompt_flag_and_disables_stdin() -> None:
    adapter = ContinueToolAdapter(tool="continue", binary="continue")
    with patch("toonprompt.adapters.shutil.which", return_value="/usr/local/bin/continue"), patch(
        "toonprompt.adapters.subprocess.run"
    ) as run:
        run.return_value.returncode = 0
        rc = run_adapter(adapter, ["--model", "fast"], "summarize this file")
    assert rc == 0
    assert run.call_args.args[0][:3] == ["continue", "--prompt", "summarize this file"]
    assert run.call_args.kwargs["input"] is None
