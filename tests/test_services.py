from __future__ import annotations

import asyncio

from toonprompt.services import PromptProcessingService


def test_service_stream_process_returns_chunks() -> None:
    service = PromptProcessingService()
    prompt = "\n".join([f"log line {idx}" for idx in range(80)])
    chunks = list(service.stream_process(prompt, None, False, chunk_size=48))
    assert chunks
    assert len(chunks) > 1
    assert "".join(chunks)


def test_service_stream_process_async_returns_chunks() -> None:
    service = PromptProcessingService()

    async def _collect() -> list[str]:
        out: list[str] = []
        async for chunk in service.stream_process_async("a\nb\nc\nd", None, False, chunk_size=2):
            out.append(chunk)
        return out

    chunks = asyncio.run(_collect())
    assert chunks
    assert "".join(chunks)
