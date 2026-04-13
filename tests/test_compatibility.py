from __future__ import annotations

from pathlib import Path
import json

from toonprompt.cli import TOOLS


def test_compatibility_matrix_matches_supported_tools() -> None:
    matrix_path = Path(__file__).resolve().parents[1] / "compatibility" / "cli_matrix.json"
    payload = json.loads(matrix_path.read_text())
    assert set(payload["tools"]) == set(TOOLS)


def test_all_tools_document_prompt_sources() -> None:
    matrix_path = Path(__file__).resolve().parents[1] / "compatibility" / "cli_matrix.json"
    payload = json.loads(matrix_path.read_text())
    required = {"--prompt", "--prompt-file", "--stdin"}
    for tool_data in payload["tools"].values():
        assert set(tool_data["prompt_sources"]) == required
