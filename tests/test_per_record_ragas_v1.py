"""T019 (US1, SC-002): each Ragas evaluator, scoring a caller-shaped record, reproduces the
v1 path's per-case score from committed evidence — offline, no socket, $0.00."""

from __future__ import annotations

import math

import pytest

from evals.golden.load import load_golden
from tests.per_record_v1 import VARIANTS, answers, ragas_scores, record_for
from trustnoagent import evaluate

NAMES = ("faithfulness", "context_recall", "context_precision", "response_relevancy")
CASES = [(name, variant, index) for name in NAMES for variant in VARIANTS for index in (0, 1)]


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize(("name", "variant", "index"), CASES)
def test_reproduces_the_v1_per_case_score(name: str, variant: str, index: int) -> None:
    record = record_for(load_golden()[index], answers()[variant][index])
    expected = ragas_scores()[variant][name][index]
    result = evaluate(f"tna.ragas.{name}", record)
    if math.isnan(expected):  # v1 averages NaN away; the new path must name it instead
        assert (result.status, result.score) == ("invalid_output", None)
        return
    assert result.status == "ok", result.error
    assert result.score == pytest.approx(expected, abs=1e-9)
    assert result.fingerprint_provenance == "not_recorded"  # v1.0.0-era evidence
    assert result.tokens_in is None  # v1 Ragas entries record 0/0: unknown, never zero
    assert result.judge_fingerprint and result.raw["cache_keys"]
