"""FR-042/048: the deepeval half of `build_summary` — `RefusalCorrectness`'s one
`MetricRow` and its worst regressions. Scoring lives in `evals/ops/refusal_means.py`,
shared with `calibrate`; this module only attaches the threshold and builds regressions.
"""

from __future__ import annotations

from app.models import AgentResult
from evals.golden.schema import GoldenCase
from evals.ops.refusal_means import METRIC_NAME, mean, measured
from evals.ops.run_summary import MetricRow, Regression
from evals.thresholds import threshold_for


def refusal_row(
    cases: list[GoldenCase], answers: dict[str, list[AgentResult]]
) -> tuple[MetricRow, list[Regression]]:
    triples = measured(cases, answers)
    row = MetricRow(
        metric=METRIC_NAME,
        v1_mean=mean(triples["v1_naive"]),
        v2_mean=mean(triples["v2_fixed"]),
        threshold=threshold_for(METRIC_NAME),
    )
    regressions = [
        Regression(
            metric=METRIC_NAME, question=case.question, variant=variant, score=score,
            answer=answer.answer,
        )
        for variant, variant_triples in triples.items()
        for case, answer, score in variant_triples
    ]
    return row, regressions
