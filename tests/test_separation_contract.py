"""Article IV's separation contract, and the only place `pytest` reads the calibrated bars.

Every other gate in this suite runs on a library default (GEval's `threshold=0.5`); the
numbers in `evals/thresholds.yaml` were, until this module, read only by the ops surface.
Here they do real work: v1 must sit under every calibrated bar and v2 over it.

Lives in `tests/` because it needs both frameworks at once, and Article II forbids
`evals/component/` importing deepeval and `evals/behavior/` importing ragas.
"""

from __future__ import annotations

import pytest

from evals.cache.store import CacheMiss
from evals.gate_policy import GATED_METRICS
from evals.ops.observed import observed_means
from evals.ops.run_summary import MetricRow
from evals.thresholds import threshold_for

MIN_SEPARATING = 3  # Article IV: "at least three metrics must separate v1 from v2"
MEAN_FOR = {"v1_naive": lambda row: row.v1_mean, "v2_fixed": lambda row: row.v2_mean}

# Article IV: "v1 is never fixed." `strict=True` is the enforcement — if v1 ever cleared a
# bar the xpass fails the build, so this marker cannot rot into a silent allowance.
V1_STAYS_BROKEN = pytest.mark.xfail(strict=True, reason="Article IV: v1 is never fixed")
PARAMS = [
    pytest.param("v1_naive", name, marks=V1_STAYS_BROKEN) for name in GATED_METRICS
] + [pytest.param("v2_fixed", name) for name in GATED_METRICS]


@pytest.fixture(scope="session")
def separation_rows() -> list[MetricRow]:
    """One row per gated metric, offline from committed evidence — the same means
    `calibrate` derived the thresholds from, now checked back against the committed file."""
    try:
        means = observed_means()
    except CacheMiss as exc:
        pytest.skip(f"cache not yet populated — {exc}")
    return [
        MetricRow(metric=name, v1_mean=v1, v2_mean=v2, threshold=threshold_for(name))
        for name, (v1, v2) in means.items()
    ]


def test_separation_contract(separation_rows: list[MetricRow]) -> None:
    """Fails if fewer than three metrics clear the margin — if the demo stops
    demonstrating, CI goes red rather than the tutorial quietly losing its point."""
    separating = {row.metric for row in separation_rows if row.separates}
    assert separating == set(GATED_METRICS), f"only {separating} separate v1 from v2"
    assert len(separating) >= MIN_SEPARATING


@pytest.mark.parametrize(("variant", "metric"), PARAMS)
def test_variant_clears_the_calibrated_bar(
    variant: str, metric: str, separation_rows: list[MetricRow]
) -> None:
    row = next(r for r in separation_rows if r.metric == metric)
    mean, bar = MEAN_FOR[variant](row), threshold_for(metric)
    assert mean >= bar, f"{variant} {metric}={mean:.4f} is under the calibrated bar {bar:.4f}"
