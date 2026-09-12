"""T2.3 acceptance: `embed_query` is cache-wrapped; a repeat call is a cache hit, not a
second call (docs/api-notes.md V3.3/V3.4 — the legacy wrapper, not `embedding_factory()`).
"""

from __future__ import annotations

import pytest
from langchain_core.embeddings import Embeddings
from ragas.embeddings.base import LangchainEmbeddingsWrapper

from evals.cache.ragas_backend import RagasCacheBackend
from evals.embeddings import build_judge_embeddings


class _CountingEmbeddings(Embeddings):
    def __init__(self) -> None:
        self.calls = 0

    def embed_query(self, text: str) -> list[float]:
        self.calls += 1
        return [1.0, 2.0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


pytestmark = pytest.mark.usefixtures("isolated_cache")


@pytest.mark.usefixtures("socket_disabled")
def test_embed_query_is_cache_wrapped_and_repeat_call_is_a_hit() -> None:
    underlying = _CountingEmbeddings()
    cache = RagasCacheBackend("ragas:embeddings", "text-embedding-3-small", mode="live")
    wrapped = LangchainEmbeddingsWrapper(underlying, cache=cache)
    first = wrapped.embed_query("what is the badge policy?")
    second = wrapped.embed_query("what is the badge policy?")
    assert first == second == [1.0, 2.0]
    assert underlying.calls == 1


@pytest.mark.usefixtures("socket_disabled")
def test_build_judge_embeddings_constructs_offline_with_sentence_transformers_absent() -> None:
    """Article VI.a / IX (Ninth amendment): the `calibration` group is not installed in this
    environment — proof by mechanism, matching test_provider_credentials.py's standard. If
    construction touched the real `HuggingFaceEmbeddings`, this would be an ImportError."""
    with pytest.raises(ImportError):
        import sentence_transformers  # type: ignore[import-not-found]  # noqa: F401
    embeddings = build_judge_embeddings()
    assert embeddings.cache is not None
