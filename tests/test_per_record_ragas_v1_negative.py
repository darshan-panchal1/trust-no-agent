"""T019 negative (Article XI): the per-record path shows `v1_naive` failing the calibrated bar
on the two gated Ragas metrics — a metric never shown to fail here is not evidence."""

from __future__ import annotations

import math

import pytest

from evals.golden.load import load_golden
from evals.thresholds import threshold_for
from tests.per_record_v1 import answers, ragas_scores, record_for
from trustnoagent import evaluate


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize("name", ["faithfulness", "context_recall"])
def test_the_worst_v1_answer_misses_the_calibrated_bar(name: str) -> None:
    scores = ragas_scores()["v1_naive"][name]
    worst = min((s, i) for i, s in enumerate(scores) if not math.isnan(s))[1]
    record = record_for(load_golden()[worst], answers()["v1_naive"][worst])
    result = evaluate(f"tna.ragas.{name}", record)
    assert result.status == "ok", result.error
    assert result.score is not None and result.score < threshold_for(name)


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize(("name", "case"), [("context_precision", 16), ("response_relevancy", 0)])
def test_a_v1_answer_scores_worse_than_v2_on_the_same_question(name: str, case: int) -> None:
    """Neither metric is gated, so there is no calibrated bar (Article IV) to miss — the
    negative signal is that v1 can score strictly worse than v2 on the identical question."""
    golden = load_golden()[case]
    v1_result = evaluate(f"tna.ragas.{name}", record_for(golden, answers()["v1_naive"][case]))
    v2_result = evaluate(f"tna.ragas.{name}", record_for(golden, answers()["v2_fixed"][case]))
    assert v1_result.status == "ok", v1_result.error
    assert v2_result.status == "ok", v2_result.error
    assert v1_result.score is not None and v2_result.score is not None
    assert v1_result.score < v2_result.score
