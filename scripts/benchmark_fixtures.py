from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from toonprompt.config import Config
from toonprompt.detector import build_document
from toonprompt.transformer import transform_document


def main() -> int:
    fixtures = ROOT / "benchmarks" / "fixtures"
    config = Config()
    for fixture in sorted(fixtures.iterdir()):
        if not fixture.is_file():
            continue
        text = fixture.read_text()
        result = transform_document(build_document(text), config)
        print(
            f"{fixture.name}: tokens {result.estimated_input_tokens} -> "
            f"{result.estimated_output_tokens} delta "
            f"{result.estimated_input_tokens - result.estimated_output_tokens}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
