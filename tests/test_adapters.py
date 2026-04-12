from __future__ import annotations

from unittest.mock import patch

from toonprompt.adapters import Adapter, resolve_adapter, run_adapter, tool_status
from toonprompt.config import Config


def test_resolve_adapter_uses_configured_binary() -> None:
    config = Config()
    config.tool_paths["codex"] = "/usr/local/bin/codex"
    adapter = resolve_adapter("codex", config)
    assert adapter == Adapter(tool="codex", binary="/usr/local/bin/codex")


def test_tool_status_returns_missing_binary() -> None:
    with patch("toonprompt.adapters.shutil.which", return_value=None):
        present, detail = tool_status("gemini", Config())
    assert present is False
    assert detail == "gemini"


def test_run_adapter_streams_prompt_to_subprocess() -> None:
    adapter = Adapter(tool="claude", binary="claude")
    with patch("toonprompt.adapters.subprocess.run") as run:
        run.return_value.returncode = 0
        rc = run_adapter(adapter, ["--print"], "hello")
    assert rc == 0
    assert run.call_args.kwargs["input"] == "hello"
    assert run.call_args.kwargs["text"] is True
