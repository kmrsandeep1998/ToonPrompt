from __future__ import annotations

from toonprompt.compressors import compress_logs, compress_stacktrace, compress_yaml


def test_compress_logs_collapses_repeated_lines() -> None:
    text = "\n".join(
        [
            "2026-04-13T10:00:00Z ERROR database timeout",
            "2026-04-13T10:00:01Z ERROR database timeout",
            "2026-04-13T10:00:02Z ERROR database timeout",
        ]
    )
    output, changed = compress_logs(text)
    assert changed is True
    assert "[×3] ERROR database timeout" in output


def test_compress_stacktrace_omits_middle_frames() -> None:
    lines = ["Traceback (most recent call last):"]
    lines.extend([f'  File "mod{i}.py", line {i}, in fn' for i in range(10)])
    lines.append("ValueError: boom")
    output, changed = compress_stacktrace("\n".join(lines))
    assert changed is True
    assert "frames omitted" in output


def test_compress_yaml_converts_to_toon() -> None:
    text = "nodes:\n  - id: 1\n    name: Alpha\n  - id: 2\n    name: Beta\n"
    output, changed = compress_yaml(text)
    assert changed is True
    assert "nodes[2]{id,name}:" in output
