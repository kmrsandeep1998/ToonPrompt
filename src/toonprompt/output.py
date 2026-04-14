from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from typing import TextIO


def print_summary(result, stream: TextIO) -> None:
    if _rich_available():
        try:
            _print_rich_summary(result, stream)
            return
        except Exception:
            pass
    _print_plain_summary(result, stream)


def _rich_available() -> bool:
    try:
        import rich  # noqa: F401
    except Exception:
        return False
    return True


def _print_plain_summary(result, stream: TextIO) -> None:
    stream.write(format_transform_summary(result) + "\n")


def _print_rich_summary(result, stream: TextIO) -> None:
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console(file=stream)
    table = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white")
    delta = result.estimated_output_tokens - result.estimated_input_tokens
    delta_str = f"[green]{delta:+,}[/green]" if delta < 0 else f"[red]{delta:+,}[/red]"
    table.add_row("Action", result.safety.action)
    table.add_row("Reason", result.safety.reason)
    table.add_row("Estimator", result.estimator_name)
    table.add_row("Input tokens", f"{result.estimated_input_tokens:,}")
    table.add_row("Output tokens", f"{result.estimated_output_tokens:,}")
    table.add_row("Delta", delta_str)
    console.print(table)


@dataclass
class SegmentBreakdown:
    index: int
    segment_type: str
    source: str
    line_start: int
    line_end: int
    input_tokens: int
    output_tokens: int
    delta: int
    changed: bool
    reason: str | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "type": self.segment_type,
            "source": self.source,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "delta": self.delta,
            "changed": self.changed,
            "reason": self.reason,
        }


def build_segment_breakdowns(result, estimator) -> list[SegmentBreakdown]:
    ranges = _segment_line_ranges(result.original_text, [segment.text for segment in result.segments])
    rows: list[SegmentBreakdown] = []
    for idx, segment in enumerate(result.segments, start=1):
        original = segment.text
        transformed = segment.transformed_text if segment.transformed_text is not None else segment.text
        input_tokens = estimator.estimate(original)
        output_tokens = estimator.estimate(transformed)
        line_start, line_end = ranges[idx - 1]
        rows.append(
            SegmentBreakdown(
                index=idx,
                segment_type=segment.segment_type.value,
                source=segment.source,
                line_start=line_start,
                line_end=line_end,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                delta=input_tokens - output_tokens,
                changed=transformed != original,
                reason=segment.reason,
            )
        )
    return rows


def format_transform_summary(result, markdown: bool = False) -> str:
    delta = result.estimated_input_tokens - result.estimated_output_tokens
    if markdown:
        return (
            f"- Action: `{result.safety.action}`\n"
            f"- Reason: `{result.safety.reason}`\n"
            f"- Estimator: `{result.estimator_name}`\n"
            f"- Estimated input tokens: `{result.estimated_input_tokens}`\n"
            f"- Estimated output tokens: `{result.estimated_output_tokens}`\n"
            f"- Delta: `{delta}`"
        )
    return (
        f"Action          : {result.safety.action}\n"
        f"Reason          : {result.safety.reason}\n"
        f"Estimator       : {result.estimator_name}\n"
        f"Est. input      : {result.estimated_input_tokens}\n"
        f"Est. output     : {result.estimated_output_tokens}\n"
        f"Delta           : {delta}"
    )


def build_inspect_payload(
    result,
    input_bytes: int,
    breakdown: list[SegmentBreakdown],
    explanations: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        "action": result.safety.action,
        "reason": result.safety.reason,
        "estimator": result.estimator_name,
        "estimated_input_tokens": result.estimated_input_tokens,
        "estimated_output_tokens": result.estimated_output_tokens,
        "delta": result.estimated_input_tokens - result.estimated_output_tokens,
        "input_bytes": input_bytes,
        "segments": [row.to_payload() for row in breakdown],
        "transformed": result.final_text,
    }
    if explanations is not None:
        payload["explanations"] = explanations
    return payload


