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
