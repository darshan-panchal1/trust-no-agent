"""Article V's schema test: the committed `thresholds.yaml` and the code must agree
exactly — no threshold without a metric, no metric without a threshold. `GATED_METRICS`
(Article IV's gate table) is "the code" this asserts the file against.
"""

from __future__ import annotations

from evals.gate_policy import GATED_METRICS
from evals.thresholds import load_thresholds


def test_committed_thresholds_file_has_exactly_the_gated_metrics() -> None:
    assert set(load_thresholds().metrics) == set(GATED_METRICS)
