from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
from typing import Protocol

from .config import Config
from .errors import AdapterExecutionError


class ToolAdapter(Protocol):
    tool: str
    binary: str

    def build_command(self, native_args: list[str]) -> list[str]:
        ...

    def supports_stdin(self) -> bool:
        ...

    def doctor_check(self) -> tuple[bool, str]:
        ...


@dataclass
class BinaryToolAdapter:
    tool: str
    binary: str

    def build_command(self, native_args: list[str]) -> list[str]:
        return [self.binary, *native_args]

    def supports_stdin(self) -> bool:
        return True

    def doctor_check(self) -> tuple[bool, str]:
        resolved = shutil.which(self.binary)
        if resolved:
            return True, resolved
        return False, self.binary


def resolve_adapter(tool: str, config: Config) -> ToolAdapter:
    binary = config.tool_paths.get(tool, tool)
    return BinaryToolAdapter(tool=tool, binary=binary)


def tool_status(tool: str, config: Config) -> tuple[bool, str]:
    return resolve_adapter(tool, config).doctor_check()


def run_adapter(adapter: ToolAdapter, native_args: list[str], prompt_text: str | None) -> int:
    present, detail = adapter.doctor_check()
    if not present:
        raise AdapterExecutionError(f"{adapter.tool} CLI not found: {detail}")
    try:
        process = subprocess.run(
            adapter.build_command(native_args),
            input=prompt_text if adapter.supports_stdin() else None,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise AdapterExecutionError(f"failed to launch {adapter.tool}: {exc}") from exc
    return process.returncode
