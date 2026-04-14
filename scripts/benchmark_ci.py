from __future__ import annotations

import argparse
import json
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
    parser = argparse.ArgumentParser(description="Benchmark regression gate for ToonPrompt fixtures.")
    parser.add_argument("--update-baseline", action="store_true", help="Write baseline from current implementation.")
    parser.add_argument("--tolerance-pct", type=float, default=5.0, help="Allowed degradation in delta percent.")
    args = parser.parse_args()

    baseline_path = ROOT / "benchmarks" / "baseline.json"
    current = _run_fixtures()

    if args.update_baseline or not baseline_path.exists():
        payload = {"version": "0.1.0a2", "fixtures": current}
        baseline_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(f"Updated baseline: {baseline_path}")
        return 0

    baseline = json.loads(baseline_path.read_text())
    failures: list[str] = []
    for name, data in current.items():
        expected = baseline.get("fixtures", {}).get(name)
        if not isinstance(expected, dict):
            failures.append(f"{name}: missing baseline fixture")
            continue
        current_pct = float(data["delta_pct"])
        baseline_pct = float(expected.get("delta_pct", 0.0))
        if current_pct > baseline_pct + args.tolerance_pct:
            failures.append(
                f"{name}: regression current={current_pct:.2f}% baseline={baseline_pct:.2f}% "
                f"tolerance={args.tolerance_pct:.2f}%"
            )
    if failures:
        print("Benchmark regression check failed:")
        for item in failures:
            print(f"- {item}")
        return 1
    print("Benchmark regression check passed.")
    return 0


def _run_fixtures() -> dict[str, dict[str, float]]:
    fixtures = ROOT / "benchmarks" / "fixtures"
    config = Config()
    result: dict[str, dict[str, float]] = {}
    for fixture in sorted(fixtures.iterdir()):
        if not fixture.is_file():
            continue
        text = fixture.read_text()
        transformed = transform_document(build_document(text), config)
        input_tokens = transformed.estimated_input_tokens
        output_tokens = transformed.estimated_output_tokens
        delta_pct = ((output_tokens - input_tokens) / input_tokens * 100.0) if input_tokens else 0.0
        result[fixture.stem] = {
            "input_tokens": float(input_tokens),
            "output_tokens": float(output_tokens),
            "delta_pct": round(delta_pct, 2),
        }
    return result


if __name__ == "__main__":
    raise SystemExit(main())
