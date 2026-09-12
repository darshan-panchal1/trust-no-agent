"""Build retrieval context for one question: chunk the corpus, run BM25, optionally rerank."""

from __future__ import annotations

from collections.abc import Callable

from app.chunking import chunk_text
from app.corpus_loader import list_documents, read_document
from app.models import RetrievedChunk
from app.retrieval import BM25Index

RerankFn = Callable[[list[RetrievedChunk], str], list[RetrievedChunk]]


def build_context(
    question: str,
    chunk_size: int,
    overlap: int,
    top_k: int,
    rerank_fn: RerankFn | None = None,
) -> list[RetrievedChunk]:
    pairs: list[tuple[str, str]] = []
    for filename in list_documents():
        for piece in chunk_text(read_document(filename), chunk_size, overlap):
            pairs.append((piece, filename))
    index = BM25Index([text for text, _ in pairs])
    top_indices = index.top_k(question, top_k)
    contexts = [
        RetrievedChunk(
            text=pairs[i][0], source_document=pairs[i][1], score=index.score(question, i)
        )
        for i in top_indices
    ]
    return rerank_fn(contexts, question) if rerank_fn else contexts
