"""T3.4: RefusalCorrectness judges whether refuse/answer matches the golden expectation.
Reads from the committed evidence store only — a miss (generation or judge) skips cleanly,
same pattern as T1.11/T2.6, pending T3.8a's live pass.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from deepeval.metrics import BaseMetric

from app.models import AgentResult
from app.v1_naive import answer as v1_answer
from app.v2_fixed import answer as v2_answer
from conftest import assert_test
from evals.adapters.deepeval_adapter import to_llm_test_case
from evals.behavior.refusal import build_refusal_correctness_metric
from evals.cache.store import CacheMiss
from evals.golden.load import load_golden
from evals.golden.schema import GoldenCase

pytestmark = pytest.mark.deepeval

RELEVANT_CASES = [c for c in load_golden() if c.category in ("out-of-scope", "answerable")][:4]

# This slice is answerable-only — every out-of-scope case sorts after it — and all four score
# 1.00 for both variants, so GEval's default `threshold=0.5` gates nothing here: no result
# changes at any bar between 0 and 1. The calibrated 0.90 bar, and the three 0.00 scores that
# produce the whole 0.80-vs-1.00 separation, are enforced by tests/test_separation_contract.py.
# Kept narrow deliberately: this is a per-case smoke check on the judge, not the gate.


@pytest.mark.parametrize("variant_answer", [v1_answer, v2_answer])
@pytest.mark.parametrize("case", RELEVANT_CASES, ids=lambda c: c.question[:40])
def test_refusal_correctness(
    variant_answer: Callable[[str], AgentResult], case: GoldenCase
) -> None:
    try:
        result = variant_answer(case.question)
        test_case = to_llm_test_case(case, result)
        metrics: list[BaseMetric] = [build_refusal_correctness_metric()]
        assert_test(test_case, metrics)
    except CacheMiss:
        pytest.skip("cache not yet populated — T3.8a's live pass has not run")
