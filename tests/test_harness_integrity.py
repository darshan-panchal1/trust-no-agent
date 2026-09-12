"""T3.6 / Article XI: reproduces `copy_metrics()`'s `run_async=True` score-laundering bug
against the pinned `deepeval`, and asserts it is STILL PRESENT. Inverted on purpose — this
test PASSES while the bug exists. If it starts failing, upstream has fixed the defect:
delete `conftest.py`'s `run_async=False` wrapper and this test, and record the fixing
version in `CONSTITUTION.md`'s amendment history.

The reproduction metric is built via `evals.judge.build_score_laundering_probe` (Article
VI.a's one door), not a bare custom `BaseMetric` — deliberately, even though this metric
takes no judge model and needs no live call. Calls `deepeval.assert_test` directly, with
both `run_async` values, because reproducing the defect this file exists to catch is the
one thing `conftest.py`'s wrapper must never do.
"""

from __future__ import annotations

import pytest
from deepeval.evaluate import assert_test
from deepeval.test_case import LLMTestCase

from evals.judge import build_score_laundering_probe

pytestmark = pytest.mark.deepeval

CASE = LLMTestCase(input="q", actual_output="a")


def test_run_async_true_silently_launders_a_failing_score() -> None:
    """Constructed with score=0.1 < threshold=0.5 — a real, deliberate fail. The async
    rebuild replaces it with the class default (0.9) before scoring ever runs.
    """
    metric = build_score_laundering_probe(score=0.1, threshold=0.5)
    assert_test(CASE, [metric], run_async=True)  # no exception == the bug is still present


def test_run_async_false_catches_the_same_failure() -> None:
    """Proves the workaround (`conftest.py` forcing `run_async=False`) actually defends
    against the bug the test above reproduces.
    """
    metric = build_score_laundering_probe(score=0.1, threshold=0.5)
    with pytest.raises(AssertionError):
        assert_test(CASE, [metric], run_async=False)
