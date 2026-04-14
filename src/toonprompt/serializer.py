from __future__ import annotations

from collections.abc import Mapping, Sequence


def to_toon(value: object, name: str = "data", depth: int = 0, max_depth: int = 12) -> str:
    if depth > max_depth:
        return f"{_indent(depth)}{name}: <max-depth>"
    if isinstance(value, Mapping):
        lines = [f"{_indent(depth)}{name}:"]
        for key, item in value.items():
            lines.extend(_serialize_entry(str(key), item, depth + 1, max_depth))
        return "\n".join(lines)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return "\n".join(_serialize_sequence(name, value, depth, max_depth))
    return f"{_indent(depth)}{name}: {_format_scalar(value)}"


def _serialize_entry(key: str, value: object, depth: int, max_depth: int) -> list[str]:
    if isinstance(value, Mapping):
        lines = [f"{_indent(depth)}{key}:"]
        for nested_key, nested_value in value.items():
            lines.extend(_serialize_entry(str(nested_key), nested_value, depth + 1, max_depth))
        return lines
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return _serialize_sequence(key, value, depth, max_depth)
    return [f"{_indent(depth)}{key}: {_format_scalar(value)}"]


def _serialize_sequence(name: str, value: Sequence[object], depth: int, max_depth: int) -> list[str]:
    seq = list(value)
    records = _extract_homogenous_scalar_records(seq)
    if records is not None:
        keys = list(records[0].keys())
        lines = [f"{_indent(depth)}{name}[{len(seq)}]{{{','.join(keys)}}}:"]
        for row in records:
            lines.append(f"{_indent(depth + 1)}{','.join(_format_cell(row[key]) for key in keys)}")
        return lines

    lines = [f"{_indent(depth)}{name}[{len(seq)}]:"]
    for item in seq:
        if isinstance(item, Mapping):
            lines.append(f"{_indent(depth + 1)}-")
            for nested_key, nested_value in item.items():
                lines.extend(_serialize_entry(str(nested_key), nested_value, depth + 2, max_depth))
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            lines.extend(_serialize_sequence("-", item, depth + 1, max_depth))
        else:
            lines.append(f"{_indent(depth + 1)}- {_format_scalar(item)}")
    return lines


def _extract_homogenous_scalar_records(seq: list[object]) -> list[dict[str, object]] | None:
    if not seq or not all(isinstance(item, Mapping) for item in seq):
        return None
    first = seq[0]
    if not isinstance(first, Mapping):
        return None
    keys = [str(key) for key in first.keys()]
    if not keys:
        return None
    records: list[dict[str, object]] = []
    for item in seq:
        if not isinstance(item, Mapping):
            return None
        if [str(key) for key in item.keys()] != keys:
            return None
        if any(isinstance(item.get(key), (Mapping, list, tuple)) for key in keys):
            return None
        records.append({key: item.get(key) for key in keys})
    return records


def _indent(depth: int) -> str:
    return "  " * depth


def _format_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _format_cell(value: object) -> str:
    text = _format_scalar(value)
    return text.replace("\\", "\\\\").replace(",", "\\,").replace("\n", "\\n")
