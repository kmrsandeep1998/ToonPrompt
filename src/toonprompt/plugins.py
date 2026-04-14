from __future__ import annotations

import importlib
import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger("toonprompt.plugins")


@runtime_checkable
class Compressor(Protocol):
    name: str

    def can_handle(self, text: str, segment_type: str) -> bool:
        ...

    def compress(self, text: str) -> tuple[str, bool]:
        ...


def load_entry_point_compressors(
    *,
    trusted_prefixes: list[str] | None = None,
    allow_untrusted: bool = False,
) -> list[Compressor]:
    try:
        from importlib.metadata import entry_points
        eps = entry_points(group="toonprompt.compressors")
    except Exception:
        return []
    trusted_prefixes = trusted_prefixes or []
    loaded: list[Compressor] = []
    for ep in eps:
        try:
            module_path = _entry_point_module(ep)
            if not allow_untrusted and not is_trusted_module(module_path, trusted_prefixes):
                logger.warning("Skipping untrusted compressor entry point: %s", ep.name)
                continue
            cls = ep.load()
            instance = cls()
            if isinstance(instance, Compressor):
                loaded.append(instance)
        except Exception:
            continue
    return loaded


def load_config_compressors(
    class_paths: list[str],
    *,
    trusted_prefixes: list[str] | None = None,
    allow_untrusted: bool = False,
) -> list[Compressor]:
    trusted_prefixes = trusted_prefixes or []
    result: list[Compressor] = []
    for class_path in class_paths:
        try:
            module_path, cls_name = class_path.rsplit(":", 1)
            if not allow_untrusted and not is_trusted_module(module_path, trusted_prefixes):
                logger.warning("Skipping untrusted compressor class path: %s", class_path)
                continue
            module = importlib.import_module(module_path)
            cls = getattr(module, cls_name)
            instance = cls()
            if isinstance(instance, Compressor):
                result.append(instance)
        except Exception:
            continue
    return result


def is_trusted_module(module_path: str, trusted_prefixes: list[str]) -> bool:
    normalized = module_path.strip()
    if not normalized:
        return False
    return any(
        normalized == prefix or normalized.startswith(f"{prefix}.")
        for prefix in trusted_prefixes
        if isinstance(prefix, str) and prefix.strip()
    )


def _entry_point_module(ep: object) -> str:
    module_name = getattr(ep, "module", None)
    if isinstance(module_name, str) and module_name.strip():
        return module_name
    value = getattr(ep, "value", "")
    if isinstance(value, str) and ":" in value:
        return value.split(":", 1)[0]
    return ""
