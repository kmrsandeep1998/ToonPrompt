from __future__ import annotations

from pathlib import Path

from toonprompt.config import Config
from toonprompt.detector import build_document
from toonprompt.transformer import transform_document


FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "golden"


def test_golden_cases() -> None:
    for case in sorted(FIXTURES.iterdir()):
        if not case.is_dir():
            continue
        input_text = (case / "input.txt").read_text()
        expected_text = (case / "expected.txt").read_text()
        result = transform_document(build_document(input_text), Config())
        assert result.final_text == expected_text, case.name
