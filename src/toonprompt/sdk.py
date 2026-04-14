from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Iterator

from .config import Config, load_config, validate_config
from .detector import build_document
from .policy import TransformationPolicy


@dataclass
class SDKTransformResult:
    output: str
    action: str
    reason: str
    estimator_name: str
    input_tokens: int
    output_tokens: int
    delta_tokens: int

    @property
    def compression_ratio(self) -> float:
        if self.input_tokens == 0:
            return 0.0
        return self.delta_tokens / self.input_tokens


class ToonPrompt:
    """High-level Python API for ToonPrompt prompt transformations."""

    def __init__(
        self,
        *,
        config_path: Path | str | None = None,
        profile: str = "default",
        cwd: Path | None = None,
        **config_overrides: object,
    ) -> None:
        path = Path(config_path) if config_path is not None else None
        config = load_config(path=path, cwd=cwd, profile=profile)
        for key, value in config_overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self._config = validate_config(config)
        self._policy = TransformationPolicy()

    def transform(self, prompt: str, *, tool: str = "") -> SDKTransformResult:
        config = Config(**self._config.__dict__)
        config.active_adapter = tool
        result = self._policy.apply(build_document(prompt), config, tool=tool)
        return SDKTransformResult(
            output=result.final_text,
            action=result.safety.action,
            reason=result.safety.reason,
            estimator_name=result.estimator_name,
            input_tokens=result.estimated_input_tokens,
            output_tokens=result.estimated_output_tokens,
            delta_tokens=result.estimated_output_tokens - result.estimated_input_tokens,
        )

    async def transform_async(self, prompt: str, *, tool: str = "") -> SDKTransformResult:
        import asyncio

        return await asyncio.to_thread(self.transform, prompt, tool=tool)

    def stream(self, prompt: str, *, tool: str = "", chunk_size: int = 2048) -> Iterator[str]:
        config = Config(**self._config.__dict__)
        config.active_adapter = tool
        yield from self._policy.apply_stream(prompt, config, tool=tool, chunk_size=max(1, chunk_size))

    async def stream_async(self, prompt: str, *, tool: str = "", chunk_size: int = 2048) -> AsyncIterator[str]:
        config = Config(**self._config.__dict__)
        config.active_adapter = tool
        async for chunk in self._policy.apply_stream_async(prompt, config, tool=tool, chunk_size=max(1, chunk_size)):
            yield chunk
