"""Pure-Python BM25 retrieval (FR-007) — no embedding model, runs live on the viewer's
machine so the v1/v2 delta is genuinely observable, not replayed from a cache.
"""

from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    """Standard BM25 (k1=1.5, b=0.75) over a fixed list of chunks."""

    def __init__(self, chunk_texts: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.chunk_tokens = [tokenize(t) for t in chunk_texts]
        self.doc_lengths = [len(toks) for toks in self.chunk_tokens]
        self.n_docs = len(chunk_texts)
        self.avg_doc_length = sum(self.doc_lengths) / self.n_docs if self.n_docs else 0.0
        self.doc_freq: Counter[str] = Counter()
        for toks in self.chunk_tokens:
            for term in set(toks):
                self.doc_freq[term] += 1

    def _idf(self, term: str) -> float:
        df = self.doc_freq.get(term, 0)
        return math.log((self.n_docs - df + 0.5) / (df + 0.5) + 1)

    def score(self, query: str, doc_index: int) -> float:
        term_counts = Counter(self.chunk_tokens[doc_index])
        doc_len = self.doc_lengths[doc_index]
        total = 0.0
        for term in tokenize(query):
            tf = term_counts.get(term, 0)
            if tf == 0:
                continue
            numerator = tf * (self.k1 + 1)
            denom = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
            total += self._idf(term) * numerator / denom
        return total

    def top_k(self, query: str, k: int) -> list[int]:
        """Indices of the top-k chunks by score, highest first."""
        return sorted(range(self.n_docs), key=lambda i: self.score(query, i), reverse=True)[:k]
