"""T1.7 acceptance: `generate()` is offline by default, live only on explicit `mode="live"`."""

from __future__ import annotations

from typing import cast

import openai
import pytest

from app.generate import generate
from evals.cache import store
from tests.fakes import FakeClient

pytestmark = pytest.mark.usefixtures("isolated_cache")


@pytest.mark.usefixtures("socket_disabled")
def test_default_mode_offline_raises_on_miss_even_with_key_exported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-fake-but-present")
    with pytest.raises(store.CacheMiss, match="cache miss"):
        generate("v1_naive", "system prompt", "user prompt")


def test_live_mode_with_stub_client_writes_one_entry_via_read_or_call() -> None:
    stub = cast(openai.OpenAI, FakeClient())
    answer = generate("v1_naive", "system prompt", "user prompt", mode="live", client=stub)
    assert answer == "stub answer"
    written = list(store.CACHE_DIR.glob("*.json"))
    assert len(written) == 1
