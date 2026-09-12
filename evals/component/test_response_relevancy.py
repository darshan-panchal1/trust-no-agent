"""T2.6 — diagnostic only. Unlike the three retrieval/prompt metrics, `response_relevancy`
scores whether an answer addresses the literal question, independent of grounding — it is
not in `docs/attribution.md`'s separating-metric table (Article IV), so no directional claim
is asserted here, only that both variants produce a valid score.
"""

from __future__ import annotations

import pytest
from ragas.dataset_schema import EvaluationResult

from evals.component.matrix import mean_score

pytestmark = pytest.mark.ragas


def test_response_relevancy_is_a_valid_score_for_both_variants(
    score_matrix: dict[str, EvaluationResult],
) -> None:
    v1 = mean_score(score_matrix["v1_naive"], "response_relevancy")
    v2 = mean_score(score_matrix["v2_fixed"], "response_relevancy")
    assert 0.0 <= v1 <= 1.0
    assert 0.0 <= v2 <= 1.0
