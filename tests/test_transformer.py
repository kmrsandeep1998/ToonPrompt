from __future__ import annotations

from pathlib import Path

from toonprompt.config import Config, write_default_config
from toonprompt.detector import build_document
from toonprompt.serializer import to_toon
from toonprompt.transformer import transform_document


def test_json_transforms_to_toon() -> None:
    text = '{"nodes":[{"id":1,"name":"Node 1"},{"id":2,"name":"Node 2"}]}'
    result = transform_document(build_document(text), Config())
    assert result.transformed is True
    assert "nodes[2]{id,name}:" in result.final_text


def test_plain_text_stays_plain() -> None:
    text = "Explain why this test is failing."
    result = transform_document(build_document(text), Config())
    assert result.transformed is False
    assert result.final_text == text


def test_stacktrace_transforms() -> None:
    text = "Traceback (most recent call last):\n  File \"app.py\", line 10, in <module>\nValueError: bad"
    result = transform_document(build_document(text), Config())
    assert result.transformed is False
    assert result.safety.reason == "rewrite did not reduce estimated tokens"


def test_tree_like_input_is_preserved() -> None:
    text = "nodes[1]:\n  -\n    id: 1\n    name: Node 1"
    result = transform_document(build_document(text), Config())
    assert result.transformed is False
    assert result.final_text == text


def test_rewrite_that_expands_is_skipped() -> None:
    text = "2026-04-12T10:00:00Z ERROR database timeout\n2026-04-12T10:00:01Z ERROR database timeout"
    result = transform_document(build_document(text), Config())
    assert result.transformed is False
    assert result.safety.reason == "rewrite did not reduce estimated tokens"


def test_to_toon_serializer_handles_nested_data() -> None:
    output = to_toon({"children": [{"id": 1, "name": "A"}]}, name="data")
    assert "children[1]{id,name}:" in output


def test_write_default_config(tmp_path: Path) -> None:
    path = write_default_config(tmp_path / "config.toml")
    assert path.exists()
    assert "structured-only" in path.read_text()
