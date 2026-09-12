"""T4.4 acceptance: identical runs report nothing; a perturbed score regresses (FR-043)."""

from __future__ import annotations

import datetime

import pytest

from evals.ops.compare import regressions
from evals.ops.run_summary import MetricRow, RunSummary

TOLERANCE = 0.02


def _summary(faithfulness: float) -> RunSummary:
    return RunSummary(
        generated_at=datetime.datetime(2026, 9, 7, 12, 0, tzinfo=datetime.UTC),
        metrics=[
            MetricRow(metric="faithfulness", v1_mean=0.40, v2_mean=faithfulness, threshold=0.65)
        ],
        worst_regressions=[],
        costs=[],
    )


def test_identical_runs_report_no_regression() -> None:
    assert regressions(_summary(0.88), _summary(0.88), TOLERANCE) == []


def test_a_drop_beyond_tolerance_is_a_regression() -> None:
    found = regressions(_summary(0.88), _summary(0.80), TOLERANCE)
    assert [item.metric for item in found] == ["faithfulness"]
    assert found[0].drop == pytest.approx(0.08)


def test_a_drop_within_tolerance_is_not_a_regression() -> None:
    assert regressions(_summary(0.88), _summary(0.87), TOLERANCE) == []


def test_an_improvement_is_not_a_regression() -> None:
    assert regressions(_summary(0.80), _summary(0.90), TOLERANCE) == []


def test_a_metric_missing_from_the_candidate_counts_as_regressed() -> None:
    """Quietly dropping a gate must not read as an improvement."""
    candidate = _summary(0.88)
    candidate.metrics = []
    found = regressions(_summary(0.88), candidate, TOLERANCE)
    assert [item.metric for item in found] == ["faithfulness"]
