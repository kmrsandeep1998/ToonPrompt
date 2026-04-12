from __future__ import annotations

import csv
import json
from pathlib import Path
import re
import sys

import yaml

from .models import PromptDocument, PromptSegment, SegmentType


FENCE_RE = re.compile(r"```(?P<label>[a-zA-Z0-9_-]*)\n(?P<body>.*?)```", re.DOTALL)


def read_prompt(prompt: str | None, prompt_file: Path | None, use_stdin: bool) -> str:
    sources = [prompt is not None, prompt_file is not None, use_stdin]
    if sum(sources) > 1:
        raise ValueError("choose only one prompt source: --prompt, --prompt-file, or --stdin")
    if prompt is not None:
        return prompt
    if prompt_file is not None:
        return prompt_file.read_text()
    if use_stdin:
        return sys.stdin.read()
    return ""


def build_document(text: str) -> PromptDocument:
    if not text:
        return PromptDocument(original_text="", segments=[])
    whole_segment = _detect_block(text.strip())
    if whole_segment.segment_type is not SegmentType.PLAIN:
        return PromptDocument(original_text=text, segments=[whole_segment])

    segments: list[PromptSegment] = []
    last_index = 0
    for match in FENCE_RE.finditer(text):
        if match.start() > last_index:
            plain = text[last_index:match.start()]
            if plain:
                segments.append(PromptSegment(SegmentType.PLAIN, plain, "plain", 1.0))
        label = match.group("label").strip().lower()
        body = match.group("body")
        segments.append(_detect_fenced(label, body))
        last_index = match.end()
    if last_index < len(text):
        tail = text[last_index:]
        if tail:
            segments.append(_detect_mixed_text(tail))
    return PromptDocument(original_text=text, segments=segments or [PromptSegment(SegmentType.PLAIN, text, "plain", 1.0)])


def _detect_fenced(label: str, body: str) -> PromptSegment:
    if label == "json":
        return _parse_json(body, source="fenced-json")
    if label in {"yaml", "yml"}:
        return _parse_yaml(body, source="fenced-yaml")
    if label in {"log", "logs"}:
        return _parse_logs(body, source="fenced-log")
    return _detect_block(body, source=f"fenced-{label or 'plain'}")


def _detect_mixed_text(text: str) -> PromptSegment:
    stripped = text.strip()
    if "\n" not in stripped:
        return PromptSegment(SegmentType.PLAIN, text, "plain", 1.0)
    return _detect_block(text, source="mixed-tail")


def _detect_block(text: str, source: str = "whole") -> PromptSegment:
    stripped = text.strip()
    for parser in (_parse_json, _parse_stacktrace, _parse_tree, _parse_table, _parse_logs, _parse_yaml):
        segment = parser(stripped, source=source)
        if segment.segment_type is not SegmentType.PLAIN:
            return segment
    return PromptSegment(SegmentType.PLAIN, text, source, 1.0, reason="left as plain text")


def _parse_json(text: str, source: str) -> PromptSegment:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return PromptSegment(SegmentType.PLAIN, text, source, 0.0)
    return PromptSegment(SegmentType.JSON, text, source, 0.99, parsed=parsed, reason="parsed as JSON")


def _parse_yaml(text: str, source: str) -> PromptSegment:
    if not any(token in text for token in (":", "- ", "\n")):
        return PromptSegment(SegmentType.PLAIN, text, source, 0.0)
    if "Traceback" in text or re.search(r"\b\w+\[\d+\]:", text):
        return PromptSegment(SegmentType.PLAIN, text, source, 0.0)
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError:
        return PromptSegment(SegmentType.PLAIN, text, source, 0.0)
    if isinstance(parsed, (dict, list)):
        return PromptSegment(SegmentType.YAML, text, source, 0.9, parsed=parsed, reason="parsed as YAML")
    return PromptSegment(SegmentType.PLAIN, text, source, 0.0)


def _parse_logs(text: str, source: str) -> PromptSegment:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return PromptSegment(SegmentType.PLAIN, text, source, 0.0)
    if sum(1 for line in lines if re.search(r"\b(INFO|WARN|ERROR|DEBUG|TRACE)\b", line)) >= 2:
        records = []
        for line in lines:
            match = re.match(r"(?:(?P<ts>\S+)\s+)?(?P<level>INFO|WARN|ERROR|DEBUG|TRACE)\s+(?P<msg>.*)", line)
            if match:
                records.append(match.groupdict())
            else:
                records.append({"line": line})
        return PromptSegment(SegmentType.LOG, text, source, 0.8, parsed=records, reason="parsed as log lines")
    return PromptSegment(SegmentType.PLAIN, text, source, 0.0)


def _parse_stacktrace(text: str, source: str) -> PromptSegment:
    if "Traceback" not in text and not re.search(r"\bat .*:\d+", text):
        return PromptSegment(SegmentType.PLAIN, text, source, 0.0)
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return PromptSegment(SegmentType.PLAIN, text, source, 0.0)
    return PromptSegment(SegmentType.STACKTRACE, text, source, 0.75, parsed={"lines": lines}, reason="detected stack trace")


def _parse_tree(text: str, source: str) -> PromptSegment:
    if not re.search(r"\b\w+\[\d+\]:", text):
        return PromptSegment(SegmentType.PLAIN, text, source, 0.0)
    lines = text.splitlines()
    if sum(1 for line in lines if ":" in line) < 2:
        return PromptSegment(SegmentType.PLAIN, text, source, 0.0)
    return PromptSegment(SegmentType.TREE, text, source, 0.7, parsed={"lines": lines}, reason="detected tree-like structured text")


def _parse_table(text: str, source: str) -> PromptSegment:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2 or not all("," in line or "\t" in line for line in lines[:2]):
        return PromptSegment(SegmentType.PLAIN, text, source, 0.0)
    dialect = csv.excel_tab if "\t" in lines[0] else csv.excel
    reader = csv.reader(lines, dialect=dialect)
    rows = [row for row in reader if row]
    widths = {len(row) for row in rows}
    if len(widths) != 1:
        return PromptSegment(SegmentType.PLAIN, text, source, 0.0)
    return PromptSegment(SegmentType.TABLE, text, source, 0.7, parsed=rows, reason="parsed as tabular data")
