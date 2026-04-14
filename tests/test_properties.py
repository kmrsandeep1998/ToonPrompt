from __future__ import annotations

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st

from toonprompt import ToonPrompt


@given(st.text(max_size=10_000))
@settings(max_examples=200, deadline=2000)
def test_no_crash_on_arbitrary_input(text: str) -> None:
    result = ToonPrompt().transform(text)
    assert result.output is not None


@given(
    st.lists(
        st.fixed_dictionaries({"id": st.integers(), "name": st.text(max_size=20)}),
        min_size=1,
        max_size=50,
    )
)
@settings(max_examples=100, deadline=2000)
def test_json_list_never_inflates(records: list[dict[str, object]]) -> None:
    import json

    prompt = json.dumps(records)
    result = ToonPrompt().transform(prompt)
    assert result.delta_tokens <= 0


@given(st.text(max_size=5_000))
@settings(max_examples=200, deadline=2000)
def test_idempotency(text: str) -> None:
    toon = ToonPrompt()
    first = toon.transform(text).output
    second = toon.transform(first).output
    assert first == second
