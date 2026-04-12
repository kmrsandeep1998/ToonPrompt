from __future__ import annotations

from .config import Config
from .models import PromptDocument, TransformResult
from .policy import TransformationPolicy


def transform_document(document: PromptDocument, config: Config) -> TransformResult:
    return TransformationPolicy().apply(document, config)
