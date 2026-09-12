"""T2.6 — diagnostic only (not yet a gate): v1's `top_k=2`, no-rerank retrieval should recall
less of the reference answer's supporting context than v2's reranked `top_k=5`.
"""

from __future__ import annotations

import pytest
from ragas.dataset_schema import EvaluationResult

from evals.component.matrix import mean_score

pytestmark = pytest.mark.ragas


def test_v1_scores_worse_than_v2_on_context_recall(
    score_matrix: dict[str, EvaluationResult],
) -> None:
    v1 = mean_score(score_matrix["v1_naive"], "context_recall")
    v2 = mean_score(score_matrix["v2_fixed"], "context_recall")
    assert v1 < v2
