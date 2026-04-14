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

    def build_command(self, native_args: list[str], prompt_text: str | None = None) -> list[str]:
        ...

    def supports_stdin(self) -> bool:
        ...

    def doctor_check(self) -> tuple[bool, str]:
        ...


@dataclass
class BinaryToolAdapter:
    tool: str
    binary: str

    def build_command(self, native_args: list[str], prompt_text: str | None = None) -> list[str]:
        return [self.binary, *native_args]

    def supports_stdin(self) -> bool:
        return True

    def doctor_check(self) -> tuple[bool, str]:
        resolved = shutil.which(self.binary)
        if resolved:
            return True, resolved
        return False, self.binary


@dataclass
class AiderToolAdapter(BinaryToolAdapter):
    def build_command(self, native_args: list[str], prompt_text: str | None = None) -> list[str]:
        args = list(native_args)
        if prompt_text and not _has_prompt_flag(args, ("--message", "-m")):
            args = ["--message", prompt_text, *args]
        return [self.binary, *args]

    def supports_stdin(self) -> bool:
        # Aider works more reliably when prompts are passed via --message.
        return False


@dataclass
class ContinueToolAdapter(BinaryToolAdapter):
    def build_command(self, native_args: list[str], prompt_text: str | None = None) -> list[str]:
        args = list(native_args)
        if prompt_text and not _has_prompt_flag(args, ("--prompt", "-p")):
            args = ["--prompt", prompt_text, *args]
        return [self.binary, *args]

    def supports_stdin(self) -> bool:
        # Continue wrapper uses explicit prompt flag for deterministic invocation.
        return False


def resolve_adapter(tool: str, config: Config) -> ToolAdapter:
    binary = config.tool_paths.get(tool, tool)
    if tool == "aider":
        return AiderToolAdapter(tool=tool, binary=binary)
    if tool == "continue":
        return ContinueToolAdapter(tool=tool, binary=binary)
    return BinaryToolAdapter(tool=tool, binary=binary)


def tool_status(tool: str, config: Config) -> tuple[bool, str]:
    return resolve_adapter(tool, config).doctor_check()


def run_adapter(adapter: ToolAdapter, native_args: list[str], prompt_text: str | None) -> int:
    present, detail = adapter.doctor_check()
    if not present:
        raise AdapterExecutionError(f"{adapter.tool} CLI not found: {detail}")
    try:
        process = subprocess.run(
            adapter.build_command(native_args, prompt_text),
            input=prompt_text if adapter.supports_stdin() else None,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise AdapterExecutionError(f"failed to launch {adapter.tool}: {exc}") from exc
    return process.returncode


def _has_prompt_flag(native_args: list[str], flags: tuple[str, ...]) -> bool:
    for arg in native_args:
        if arg in flags:
            return True
        if any(arg.startswith(f"{flag}=") for flag in flags if flag.startswith("--")):
            return True
    return False
