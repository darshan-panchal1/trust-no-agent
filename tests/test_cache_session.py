"""T009: the judging session at the store's one door (research R2, R4, R5). Writes go only
through `RagasCacheBackend`, a sanctioned writer — never `read_or_call` from a test."""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.cache import session, store
from evals.cache.keys import make_key
from evals.cache.ragas_backend import RagasCacheBackend
from evals.cache.store import CacheEntry
from tests.fakes import FakeChatCompletion, FakeUsage

pytestmark = pytest.mark.usefixtures("isolated_cache")
KIND, MODEL = "ragas:faithfulness", "judge/model"


def _path(kind: str, ragas_key: str) -> Path:
    return store.CACHE_DIR / f"{make_key(kind, MODEL, ragas_key)}.json"


def _entry(kind: str, ragas_key: str) -> CacheEntry:
    return CacheEntry.model_validate_json(_path(kind, ragas_key).read_text())


def test_without_a_session_a_write_is_exactly_v1() -> None:
    RagasCacheBackend(KIND, MODEL, mode="live").set("k", {"a": 1})
    assert '"fingerprint"' not in _path(KIND, "k").read_text()
    assert (_entry(KIND, "k").input_tokens, _entry(KIND, "k").output_tokens) == (0, 0)


def test_a_session_stamps_only_its_judge_kind_and_pairs_usage_with_it() -> None:
    with session.begin("F", KIND):
        session.push_usage(FakeChatCompletion(choices=[], usage=FakeUsage(10, 5)))
        RagasCacheBackend("ragas:embeddings", MODEL, mode="live").set("e", [0.1])
        RagasCacheBackend(KIND, MODEL, mode="live").set("k", {"a": 1})
    assert '"fingerprint"' not in _path("ragas:embeddings", "e").read_text()
    judged = _entry(KIND, "k")
    assert (judged.fingerprint, judged.input_tokens, judged.output_tokens) == ("F", 10, 5)


def test_a_stored_fingerprint_that_disagrees_is_refused() -> None:
    RagasCacheBackend(KIND, MODEL, mode="live").set("k", {"a": 1})
    tampered = _entry(KIND, "k").model_copy(update={"fingerprint": "G"})
    _path(KIND, "k").write_text(tampered.model_dump_json())
    with session.begin("F", KIND), pytest.raises(session.FingerprintMismatch, match="G != .* F"):
        RagasCacheBackend(KIND, MODEL).has_key("k")


def test_an_unfingerprinted_read_is_served_and_sessions_never_nest_or_leak() -> None:
    RagasCacheBackend(KIND, MODEL, mode="live").set("k", {"a": 1})
    with pytest.raises(ValueError), session.begin("F", KIND) as active:
        assert RagasCacheBackend(KIND, MODEL).get("k") == {"a": 1}
        assert list(active.served) == [make_key(KIND, MODEL, "k")]
        with pytest.raises(RuntimeError, match="nest"), session.begin("G", KIND):
            pass
        raise ValueError("boom")
    assert session.active() is None
