"""FR-043: has this run regressed against a previous one, beyond tolerance?

Tolerance is one top-level value in `thresholds.yaml` (FR-037), so Article V's one-file
rule still holds. The answer is an exit code, not a printed opinion — non-zero means a
gate moved the wrong way, and CI can act on it without parsing prose.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from evals.ops.run_summary import RunSummary
from evals.thresholds import load_thresholds


class Regressed(BaseModel):
    metric: str
    baseline: float
    candidate: float

    @property
    def drop(self) -> float:
        return self.baseline - self.candidate


def regressions(
    baseline: RunSummary, candidate: RunSummary, tolerance: float
) -> list[Regressed]:
    """Metrics whose corrected-variant score fell by more than `tolerance`.

    A metric present in the baseline and missing from the candidate counts as regressed:
    quietly dropping a gate must not read as an improvement.
    """
    candidate_rows = {row.metric: row for row in candidate.metrics}
    found: list[Regressed] = []
    for base in baseline.metrics:
        current = candidate_rows.get(base.metric)
        if current is None:
            found.append(Regressed(metric=base.metric, baseline=base.v2_mean, candidate=0.0))
        elif base.v2_mean - current.v2_mean > tolerance:
            found.append(
                Regressed(
                    metric=base.metric, baseline=base.v2_mean, candidate=current.v2_mean
                )
            )
    return found


def compare_runs(baseline_path: Path, candidate_path: Path) -> list[Regressed]:
    """Load two summaries and diff them against the calibrated tolerance."""
    tolerance = load_thresholds().comparison_tolerance
    baseline = RunSummary.load(baseline_path)
    candidate = RunSummary.load(candidate_path)
    return regressions(baseline, candidate, tolerance)