def format_inspect_text(result, input_bytes: int, breakdown: list[SegmentBreakdown], markdown: bool = False) -> str:
    seg_count = len(result.segments)
    type_counts = _segment_type_counts(result)
    seg_parts = ", ".join(f"{count} {name}" for name, count in sorted(type_counts.items())) or "0"
    if markdown:
        lines = [
            "### ToonPrompt Inspection",
            f"- Size: `{input_bytes}` bytes",
            f"- Segments: `{seg_count}` ({seg_parts})",
            format_transform_summary(result, markdown=True),
            "",
            "#### Segment Breakdown",
            "| # | Type | Source | Lines | Tokens (in->out) | Delta | Changed |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in breakdown:
            lines.append(
                f"| {row.index} | {row.segment_type} | {row.source} | {row.line_start}-{row.line_end} | "
                f"{row.input_tokens}->{row.output_tokens} | {row.delta} | {'yes' if row.changed else 'no'} |"
            )
        return "\n".join(lines)
    lines = [
        "=== ToonPrompt Inspection ===",
        f"Size            : {input_bytes} bytes",
        f"Segments        : {seg_count} ({seg_parts})",
        format_transform_summary(result),
        "Segment breakdown:",
    ]
    for row in breakdown:
        lines.append(
            f"- #{row.index} {row.segment_type.upper()} [{row.source}] "
            f"lines {row.line_start}-{row.line_end} "
            f"tokens {row.input_tokens}->{row.output_tokens} "
            f"(delta {row.delta}) {'changed' if row.changed else 'unchanged'}"
        )
    return "\n".join(lines)


def format_metrics_text(summary) -> str:
    lines = [
        "Local transformation metrics:",
        f"- Transforms attempted: {summary.transforms_attempted}",
        f"- Transforms applied: {summary.transforms_applied}",
        f"- Pass-through count: {summary.pass_through}",
        f"- Estimated token delta total: {summary.estimated_token_delta_total}",
    ]
    if summary.pass_through_reasons:
        lines.append("- Pass-through reasons:")
        for reason, count in sorted(summary.pass_through_reasons.items()):
            lines.append(f"  - {reason}: {count}")
    if summary.by_tool:
        lines.append("- By tool:")
        for tool, data in sorted(summary.by_tool.items()):
            lines.append(f"  - {tool}: {data['applied']} applied / {data['attempted']} attempted (delta {data['delta']})")
    if summary.daily:
        lines.append("- Daily trend:")
        for day, data in sorted(summary.daily.items()):
            attempted = data["attempted"]
            applied = data["applied"]
            ratio = (applied / attempted) if attempted else 0.0
            lines.append(
                f"  - {day}: {applied} applied / {attempted} attempted "
                f"(delta {data['delta']}) {render_trend_bar(ratio)}"
            )
    return "\n".join(lines)


def render_trend_bar(ratio: float, width: int = 12) -> str:
    bounded = min(max(ratio, 0.0), 1.0)
    filled = int(round(bounded * width))
    return f"|{'#' * filled}{'-' * (width - filled)}| {int(round(bounded * 100)):>3}%"


def inspect_json_dump(
    result,
    input_bytes: int,
    breakdown: list[SegmentBreakdown],
    explanations: list[str] | None = None,
) -> str:
    return json.dumps(build_inspect_payload(result, input_bytes, breakdown, explanations=explanations), indent=2)


def _segment_type_counts(result) -> dict[str, int]:
    stats: dict[str, int] = {}
    for segment in result.segments:
        key = segment.segment_type.value.upper()
        stats[key] = stats.get(key, 0) + 1
    return stats


def _segment_line_ranges(text: str, segment_texts: list[str]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    cursor = 0
    for segment_text in segment_texts:
        segment_body = segment_text or ""
        start = text.find(segment_body, cursor) if segment_body else cursor
        if start < 0:
            start = cursor
        end = start + len(segment_body)
        line_start = text.count("\n", 0, start) + 1
        line_end = text.count("\n", 0, max(start, end - 1)) + 1
        ranges.append((line_start, line_end))
        cursor = max(cursor, end)
    return ranges
