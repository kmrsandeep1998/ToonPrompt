from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Iterator

from .config import Config, default_config_path, load_config
from .detector import build_document, read_prompt
from .estimators import estimator_status
from .errors import PromptInputError
from .metrics import LocalMetricsStore, MetricsSummary
from .models import TransformResult
from .policy import TransformationPolicy


@dataclass
class ProcessedPrompt:
    config: Config
    result: TransformResult


class PromptProcessingService:
    def __init__(self, policy: TransformationPolicy | None = None) -> None:
        self.policy = policy or TransformationPolicy()

    def process(
        self,
        prompt: str | None,
        prompt_file: Path | None,
        use_stdin: bool,
        cwd: Path | None = None,
        profile: str = "default",
        tool: str = "",
    ) -> ProcessedPrompt:
        config = load_config(cwd=cwd, profile=profile)
        config.active_adapter = tool
        try:
            text = read_prompt(prompt, prompt_file, use_stdin)
        except (OSError, ValueError) as exc:
            raise PromptInputError(str(exc)) from exc
        document = build_document(text)
        return ProcessedPrompt(config=config, result=self.policy.apply(document, config, tool=tool))

    async def process_async(
        self,
        prompt: str | None,
        prompt_file: Path | None,
        use_stdin: bool,
        cwd: Path | None = None,
        profile: str = "default",
        tool: str = "",
    ) -> ProcessedPrompt:
        config = load_config(cwd=cwd, profile=profile)
        config.active_adapter = tool
        try:
            text = read_prompt(prompt, prompt_file, use_stdin)
        except (OSError, ValueError) as exc:
            raise PromptInputError(str(exc)) from exc
        document = build_document(text)
        result = await self.policy.run_async(document, config, tool=tool)
        return ProcessedPrompt(config=config, result=result)

    def stream_process(
        self,
        prompt: str | None,
        prompt_file: Path | None,
        use_stdin: bool,
        *,
        chunk_size: int = 8192,
        cwd: Path | None = None,
        profile: str = "default",
        tool: str = "",
    ) -> Iterator[str]:
        config = load_config(cwd=cwd, profile=profile)
        config.active_adapter = tool
        try:
            text = read_prompt(prompt, prompt_file, use_stdin)
        except (OSError, ValueError) as exc:
            raise PromptInputError(str(exc)) from exc
        yield from self.policy.apply_stream(text, config, tool=tool, chunk_size=chunk_size)

    async def stream_process_async(
        self,
        prompt: str | None,
        prompt_file: Path | None,
        use_stdin: bool,
        *,
        chunk_size: int = 8192,
        cwd: Path | None = None,
        profile: str = "default",
        tool: str = "",
    ) -> AsyncIterator[str]:
        config = load_config(cwd=cwd, profile=profile)
        config.active_adapter = tool
        try:
            text = read_prompt(prompt, prompt_file, use_stdin)
        except (OSError, ValueError) as exc:
            raise PromptInputError(str(exc)) from exc
        async for chunk in self.policy.apply_stream_async(text, config, tool=tool, chunk_size=chunk_size):
            yield chunk


def doctor_report(cwd: Path | None = None, profile: str = "default") -> tuple[Config, str]:
    config = load_config(cwd=cwd, profile=profile)
    return config, f"Config path: {default_config_path()}\nEstimator backend: {estimator_status(config)}"


def metrics_report(cwd: Path | None = None, profile: str = "default") -> tuple[Config, MetricsSummary]:
    config = load_config(cwd=cwd, profile=profile)
    summary = LocalMetricsStore().summary()
    return config, summary
