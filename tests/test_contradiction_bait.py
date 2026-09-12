"""T1.10 acceptance (FR-051): v1's narrow retrieval surfaces the superseded expense policy;
v2's wider retrieval + rerank surfaces the superseding one. Pure retrieval — no model calls,
always offline. Questions come from the golden dataset itself, never a separate list, so the
two cannot drift apart.
"""

from __future__ import annotations

from app.context import build_context
from app.rerank import rerank
from evals.golden.load import load_golden

BAIT_QUESTIONS = [c.question for c in load_golden() if c.category == "contradiction-bait"]


def test_bait_category_is_non_empty() -> None:
    assert len(BAIT_QUESTIONS) >= 4


def test_v1_retrieves_the_superseded_document() -> None:
    for question in BAIT_QUESTIONS:
        contexts = build_context(question, chunk_size=200, overlap=0, top_k=2)
        sources = {c.source_document for c in contexts}
        assert "expenses-v1.md" in sources, f"v1 should retrieve the superseded doc for: {question}"


def test_v2_retrieves_the_superseding_document() -> None:
    for question in BAIT_QUESTIONS:
        raw = build_context(question, chunk_size=800, overlap=200, top_k=5)
        contexts = rerank(raw, question)
        sources = {c.source_document for c in contexts}
        assert "expenses-v2.md" in sources, f"v2 must retrieve the superseding doc: {question}"
