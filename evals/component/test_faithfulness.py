"""T2.6 — diagnostic only (not yet a gate): v1's narrower, unranked retrieval should make
its answers less faithful to what was actually retrieved than v2's.
"""

from __future__ import annotations

import pytest
from ragas.dataset_schema import EvaluationResult

from evals.component.matrix import mean_score

pytestmark = pytest.mark.ragas


def test_v1_scores_worse_than_v2_on_faithfulness(
    score_matrix: dict[str, EvaluationResult],
) -> None:
    v1 = mean_score(score_matrix["v1_naive"], "faithfulness")
    v2 = mean_score(score_matrix["v2_fixed"], "faithfulness")
    assert v1 < v2
