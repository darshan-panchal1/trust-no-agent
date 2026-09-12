"""Cached embeddings for `ResponseRelevancy` (FR-017).

`ResponseRelevancy` calls `embed_query`/`embed_documents` — LangChain-interface names the
modern `embedding_factory()` embeddings type does not implement (docs/api-notes.md V3.4).
The legacy `LangchainEmbeddingsWrapper` is required, deprecation warning and all.

Ninth amendment: local `sentence-transformers` model, not OpenAI. Its `__init__` imports
`sentence_transformers` and loads real model weights immediately (docs/api-notes.md V7.1) —
stronger than Groq's eager credential check, so VI.a's no-real-construction-offline rule
extends here too: the offline path never even imports the real class.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.embeddings import Embeddings
from ragas.embeddings.base import BaseRagasEmbeddings, LangchainEmbeddingsWrapper

from evals.cache.ragas_backend import RagasCacheBackend

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class _NeverCalledEmbeddings(Embeddings):
    def embed_query(self, text: str) -> list[float]:
        raise AssertionError("offline embeddings stub must never reach a real model")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise AssertionError("offline embeddings stub must never reach a real model")


def build_judge_embeddings(mode: Literal["offline", "live"] = "offline") -> BaseRagasEmbeddings:
    """Cached embeddings for the judge, keyed under `ragas:embeddings`.

    Offline mode never constructs — or imports — the real `HuggingFaceEmbeddings`: package
    absence on a viewer's machine (Article IX, `calibration` group) would raise `ImportError`,
    and even installed, construction loads model weights, not something an offline stub may
    ever trigger. `RagasCacheBackend` blocks the call on a miss well before either matters.
    """
    cache = RagasCacheBackend("ragas:embeddings", EMBEDDING_MODEL, mode=mode)
    embeddings: Embeddings = _NeverCalledEmbeddings()
    if mode == "live":
        from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)  # only ever here — VI.a
    wrapper: BaseRagasEmbeddings = LangchainEmbeddingsWrapper(embeddings, cache=cache)
    return wrapper
