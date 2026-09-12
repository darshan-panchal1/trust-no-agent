"""T1.5 acceptance: v1-style and v2-style retrieval configs produce different chunk sets,
each carrying its source filename (FR-007, FR-050).
"""

from __future__ import annotations

from app.chunking import chunk_text
from app.corpus_loader import list_documents, read_document
from app.models import RetrievedChunk
from app.rerank import rerank
from app.retrieval import BM25Index

QUERY = "international travel approval per diem director level"


def _build_chunks(chunk_size: int, overlap: int) -> list[tuple[str, str]]:
    pairs = []
    for filename in list_documents():
        content = read_document(filename)
        for piece in chunk_text(content, chunk_size=chunk_size, overlap=overlap):
            pairs.append((piece, filename))
    return pairs


def _retrieve(chunk_size: int, overlap: int, top_k: int) -> list[RetrievedChunk]:
    pairs = _build_chunks(chunk_size, overlap)
    index = BM25Index([text for text, _ in pairs])
    indices = index.top_k(QUERY, top_k)
    return [
        RetrievedChunk(text=pairs[i][0], source_document=pairs[i][1], score=index.score(QUERY, i))
        for i in indices
    ]


def test_v1_and_v2_configs_retrieve_different_chunk_sets() -> None:
    v1_chunks = _retrieve(chunk_size=200, overlap=0, top_k=2)
    v2_raw = _retrieve(chunk_size=800, overlap=200, top_k=5)
    v2_chunks = rerank(v2_raw, QUERY)

    assert len(v1_chunks) == 2
    assert len(v2_chunks) == 5
    v1_texts = {c.text for c in v1_chunks}
    v2_texts = {c.text for c in v2_chunks}
    assert v1_texts != v2_texts

    for chunk in v1_chunks + v2_chunks:
        assert chunk.source_document in list_documents()
