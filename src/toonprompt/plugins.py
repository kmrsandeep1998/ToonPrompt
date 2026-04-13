from __future__ import annotations

import importlib
from typing import Protocol, runtime_checkable


@runtime_checkable
class Compressor(Protocol):
    name: str

    def can_handle(self, text: str, segment_type: str) -> bool:
        ...

    def compress(self, text: str) -> tuple[str, bool]:
        ...


def load_entry_point_compressors() -> list[Compressor]:
    try:
        from importlib.metadata import entry_points
        eps = entry_points(group="toonprompt.compressors")
    except Exception:
        return []
    loaded: list[Compressor] = []
    for ep in eps:
        try:
            cls = ep.load()
            instance = cls()
            if isinstance(instance, Compressor):
                loaded.append(instance)
        except Exception:
            continue
    return loaded


def load_config_compressors(class_paths: list[str]) -> list[Compressor]:
    result: list[Compressor] = []
    for class_path in class_paths:
        try:
            module_path, cls_name = class_path.rsplit(":", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, cls_name)
            instance = cls()
            if isinstance(instance, Compressor):
                result.append(instance)
        except Exception:
            continue
    return result
