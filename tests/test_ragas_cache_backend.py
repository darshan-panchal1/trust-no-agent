"""T2.1 acceptance: `RagasCacheBackend` re-keys ragas' own key (Trap 19 fix)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from evals.cache import store
from evals.cache.ragas_backend import RagasCacheBackend

# docs/api-notes.md V4.1: the actual key ragas computed for one prompt, identical across
# claude-sonnet-5 and claude-opus-5 — the exact collision this backend must not reproduce.
RAGAS_COMPUTED_KEY = "495542df537934cdb7d0e05c"


pytestmark = pytest.mark.usefixtures("isolated_cache")


@pytest.mark.usefixtures("socket_disabled")
def test_offline_miss_raises_even_with_key_exported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake-but-present")
    backend = RagasCacheBackend("ragas:faithfulness", "claude-sonnet-5")
    with pytest.raises(store.CacheMiss, match="cache miss"):
        backend.has_key(RAGAS_COMPUTED_KEY)


def test_same_ragas_key_different_model_identity_persists_different_entries() -> None:
    sonnet = RagasCacheBackend("ragas:faithfulness", "claude-sonnet-5", mode="live")
    opus = RagasCacheBackend("ragas:faithfulness", "claude-opus-5", mode="live")
    assert sonnet.has_key(RAGAS_COMPUTED_KEY) is False
    assert opus.has_key(RAGAS_COMPUTED_KEY) is False
    sonnet.set(RAGAS_COMPUTED_KEY, {"answer": "sonnet-answer"})
    opus.set(RAGAS_COMPUTED_KEY, {"answer": "opus-answer"})
    written = list(store.CACHE_DIR.glob("*.json"))
    assert len(written) == 2
    assert sonnet.get(RAGAS_COMPUTED_KEY) == {"answer": "sonnet-answer"}
    assert opus.get(RAGAS_COMPUTED_KEY) == {"answer": "opus-answer"}


class _StatementModel(BaseModel):
    statement: str
    verdict: int


def test_a_pydantic_model_round_trips_through_a_cache_hit() -> None:
    """Trap 29: `json.dumps(model, default=str)` used to silently stringify a pydantic
    model instead of raising, so a cache HIT (the second identical call, e.g. ragas'
    self-consistency re-asks) returned a bare string. The only method ever called on the
    result downstream is `.model_dump_json()` (`ragas/prompt/pydantic_prompt.py`), so that
    is what must survive the round-trip — reproducing the exact consumer, not just the type."""
    backend = RagasCacheBackend(
        "ragas:faithfulness", "nvidia/nemotron-3-super-120b-a12b", mode="live"
    )
    model = _StatementModel(statement="the sky is blue", verdict=1)
    backend.set(RAGAS_COMPUTED_KEY, model)
    cached = backend.get(RAGAS_COMPUTED_KEY)
    assert cached.model_dump_json() == model.model_dump_json()
