from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Config, default_config_path, load_config
from .detector import build_document, read_prompt
from .errors import PromptInputError
from .models import TransformResult
from .policy import TransformationPolicy


@dataclass
class ProcessedPrompt:
    config: Config
    result: TransformResult


class PromptProcessingService:
    def __init__(self, policy: TransformationPolicy | None = None) -> None:
        self.policy = policy or TransformationPolicy()

    def process(self, prompt: str | None, prompt_file: Path | None, use_stdin: bool, cwd: Path | None = None) -> ProcessedPrompt:
        config = load_config(cwd=cwd)
        try:
            text = read_prompt(prompt, prompt_file, use_stdin)
        except (OSError, ValueError) as exc:
            raise PromptInputError(str(exc)) from exc
        document = build_document(text)
        return ProcessedPrompt(config=config, result=self.policy.apply(document, config))


def doctor_report(cwd: Path | None = None) -> tuple[Config, str]:
    config = load_config(cwd=cwd)
    return config, f"Config path: {default_config_path()}"
