from __future__ import annotations

from ..serializer import to_toon


def compress_yaml(text: str) -> tuple[str, bool]:
    try:
        import yaml  # type: ignore
    except Exception:
        return text, False
    try:
        docs = list(yaml.safe_load_all(text))
    except Exception:
        return text, False
    compressed_parts: list[str] = []
    for doc in docs:
        if doc is None:
            continue
        compressed_parts.append(to_toon(doc, name="data"))
    if not compressed_parts:
        return text, False
    return "\n---\n".join(compressed_parts) + "\n", True
