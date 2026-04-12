from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess

from .config import Config


@dataclass
class Adapter:
    tool: str
    binary: str

    def command(self, native_args: list[str]) -> list[str]:
        return [self.binary, *native_args]


def resolve_adapter(tool: str, config: Config) -> Adapter:
    binary = config.tool_paths.get(tool, tool)
    return Adapter(tool=tool, binary=binary)


def tool_status(tool: str, config: Config) -> tuple[bool, str]:
    binary = config.tool_paths.get(tool, tool)
    resolved = shutil.which(binary)
    if resolved:
        return True, resolved
    return False, binary


def run_adapter(adapter: Adapter, native_args: list[str], prompt_text: str | None) -> int:
    process = subprocess.run(
        adapter.command(native_args),
        input=prompt_text,
        text=True,
        check=False,
    )
    return process.returncode
