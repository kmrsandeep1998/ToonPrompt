from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
from unittest.mock import patch

import pytest

from toonprompt.audit import read_audit, write_audit_record
from toonprompt.config import Config
from toonprompt.errors import ConfigError
from toonprompt.logging_utils import sanitize_prompt_for_hash
from toonprompt.plugins import load_config_compressors
from toonprompt.policy import TransformationPolicy
from toonprompt.telemetry import emit_transform_span
from toonprompt.models import PromptSegment, SafetyDecision, SegmentType, TransformResult
import toonprompt.telemetry as telemetry_mod


def test_sanitize_prompt_for_hash_masks_env_assignments() -> None:
    text = "export API_KEY=secret TOKEN='abc def' foo=bar"
    assert sanitize_prompt_for_hash(text) == "export API_KEY=*** TOKEN=*** foo=bar"


def test_audit_uses_sanitized_hash(tmp_path: Path) -> None:
    config = replace(
        Config(),
        audit_log_enabled=True,
        audit_log_path=str(tmp_path / "audit.jsonl"),
    )
    prompt = "API_KEY=secret_value\npayload"
    write_audit_record(
        config=config,
        tool="codex",
        action="pass-through",
        reason="test",
        estimator="heuristic",
        input_text=prompt,
        input_tokens=10,
        output_tokens=10,
        duration_ms=1,
    )
    payload = json.loads((tmp_path / "audit.jsonl").read_text().strip())
    expected_hash = hashlib.sha256(sanitize_prompt_for_hash(prompt).encode("utf-8")).hexdigest()
    assert payload["input_hash"] == f"sha256:{expected_hash}"


def test_audit_rejects_unsafe_path() -> None:
    config = replace(
        Config(),
        audit_log_enabled=True,
        audit_log_path="/etc/toonprompt-audit.jsonl",
    )
    with pytest.raises(ConfigError, match="audit path"):
        write_audit_record(
            config=config,
            tool="codex",
            action="pass-through",
            reason="test",
            estimator="heuristic",
            input_text="x",
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
        )
    with pytest.raises(ConfigError, match="audit path"):
        read_audit(config)


def test_untrusted_config_plugin_is_skipped_without_import() -> None:
    called = False

    def _fake_import(name: str):
        nonlocal called
        called = True
        raise AssertionError("import should not be called for untrusted plugins")

    with patch("toonprompt.plugins.importlib.import_module", side_effect=_fake_import):
        loaded = load_config_compressors(
            ["evil.plugins:BadCompressor"],
            trusted_prefixes=["toonprompt.plugins"],
            allow_untrusted=False,
        )
    assert loaded == []
    assert called is False


def test_allow_untrusted_plugin_explicitly_enabled() -> None:
    class DemoCompressor:
        name = "demo"

        def can_handle(self, text: str, segment_type: str) -> bool:
            return False

        def compress(self, text: str) -> tuple[str, bool]:
            return text, False

    fake_module = SimpleNamespace(DemoCompressor=DemoCompressor)
    with patch("toonprompt.plugins.importlib.import_module", return_value=fake_module):
        loaded = load_config_compressors(
            ["evil.plugins:DemoCompressor"],
            trusted_prefixes=["toonprompt.plugins"],
            allow_untrusted=True,
        )
    assert len(loaded) == 1
    assert loaded[0].name == "demo"


def test_policy_hash_uses_sanitized_prompt() -> None:
    captured: dict[str, object] = {}
    policy = TransformationPolicy()
    config = Config()
    prompt = 'export API_KEY=secret\n{"key":"value"}'
    expected_hash = hashlib.sha256(sanitize_prompt_for_hash(prompt).encode("utf-8")).hexdigest()
    result = TransformResult(
        original_text=prompt,
        final_text=prompt,
        transformed=False,
        segments=[PromptSegment(segment_type=SegmentType.PLAIN, text=prompt, source="inline", confidence=1.0)],
        safety=SafetyDecision(action="pass-through", reason="test"),
        estimated_input_tokens=10,
        estimated_output_tokens=10,
    )
    with patch("toonprompt.policy.log_event", side_effect=lambda event, payload: captured.update(payload)):
        policy._log_result(result, config)  # noqa: SLF001 - intentional private method test
    assert captured["prompt_hash"] == expected_hash


def test_telemetry_configures_once_per_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(telemetry_mod, "_TRACER", None)
    monkeypatch.setattr(telemetry_mod, "_CONFIGURED_KEY", None)
    calls: list[tuple[str, str]] = []

    class _Span:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def set_attribute(self, _k: str, _v) -> None:
            return None

    class _Tracer:
        def start_as_current_span(self, _name: str):
            return _Span()

    def _fake_configure(*, service_name: str, endpoint: str):
        calls.append((service_name, endpoint))
        return _Tracer()

    monkeypatch.setattr(telemetry_mod, "_configure_tracing", _fake_configure)
    cfg = replace(Config(), otel_enabled=True, otel_service_name="svc", otel_endpoint="http://otel")
    emit_transform_span(
        config=cfg,
        tool="codex",
        action="transformed",
        estimator="heuristic",
        input_tokens=10,
        output_tokens=5,
        segment_type="json",
    )
    emit_transform_span(
        config=cfg,
        tool="codex",
        action="transformed",
        estimator="heuristic",
        input_tokens=10,
        output_tokens=5,
        segment_type="json",
    )
    assert calls == [("svc", "http://otel")]


def test_telemetry_noop_when_configure_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(telemetry_mod, "_TRACER", None)
    monkeypatch.setattr(telemetry_mod, "_CONFIGURED_KEY", None)
    monkeypatch.setattr(telemetry_mod, "_configure_tracing", lambda **_: None)
    cfg = replace(Config(), otel_enabled=True)
    emit_transform_span(
        config=cfg,
        tool="codex",
        action="transformed",
        estimator="heuristic",
        input_tokens=10,
        output_tokens=5,
        segment_type="json",
    )
