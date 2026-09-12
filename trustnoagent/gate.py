"""Article IV's calibrated bar, applied to one `RunSummary`: which gated metrics does
`v2_fixed` (the variant this repo ships) fail to clear. Adds no scoring of its own —
`evals.gate_policy.GATED_METRICS` already decides which metrics are gates at all, and
`MetricRow.threshold` already carries `threshold_for`'s value (Article V).

Deliberately not `MetricRow.separates`: that property additionally requires v1 to miss the
bar, which answers "does this repo still demonstrate its point," not "does the candidate
pass." A caller gating a build wants the latter.
"""

from __future__ import annotations

from evals.gate_policy import GATED_METRICS
from evals.ops.run_summary import RunSummary


def failing_metrics(summary: RunSummary) -> list[str]:
    """Names of every gated metric whose `v2_mean` misses its calibrated threshold."""
    rows = {row.metric: row for row in summary.metrics}
    return [
        name
        for name in GATED_METRICS
        if (row := rows[name]).threshold is not None and row.v2_mean < row.threshold
    ]
