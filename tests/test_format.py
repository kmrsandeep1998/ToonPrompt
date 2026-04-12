from __future__ import annotations

from toonprompt.config import Config
from toonprompt.detector import build_document
from toonprompt.format import FORMAT_VERSION, supported_format
from toonprompt.transformer import transform_document


def test_current_format_version_is_supported() -> None:
    assert supported_format(FORMAT_VERSION) is True


def test_unsupported_format_fails_open() -> None:
    config = Config()
    config.toon_format = "999"
    result = transform_document(build_document('{"id":1}'), config)
    assert result.transformed is False
    assert result.safety.reason == "unsupported toon_format 999"
    assert result.final_text == '{"id":1}'
