from __future__ import annotations

import asyncio

from toonprompt import ToonPrompt


def test_sdk_transform_returns_output() -> None:
    client = ToonPrompt()
    result = client.transform('{"nodes":[{"id":1,"name":"Node 1"},{"id":2,"name":"Node 2"}]}')
    assert "nodes[2]{id,name}:" in result.output
    assert result.input_tokens >= result.output_tokens


def test_sdk_stream_chunks() -> None:
    client = ToonPrompt()
    chunks = list(client.stream('{"id":1,"name":"Node 1"}', chunk_size=5))
    assert chunks
    assert "".join(chunks)


def test_sdk_transform_async() -> None:
    client = ToonPrompt()
    result = asyncio.run(client.transform_async('{"id":1}'))
    assert result.output


def test_sdk_stream_uses_chunk_pipeline_for_large_prompt() -> None:
    client = ToonPrompt()
    prompt = "\n".join([f"line {idx}" for idx in range(200)])
    chunks = list(client.stream(prompt, chunk_size=64))
    assert len(chunks) > 1
    assert "".join(chunks)


def test_sdk_stream_async() -> None:
    client = ToonPrompt()

    async def _collect() -> list[str]:
        out: list[str] = []
        async for chunk in client.stream_async("line1\nline2\nline3", chunk_size=6):
            out.append(chunk)
        return out

    chunks = asyncio.run(_collect())
    assert chunks
    assert "".join(chunks)
