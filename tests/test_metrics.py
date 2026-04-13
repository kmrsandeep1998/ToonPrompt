from __future__ import annotations

from pathlib import Path

from toonprompt.metrics import LocalMetricsStore


def test_metrics_store_recovers_from_corrupt_file(tmp_path: Path) -> None:
    store = LocalMetricsStore(state_dir=tmp_path)
    corrupt = tmp_path / "metrics.json"
    corrupt.write_text("{bad json")
    summary = store.summary()
    assert summary.transforms_attempted == 0
    store.record(transformed=True, input_tokens=10, output_tokens=5, reason="ok")
    summary = store.summary()
    assert summary.transforms_attempted == 1
    assert summary.transforms_applied == 1
