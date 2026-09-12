"""Deterministic rerank for v2 only — query-term coverage over BM25's own top-k.

v1 never reranks (FR-003); this is one of the three axes Article IV names.
"""

from __future__ import annotations

from app.models import RetrievedChunk
from app.retrieval import tokenize


def rerank(chunks: list[RetrievedChunk], query: str) -> list[RetrievedChunk]:
    """Reorder by count of distinct query terms present in the chunk, ties broken by the
    original BM25 score. Deterministic — no randomness, no model call.
    """
    query_terms = set(tokenize(query))

    def coverage(chunk: RetrievedChunk) -> int:
        return len(query_terms & set(tokenize(chunk.text)))

    return sorted(chunks, key=lambda c: (coverage(c), c.score), reverse=True)
