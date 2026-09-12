"""T1.4 acceptance: the one door — `read_or_raise` cannot write, `read_or_call` is the
only path that ever does. CONSTITUTION.md Article III.
"""

from __future__ import annotations

import inspect

import pytest

from evals.cache import store
from evals.cache.keys import make_key

pytestmark = pytest.mark.usefixtures("isolated_cache")


def test_read_or_raise_signature_accepts_no_call_function() -> None:
    params = inspect.signature(store.read_or_raise).parameters
    assert list(params) == ["key"]


def test_read_or_raise_on_miss_names_key_and_refresh_command() -> None:
    """FR-031: the message names a real, runnable command, not a description of one."""
    with pytest.raises(store.CacheMiss) as exc_info:
        store.read_or_raise("deadbeef")
    message = str(exc_info.value)
    assert "deadbeef" in message
    assert "uv run python -m evals.cli record" in message


def test_read_or_call_on_miss_invokes_once_and_writes_one_file() -> None:
    calls = []

    def call_fn() -> store.CacheEntry:
        calls.append(1)
        return store.CacheEntry(
            call_kind="generate:v1_naive", response="hi", input_tokens=1, output_tokens=1, usd=0.0
        )

    key = make_key("generate:v1_naive", "claude-haiku-4-5", "abc123")
    first = store.read_or_call(key, call_fn)
    second = store.read_or_call(key, call_fn)

    assert first == second
    assert len(calls) == 1  # cache hit on the second call, call_fn not invoked again
    written = list(store.CACHE_DIR.glob("*.json"))
    assert len(written) == 1
    assert written[0].name == f"{key}.json"


def test_same_prompt_different_model_identity_yields_different_keys() -> None:
    key_sonnet = make_key("deepeval:refusal_correctness", "claude-sonnet-5", "sameprompthash")
    key_opus = make_key("deepeval:refusal_correctness", "claude-opus-5", "sameprompthash")
    assert key_sonnet != key_opus
