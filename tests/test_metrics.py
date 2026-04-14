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
    assert summary.by_tool["unknown"]["applied"] == 1


def test_metrics_store_recovers_from_unexpected_json_shape(tmp_path: Path) -> None:
    store = LocalMetricsStore(state_dir=tmp_path)
    malformed = tmp_path / "metrics.json"
    malformed.write_text("{}")
    store.record(transformed=False, input_tokens=5, output_tokens=5, reason="pass-through")
    summary = store.summary()
    assert summary.transforms_attempted == 1
    assert summary.pass_through == 1


def test_metrics_store_tracks_tool_and_daily_breakdown(tmp_path: Path) -> None:
    store = LocalMetricsStore(state_dir=tmp_path)
    store.record(transformed=True, input_tokens=20, output_tokens=10, reason="ok", tool="codex")
    summary = store.summary()
    assert summary.by_tool["codex"]["attempted"] == 1
    assert summary.by_tool["codex"]["applied"] == 1
    assert len(summary.daily) == 1
